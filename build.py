#!/usr/bin/env python3
"""QQFavoriteExtract 构建脚本。

支持两种打包器与三种打包模式：
  打包器：--nuitka（默认） / --pyinstaller
  模式：  --single（仅单文件） / --multi（仅多文件 zip） / --both（默认，两者都打）

在 GitHub Actions 环境中的完整流程：
  解析版本号（--build-version / BUILD_VERSION / GITHUB_REF 标签 / version.txt / pyproject.toml）
  -> 更新 src/__init__.py 的 __version__
  -> 按所选打包器与模式构建并重命名产物：
     单文件 exe：QQFavoriteExtract_<version>_<packager>_onefile.exe
     多文件 zip：QQFavoriteExtract_<version>_<packager>_portable.zip（文件位于 zip 根目录）
  -> 将 version / nuitka_version 写入 GITHUB_OUTPUT 供工作流后续步骤使用

本地直接运行 `uv run python build.py` 时仅构建，不修改 src/__init__.py。
"""

import argparse
import importlib.util
import os
import re
import subprocess
import sys
import zipfile

# GitHub Actions Windows runner 控制台代码页为 cp1252，打印中文会报
# UnicodeEncodeError；强制 UTF-8 输出（Python 3.7+ 支持 reconfigure）
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        try:
            _stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass


def parse_args():
    """解析命令行参数。

    --nuitka / --pyinstaller    打包器（默认 Nuitka）
    --single / --multi / --both 打包模式（默认 both）
    --build-version VERSION     指定版本号（优先级最高）
    """
    parser = argparse.ArgumentParser(description='QQFavoriteExtract 构建脚本')
    parser.add_argument('--build-version', default=None,
                        help='指定构建版本号（优先级最高）')
    packager = parser.add_mutually_exclusive_group()
    packager.add_argument('--nuitka', action='store_true',
                          help='使用 Nuitka 打包（默认）')
    packager.add_argument('--pyinstaller', action='store_true',
                          help='使用 PyInstaller 打包')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--single', action='store_true', help='仅打包单文件版')
    mode.add_argument('--multi', action='store_true', help='仅打包多文件版')
    mode.add_argument('--both', action='store_true',
                      help='同时打包单文件与多文件版（默认）')
    return parser.parse_args()


def extract_version(build_version=None):
    """按优先级解析版本号：--build-version 参数 > BUILD_VERSION 环境变量 >
    GITHUB_REF 标签 > version.txt > pyproject.toml。"""
    if build_version and build_version.strip():
        return build_version.strip()
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


