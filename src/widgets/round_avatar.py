# coding=utf-8
"""圆形头像：从 URL 异步加载，本地缓存按小时刷新，加载中显示不确定进度环。"""

import os
import time

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QPainter, QPainterPath, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import QLabel, QStackedLayout, QWidget

from qfluentwidgets import FluentIcon as FIF, IndeterminateProgressRing

from src.utils.helpers import get_app_data_dir

# 头像缓存有效期（秒）：1 小时
AVATAR_TTL = 3600
# 下载超时（毫秒）
DOWNLOAD_TIMEOUT_MS = 15000


def _round_pixmap(pixmap, size):
    """将任意 pixmap 裁剪为 size x size 的圆形。"""
    scaled = pixmap.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation)
    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, scaled)
    painter.end()
    return result


class RoundAvatar(QWidget):
    """圆形头像控件。

    加载策略：本地缓存未过期则直接显示；过期后先显示旧缓存，
    再异步下载刷新；无缓存或下载失败时显示占位图标。
    """

    def __init__(self, size, url, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._size = size
        self._url = url

        stack = QStackedLayout(self)
        stack.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel(self)
        self._label.setFixedSize(size, size)
        stack.addWidget(self._label)

        # 未加载完成时显示的「不确定进度环」
        self._ring = IndeterminateProgressRing(self)
        self._ring.setFixedSize(int(size * 0.5), int(size * 0.5))
        stack.addWidget(self._ring)
        stack.setCurrentWidget(self._ring)

        self._load_avatar()

    # ---------- 加载流程 ----------

    def _load_avatar(self):
        cache_file = os.path.join(get_app_data_dir(), 'avatar_cache.png')
        if os.path.exists(cache_file) and time.time() - os.path.getmtime(cache_file) < AVATAR_TTL:
            # 缓存未过期，直接使用
            self._show_pixmap(QPixmap(cache_file))
            return
        if os.path.exists(cache_file):
            # 缓存过期：先显示旧头像，后台刷新
            self._show_pixmap(QPixmap(cache_file))

        # 异步下载新头像（不阻塞 UI）
        self._net = QNetworkAccessManager(self)
        request = QNetworkRequest(QUrl(self._url))
        request.setTransferTimeout(DOWNLOAD_TIMEOUT_MS)
        self._net.finished.connect(self._on_downloaded)
        self._net.get(request)

    def _on_downloaded(self, reply):
        ok = False
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                data = bytes(reply.readAll())
                pixmap = QPixmap()
                if pixmap.loadFromData(data):
                    cache_file = os.path.join(get_app_data_dir(), 'avatar_cache.png')
                    try:
                        with open(cache_file, 'wb') as f:
                            f.write(data)
                    except OSError:
                        pass
                    self._show_pixmap(pixmap)
                    ok = True
        finally:
            if not ok:
                # 下载失败且无可用缓存：显示占位图标
                self._show_placeholder()
            reply.deleteLater()

    # ---------- 显示 ----------

    def _show_pixmap(self, pixmap):
        if pixmap.isNull():
            self._show_placeholder()
            return
        self._label.setPixmap(_round_pixmap(pixmap, self._size))
        self._stack_set_image()

    def _show_placeholder(self):
        placeholder = FIF.PERSON.icon().pixmap(self._size, self._size)
        self._label.setPixmap(_round_pixmap(placeholder, self._size))
        self._stack_set_image()

    def _stack_set_image(self):
        self._ring.stop()
        self._ring.hide()
        self._label.show()
        stack = self.layout()
        if isinstance(stack, QStackedLayout):
            stack.setCurrentWidget(self._label)
