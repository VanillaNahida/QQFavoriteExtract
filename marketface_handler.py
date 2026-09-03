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


def is_marketface_candidate(file_path: str) -> bool:
    """过滤缩略图及元数据，只保留可能是原始 marketface 的文件。"""
    return Path(file_path).suffix.lower() not in AUXILIARY_SUFFIXES