def _run_cmd(cmd):
    """运行子进程命令，打印命令并返回是否成功。"""
    print(f"运行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode == 0


# ---------------- Nuitka ----------------

def _nuitka_common(version, nuitka_version):
    """Nuitka 公共参数（不含模式标志与 onefile 专属参数）。"""
    return [
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
        '--include-data-files=LICENSE=LICENSE',
        '--include-data-files=README.md=README.md',
        '--include-data-dir=img=img',
        '--include-data-dir=src/assets=src/assets',
        # 内置 UI 字体（常规+粗体）随 exe 内嵌
        '--include-data-dir=src/fonts=src/fonts',
        f'--file-version={nuitka_version}',
        f'--product-version={nuitka_version}',
        '--product-name=QQFavoriteExtract',
        '--file-description=QQ表情包导出工具',
        'src/main.py',
    ]


def build_nuitka_single(version, nuitka_version):
    """Nuitka onefile 构建（单文件 exe），返回是否成功。"""
    cmd = ([sys.executable, '-m', 'nuitka', '--onefile']
           + _nuitka_common(version, nuitka_version))
    cmd.append(f'--onefile-tempdir-spec={{TEMP}}\\qqfavorite_{version}')
    return _run_cmd(cmd)


def build_nuitka_multi(version, nuitka_version):
    """Nuitka standalone 构建（多文件目录），返回是否成功。"""
    cmd = ([sys.executable, '-m', 'nuitka', '--standalone']
           + _nuitka_common(version, nuitka_version))
    return _run_cmd(cmd)


# ---------------- PyInstaller ----------------

def pyinstaller_available():
    """检测 PyInstaller 是否已安装（importlib 方式，兼容 venv 内 python -m PyInstaller）。"""
    return importlib.util.find_spec('PyInstaller') is not None


def _pyinstaller_version_file(version):
    """生成 PyInstaller 版本文件内容，字段与 Nuitka 元数据保持一致。

    对应关系：
      Nuitka --file-version / --product-version  -> FixedFileInfo + FileVersion/ProductVersion
      Nuitka --product-name                      -> ProductName / InternalName / OriginalFilename
      Nuitka --copyright                         -> LegalCopyright
      Nuitka --company-name                      -> CompanyName
      Nuitka --file-description                  -> FileDescription

    注意：必须同时提供 VarFileInfo\\Translation，且其语言/代码页（0x0409/0x04B0）
    与 StringTable 的 '040904B0' 对应。Windows 资源管理器“详细信息”页依据
    Translation 选择要展示的字符串块；缺少它时只会显示 FixedFileInfo 的数字文件版本，
    版权/产品名称/文件说明等字符串在属性页中全部为空白。
    """
    ver = tuple(int(x) for x in version.split('.'))
    return f'''# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={ver!r},
    prodvers={ver!r},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [StringStruct('CompanyName', 'VanillaNahida'),
           StringStruct('FileDescription', 'QQ表情包导出工具'),
           StringStruct('FileVersion', '{version}'),
           StringStruct('InternalName', 'QQFavoriteExtract'),
           StringStruct('LegalCopyright', 'VanillaNahida'),
           StringStruct('OriginalFilename', 'QQFavoriteExtract.exe'),
           StringStruct('ProductName', 'QQFavoriteExtract'),
           StringStruct('ProductVersion', '{version}')])
      ]),
    # 语言映射：0x0409=英语(美国)，0x04B0=1200(Unicode)，与上方 StringTable '040904B0' 对应
    # 缺少此块时资源管理器“详细信息”页无法关联字符串，版权等字段会显示为空白
    VarFileInfo([VarStruct('Translation', [0x0409, 0x04B0])])
  ]
)
'''


def _write_pyinstaller_version_file(version):
    """将版本文件写入 build/pyinstaller_version.txt（UTF-8 BOM，PyInstaller 要求）。

    返回文件路径。
    """
    os.makedirs('build', exist_ok=True)
    path = os.path.join('build', 'pyinstaller_version.txt')
    with open(path, 'w', encoding='utf-8-sig') as f:
        f.write(_pyinstaller_version_file(version))
    return path


def _pyinstaller_cmd(onefile, version_file):
    """构造 PyInstaller 构建命令（onefile=True 单文件，False 多文件目录）。

    注意：PyInstaller 6.x 会相对 spec 文件所在目录（--specpath）解析
    --add-data 的源路径，因此源路径必须使用绝对路径，否则找不到文件。
    """
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile' if onefile else '--onedir',
        '--noconfirm',
        '--clean',
        '--windowed',                       # 无控制台窗口
        '--name=QQFavoriteExtract',
        '--distpath=dist',
        '--workpath=build/pyinstaller',
        '--specpath=build/pyinstaller',
        f'--icon={os.path.abspath("img/icon.ico")}',
        f'--version-file={os.path.abspath(version_file)}',  # 与 Nuitka 一致的 exe 版本元数据
        # 数据文件按源码相对布局放置（与 get_asset_path/get_font_path 的定位方式一致）
        f'--add-data={os.path.abspath("src/assets")};src/assets',
        f'--add-data={os.path.abspath("src/fonts")};src/fonts',
        f'--add-data={os.path.abspath("img")};img',
        f'--add-data={os.path.abspath("LICENSE")};LICENSE',
        f'--add-data={os.path.abspath("README.md")};README.md',
        # qfluentwidgets 的 qss/图标等数据需一并收集
        '--collect-data=qfluentwidgets',
        os.path.abspath('src/main.py'),
    ]
    return cmd


def build_pyinstaller_single(version):
    """PyInstaller onefile 构建，返回是否成功。"""
    version_file = _write_pyinstaller_version_file(version)
    return _run_cmd(_pyinstaller_cmd(onefile=True, version_file=version_file))


def build_pyinstaller_multi(version):
    """PyInstaller onedir 构建，返回是否成功。"""
    version_file = _write_pyinstaller_version_file(version)
    return _run_cmd(_pyinstaller_cmd(onefile=False, version_file=version_file))


