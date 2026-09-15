"""预览区加载提示与到底提示：提示图 + 提示文本 + 不确定进度条。"""

import random

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QStackedLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CardWidget, IndeterminateProgressBar, isDarkTheme

from src.utils.helpers import get_asset_path

# 加载提示图：每次展示时随机取一张
LOADING_IMAGES = ('Loading_1.png', 'Loading_2.png', 'Loading_3.png')
# 已滑到预览最底部且没有更多表情时的提示语：每次展示时随机取一句
END_TEXTS = ('已到达什亭之匣尽头~', '我也是有底线的 ^_^', '没有更多了……', '已经到底啦~')


def _scaled_pixmap(name, width=None, height=None):
    """按指定宽/高等比缩放素材图；素材缺失时返回空 QPixmap。"""
    pixmap = QPixmap(get_asset_path(name))
    if pixmap.isNull():
        return pixmap
    mode = Qt.TransformationMode.SmoothTransformation
    return pixmap.scaledToWidth(width, mode) if width is not None else pixmap.scaledToHeight(height, mode)


class LoadingHint(QWidget):
    """加载提示：提示图居左，提示文本居右侧偏上，不确定进度条位于文本正下方。"""

    def __init__(self, image_width=180, bar_width=220,
                 text='请稍后，正在加载预览……', parent=None):
        super().__init__(parent=parent)
        self._image_width = image_width

        self.icon_label = QLabel(self)
        self.icon_label.setFixedWidth(image_width)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.text_label = BodyLabel(text, self)
        self.loading_bar = IndeterminateProgressBar(self)
        self.loading_bar.setFixedWidth(bar_width)

        # 右侧列：文本在上、进度条紧随其下；底部留白多于顶部，使整组略偏上
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(10)
        right.addStretch(2)
        right.addWidget(self.text_label)
        right.addWidget(self.loading_bar)
        right.addStretch(3)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self.icon_label)
        layout.addLayout(right, 1)

        self.set_random_image()

    def set_random_image(self):
        """随机换一张加载提示图（每次展示时调用）。"""
        self.icon_label.setPixmap(
            _scaled_pixmap(random.choice(LOADING_IMAGES), width=self._image_width))


class PreviewBottomBar(CardWidget):
    """预览网格下方的提示条：参与布局、位于缩略图下方，不会遮挡图片。

    两种模式：
    - LOADING：滑到底部触发懒加载时显示「随机提示图 + 提示文本 + 不确定进度条」
    - END：全部缩略图加载完毕且已滑到最底部时显示「footer 图 + 随机文案」
    """

    LOADING = 'loading'
    END = 'end'

    WIDTH = 440
    HEIGHT = 92

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # 悬浮提示条：鼠标点击穿透，不拦截/遮挡下方缩略图的任何操作
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._mode = None

        self.loading_hint = LoadingHint(
            image_width=100, bar_width=200, text='正在加载更多预览……', parent=self)
        self.end_hint = self._build_end_hint()

        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._stack.addWidget(self.loading_hint)
        self._stack.addWidget(self.end_hint)

        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setVisible(False)

    def _build_end_hint(self):
        """到底提示页：footer 图居左 + 随机文案居右。"""
        page = QWidget(self)
        self.end_icon = QLabel(page)
        self.end_icon.setPixmap(_scaled_pixmap('footer.png', height=56))
        self.end_label = BodyLabel('', page)

        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addStretch()
        layout.addWidget(self.end_icon)
        layout.addWidget(self.end_label)
        layout.addStretch()
        return page

    def set_mode(self, mode):
        """切换提示条模式（None 为隐藏）；模式未变化时不重复随机提示图/文案。"""
        if mode == self._mode:
            return
        self._mode = mode
        if mode is None:
            # 隐藏时停掉进度条动画，避免不可见的动画持续占用 CPU
            self.loading_hint.loading_bar.stop()
            self.setVisible(False)
            return
        if mode == self.LOADING:
            self.loading_hint.set_random_image()
            self.loading_hint.loading_bar.start()
            self._stack.setCurrentWidget(self.loading_hint)
        else:
            self.end_label.setText(random.choice(END_TEXTS))
            self._stack.setCurrentWidget(self.end_hint)
        self.setVisible(True)

    def _normalBackgroundColor(self):
        # 悬浮窗半透明背景：深色/浅色模式下均留一定透明度，确保不干扰下方图片
        return QColor(40, 40, 40, 205) if isDarkTheme() else QColor(255, 255, 255, 205)

    def _hoverBackgroundColor(self):
        return self._normalBackgroundColor()

    def _pressedBackgroundColor(self):
        return self._normalBackgroundColor()
