#!/usr/bin/env python3
"""QQFavoriteExtract 构建脚本。

在 GitHub Actions 环境中的完整流程：
  解析版本号（--build-version / BUILD_VERSION / GITHUB_REF 标签 / version.txt / pyproject.toml）
  -> 更新 src/__init__.py 的 __version__
  -> Nuitka 构建 onefile exe
  -> 重命名为 QQFavoriteExtract_<version>.exe
  -> 将 version / nuitka_version 写入 GITHUB_OUTPUT 供工作流后续步骤（打包/上传）使用

本地直接运行 `uv run python build.py` 时仅构建，不修改 src/__init__.py。
"""

import os
import re
import subprocess
import sys


def extract_version():
    """按优先级解析版本号：--build-version 参数 > BUILD_VERSION 环境变量 >
    GITHUB_REF 标签 > version.txt > pyproject.toml。"""
    args = sys.argv[1:]
    if '--build-version' in args:
        idx = args.index('--build-version')
        if idx + 1 < len(args):
            return args[idx + 1].strip()
    if os.environ.get('BUILD_VERSION', '').strip():
        return os.environ['BUILD_VERSION'].strip()
    github_ref = os.environ.get('GITHUB_REF', '')
    if github_ref:
        # 匹配 refs/tags/v1.4.2 或 refs/tags/1.4.2
        match = re.search(r'refs/tags/(?:v)?(\d+\.\d+\.\d+(?:\.\d+)?)', github_ref)
        if match:
            return match.group(1)
    try:
        with open('version.txt', encoding='utf-8') as f:
            version = f.read().strip()
            if version:
                return version
    except FileNotFoundError:
        pass
    try:
        import tomllib
        with open('pyproject.toml', 'rb') as f:
            version = tomllib.load(f).get('project', {}).get('version')
            if version:
                return str(version)
    except Exception:
        pass
    print('警告: 未找到版本号，使用默认 1.0.0')
    return '1.0.0'


def normalize_version(version):
    """校验版本号并补齐为 4 段（1.4.2 -> 1.4.2.0，--file-version 需点分格式）。

    返回 (展示用版本, nuitka 版本格式)。
    """
    if not re.match(r'\d+(?:\.\d+)+', version):
        raise ValueError(f'无效的版本号: {version}')
    parts = version.split('.')[:4]
    while len(parts) < 4:
        parts.append('0')
    return version, '.'.join(parts)


def update_version_in_src(version):
    """将 src/__init__.py 中的 __version__ 更新为指定版本。

    返回是否发生了修改。
    """
    path = os.path.join('src', '__init__.py')
    with open(path, encoding='utf-8') as f:
        content = f.read()
    new_content = re.sub(
        r'__version__\s*=\s*["\'][^"\']*["\']',
        f'__version__ = "{version}"',
        content,
        count=1,
    )
    if new_content == content:
        return False
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True


def write_github_output(**kwargs):
    """向 GITHUB_OUTPUT 写入键值（非 CI 环境无此变量时跳过）。"""
    out_path = os.environ.get('GITHUB_OUTPUT')
    if not out_path:
        return
    with open(out_path, 'a', encoding='utf-8') as f:
        for key, value in kwargs.items():
            f.write(f'{key}={value}\n')


def build(version, nuitka_version):
    """执行 Nuitka onefile 构建，返回是否成功。"""
    cmd = [
        sys.executable, '-m', 'nuitka',
        '--onefile',
        '--remove-output',
        '--assume-yes-for-downloads',
        '--output-dir=dist',
        '--windows-console-mode=disable',
        '--windows-icon-from-ico=img/icon.ico',
        '--copyright=VanillaNahida',
        '--company-name=VanillaNahida',
        '--lto=yes',
        '--enable-plugin=pyqt6',
        '--include-package=src',
        f'--onefile-tempdir-spec={{TEMP}}\\qqfavorite_{version}',
        '--include-data-files=LICENSE=LICENSE',
        '--include-data-files=README.md=README.md',
        '--include-data-dir=img=img',
        '--include-data-dir=src/assets=src/assets',
        f'--file-version={nuitka_version}',
        f'--product-version={nuitka_version}',
        '--product-name=QQFavoriteExtract',
        '--file-description=QQ表情包导出工具',
        'src/main.py',
    ]
    print(f"运行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode == 0


def rename_exe(version):
    """将 dist 下最新生成的 exe 重命名为 QQFavoriteExtract_<version>.exe。

    返回最终 exe 路径；无 exe 时返回 None。
    """
    dist = 'dist'
    if not os.path.isdir(dist):
        return None
    exes = [
        os.path.join(dist, f)
        for f in os.listdir(dist)
        if f.lower().endswith('.exe')
    ]
    if not exes:
        return None
    latest = max(exes, key=os.path.getmtime)
    target = os.path.join(dist, f'QQFavoriteExtract_{version}.exe')
    if os.path.abspath(latest) != os.path.abspath(target):
        os.replace(latest, target)
    return target


def main():
    version = extract_version()
    version, nuitka_version = normalize_version(version)
    print(f'\n{"=" * 60}')
    print(f'构建版本: {version}')
    print(f'Nuitka 版本格式: {nuitka_version}')
    print(f'{"=" * 60}\n')

    # 仅在 GitHub Actions 环境更新源码版本号（保证打包产物内置版本与发布版本一致）
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        changed = update_version_in_src(version)
        print(f'src/__init__.py 版本号已更新为 {version}' if changed
              else f'src/__init__.py 版本号已为 {version}，无需修改')

    # 供工作流后续步骤（zip 打包 / 上传）读取
    write_github_output(version=version, nuitka_version=nuitka_version)

    if not build(version, nuitka_version):
        print('\n构建失败')
        return 1

    target = rename_exe(version)
    if target is None:
        print('\n构建完成但未在 dist 找到可执行文件')
        return 1
    size_mb = os.path.getsize(target) / (1024 * 1024)
    print(f'\n构建成功: {target} ({size_mb:.2f} MB)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
