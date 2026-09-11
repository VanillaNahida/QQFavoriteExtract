# coding=utf-8
"""应用入口：QApplication、内置字体、主题初始化、启动 MainWindow。

运行方式：uv run python -m src.main
"""

import sys

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from qfluentwidgets import setFontFamilies

from src.app.main_window import MainWindow
from src.app.theme import apply_brand_color
from src.core.app_settings import cfg, sync_theme_from_cfg
from src.utils.helpers import get_font_path

# 内置 UI 字体（构建时随 exe 内嵌，见 build.py --include-data-files）
# 常规 + 粗体两级字重：Medium 命中常规文本，Semibold 命中加粗文本，Qt 按字重自动匹配
UI_FONT_FILES = ('MiSans-Medium.ttf', 'MiSans-Semibold.ttf')


def _apply_builtin_font():
    """注册内置 MiSans 字体（常规+粗体）并设为全局 UI 字体；加载失败时静默回退系统字体。"""
    registered = []
    for file in UI_FONT_FILES:
        path = get_font_path(file)
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id >= 0:
            registered.extend(QFontDatabase.applicationFontFamilies(font_id))
    if not registered:
        return
    # 将 MiSans 置于字体族最前，缺失字形时回退系统字体；仅运行时生效，不写入配置
    setFontFamilies([registered[0], 'Microsoft YaHei', 'PingFang SC'], save=False)

    # 消除字体锯齿：开启灰度抗锯齿 + 关闭字形 hinting（最平滑的渲染效果）
    font = QApplication.font()
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    QApplication.setFont(font)


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
