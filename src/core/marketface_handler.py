# coding=utf-8
"""QQNT marketface 专用的内存解密与校验工具。"""

from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

try:
    from PIL import Image
except ImportError:
    Image = None


GIF_HEADERS = (b"GIF87a", b"GIF89a")
# marketface 中这些通常是可直接查看的缩略图/辅助图，不是待恢复原图。
AUXILIARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".apng", ".json", ".ini"
}


def is_gif_header(data: bytes) -> bool:
    return len(data) >= 6 and data[:6] in GIF_HEADERS


def restore_marketface(data: bytes) -> bytes:
    """执行 QQNT marketface 的 20 字节 XOR + 30 字节明文循环。"""
    restored = bytearray(data)
    for offset in range(0, len(restored), 50):
        end = min(offset + 20, len(restored))
        for index in range(offset, end):
            restored[index] ^= 0xFF
    return bytes(restored)


def validate_gif(data: bytes) -> int:
    """在内存中验证 GIF，返回帧数；失败时抛出异常。"""
    if Image is None:
        raise RuntimeError("未安装 Pillow，无法验证 marketface GIF")
    with Image.open(BytesIO(data)) as image:
        image.load()
        frames = getattr(image, "n_frames", 1)
        for frame in range(frames):
            image.seek(frame)
            image.copy().load()
        return frames


def recover_marketface_data(file_path: str) -> Optional[Tuple[bytes, int]]:
    """读取并恢复单个 marketface 文件，成功时返回 (GIF数据, 帧数)。"""
    try:
        data = Path(file_path).read_bytes()
        restored = data if is_gif_header(data) else restore_marketface(data)
        if not is_gif_header(restored):
            return None
        return restored, validate_gif(restored)
    except Exception:
        return None


def recover_marketface_preview(file_path: str) -> Optional[bytes]:
    """轻量恢复 marketface 数据用于预览（只做头部校验，不做全帧验证，速度更快）。"""
    try:
        data = Path(file_path).read_bytes()
        restored = data if is_gif_header(data) else restore_marketface(data)
        if not is_gif_header(restored):
            return None
        return restored
    except Exception:
        return None


def load_marketface_first_frame(data: bytes):
    """用 Pillow 解码 GIF 首帧，返回 (RGBA PIL.Image, 帧数)；失败返回 (None, 0)。"""
    if Image is None:
        return None, 0
    try:
        with Image.open(BytesIO(data)) as im:
            im.seek(0)
            frame = im.convert('RGBA')
            frame.load()
            return frame.copy(), int(getattr(im, 'n_frames', 1))
    except Exception:
        return None, 0


def load_marketface_frames(data: bytes):
    """用 Pillow 提取 GIF 全部帧，返回 [(RGBA PIL.Image, 帧时长ms), ...]；失败返回 None。

    注意：marketface 恢复出的部分 GIF 数据会让 Qt 的 GIF 解码器偶发崩溃
    （未初始化内存访问，Pillow 却能正常解析）。因此动图播放一律基于
    Pillow 帧驱动，不经过 QMovie/QImageReader。
    """
    if Image is None:
        return None
    try:
        with Image.open(BytesIO(data)) as im:
            frame_count = int(getattr(im, 'n_frames', 1))
            frames = []
            for i in range(frame_count):
                im.seek(i)
                frame = im.convert('RGBA')
                frame.load()
                frames.append((frame.copy(), max(int(im.info.get('duration', 80)) or 80, 20)))
            return frames
    except Exception:
        return None


def is_marketface_candidate(file_path: str) -> bool:
    """过滤缩略图及元数据，只保留可能是原始 marketface 的文件。"""
    return Path(file_path).suffix.lower() not in AUXILIARY_SUFFIXES
