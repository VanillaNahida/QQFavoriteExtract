# coding=utf-8
"""右侧详情面板：大图/动图播放 + 属性信息。"""

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from qfluentwidgets import BodyLabel, StrongBodyLabel

from src.utils.pillow_gif_player import PillowGifPlayer

PREVIEW_SIZE = 240


class EmojiDetailWidget(QWidget):
    """表情详细预览面板：常驻可折叠，点选即预览动图/大图。"""

    collapsedChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._player = PillowGifPlayer(self)
        self._collapsed = False

        self.setFixedWidth(300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 标题行
        header = QHBoxLayout()
        self.titleLabel = StrongBodyLabel('表情详细预览')
        header.addWidget(self.titleLabel)
        header.addStretch()
        layout.addLayout(header)

        # 大图预览
        self.previewLabel = QLabel()
        self.previewLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.previewLabel.setFixedSize(PREVIEW_SIZE, PREVIEW_SIZE)
        self.previewLabel.setStyleSheet('background: transparent;')
        layout.addWidget(self.previewLabel, alignment=Qt.AlignmentFlag.AlignCenter)
        self._player.attach(self.previewLabel)
        self._player.set_target_size(QSize(PREVIEW_SIZE, PREVIEW_SIZE))

        # 属性信息
        self.infoLabel = BodyLabel('未选中表情')
        self.infoLabel.setWordWrap(True)
        self.infoLabel.setTextFormat(Qt.TextFormat.RichText)
        self.infoLabel.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.infoLabel)

        layout.addStretch()

    # ---------- 折叠 ----------

    def set_collapsed(self, collapsed, persist=True):
        self._collapsed = collapsed
        # 面板整体显隐由工作台的卡片宽度动画控制，这里不再直接隐藏自身，
        # 否则动画期间内容会瞬间消失并导致卡片宽度动画失真。
        if persist:
            self.collapsedChanged.emit(collapsed)

    def is_collapsed(self):
        return self._collapsed

    # ---------- 播放控制 ----------

    def stop_playback(self):
        self._player.clear()

    def show_placeholder(self, text='未选中表情'):
        self.stop_playback()
        self.previewLabel.setText('')
        self.set_info(text)

    def play_bytes(self, data):
        """用内存数据播放动图（marketface 解密结果，Pillow 帧驱动，避开 Qt 解码器）。"""
        self.stop_playback()
        if not self._player.load(data):
            self.previewLabel.setText('图片加载失败')
            return
        self._player.play()

    def play_file(self, path):
        """从文件播放动图（GIF / 转换后的临时 GIF）。"""
        self.stop_playback()
        try:
            with open(path, 'rb') as f:
                data = f.read()
        except Exception:
            self.previewLabel.setText('图片加载失败')
            return
        if not self._player.load(data):
            self.previewLabel.setText('图片加载失败')
            return
        self._player.play()

    def show_image(self, path):
        """显示静态大图。"""
        self.stop_playback()
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.previewLabel.setText('图片加载失败')
            return
        scaled = pixmap.scaled(
            PREVIEW_SIZE, PREVIEW_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.previewLabel.setPixmap(scaled)

    def set_info(self, html):
        self.infoLabel.setText(html)
