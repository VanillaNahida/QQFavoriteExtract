# coding=utf-8
"""基于 Pillow 帧 + QTimer 的 GIF 播放器。

marketface 恢复出的部分 GIF 数据会让 Qt 的 GIF 解码器（QMovie / QImageReader）
偶发崩溃（未初始化内存访问，0xC0000005），Pillow 却能正常解析。因此所有动图
播放一律基于 Pillow 帧驱动，不经过 QMovie / QImageReader。
"""

from PyQt6.QtCore import QObject, QSize, QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap

from src.core.marketface_handler import load_marketface_frames


def pil_to_qimage(pil_image) -> QImage:
    """PIL RGBA Image -> QImage（RGBA8888）。返回副本，脱离 PIL 对象独立生命周期。"""
    data = pil_image.tobytes('raw', 'RGBA')
    return QImage(data, pil_image.width, pil_image.height, pil_image.width * 4,
                  QImage.Format.Format_RGBA8888).copy()


class PillowGifPlayer(QObject):
    """用 Pillow 解码 GIF 全部帧并由 QTimer 驱动循环播放。

    用法：
        player = PillowGifPlayer(widget)
        player.attach(label)                    # 绑定显示 QLabel
        player.set_target_size(QSize(240, 240)) # 可选：限制显示尺寸
        if player.load(data):                   # data 为 GIF 字节
            player.play()
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._frames = []          # [(QImage, 时长ms)]
        self._scaled_cache = []    # 按当前目标尺寸缓存的 QPixmap，None 表示未缩放
        self._index = 0
        self._target = QSize()     # 目标显示尺寸；无效尺寸表示不缩放
        self._label = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._show_next)

    # ---------- 生命周期 ----------

    def load(self, data: bytes) -> bool:
        """加载 GIF 字节数据并重置播放状态；成功返回 True。"""
        self.stop()
        pil_frames = load_marketface_frames(data)
        if not pil_frames:
            return False
        self._frames = [(pil_to_qimage(pil), duration) for pil, duration in pil_frames]
        self._scaled_cache = [None] * len(self._frames)
        self._index = 0
        return True

    def attach(self, label):
        """绑定显示用 QLabel（播放时直接 setPixmap）。"""
        self._label = label

    def set_target_size(self, size: QSize):
        """设置目标显示尺寸（KeepAspectRatio 缩放）；变化时重建缩放缓存。"""
        if size == self._target:
            return
        self._target = QSize(size)
        self._scaled_cache = [None] * len(self._frames)

    def play(self):
        """开始循环播放。"""
        if not self._frames or self._label is None:
            return
        self._show_current()
        self._timer.start(self._frames[self._index][1])

    def stop(self):
        """停止播放并释放帧内存。"""
        self._timer.stop()
        self._frames = []
        self._scaled_cache = []
        self._index = 0

    def clear(self):
        """停止播放并清空标签内容。"""
        self.stop()
        if self._label is not None:
            self._label.clear()

    def refresh(self):
        """按当前目标尺寸重绘当前帧（窗口尺寸变化后调用）。"""
        if self._frames:
            self._show_current()

    @property
    def is_active(self) -> bool:
        return bool(self._frames)

    def current_source_size(self) -> QSize:
        """当前帧原始尺寸（用于窗口尺寸适配）。"""
        if self._frames:
            return self._frames[self._index][0].size()
        return QSize()

    # ---------- 内部 ----------

    def _show_next(self):
        self._index = (self._index + 1) % len(self._frames)
        self._timer.start(self._frames[self._index][1])
        self._show_current()

    def _show_current(self):
        if self._label is None or not self._frames:
            return
        qimg, _ = self._frames[self._index]
        if (self._target.isValid() and self._target.width() > 0
                and self._target.height() > 0):
            scaled = self._scaled_cache[self._index]
            if scaled is None:
                scaled = QPixmap.fromImage(qimg.scaled(
                    self._target, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation))
                self._scaled_cache[self._index] = scaled
            self._label.setPixmap(scaled)
        else:
            self._label.setPixmap(QPixmap.fromImage(qimg))
