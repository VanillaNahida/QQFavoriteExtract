# coding=utf-8
"""全局信号总线：跨线程、跨页面通信。"""

from PyQt6.QtCore import QObject, pyqtSignal


class SignalBus(QObject):
    """应用内所有跨模块信号统一走这里（Qt::QueuedConnection 自动跨线程排队）。"""

    # 日志（日志页收集；主界面用 InfoBar 呈现必要通知）
    logMessage = pyqtSignal(str, str)        # (level: info/warn/error, message)

    # 状态栏
    statusChanged = pyqtSignal(str)

    # 扫描
    scanProgress = pyqtSignal(int, int)      # (current, total)
    scanFinished = pyqtSignal(list)          # (paths)

    # 昵称
    nicknameReady = pyqtSignal(str, str)     # (qq, nickname)

    # 主题
    themeChanged = pyqtSignal(object)        # (Theme)


signalBus = SignalBus()