# ---------------- 产物整理 ----------------

def rename_exe(version, packager):
    """将 dist 下最新生成的 exe 重命名为 QQFavoriteExtract_<version>_<packager>_onefile.exe。

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
    target = os.path.join(dist, f'QQFavoriteExtract_{version}_{packager}_onefile.exe')
    if os.path.abspath(latest) != os.path.abspath(target):
        os.replace(latest, target)
    return target


def zip_standalone(version, packager, src_dir):
    """将多文件产物目录压缩为 QQFavoriteExtract_<version>_<packager>_portable.zip。

    返回 zip 路径；产物目录不存在时返回 None。
    """
    if not os.path.isdir(src_dir):
        return None
    # Nuitka standalone 主程序名为 main.exe，重命名为 QQFavoriteExtract.exe 更符合分发习惯
    main_exe = os.path.join(src_dir, 'main.exe')
    app_exe = os.path.join(src_dir, 'QQFavoriteExtract.exe')
    if os.path.exists(main_exe) and not os.path.exists(app_exe):
        os.replace(main_exe, app_exe)

    target = os.path.join('dist', f'QQFavoriteExtract_{version}_{packager}_portable.zip')
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src_dir):
            for name in files:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, src_dir)
                zf.write(full, rel)  # 直接放 zip 根目录
    return target


# ---------------- 按模式编排 ----------------

def build_single(packager, version, nuitka_version):
    """构建单文件版并重命名，返回是否成功。"""
    if packager == 'nuitka':
        if not build_nuitka_single(version, nuitka_version):
            return False
    else:
        if not build_pyinstaller_single(nuitka_version):
            return False
    exe = rename_exe(version, packager)
    if exe is None:
        print('\n构建完成但未在 dist 找到单文件 exe')
        return False
    size_mb = os.path.getsize(exe) / (1024 * 1024)
    print(f'\n单文件版构建成功: {exe} ({size_mb:.2f} MB)')
    return True


def build_multi(packager, version, nuitka_version):
    """构建多文件版并压缩为 zip，返回是否成功。"""
    if packager == 'nuitka':
        if not build_nuitka_multi(version, nuitka_version):
            return False
        src_dir = os.path.join('dist', 'main.dist')
    else:
        if not build_pyinstaller_multi(nuitka_version):
            return False
        src_dir = os.path.join('dist', 'QQFavoriteExtract')
    zip_target = zip_standalone(version, packager, src_dir)
    if zip_target is None:
        print('\n未找到多文件产物目录，跳过 zip 打包')
        return False
    size_mb = os.path.getsize(zip_target) / (1024 * 1024)
    print(f'\n多文件版打包成功: {zip_target} ({size_mb:.2f} MB)')
    return True


def main():
    args = parse_args()
    version = extract_version(args.build_version)
    version, nuitka_version = normalize_version(version)
    packager = 'pyinstaller' if args.pyinstaller else 'nuitka'
    mode = 'single' if args.single else 'multi' if args.multi else 'both'

    print(f'\n{"=" * 60}')
    print(f'构建版本: {version}')
    print(f'打包器: {packager}')
    print(f'打包模式: {mode}')
    print(f'{"=" * 60}\n')

    if packager == 'pyinstaller' and not pyinstaller_available():
        print('错误: 未安装 PyInstaller，请先执行 `uv add --dev pyinstaller`')
        return 1

    # 仅在 GitHub Actions 环境更新源码版本号（保证打包产物内置版本与发布版本一致）
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        changed = update_version_in_src(version)
        print(f'src/__init__.py 版本号已更新为 {version}' if changed
              else f'src/__init__.py 版本号已为 {version}，无需修改')

    # 供工作流后续步骤（上传/发布）读取版本号
    write_github_output(version=version, nuitka_version=nuitka_version)

    ok = True
    if mode in ('single', 'both') and not build_single(packager, version, nuitka_version):
        ok = False
    if mode in ('multi', 'both') and not build_multi(packager, version, nuitka_version):
        ok = False
    if not ok:
        print('\n构建失败')
        return 1
    print('\n全部构建完成')
    return 0


if __name__ == '__main__':
    sys.exit(main())
