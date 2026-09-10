# coding=utf-8
"""检查更新：比对 GitHub Release 最新版本与本地版本（异步，不阻塞 UI）。"""

import json
import re

from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from src import __version__

GITHUB_REPO = 'VanillaNahida/QQFavoriteExtract'
# Release 最新版页面（用于跳转下载）
GITHUB_RELEASES_URL = f'https://github.com/{GITHUB_REPO}/releases/latest'
# GitHub API：查询最新 Release 信息
API_RELEASES_LATEST = f'https://api.github.com/repos/{GITHUB_REPO}/releases/latest'
# 请求超时（毫秒）
UPDATE_TIMEOUT_MS = 10000


def version_key(text):
    """把版本字符串解析为可比较元组（忽略 v 前缀与预发布后缀）。

    例如 "v1.5.0" -> (1, 5, 0)；解析不出数字时返回空元组。
    """
    parts = re.findall(r'\d+', str(text).strip().lstrip('vV'))
    key = tuple(int(p) for p in parts[:3])
    return key


def has_new_version(latest, local=None):
    """latest > local 时返回 True；任一无法解析视为无更新。"""
    local = local or __version__
    latest_key = version_key(latest)
    local_key = version_key(local)
    if not latest_key or not local_key:
        return False
    return latest_key > local_key


class UpdateChecker(QObject):
    """异步查询 GitHub 最新 Release 版本号。

    finished 信号参数：(是否有新版本, 最新版本号, 错误信息)。
    请求失败时前两个参数为空值，错误信息非空。
    """

    finished = pyqtSignal(bool, str, str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._net = QNetworkAccessManager(self)
        self._net.finished.connect(self._on_finished)

    def check(self):
        """发起一次检查请求（同一实例请勿并发调用）。"""
        request = QNetworkRequest(QUrl(API_RELEASES_LATEST))
        # GitHub API 强制要求 User-Agent 头
        request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, 'QQFavoriteExtract')
        request.setTransferTimeout(UPDATE_TIMEOUT_MS)
        self._net.get(request)

    def _on_finished(self, reply):
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self.finished.emit(False, '', reply.errorString())
                return
            payload = json.loads(bytes(reply.readAll()).decode('utf-8', errors='ignore'))
            tag = (payload or {}).get('tag_name') or ''
            latest = str(tag).lstrip('vV')
            self.finished.emit(has_new_version(latest), latest, '')
        except Exception as exc:
            self.finished.emit(False, '', str(exc))
        finally:
            reply.deleteLater()
