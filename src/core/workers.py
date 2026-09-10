# coding=utf-8
"""QThread 工作线程层。

设计原则：
- 每个耗时任务 = Worker(QObject) + 独立 QThread（moveToThread 模式）
- 工作线程只发信号，绝不碰控件；UI 线程只接收信号、更新控件
- 代际令牌（generation）：切换用户/分类/重新扫描时递增，旧 worker 结果带旧令牌被 UI 丢弃
- 取消标志：切换时置 cancel，worker 循环内检查并提前退出
"""

import os

from PyQt6.QtCore import QObject, QRect, QThread, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QImage, QImageReader, QPainter

from src.core.emoji_converter import convert_apng_to_gif, is_apng_file
from src.core.emoji_scanner import ScanCancelled, get_actual_extension, scan_emoji_folder
from src.core.exporter import export_emoji_files
from src.core.marketface_handler import load_marketface_first_frame, recover_marketface_preview
from src.utils.pillow_gif_player import pil_to_qimage

THUMBNAIL_SIZE = 100
BADGE_RECT = (55, 84, 45, 16)


class WorkerBase(QObject):
    """工作线程基类：提供取消标志。"""

    def __init__(self, generation):
        super().__init__()
        self.generation = generation
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    @property
    def is_cancelled(self):
        return self._cancelled


class ScanWorker(WorkerBase):
    """扫描表情文件（遍历/魔数校验/评分全在工作线程）。"""

    progress = pyqtSignal(int, int)          # (current, total)
    finished = pyqtSignal(int, list)         # (generation, paths)

    def __init__(self, generation, emoji_path, folder_key):
        super().__init__(generation)
        self.emoji_path = emoji_path
        self.folder_key = folder_key

    def run(self):
        try:
            paths = scan_emoji_folder(
                self.emoji_path,
                self.folder_key,
                progress_callback=self._on_progress,
                cancel_check=lambda: self._cancelled,
            )
            self.finished.emit(self.generation, paths)
        except ScanCancelled:
            self.finished.emit(self.generation, [])

    def _on_progress(self, current, total):
        self.progress.emit(current, total)


