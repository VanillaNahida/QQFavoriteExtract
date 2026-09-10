# coding=utf-8
"""右上角 StateToolTip 统一管理：定位联动、show/update/finish。

StateToolTip 完成态淡出动画结束后会自行 deleteLater 销毁，
其 C++ 对象可能先于引用释放被删除。因此所有访问 _tip 的路径
都必须防御 RuntimeError（已删除对象），并借助 destroyed 信号
及时清空悬垂引用，避免再次 show() 时崩溃。
"""

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
        """显示（或更新标题/内容）。若旧 tip 已淡出/自毁，则重建新实例。"""
        tip = self._tip
        if tip is not None and not self._finished:
            try:
                tip.setTitle(title)
                tip.setContent(content)
                self._reposition()
                return
            except RuntimeError:
                # 旧 tip 的 C++ 对象已被删除（自毁后引用未及时释放）
                tip = None
        if tip is not None:
            # 上一轮已进入完成态（淡出中）：丢弃旧实例，另起新实例
            try:
                tip.hide()
            except RuntimeError:
                pass
            self._release_ref()
        self._finished = False
        self._tip = StateToolTip(title, content, self.parent())
        # 自毁时自动清空引用，避免悬垂
        self._tip.destroyed.connect(self._release_ref)
        self._tip.show()
        self._reposition()

    def update(self, content):
        """更新内容文本。"""
        if self._finished:
            return
        tip = self._tip
        if tip is None:
            return
        try:
            tip.setContent(content)
            self._reposition()
        except RuntimeError:
            self._tip = None

    def finish(self, title=None, content=None):
        """置为完成态（打勾）。StateToolTip 内部会淡出并自毁，此处仅延后释放引用。"""
        tip = self._tip
        if tip is None:
            return
        try:
            if title is not None:
                tip.setTitle(title)
            if content is not None:
                tip.setContent(content)
            tip.setState(True)
        except RuntimeError:
            self._tip = None
            self._finished = False
            return
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
        tip = self._tip
        if tip is None:
            return
        parent = self.parent()
        if parent is None:
            return
        try:
            x = max(10, parent.width() - tip.width() - 40)
            tip.move(x, 40)
        except RuntimeError:
            # 定时回调执行时 tip 已被销毁：清空悬垂引用
            self._tip = None
