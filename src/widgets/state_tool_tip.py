# coding=utf-8
"""右上角 StateToolTip 统一管理：定位联动、show/update/finish。"""

from PyQt6.QtCore import QObject, QTimer

from qfluentwidgets import StateToolTip


class StateToolTipManager(QObject):
    """管理单个 StateToolTip 实例，定位到父控件右上角（随父控件缩放联动）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tip = None
        self._finished = False

    def is_active(self):
        return self._tip is not None

    def show(self, title, content=""):
        """显示（或更新标题/内容）。"""
        if self._tip is not None:
            self._tip.setTitle(title)
            self._tip.setContent(content)
            self._reposition()
            return
        self._finished = False
        self._tip = StateToolTip(title, content, self.parent())
        self._tip.show()
        self._reposition()

    def update(self, content):
        """更新内容文本。"""
        if self._tip is not None and not self._finished:
            self._tip.setContent(content)
            self._reposition()

    def finish(self, title=None, content=None):
        """置为完成态（打勾）。StateToolTip 内部会淡出并自毁，此处仅延后释放引用。"""
        if self._tip is None:
            return
        if title is not None:
            self._tip.setTitle(title)
        if content is not None:
            self._tip.setContent(content)
        self._tip.setState(True)
        self._finished = True
        QTimer.singleShot(2000, self._release_ref)

    def cancel(self):
        """直接隐藏（不显示完成态）。"""
        if self._tip is not None:
            try:
                self._tip.hide()
            except Exception:
                pass
        self._release_ref()

    def reposition(self):
        """父控件尺寸变化时调用，保持右上角定位。"""
        self._reposition()

    def _release_ref(self):
        """丢弃引用。控件自身的销毁由 StateToolTip 内部动画完成后 deleteLater 负责。"""
        self._tip = None
        self._finished = False

    def _reposition(self):
        if self._tip is None:
            return
        parent = self.parent()
        if parent is None:
            return
        QTimer.singleShot(0, self._do_reposition)

    def _do_reposition(self):
        if self._tip is None:
            return
        parent = self.parent()
        if parent is None:
            return
        x = max(10, parent.width() - self._tip.width() - 40)
        self._tip.move(x, 40)
