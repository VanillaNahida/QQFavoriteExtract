# coding=utf-8
"""应用入口：QApplication、主题初始化、启动 MainWindow。

运行方式：uv run python -m src.main
"""

import sys

from PyQt6.QtWidgets import QApplication

from src.app.main_window import MainWindow
from src.app.theme import apply_brand_color
from src.core.app_settings import cfg, sync_theme_from_cfg


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('QQ表情包批量提取工具')

    # 从 cfg 同步主题到 qconfig 并应用
    sync_theme_from_cfg()
    apply_brand_color()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
