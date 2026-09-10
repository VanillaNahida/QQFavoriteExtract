# coding=utf-8
"""关于页：第一行程序信息，第二行作者信息。"""

import html as html_mod
import os
import re
import time

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from qfluentwidgets import (BodyLabel, CaptionLabel, FluentIcon as FIF,
                            HyperlinkButton, InfoBar, MessageBox, PushButton,
                            StrongBodyLabel, SubtitleLabel, TitleLabel)

from src import __version__
from src.core.update_checker import GITHUB_RELEASES_URL, UpdateChecker
from src.utils.helpers import get_app_data_dir
from src.widgets.round_avatar import AVATAR_TTL, RoundAvatar, _round_pixmap

GITHUB_URL = 'https://github.com/VanillaNahida/QQFavoriteExtract'
ISSUES_URL = GITHUB_URL + '/issues'
AUTHOR_HEATPHOTO_URL = 'https://q1.qlogo.cn/g?b=qq&nk=3051979160&s=640'
AUTHOR_BILIBILI_URL = 'https://space.bilibili.com/1347891621'
AUTHOR_WEBSITE = 'https://www.xcnahida.cn'
GROUP_LINK = 'https://www.xcnahida.cn/contact'

APP_NAME = 'QQNT表情包批量提取工具'
APP_DESCRIPTION = '使用 Python + Qt6 + QFluentWidgets 构建的现代化 QQ 表情包提取工具'
AUTHOR_NAME = '香草味的纳西妲喵'
DEFAULT_AUTHOR_MOTTO = '与你的日常，就是奇迹！'
# 作者简介抓取超时（毫秒）
MOTTO_TIMEOUT_MS = 10000
# 程序图标 / 作者头像圆形控件统一尺寸
ICON_SIZE = 96


