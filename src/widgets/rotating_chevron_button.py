# coding=utf-8
"""带旋转动画的 ChevronDown 按钮：同一图标通过 QPropertyAnimation 旋转指向不同方向。"""

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget

from qfluentwidgets import FluentIcon as FIF, drawIcon


class RotatingChevronButton(QWidget):
    """基于 ChevronDown 的透明旋转按钮。

    角度约定（QPainter.rotate 顺时针为正）：
    - 0°   向下（配置面板收起，点击展开）
    - 180° 向上（配置面板展开，点击收起）
    - 90°  向左（详情面板收起，点击展开）
    - -90° 向右（详情面板展开，点击收起）
    """

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._angle = 0.0
        self._anim = None
        self._hover = False
        self._pressed = False
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip('展开/收起面板')

    # ---------- 旋转角度属性 ----------

    def getAngle(self):
        return self._angle

    def setAngle(self, angle):
        self._angle = float(angle)
        self.update()

    angle = pyqtProperty(float, getAngle, setAngle)

    def set_direction(self, angle, animated=True):
        """旋转到指定角度（默认带 250ms 缓动动画）。"""
        if not animated or abs(self._angle - angle) < 0.5:
            self.setAngle(angle)
            return
        if self._anim is not None:
            self._anim.stop()
        anim = QPropertyAnimation(self, b'angle', self)
        anim.setDuration(250)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.setStartValue(self._angle)
        anim.setEndValue(float(angle))
        anim.start()
        self._anim = anim

    # ---------- 事件 ----------

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self._pressed = False
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._pressed = False
            self.update()
            if self.rect().contains(e.position().toPoint()):
                self.clicked.emit()
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.SmoothPixmapTransform)

        # 背景（悬停/按下时的浅色底）
        bg = QColor(0, 0, 0, 26) if self._hover else QColor(0, 0, 0, 0)
        if self._pressed:
            bg = QColor(0, 0, 0, 51)
        painter.fillRect(self.rect(), bg)

        # 绕图标中心旋转后绘制 ChevronDown
        cx, cy = self.width() / 2, self.height() / 2
        painter.translate(cx, cy)
        painter.rotate(self._angle)
        painter.translate(-cx, -cy)
        icon_size = 16
        icon_rect = QRectF(cx - icon_size / 2, cy - icon_size / 2, icon_size, icon_size)
        drawIcon(FIF.CHEVRON_DOWN_MED, painter, icon_rect)
