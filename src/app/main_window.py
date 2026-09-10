# coding=utf-8
"""主窗口：FluentWindow 四页导航注册 + 标题栏主题切换按钮。"""

import os

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QGuiApplication, QIcon

from qfluentwidgets import (FluentIcon as FIF, FluentTitleBarButton,
                            FluentWindow, MessageBox, NavigationItemPosition,
                            SystemThemeListener, Theme, isDarkTheme,
                            setTheme, toggleTheme)

from src.core.app_settings import cfg
from src.views.about_view import AboutView
from src.views.log_view import LogView
from src.views.setting_view import SettingView
from src.views.workspace_view import WorkspaceView
from src.widgets.teaching_tutorial import run_newbie_tutorial

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

        # 首次使用：窗口显示后询问是否查看新手教程
        QTimer.singleShot(0, self._maybe_show_newbie_tutorial)

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
        # lazy=True：只重绘可见控件，加快主题切换并降低与气泡阴影的交互风险
        toggleTheme(save=True, lazy=True)
        is_dark = isDarkTheme()
        self.theme_button.setToolTip('切换为浅色主题' if is_dark else '切换为深色主题')

    def _on_system_theme_changed(self):
        # 仅当主题模式为「跟随系统」时，SystemThemeListener 才会发出该信号
        setTheme(Theme.AUTO, lazy=True)

    # ---------- 新手教程 ----------

    def _maybe_show_newbie_tutorial(self):
        """首次使用（tutorialDone 为 False）时弹窗询问是否查看新手教程。"""
        if cfg.get(cfg.tutorialDone):
            return
        box = MessageBox(
            '欢迎使用 QQ表情包批量提取工具',
            '是否查看新手教程？\n教程将以气泡形式逐项介绍各功能与按钮的用法。',
            self,
        )
        box.yesButton.setText('查看教程')
        box.cancelButton.setText('跳过')
        if box.exec():
            run_newbie_tutorial(self)
        # 无论是否查看，首次询问后都不再自动弹出（可在设置页重置后重温）
        cfg.set(cfg.tutorialDone, True)

    def initNavigation(self):
        self.addSubInterface(self.workspace_view, FIF.EMOJI_TAB_SYMBOLS, '工作台')
        self.navigationInterface.addSeparator()
        self.addSubInterface(self.log_view, FIF.DOCUMENT, '日志', NavigationItemPosition.SCROLL)
        self.addSubInterface(self.setting_view, FIF.SETTING, '设置', NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.about_view, FIF.INFO, '关于', NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.setMinimumSize(1000, 640)
        self.setWindowTitle('QQNT表情包批量提取工具')

        icon_path = os.path.join(_project_root(), 'img', 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._center_on_screen()

    def _center_on_screen(self):
        """按屏幕分辨率取可用区域中心，居中显示窗口（尺寸不超过屏幕）。"""
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        width = min(1280, avail.width())
        height = min(800, avail.height())
        self.resize(width, height)
        # 以窗口边框几何中心对齐屏幕可用区域中心，避免标题栏/边框导致偏移
        frame = self.frameGeometry()
        frame.moveCenter(avail.center())
        self.move(frame.topLeft())
