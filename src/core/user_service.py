# coding=utf-8
"""QQ 昵称查询服务：缓存读写 + QNetworkAccessManager 异步网络请求。"""

import json
import os
import time

from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest

from src.utils.helpers import get_app_data_dir

NICKNAME_API = "https://uapis.cn/api/v1/social/qq/userinfo?qq={qq}"
CACHE_EXPIRE_SECONDS = 3600 * 24  # 昵称缓存 1 天后过期
REQUEST_TIMEOUT_MS = 10000


class UserService(QObject):
    """负责昵称的缓存读取与异步获取，不阻塞 UI 线程。"""

    nicknameReady = pyqtSignal(str, str)  # (qq, nickname)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)
        self._nam.finished.connect(self._on_reply_finished)
        self._pending_replies = {}  # QNetworkReply -> qq

    # ---------- 缓存读写 ----------

    def get_nickname_cache_path(self):
        return os.path.join(get_app_data_dir(), '用户昵称缓存.json')

    def load_nickname_cache(self):
        cache_path = self.get_nickname_cache_path()
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_nickname_cache(self, cache_data):
        cache_path = self.get_nickname_cache_path()
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_cached_nickname(self, qq_number):
        """返回缓存中未过期的昵称，无则返回空串"""
        cache = self.load_nickname_cache()
        now = int(time.time())
        if qq_number in cache and \
           'username_expire_time' in cache[qq_number] and \
           cache[qq_number]['username_expire_time'] > now:
            return cache[qq_number].get('name', '')
        return ''

    def get_display_name(self, qq_number):
        """返回 '昵称（QQ号）' 或纯 QQ 号"""
        nickname = self.get_cached_nickname(qq_number)
        if nickname:
            return f"{nickname}（{qq_number}）"
        return qq_number

    # ---------- 异步请求 ----------

    def fetch_nickname(self, qq_number):
        """异步获取昵称。缓存有效时立即发信号；否则发起网络请求。"""
        cached = self.get_cached_nickname(qq_number)
        if cached:
            self.nicknameReady.emit(qq_number, cached)
            return

        request = QNetworkRequest(QUrl(NICKNAME_API.format(qq=qq_number)))
        request.setTransferTimeout(REQUEST_TIMEOUT_MS)
        reply = self._nam.get(request)
        self._pending_replies[reply] = qq_number

    def _on_reply_finished(self, reply):
        qq_number = self._pending_replies.pop(reply, None)
        try:
            if reply.error() == reply.NetworkError.NoError:
                data = reply.readAll().data()
                payload = json.loads(data.decode('utf-8', errors='ignore'))
                nickname = payload.get('nickname') or ''
                if nickname:
                    cache = self.load_nickname_cache()
                    cache[qq_number] = {
                        'name': nickname,
                        'username_expire_time': int(time.time()) + CACHE_EXPIRE_SECONDS
                    }
                    self.save_nickname_cache(cache)
                    self.nicknameReady.emit(qq_number, nickname)
                    return
        except Exception:
            pass
        finally:
            reply.deleteLater()
        # 失败/超时/无昵称时静默降级（界面仍显示 QQ 号）
        self.nicknameReady.emit(qq_number, '')

    def clear_cache(self):
        """清除昵称缓存文件"""
        cache_path = self.get_nickname_cache_path()
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
                return True
            except Exception:
                return False
        return False
