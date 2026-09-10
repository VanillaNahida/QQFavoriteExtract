# coding=utf-8
"""关于页。"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from qfluentwidgets import (BodyLabel, CaptionLabel, FluentIcon as FIF,
                            HyperlinkButton, SubtitleLabel)

from src import __version__

GITHUB_URL = 'https://github.com/VanillaNahida'
LICENSE_URL = 'https://github.com/VanillaNahida/QQFavoriteExtract/blob/main/LICENSE'


class AboutView(QWidget):
    """Logo + 版本 + 简介 + 链接。"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('aboutView')

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(16)

        logo = QLabel(self)
        logo.setPixmap(FIF.EMOJI_TAB_SYMBOLS.icon().pixmap(96, 96))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(logo)

        title = SubtitleLabel('QQNT表情包批量提取工具')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        version = CaptionLabel(f'版本 {__version__}')
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(version)

        desc = BodyLabel(
            '从本地 QQNT 缓存中批量提取收藏的表情包，'
            '支持 marketface 内存解密、APNG 动图转 GIF 导出。'
            '\n基于 PyQt-Fluent-Widgets 构建。'
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        root.addWidget(desc)

        root.addSpacing(8)

        links = QVBoxLayout()
        links.setSpacing(8)
        github_link = HyperlinkButton(GITHUB_URL, 'GitHub 主页')
        github_link.setFixedHeight(36)
        license_link = HyperlinkButton(LICENSE_URL, '开源许可证 (MIT)')
        license_link.setFixedHeight(36)
        links.addWidget(github_link)
        links.addWidget(license_link)
        root.addLayout(links)

        root.addStretch(1)
