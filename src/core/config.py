# coding=utf-8
"""QQ 聊天数据目录定位与分类枚举。"""

import os
import configparser
from pathlib import Path

from src.utils.helpers import read_file_with_correct_encoding

DEFAULT_INI_PATH = r'C:\Users\Public\Documents\Tencent\QQ\UserDataInfo.ini'

# 常见分类的显示名称映射
CATEGORY_NAME_MAPPING = {
    'personal_emoji': '个人收藏表情 (personal_emoji)',
    'emoji-recv': '接收到表情 [谨慎加载,内含巨量表情] (emoji-recv)',
    'marketface': '商店表情 (marketface)',
    'BaseEmojiSyastems': '系统表情 [已支持APNG动图转GIF导出] (BaseEmojiSyastems)',
    'emoji-related': '候选表情 [打字时系统推荐] (emoji-related)',
    'pic': '收藏图片 [注意：包含聊天接收的图片，和收藏图片混杂在一起，暂无法避免] (Pic)',
}


def get_category_display_name(folder_key):
    """获取分类目录的友好显示名"""
    return CATEGORY_NAME_MAPPING.get(folder_key, f"{folder_key} (其他分类)")


def detect_tencent_files_path():
    """自动检测系统文档中是否存在 Tencent Files 目录，且在该目录下含有符合QQ结构的数字子文件夹"""
    def get_windows_documents_path():
        try:
            import winreg
            sub_key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                personal_path, _ = winreg.QueryValueEx(key, "Personal")
                return personal_path
        except Exception:
            return None

    candidate_roots = []

    # 1. 注册表读取的"我的文档"绝对路径
    doc_path = get_windows_documents_path()
    if doc_path:
        candidate_roots.append(Path(doc_path))

    # 2. 常见的系统文件夹与用户主目录
    user_home = Path(os.path.expanduser('~'))
    candidate_roots.append(user_home / "Documents")
    candidate_roots.append(user_home)
    candidate_roots.append(Path(r"C:\Users\Public\Documents"))

    # 去重并确保目录真实存在
    seen = set()
    unique_roots = []
    for root in candidate_roots:
        try:
            resolved = root.resolve()
            if resolved not in seen and resolved.exists():
                seen.add(resolved)
                unique_roots.append(resolved)
        except Exception:
            continue

    # 遍历根目录寻找含有 {QQ号}/nt_qq 的 Tencent Files 文件夹
    for root in unique_roots:
        tencent_dir = root / "Tencent Files"
        if tencent_dir.exists() and tencent_dir.is_dir():
            try:
                for sub in os.listdir(tencent_dir):
                    sub_path = tencent_dir / sub
                    if sub.isdigit() and sub_path.is_dir():
                        # 若纯数字QQ号子目录下包含 nt_qq 目录，认定这就是我们要找的聊天记录根目录
                        if (sub_path / "nt_qq").exists():
                            return str(tencent_dir)
            except Exception:
                continue
    return None


def get_userdata_save_path(ini_file_path=DEFAULT_INI_PATH):
    """
    解析 UserDataInfo.ini 获取聊天数据保存路径；
    解析失败或路径不存在时，回退到系统目录智能扫描。
    返回路径字符串，失败返回 None。
    """
    userdata_save_path = None

    # 1. 尝试从配置文件中读取路径
    if os.path.exists(ini_file_path):
        try:
            encode = read_file_with_correct_encoding(ini_file_path, '[UserDataSet]', require_chinese=False)
            if encode:
                config = configparser.ConfigParser()
                config.read(ini_file_path, encoding=encode)
                if 'UserDataSet' in config:
                    userdata_save_path = config.get('UserDataSet', 'UserDataSavePath', fallback=None)
        except Exception:
            userdata_save_path = None

    # 2. 如果配置文件读取失败或路径不存在，启动系统目录智能扫描
    if not userdata_save_path or not os.path.exists(userdata_save_path):
        detected_path = detect_tencent_files_path()
        if detected_path:
            userdata_save_path = detected_path

    if userdata_save_path and os.path.exists(userdata_save_path):
        return userdata_save_path

    return None


def get_numeric_subdirectories(parent_dir):
    """返回目录下的纯数字子目录（QQ号文件夹）列表"""
    try:
        subdirs = [name for name in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir, name))]
        return [name for name in subdirs if name.isdigit()]
    except Exception:
        return []


def get_emoji_root(userdata_save_path, qq_number):
    """返回某用户 Emoji 根目录 Path"""
    return Path(userdata_save_path) / qq_number / "nt_qq" / "nt_data" / "Emoji"


def get_pic_root(userdata_save_path, qq_number):
    """返回某用户 Pic 收藏图片根目录 Path（内含日期命名的子文件夹，如 2026-02）"""
    return Path(userdata_save_path) / qq_number / "nt_qq" / "nt_data" / "Pic"


def get_category_path(userdata_save_path, qq_number, folder_key):
    """返回某分类的表情目录 Path；收藏图片分类指向 Pic 根目录而非 Emoji 目录"""
    if folder_key == 'pic':
        return get_pic_root(userdata_save_path, qq_number)
    return get_emoji_root(userdata_save_path, qq_number) / folder_key
