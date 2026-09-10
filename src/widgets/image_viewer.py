# coding=utf-8
"""大图查看窗口：双击预览图打开，支持 GIF 动图播放与静态大图等比缩放显示。"""

import os

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout

from qfluentwidgets import FluentIcon as FIF, TransparentToolButton

from src.utils.pillow_gif_player import PillowGifPlayer

# 兜底上限：主窗口不可用（找不到）时使用；正常情况以主窗口尺寸为上限
MAX_SIZE = QSize(1000, 700)
MIN_DIALOG = QSize(360, 300)
# 内容区 = 标签区 + 左右边距(16*2) + 头部按钮行(32) + 间距(10) + 上下边距(12*2)
CONTENT_EXTRA_W = 32
CONTENT_EXTRA_H = 32 + 10 + 12 * 2


class LargeImageViewer(QDialog):
    """表情大图查看窗口（独立对话框，Esc / 右上角关闭按钮退出）。"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._player = PillowGifPlayer(self)
        self._pixmap = None          # 原始静态图片，窗口尺寸变化时据此重新适配

        self.setWindowTitle('表情大图预览（按ESC关闭）')
        self.resize(720, 540)
        self.setMinimumSize(MIN_DIALOG)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # 右上角关闭按钮
        header = QHBoxLayout()
        header.addStretch()
        self.close_button = TransparentToolButton(FIF.CLOSE, self)
        self.close_button.setFixedSize(32, 32)
        self.close_button.setToolTip('关闭 (Esc)')
        self.close_button.clicked.connect(self.close)
        header.addWidget(self.close_button)
        layout.addLayout(header)

        self.preview_label = QLabel(self)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(300, 200)
        self.preview_label.setText('加载中…')
        layout.addWidget(self.preview_label, 1)
        self._player.attach(self.preview_label)

    # ---------- 事件 ----------

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)

    def closeEvent(self, e):
        self._stop()
        super().closeEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # 布局在事件循环中才完成重新分配，延迟到下一轮再按标签实际尺寸适配
        QTimer.singleShot(0, self._refresh_preview_size)

    # ---------- 播放控制 ----------

    def _stop(self):
        self._player.clear()
        self._pixmap = None

    def show_payload(self, payload):
        """显示 DetailLoaderWorker 返回的 payload（'data' 内存解密 / 'path' 文件路径）。"""
        self._stop()
        self.preview_label.setText('')
        if not payload:
            self.preview_label.setText('预览失败')
            return
        if payload.get('kind') == 'data':
            self._play_bytes(payload['data'])
            return
        path = payload.get('path') or ''
        ext = (payload.get('ext') or os.path.splitext(path)[1].lstrip('.')).lower()
        if ext == 'gif':
            self._play_file(path)
        else:
            self._show_image(path)

    def _play_bytes(self, data):
        if not self._player.load(data):
            self.preview_label.setText('图片加载失败')
            return
        self._fit_to_image(self._player.current_source_size())
        self._player.play()
        QTimer.singleShot(0, self._refresh_preview_size)

    def _play_file(self, path):
        try:
            with open(path, 'rb') as f:
                data = f.read()
        except Exception:
            self.preview_label.setText('图片加载失败')
            return
        if not self._player.load(data):
            self.preview_label.setText('图片加载失败')
            return
        self._fit_to_image(self._player.current_source_size())
        self._player.play()
        QTimer.singleShot(0, self._refresh_preview_size)

    def _show_image(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.preview_label.setText('图片加载失败')
            return
        self._pixmap = pixmap
        self._fit_to_image(pixmap.size())
        self._refresh_preview_size()

    def _fit_to_image(self, img_size):
        """按图片宽高比调整窗口内容区尺寸，让图片完整显示而不被裁剪。"""
        if not img_size.isValid() or img_size.width() <= 0 or img_size.height() <= 0:
            return
        # 宽高上限：主窗口可用时不超过主窗口（各留 80px 边距），否则退回常量上限
        max_w, max_h = MAX_SIZE.width(), MAX_SIZE.height()
        main = self._main_window()
        if main is not None:
            max_w = min(max_w, main.width() - 80)
            max_h = min(max_h, main.height() - 80)
        screen_geo = self.screen().availableGeometry() if self.screen() else None
        if screen_geo:
            max_w = min(max_w, screen_geo.width() - 80)
            max_h = min(max_h, screen_geo.height() - 80)
        # 下限兜底：不能小于最小窗口尺寸
        max_w = max(max_w, MIN_DIALOG.width())
        max_h = max(max_h, MIN_DIALOG.height())
        ratio = img_size.width() / img_size.height()
        if ratio >= 1:
            w = max_w
            h = int(max_w / ratio)
            if h > max_h:
                h = max_h
                w = int(max_h * ratio)
        else:
            h = max_h
            w = int(max_h * ratio)
            if w > max_w:
                w = max_w
                h = int(max_w / ratio)
        # 窗口总尺寸上限与主窗口一致，用户也无法手动拖大
        self.setMaximumSize(max_w + CONTENT_EXTRA_W, max_h + CONTENT_EXTRA_H)
        self.resize(max(w + CONTENT_EXTRA_W, MIN_DIALOG.width()),
                    max(h + CONTENT_EXTRA_H, MIN_DIALOG.height()))

    def _main_window(self):
        """沿 parent 链向上查找主窗口（LargeImageViewer 自身是独立 QDialog 窗口）。"""
        w = self.parent()
        while w is not None:
            if w.metaObject().className() == 'MainWindow':
                return w
            w = w.parent()
        return None

    def _refresh_preview_size(self):
        """窗口尺寸变化后，让图片/动图重新适配标签实际尺寸，避免显示不全。"""
        target = self.preview_label.size()
        if target.width() < 20 or target.height() < 20:
            return
        if self._player.is_active:
            self._player.set_target_size(target)
            self._player.refresh()
        elif self._pixmap is not None:
            scaled = self._pixmap.scaled(
                target, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self.preview_label.setPixmap(scaled)
