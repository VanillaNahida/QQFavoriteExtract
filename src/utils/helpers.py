# coding=utf-8
"""纯工具函数：文件编码探测、文件名清洗、格式化等。"""

import os
import mimetypes
import chardet


MIME_MAPPING = {
    'jpg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'bmp': 'image/bmp',
    'tiff': 'image/tiff',
    'webp': 'image/webp',
    'ico': 'image/x-icon',
    'psd': 'image/vnd.adobe.photoshop',
    'svg': 'image/svg+xml',
    'heic': 'image/heic',
    'avif': 'image/avif',
}


def get_app_data_dir():
    """返回应用数据目录（LOCALAPPDATA 下），不存在则创建。"""
    appdata_path = os.getenv('LOCALAPPDATA')
    if not appdata_path:
        appdata_path = os.path.join(os.getenv('USERPROFILE', ''), 'AppData', 'LocalLow')
    cache_dir = os.path.join(appdata_path, 'QQ表情包批量提取工具数据目录')
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def sanitize_filename(name):
    """去除 Windows 文件名非法字符"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '')
    return name.strip()


def is_content_valid(content, min_chinese=1):
    """验证内容是否包含至少一个中文字符（避免误判为拉丁编码）"""
    chinese_chars = sum('\u4e00' <= char <= '\u9fff' for char in content)
    return chinese_chars >= min_chinese


def read_file_with_correct_encoding(file_path, target_string, require_chinese=True):
    """
    通过候选编码探测 + 目标字符串验证，返回可正确解码的编码名。
    探测失败返回 None。

    :param require_chinese: 内容为纯 ASCII 时（如 QQ 的 UserDataInfo.ini 路径无中文），
        中文校验会误判失败，可置为 False 跳过该要求。
    """
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
    except Exception:
        return None

    # 1. 优先尝试中文相关编码（GB18030覆盖GBK，兼容性更好）
    priority_encodings = ['gb18030', 'utf-8', 'utf-16', 'ascii']

    # 2. 使用chardet检测
    try:
        detected = chardet.detect(data)
        if detected['encoding']:
            if detected['confidence'] < 0.7 or detected['encoding'].lower() not in ['gb18030', 'gbk', 'utf-8']:
                priority_encodings.append(detected['encoding'])
            else:
                priority_encodings.insert(0, detected['encoding'])
    except Exception:
        pass

    # 3. 补充其他可能编码并去重
    encodings = priority_encodings + [
        'gbk', 'big5', 'utf-16-le', 'utf-16-be', 'shift_jis',
        'iso-8859-1', 'latin-1', 'cp936', 'cp950', 'utf-7'
    ]
    seen = set()
    ordered_encodings = []
    for enc in encodings:
        enc_lower = enc.lower()
        if enc_lower not in seen:
            seen.add(enc_lower)
            ordered_encodings.append(enc)

    # 4. 严格模式解码验证
    for enc in ordered_encodings:
        try:
            content = data.decode(enc, errors='strict')
        except (UnicodeDecodeError, LookupError):
            continue
        if target_string in content and (is_content_valid(content) or not require_chinese):
            return enc.ljust(12)
    return None


def get_recommended_extension(file_path):
    """根据 MIME 类型返回推荐的文件扩展名"""
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        for ext, mt in MIME_MAPPING.items():
            if mt == mime_type:
                return ext
    return None


def format_file_size(num_bytes):
    """人性化文件大小显示"""
    size_kb = num_bytes / 1024
    if size_kb < 1024:
        return f"{size_kb:.2f} KB"
    size_mb = size_kb / 1024
    return f"{size_mb:.2f} MB"


def format_mtime(timestamp):
    """时间戳格式化为可读时间"""
    import time
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))


def get_asset_path(name):
    """返回 src/assets 下资源的绝对路径（兼容开发环境与 Nuitka 打包环境）。

    Nuitka onefile 会将 --include-data-dir 的数据解包到临时目录，模块 __file__
    在该目录下保持源码相对布局（src/utils/helpers.py），因此用 __file__ 反推
    src 目录即可定位到 assets。
    """
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'assets', name)
