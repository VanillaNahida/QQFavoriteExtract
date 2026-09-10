# coding=utf-8
"""主窗口：FluentWindow 四页导航注册 + 标题栏主题切换按钮。"""

import os

from PyQt6.QtGui import QIcon

from qfluentwidgets import (FluentIcon as FIF, FluentTitleBarButton,
                            FluentWindow, NavigationItemPosition,
                            SystemThemeListener, Theme, isDarkTheme,
                            setTheme, toggleTheme)

from src.core.app_settings import cfg
from src.views.about_view import AboutView
from src.views.log_view import LogView
from src.views.setting_view import SettingView
from src.views.workspace_view import WorkspaceView

def _project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MainWindow(FluentWindow):
    """主窗口：工作台 / 日志 / 设置 / 关于。"""

    def __init__(self):
        super().__init__()
        self.initWindow()

        self.workspace_view = WorkspaceView(self)
        self.log_view = LogView(self)
        self.setting_view = SettingView(self)
        self.about_view = AboutView(self)

        self.initNavigation()
        self._init_title_bar_theme_button()

        # 系统深浅色监听（仅「跟随系统」模式下响应）
        self.themeListener = SystemThemeListener(self)
        self.themeListener.systemThemeChanged.connect(self._on_system_theme_changed)
        self.themeListener.start()

    def connectSignals(self):
        pass

    def closeEvent(self, e):
        # 先安全停止所有后台工作线程，避免退出时线程仍存活导致崩溃
        self.workspace_view.shutdown()
        try:
            self.themeListener.terminate()
            self.themeListener.deleteLater()
        except Exception:
            pass
        super().closeEvent(e)

    # ---------- 标题栏主题按钮 ----------

    def _init_title_bar_theme_button(self):
        """在标题栏右上角三个系统按钮左侧插入深浅色切换按钮。"""
        self.theme_button = FluentTitleBarButton(FIF.BRIGHTNESS, self.titleBar)
        self.theme_button.setFixedSize(46, 32)
        self.theme_button.setToolTip('切换深浅色主题')
        self.theme_button.clicked.connect(self._on_theme_button_clicked)
        self.titleBar.buttonLayout.insertWidget(0, self.theme_button)

    def _on_theme_button_clicked(self):
        toggleTheme(save=True)
        is_dark = isDarkTheme()
        self.theme_button.setToolTip('切换为浅色主题' if is_dark else '切换为深色主题')

    def _on_system_theme_changed(self):
        # 仅当主题模式为「跟随系统」时，SystemThemeListener 才会发出该信号
        setTheme(Theme.AUTO, lazy=True)

    def initNavigation(self):
        self.addSubInterface(self.workspace_view, FIF.EMOJI_TAB_SYMBOLS, '工作台')
        self.navigationInterface.addSeparator()
        self.addSubInterface(self.log_view, FIF.DOCUMENT, '日志', NavigationItemPosition.SCROLL)
        self.addSubInterface(self.setting_view, FIF.SETTING, '设置', NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.about_view, FIF.INFO, '关于', NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(1280, 800)
        self.setMinimumSize(1000, 640)
        self.setWindowTitle('QQNT表情包批量提取工具')

        icon_path = os.path.join(_project_root(), 'img', 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
