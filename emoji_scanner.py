# coding=utf-8

import os
import re
from pathlib import Path
from emoji_converter import is_apng_file
from marketface_handler import is_marketface_candidate, recover_marketface_data

FILE_SIGNATURES = {
    'jpg': (b'\xff\xd8\xff', b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1'),
    'png': (b'\x89PNG\r\n\x1a\n',),
    'gif': (b'GIF87a', b'GIF89a'),
    'bmp': (b'BM',),
    'tiff': (b'II*\x00', b'MM\x00*'),
    'webp': (b'RIFF', b'WEBP'),
    'ico': (b'\x00\x00\x01\x00', b'\x00\x00\x02\x00'),
    'psd': (b'8BPS',),
    'svg': (b'<?xml', b'<svg'),
    'heic': (b'ftypheic', b'ftypheix', b'ftyphevc', b'ftyphevx'),
    'avif': (b'ftypavif', b'ftypavis'),
}


def get_actual_extension(file_path):
    """
    通过读取文件头签名（魔数）判断文件的真实图片格式
    """
    if not file_path or not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)
        for ext, signatures in FILE_SIGNATURES.items():
            for sig in signatures:
                if header.startswith(sig):
                    return ext
    except Exception:
        pass
    return None


def _calculate_emoji_score(file_path_str, actual_ext):
    """
    计算候选表情文件的综合质量得分：
    1. APNG/GIF 动图优先 (+1000分)
    2. 主文件优先于 _0, _1 切片 (+200分)
    3. 优先目录权重 (apng > ori/raw > png > thumb/preview)
    4. 文件体积评分 (+0~50分)
    """
    score = 0
    file_base = os.path.splitext(os.path.basename(file_path_str))[0].lower()
    lowered_path = file_path_str.lower().replace('\\', '/')

    # 1. 动图优先
    if actual_ext == 'png' and is_apng_file(file_path_str):
        score += 1000
    elif actual_ext == 'gif':
        score += 1000

    # 2. 主图优先（非切片）
    if not re.search(r'_\d+$', file_base):
        score += 200

    # 3. 目录层级权重
    if '/apng/' in lowered_path or lowered_path.endswith('/apng'):
        score += 100
    elif '/ori/' in lowered_path or '/raw/' in lowered_path:
        score += 80
    elif '/png/' in lowered_path:
        score += 40
    elif '/thumb/' in lowered_path or '/preview/' in lowered_path:
        score -= 100

    # 4. 文件体积加分
    try:
        size_kb = os.path.getsize(file_path_str) / 1024
        score += min(size_kb, 50.0)
    except Exception:
        pass

    return score


def _get_emoji_group_key(file_path_str, emoji_root_path):
    """
    根据相对路径和文件名生成归一化的表情分组键 (Group Key)。
    使得同一个表情的 apng、png、切片 (370_0, 370_1) 归入同一个 Group Key 进行打分竞争。
    """
    try:
        rel_path = os.path.relpath(file_path_str, emoji_root_path)
    except Exception:
        rel_path = os.path.basename(file_path_str)

    rel_dir = os.path.dirname(rel_path)
    file_name = os.path.basename(file_path_str)
    file_base = os.path.splitext(file_name)[0].lower()

    # 去除切片序号 (如 370_0 -> 370)
    clean_name = re.sub(r'_\d+$', '', file_base)

    # 过滤掉通用的子目录名称 (如 apng, png, ori, thumb 等)
    normalized_dir = re.sub(r'[\\/](apng|png|ori|raw|thumb|preview)$', '', rel_dir, flags=re.IGNORECASE)
    if normalized_dir in ['.', 'apng', 'png', 'ori', 'raw', 'thumb', 'preview']:
        normalized_dir = ''

    # 组合分组键
    if normalized_dir:
        group_key = f"{normalized_dir}/{clean_name}".replace('\\', '/').lower().strip('/')
    else:
        group_key = clean_name.lower().strip('/')

    return group_key


def scan_marketface_folder(emoji_root_path):
    """
    扫描并验证 QQNT marketface 原图。

    marketface 原图通常没有扩展名且经过 XOR 处理；只返回能够在内存中
    恢复并通过 GIF 全帧校验的文件路径。缩略图和辅助文件不会进入结果。
    """
    emoji_path = Path(emoji_root_path)
    if not emoji_path.exists():
        return []

    recovered_files = []
    try:
        for root, _, files in os.walk(str(emoji_path)):
            for filename in files:
                file_path = os.path.join(root, filename)
                if not is_marketface_candidate(file_path):
                    continue
                if recover_marketface_data(file_path) is not None:
                    recovered_files.append(file_path)
    except Exception:
        return []

    return sorted(recovered_files)


def scan_emoji_folder(emoji_root_path, selected_folder):
    """
    针对不同 QQNT 表情分类，全量安全扫描并利用智能评分算法筛选出最优质的表情图片文件列表。
    自动剔除冗余子帧/切片，动图自动优选，且保证不会遗漏任何有效表情。
    """
    if selected_folder.lower() == "marketface":
        return scan_marketface_folder(emoji_root_path)
    emoji_path = Path(emoji_root_path)
    if not emoji_path.exists():
        return []

    # 1. 全量安全深度遍历，确保任何层级的文件都不会遗漏
    raw_files = []
    try:
        for root, dirs, files in os.walk(str(emoji_path)):
            for f in files:
                raw_files.append(os.path.join(root, f))
    except Exception:
        return []

    # 2. 真实图片校验与分组智能竞争
    # groups: { group_key: (best_file_path, best_score) }
    groups = {}

    for file_path_str in raw_files:
        actual_ext = get_actual_extension(file_path_str)
        if not actual_ext:
            # 不是有效图片格式（如 .json, .ini, .db），直接忽略
            continue

        group_key = _get_emoji_group_key(file_path_str, emoji_path)
        score = _calculate_emoji_score(file_path_str, actual_ext)

        if group_key not in groups:
            groups[group_key] = (file_path_str, score)
        else:
            _, existing_score = groups[group_key]
            if score > existing_score:
                groups[group_key] = (file_path_str, score)

    # 3. 提取每个分组的最佳表情文件
    best_files = [val[0] for val in groups.values()]
    best_files.sort()
    return best_files
