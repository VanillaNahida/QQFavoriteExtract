# coding=utf-8
"""右侧详情面板：大图/动图播放 + 属性信息。"""

from PyQt6.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from qfluentwidgets import BodyLabel, CardWidget, StrongBodyLabel, isDarkTheme

from src.utils.pillow_gif_player import PillowGifPlayer

PREVIEW_SIZE = 240


class DetailPanelCard(CardWidget):
    """表情详细预览悬浮卡片：背景改为高不透明度。

    qfluentwidgets 原生 CardWidget 深色模式背景为 rgba(255,255,255,13)，
    几乎全透明，悬浮在网格上时文字可读性差。此处提高不透明度，
    深色模式用近实底深灰，浅色模式用近实底白，文字更易读。
    """

    def _normalBackgroundColor(self):
        return QColor(40, 40, 40, 245) if isDarkTheme() else QColor(255, 255, 255, 245)

    def _hoverBackgroundColor(self):
        return self._normalBackgroundColor()

    def _pressedBackgroundColor(self):
        return self._normalBackgroundColor()


class EmojiDetailWidget(QWidget):
    """表情详细预览面板：常驻可折叠，点选即预览动图/大图。"""

    collapsedChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._player = PillowGifPlayer(self)
        self._collapsed = False
        self._static_pixmap = None   # 原始静态大图，面板尺寸变化时据此重新缩放

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

        # 大图预览：占据 header 与信息行之间的可用空间，随面板高度缩放（最大 240）
        self.previewLabel = QLabel()
        self.previewLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.previewLabel.setMinimumSize(1, 1)
        self.previewLabel.setMaximumSize(PREVIEW_SIZE, PREVIEW_SIZE)
        self.previewLabel.setStyleSheet('background: transparent;')
        layout.addWidget(self.previewLabel, 1)
        self._player.attach(self.previewLabel)

        # 属性信息：自动换行，长文件名等连续文本由工作台注入 <wbr> 断行机会
        self.infoLabel = BodyLabel('未选中表情')
        self.infoLabel.setWordWrap(True)
        self.infoLabel.setTextFormat(Qt.TextFormat.RichText)
        self.infoLabel.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.infoLabel)

        layout.addStretch()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # 面板高度变化（配置区展开/收起、窗口缩放）后，图片需跟随缩放
        QTimer.singleShot(0, self._adapt_preview_size)

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
        self._static_pixmap = None

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
        QTimer.singleShot(0, self._adapt_preview_size)

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
        QTimer.singleShot(0, self._adapt_preview_size)

    def show_image(self, path):
        """显示静态大图（保留原图，面板尺寸变化时重新等比缩放）。"""
        self.stop_playback()
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.previewLabel.setText('图片加载失败')
            return
        self._static_pixmap = pixmap
        QTimer.singleShot(0, self._adapt_preview_size)

    def _adapt_preview_size(self):
        """按标签当前可用空间重新缩放图片/动图，避免图片溢出到下方文字。"""
        target = self.previewLabel.size()
        if target.width() < 20 or target.height() < 20:
            return
        if self._player.is_active:
            self._player.set_target_size(target)
            self._player.refresh()
        elif self._static_pixmap is not None:
            scaled = self._static_pixmap.scaled(
                target, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self.previewLabel.setPixmap(scaled)

    def set_info(self, html):
        self.infoLabel.setText(html)
