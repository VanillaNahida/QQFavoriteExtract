#!/usr/bin/env python3
import os
import sys
import subprocess
import re

def extract_version_from_tag():
    """从 GITHUB_REF 环境变量中提取版本号"""
    github_ref = os.environ.get('GITHUB_REF', '')
    print(f"GITHUB_REF: {github_ref}")
    
    if github_ref:
        # 匹配 refs/tags/v1.4.2 或 refs/tags/1.4.2
        match = re.search(r'refs/tags/(?:v)?(\d+\.\d+\.\d+(?:\.\d+)?)', github_ref)
        if match:
            version = match.group(1)
            print(f"Extracted version: {version}")
            return version
    
    # 如果没有找到标签，尝试从当前目录读取版本信息
    try:
        with open('version.txt', 'r') as f:
            version = f.read().strip()
            print(f"Read version from version.txt: {version}")
            return version
    except FileNotFoundError:
        pass
    
    # 最后尝试从 pyproject.toml 或 setup.py 中读取
    try:
        import tomli
        with open('pyproject.toml', 'rb') as f:
            data = tomli.load(f)
            version = data.get('project', {}).get('version', '1.0.0')
            print(f"Read version from pyproject.toml: {version}")
            return version
    except:
        pass
    
    print("Warning: No version found, using default 1.0.0")
    return "1.0.0"

def convert_to_nuitka_version(version):
    """转换版本号为 Nuitka 格式 (1.4.2 -> 1,4,2,0)"""
    parts = version.split('.')
    
    # 确保有4个部分
    while len(parts) < 4:
        parts.append('0')
    
    # 限制最多4个部分
    parts = parts[:4]
    
    nuitka_version = ','.join(parts)
    print(f"Nuitka version format: {nuitka_version}")
    return nuitka_version

def build_with_nuitka():
    """使用 Nuitka 构建 EXE"""
    version = extract_version_from_tag()
    nuitka_version = convert_to_nuitka_version(version)
    
    # 设置环境变量供后续步骤使用
    os.environ['VERSION'] = version
    with open(os.environ['GITHUB_ENV'], 'a') as f:
        f.write(f"VERSION={version}\n")
    
    print(f"\n{'='*60}")
    print(f"Building version: {version}")
    print(f"Nuitka version format: {nuitka_version}")
    print(f"{'='*60}\n")
    
    # 构建命令
    cmd = [
        'nuitka',
        '--onefile',
        '--standalone',
        '--windows-console-mode=disable',
        '--windows-icon-from-ico=img/icon.ico',
        '--copyright=VanillaNahida',
        '--lto=yes',
        '--enable-plugin=pyqt5',
        '--enable-plugin=upx',
        '--onefile-no-compression',
        f'--file-version={nuitka_version}',
        f'--product-version={nuitka_version}',
        'main_gui.py'
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("\nBuild completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error code: {e.returncode}")
        return False
    except Exception as e:
        print(f"\nUnexpected error during build: {str(e)}")
        return False

if __name__ == '__main__':
    success = build_with_nuitka()
    sys.exit(0 if success else 1)