def _app_root():
    """反推项目根目录（兼容开发与 Nuitka 打包环境）。"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _extract_motto(html_text):
    """从个人网站 HTML 中提取 <p class="motto"> 的内容，失败返回 None。"""
    match = re.search(r'<p\s+class="[^"]*\bmotto\b[^"]*">(.*?)</p>', html_text, re.S)
    if not match:
        return None
    text = re.sub(r'<[^>]+>', '', match.group(1))
    text = html_mod.unescape(text).strip()
    return text or None


class AboutView(QWidget):
    """第一行：程序图标 + 名称/版本/介绍/开源地址；第二行：作者头像 + 作者信息。"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('aboutView')

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(24)

        # ---- 第一行：程序信息 ----
        root.addWidget(SubtitleLabel('软件信息', self))
        app_row = QHBoxLayout()
        app_row.setSpacing(16)

        app_icon = QLabel(self)
        app_icon.setFixedSize(ICON_SIZE, ICON_SIZE)
        app_icon.setPixmap(self._app_icon_pixmap())
        app_row.addWidget(app_icon, 0, Qt.AlignmentFlag.AlignVCenter)

        app_info = QVBoxLayout()
        app_info.setSpacing(4)
        app_info.addWidget(TitleLabel(APP_NAME, self))
        app_info.addWidget(CaptionLabel(f'版本 {__version__}', self))
        desc = BodyLabel(APP_DESCRIPTION, self)
        desc.setWordWrap(True)
        app_info.addWidget(desc)
        app_info.addSpacing(4)
        # 开源地址按钮居左显示，右侧为「检查更新」按钮
        app_links = QHBoxLayout()
        app_links.setSpacing(8)
        app_links.addWidget(HyperlinkButton(GITHUB_URL, '开源地址 · GitHub', self))
        self.update_button = PushButton('检查更新', self, FIF.UPDATE)
        self.update_button.clicked.connect(self._on_check_update_clicked)
        app_links.addWidget(self.update_button)
        app_links.addStretch(1)
        app_info.addLayout(app_links)
        app_row.addLayout(app_info, 1)
        root.addLayout(app_row)

        # ---- 第二行：作者信息 ----
        root.addSpacing(16)
        root.addWidget(SubtitleLabel('作者信息', self))
        author_row = QHBoxLayout()
        author_row.setSpacing(16)

        self.avatar = RoundAvatar(ICON_SIZE, AUTHOR_HEATPHOTO_URL, self)
        author_row.addWidget(self.avatar, 0, Qt.AlignmentFlag.AlignVCenter)

        author_info = QVBoxLayout()
        author_info.setSpacing(6)
        author_name = StrongBodyLabel(AUTHOR_NAME, self)
        font = author_name.font()
        font.setPixelSize(18)  # 默认 14px，调大突出作者名
        author_name.setFont(font)
        author_info.addWidget(author_name)
        # 作者介绍：默认文本，网络可用时从个人网站 motto 字段刷新
        self.motto_label = BodyLabel(DEFAULT_AUTHOR_MOTTO, self)
        self.motto_label.setWordWrap(True)
        author_info.addWidget(self.motto_label)
        links = QHBoxLayout()
        links.setSpacing(8)
        for text, url in (
            ('哔哩哔哩主页', AUTHOR_BILIBILI_URL),
            ('个人网站', AUTHOR_WEBSITE),
            ('交流社群', GROUP_LINK),
            ('反馈 Bug', ISSUES_URL),
        ):
            links.addWidget(HyperlinkButton(url, text, self))
        links.addStretch(1)
        author_info.addLayout(links)
        author_row.addLayout(author_info, 1)
        root.addLayout(author_row)

        root.addStretch(1)

        # 异步抓取作者介绍（失败时保持默认文本）
        self._load_author_motto()

    # ---------- 作者介绍抓取 ----------

    def _load_author_motto(self):
        """读取本地缓存（TTL 与头像一致）；过期则先显示旧值再后台抓取刷新。"""
        cache_file = self._motto_cache_file()
        cached = self._read_motto_cache(cache_file) if os.path.exists(cache_file) else None
        if cached and time.time() - os.path.getmtime(cache_file) < AVATAR_TTL:
            self.motto_label.setText(cached)
            return
        if cached:
            # 缓存过期：先显示旧值，后台刷新
            self.motto_label.setText(cached)

        self._motto_net = QNetworkAccessManager(self)
        request = QNetworkRequest(QUrl(AUTHOR_WEBSITE))
        request.setTransferTimeout(MOTTO_TIMEOUT_MS)
        self._motto_net.finished.connect(self._on_motto_downloaded)
        self._motto_net.get(request)

    def _motto_cache_file(self):
        return os.path.join(get_app_data_dir(), 'author_motto.txt')

    def _read_motto_cache(self, path):
        try:
            with open(path, encoding='utf-8') as f:
                return f.read().strip() or None
        except OSError:
            return None

    def _on_motto_downloaded(self, reply):
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                html_text = bytes(reply.readAll()).decode('utf-8', errors='ignore')
                motto = _extract_motto(html_text)
                if motto:
                    self.motto_label.setText(motto)
                    # 写入本地缓存（TTL 与头像一致）
                    try:
                        with open(self._motto_cache_file(), 'w', encoding='utf-8') as f:
                            f.write(motto)
                    except OSError:
                        pass
        finally:
            reply.deleteLater()

    # ---------- 检查更新 ----------

    def _on_check_update_clicked(self):
        """点击「检查更新」：请求 GitHub Release 最新版本并比对本地版本。"""
        if getattr(self, '_checking_update', False):
            return
        self._checking_update = True
        self.update_button.setEnabled(False)
        self._update_checker = UpdateChecker(self)
        self._update_checker.finished.connect(self._on_check_update_result)
        self._update_checker.check()

    def _on_check_update_result(self, has_new, latest, error):
        self._checking_update = False
        self.update_button.setEnabled(True)
        if error:
            InfoBar.error('检查更新失败', error, duration=5000, parent=self)
            return
        if has_new:
            box = MessageBox(
                '发现新版本',
                f'检测到新版本 v{latest}（当前 v{__version__}），是否前往下载页？',
                self,
            )
            box.yesButton.setText('前往下载')
            box.cancelButton.setText('取消')
            if box.exec():
                QDesktopServices.openUrl(QUrl(GITHUB_RELEASES_URL))
        else:
            InfoBar.success('已是最新版本', f'当前已是最新版本 v{__version__}', duration=5000, parent=self)

    def _app_icon_pixmap(self):
        """程序圆形图标：优先使用本地 icon.png，失败回退 Fluent 图标。"""
        icon_path = os.path.join(_app_root(), 'img', 'icon.png')
        if os.path.exists(icon_path):
            pixmap = QIcon(icon_path).pixmap(144, 144)
            if not pixmap.isNull():
                return _round_pixmap(pixmap, 144)
        return _round_pixmap(FIF.EMOJI_TAB_SYMBOLS.icon().pixmap(144, 144), 144)