class PreviewLoaderWorker(WorkerBase):
    """批量解码预览图。工作线程内解码 QImage 并缩放，UI 线程再转 QPixmap。"""

    batchReady = pyqtSignal(int, int, list)  # (generation, startIdx, items)
    finished = pyqtSignal(int)               # (generation)

    def __init__(self, generation, paths, is_marketface, start_idx, batch_size):
        super().__init__(generation)
        self.paths = paths
        self.is_marketface = is_marketface
        self.start_idx = start_idx
        self.batch_size = batch_size

    def run(self):
        items = []
        for i, path in enumerate(self.paths):
            if self._cancelled:
                break
            item = self._load_one(path)
            if item:
                items.append(item)
        self.batchReady.emit(self.generation, self.start_idx, items)
        self.finished.emit(self.generation)

    def _load_one(self, path):
        """返回 {path, image, ext, is_animated, frame_count} 或 None"""
        try:
            reader = QImageReader()
            if self.is_marketface:
                # marketface 数据交给 Qt 的 GIF 解码器会偶发崩溃（未初始化内存访问），
                # 一律改用 Pillow 提取首帧，再由 UI 线程转 QPixmap。
                data = recover_marketface_preview(path)
                if not data:
                    return None
                ext = "gif"
                pil, frame_count = load_marketface_first_frame(data)
                if pil is None:
                    return None
                image = pil_to_qimage(pil)
            else:
                ext = get_actual_extension(path)
                if not ext:
                    return None
                reader.setFileName(path)

                if not reader.canRead():
                    return None

                frame_count = reader.imageCount() if reader.supportsAnimation() else 1
                image = reader.read()
                if image.isNull():
                    return None

            is_animated = frame_count > 1

            #  核心内存优化：立即缩放，释放原始大图在内存中的占用
            scaled = image.scaled(
                THUMBNAIL_SIZE, THUMBNAIL_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            # 将非正方形缩略图居中绘制在正方形画布上
            square = QImage(THUMBNAIL_SIZE, THUMBNAIL_SIZE, QImage.Format.Format_ARGB32)
            square.fill(QColor(0, 0, 0, 0))  # 透明背景
            p = QPainter(square)
            x = (THUMBNAIL_SIZE - scaled.width()) // 2
            y = (THUMBNAIL_SIZE - scaled.height()) // 2
            p.drawImage(x, y, scaled)

            # 如果是动图，在缩略图上画角标
            if is_animated:
                badge_text = "GIF" if ext.lower() == "gif" else ext.upper()
                rect = QRect(*BADGE_RECT)
                p.fillRect(rect, QColor(0, 0, 0, 160))
                p.setPen(QColor(255, 255, 255))
                font = QFont("Arial", 8, QFont.Weight.Bold)
                p.setFont(font)
                p.drawText(rect, Qt.AlignmentFlag.AlignCenter, badge_text)
            p.end()

            return {
                'path': path,
                'image': square,
                'ext': ext,
                'is_animated': is_animated,
                'frame_count': frame_count,
            }
        except Exception:
            return None


class ExportWorker(WorkerBase):
    """批量导出表情（marketface 解密 / APNG 转 GIF / 复制）。"""

    progress = pyqtSignal(int, int)          # (current, total)
    log = pyqtSignal(str)                    # 导出明细日志（已节流）
    finished = pyqtSignal(int, int, str)     # (generation, successCount, outputDir)

    def __init__(self, generation, file_paths, dst_dir, folder_key):
        super().__init__(generation)
        self.file_paths = file_paths
        self.dst_dir = dst_dir
        self.folder_key = folder_key
        self._log_index = 0

    def run(self):
        success = export_emoji_files(
            self.file_paths,
            self.dst_dir,
            self.folder_key,
            log_callback=self._on_log,
            progress_callback=self._on_progress,
            cancel_check=lambda: self._cancelled,
        )
        self.finished.emit(self.generation, success, self.dst_dir)

    def _on_progress(self, current, total):
        self.progress.emit(current, total)

    def _on_log(self, message):
        # 节流推送：跳过/失败类日志全量推送，常规日志每 5 条推一次
        self._log_index += 1
        if '跳过' in message or self._log_index % 5 == 0:
            self.log.emit(message)


class SortWorker(WorkerBase):
    """惰性读取文件元数据（os.stat + 魔数）并排序，排序重渲染前的重量操作。"""

    finished = pyqtSignal(int, list)          # (generation, entries)

    def __init__(self, generation, entries, sort_key, sort_order, is_marketface):
        super().__init__(generation)
        self.entries = entries
        self.sort_key = sort_key
        self.sort_order = sort_order
        self.is_marketface = is_marketface

    def run(self):
        for entry in self.entries:
            if self._cancelled:
                break
            self._fill_metadata(entry)
        if not self._cancelled:
            self._sort()
        self.finished.emit(self.generation, self.entries)

    def _fill_metadata(self, entry):
        try:
            stat = os.stat(entry.path)
            entry.size = stat.st_size
            entry.mtime = stat.st_mtime
        except Exception:
            pass
        if not entry.ext:
            if self.is_marketface:
                entry.ext = 'gif'
            else:
                ext = get_actual_extension(entry.path)
                entry.ext = ext or ''
        # 类型排序需要区分 APNG，仅对 png 做一次轻量 chunk 探测
        if (entry.ext or '').lower() == 'png':
            entry.is_apng = is_apng_file(entry.path)

    def _sort(self):
        key = self.sort_key
        if key == 'name':
            self.entries.sort(key=lambda e: os.path.basename(e.path).lower())
        elif key == 'size':
            self.entries.sort(key=lambda e: e.size)
        elif key == 'mtime':
            self.entries.sort(key=lambda e: e.mtime)
        elif key == 'type':
            self.entries.sort(key=lambda e: self._type_rank(e))
        if self.sort_order == 'desc':
            self.entries.reverse()

    @staticmethod
    def _type_rank(entry):
        ext = (entry.ext or '').lower()
        if entry.is_apng or ext == 'apng':
            return 0
        if ext == 'gif':
            return 1
        if ext == 'png':
            return 2
        if ext == 'jpg':
            return 3
        return 4


class ConvertWorker(WorkerBase):
    """详情页 APNG -> GIF 一次性转换。"""

    finished = pyqtSignal(int, str)          # (generation, gifPath 或 '')

    def __init__(self, generation, apng_path):
        super().__init__(generation)
        self.apng_path = apng_path

    def run(self):
        gif_path = convert_apng_to_gif(self.apng_path)
        self.finished.emit(self.generation, gif_path or '')


class DetailLoaderWorker(WorkerBase):
    """详情面板预览数据加载：marketface 内存解密 / APNG 转临时 GIF / 常规路径。"""

    finished = pyqtSignal(int, dict)         # (generation, payload 或 None)

    def __init__(self, generation, path, is_marketface):
        super().__init__(generation)
        self.path = path
        self.is_marketface = is_marketface

    def run(self):
        payload = None
        try:
            if self.is_marketface:
                data = recover_marketface_preview(self.path)
                if data:
                    payload = {'kind': 'data', 'data': data, 'ext': 'gif'}
            else:
                ext = get_actual_extension(self.path)
                if ext == 'png' and is_apng_file(self.path):
                    gif_path = convert_apng_to_gif(self.path)
                    if gif_path:
                        payload = {'kind': 'path', 'path': gif_path, 'ext': 'gif'}
                elif ext:
                    payload = {'kind': 'path', 'path': self.path, 'ext': ext}
        except Exception:
            payload = None
        self.finished.emit(self.generation, payload)


def start_worker(worker, owner, finished_slot=None):
    """
    在独立线程中启动一个 worker。

    :param worker: WorkerBase 子类实例
    :param owner: 用于持有线程引用的父对象（防止线程被垃圾回收）
    :param finished_slot: 可选，额外连接 finished 信号（用于清理资源）
    :return: QThread 实例
    """
    thread = QThread()
    thread.setObjectName(f"{worker.__class__.__name__}Thread")
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)

    # 注意：不能 connect(thread.deleteLater)——
    # 线程 C++ 对象被 Qt 删除后，Python 侧 worker._thread 仍是悬垂引用，
    # 窗口关闭时调用 isRunning()/quit() 会访问已释放内存导致崩溃。
    # 因此线程生命周期改由 owner 的 _live_threads 持有，结束时安全移除。
    thread.setParent(owner)

    live_threads = getattr(owner, '_live_threads', None)
    if live_threads is None:
        live_threads = {}
        owner._live_threads = live_threads

    worker._thread = thread
    live_threads[worker] = thread

    def _on_thread_finished():
        worker._thread = None
        live_threads.pop(worker, None)

    thread.finished.connect(_on_thread_finished)
    thread.start()
    return thread
