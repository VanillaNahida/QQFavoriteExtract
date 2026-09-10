# coding=utf-8
"""应用入口：QApplication、内置字体、主题初始化、启动 MainWindow。

运行方式：uv run python -m src.main
"""

import sys

from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication

from qfluentwidgets import setFontFamilies

from src.app.main_window import MainWindow
from src.app.theme import apply_brand_color
from src.core.app_settings import cfg, sync_theme_from_cfg
from src.utils.helpers import get_font_path

# 内置 UI 字体（构建时随 exe 内嵌，见 build.py --include-data-files）
UI_FONT_FILE = 'MiSans-Semibold.ttf'


def _apply_builtin_font():
    """注册内置 MiSans 字体并设为全局 UI 字体；加载失败时静默回退系统字体。"""
    path = get_font_path(UI_FONT_FILE)
    font_id = QFontDatabase.addApplicationFont(path)
    if font_id < 0:
        return
    families = QFontDatabase.applicationFontFamilies(font_id)
    if not families:
        return
    # 将 MiSans 置于字体族最前，缺失字形时回退系统字体；仅运行时生效，不写入配置
    setFontFamilies([families[0], 'Microsoft YaHei', 'PingFang SC'], save=False)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('QQ表情包批量提取工具')

    # 内置 UI 字体（在主题/窗口创建前设置，保证所有控件立即生效）
    _apply_builtin_font()

    # 从 cfg 同步主题到 qconfig 并应用
    sync_theme_from_cfg()
    apply_brand_color()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
