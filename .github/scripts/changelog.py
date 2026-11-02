#!/usr/bin/env python3
"""生成 Release 更新日志：把「上一个 tag 到本次 tag」之间的提交按 Conventional Commits 归类。

由 .github/workflows/release.yml 在打 tag 后调用，也可以本地手动跑：

    python .github/scripts/changelog.py --to v1.5.6 --repo VanillaNahida/QQFavoriteExtract

输出的 Markdown 结构：

    ## 更新说明

    ### ✨ 新功能
    - 新增「导出完成后自动打开文件夹」设置

    **完整变更**：[v1.5.5...v1.5.6](https://github.com/owner/repo/compare/v1.5.5...v1.5.6)

再（可选）把 .github/templates/release-notes-tail.md 里的 <版本>、
{{PYINSTALLER_ONEFILE_URL}}、{{PYINSTALLER_PORTABLE_URL}} 替换成真实下载直链后追加在末尾，
这样 Release 正文与旧版本保持一致的排版。
"""

import argparse
import os
import re
import subprocess
import sys

# GitHub Actions Windows runner 控制台代码页为 cp1252，打印中文会报
# UnicodeEncodeError；强制 UTF-8 输出（与 build.py 一致）
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        try:
            _stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

# 提交类型 -> 小节标题（同一标题的类型会合并；顺序即小节顺序）
SECTION_TITLES = [
    ('feat', '✨ 新功能'),
    ('fix', '🐛 问题修复'),
    ('perf', '⚡ 性能优化'),
    ('refactor', '♻️ 重构'),
    ('style', '💄 样式调整'),
    ('docs', '📖 文档'),
    ('test', '✅ 测试'),
    ('build', '🔧 构建 / CI'),
    ('ci', '🔧 构建 / CI'),
    ('revert', '⏪ 回滚'),
]
FALLBACK_TITLE = '🗂 其他改动'
BREAKING_TITLE = '⚠️ 破坏性变更'

# 小节展示顺序：破坏性变更置顶 → 其余按类型顺序 → 未归类提交垫底
SECTION_ORDER = [BREAKING_TITLE]
for _section_type, _section_title in SECTION_TITLES:
    if _section_title not in SECTION_ORDER:
        SECTION_ORDER.append(_section_title)
SECTION_ORDER.append(FALLBACK_TITLE)

# 版本号维护类提交不进更新日志（否则每次发版都会出现一条「更新版本号至 x.y.z」）
_VERSION_NOISE = re.compile(r'(更新|升级)?\s*版本号|bump(\s+the)?\s+version|^release\b', re.IGNORECASE)

_CONVENTIONAL = re.compile(r'^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^()]*)\))?(?P<breaking>!)?\s*[:：]\s*(?P<subject>.+)$')


def _git(*args):
    """执行 git 命令并返回 stdout（失败返回空串，由调用方决定默认值）。"""
    try:
        result = subprocess.run(
            ['git', *args],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=False,
        )
    except OSError:
        return ''
    if result.returncode != 0:
        return ''
    return result.stdout


def _ref_exists(ref):
    """判断 git 引用（标签 / 分支 / 提交）是否可解析。"""
    if not ref:
        return False
    return bool(_git('rev-parse', '--verify', '--quiet', f'{ref}^{{commit}}').strip())


def version_key(text):
    """把版本字符串解析为可比较元组：v1.5.10 -> (1, 5, 10)；解析不出数字时为 ()。"""
    parts = re.findall(r'\d+', str(text).strip().lstrip('vV'))
    return tuple(int(p) for p in parts[:4])


def sorted_tags():
    """所有 v* 标签，按版本号从小到大排序。"""
    tags = [t.strip() for t in _git('tag', '--list', 'v*').splitlines() if t.strip()]
    return sorted(tags, key=version_key)


def resolve_from_tag(to_tag, tags):
    """返回上一个标签；to_tag 是最早的标签时返回空串（表示从头开始统计）。"""
    to_key = version_key(to_tag)
    previous = ''
    for tag in tags:
        key = version_key(tag)
        if not key:
            continue
        if tag == to_tag:
            break
        if to_key and key >= to_key:
            # to_tag 不在标签列表里（例如用 --to HEAD 预览）时，取版本号更小的最后一个标签
            break
        previous = tag
    return previous


def collect_commits(range_spec):
    """读取提交：返回 [(sha, subject, author, iso_date)]，跳过合并提交。"""
    out = _git('log', '--no-merges', '--pretty=format:%H%x1f%s%x1f%an%x1f%aI', range_spec)
    commits = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split('\x1f')
        if len(parts) < 2:
            continue
        sha, subject = parts[0].strip(), parts[1].strip()
        author = parts[2].strip() if len(parts) > 2 else ''
        date = parts[3].strip() if len(parts) > 3 else ''
        if subject:
            commits.append((sha, subject, author, date))
    return commits


def parse_subject(subject):
    """拆解 Conventional Commits；不符合规范的返回 (None, '', False, subject)。"""
    match = _CONVENTIONAL.match(subject)
    if not match:
        return None, '', False, subject
    return (
        match.group('type').lower(),
        (match.group('scope') or '').strip(),
        bool(match.group('breaking')),
        match.group('subject').strip(),
    )


def is_version_noise(subject):
    """判断是否为「更新版本号」这类发版噪音提交。"""
    return bool(_VERSION_NOISE.search(subject))


def group_commits(commits):
    """按小节归组：返回 [(标题, [条目...])]，只保留非空小节，顺序固定。"""
    title_of_type = dict(SECTION_TITLES)
    buckets = {}
    for _, subject, _, _ in commits:
        if is_version_noise(subject):
            continue
        commit_type, scope, breaking, text = parse_subject(subject)
        title = BREAKING_TITLE if breaking else title_of_type.get(commit_type or '', FALLBACK_TITLE)
        buckets.setdefault(title, [])
        line = f'- **{scope}**：{text}' if scope else f'- {text}'
        if line not in buckets[title]:  # 同一条描述重复提交时只保留一条
            buckets[title].append(line)
    return [(title, buckets[title]) for title in SECTION_ORDER if buckets.get(title)]


def render_body(commits, from_tag, to_tag, repo):
    """渲染 Release 正文（不含下载说明尾巴）。"""
    groups = group_commits(commits)
    if not groups:
        return '## 更新说明\n\n本次发布没有可展示的提交记录。\n'

    lines = ['## 更新说明', '']
    for title, items in groups:
        lines.append(f'### {title}')
        lines.extend(items)
        lines.append('')

    if repo:
        if from_tag:
            range_text = f'{from_tag}...{to_tag}'
        else:
            range_text = to_tag
        lines.append(f'**完整变更**：[{range_text}](https://github.com/{repo}/compare/{range_text})')
        lines.append('')
    return '\n'.join(lines)


def render_tail(template_path, version, base_url):
    """读取下载说明模板并替换占位符；文件不存在时返回空串。"""
    if not template_path or not os.path.isfile(template_path):
        return ''
    with open(template_path, encoding='utf-8') as f:
        template = f.read()
    oneline = f'{base_url}/QQFavoriteExtract_{version}_pyinstaller_onefile.exe'
    portable = f'{base_url}/QQFavoriteExtract_{version}_pyinstaller_portable.zip'
    return (
        template.replace('<版本>', version)
        .replace('{{PYINSTALLER_ONEFILE_URL}}', oneline)
        .replace('{{PYINSTALLER_PORTABLE_URL}}', portable)
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='按 Conventional Commits 生成 Release 更新日志')
    parser.add_argument('--to', default=None, help='本次发布标签，默认取 GITHUB_REF_NAME / 最新的 v* 标签')
    parser.add_argument('--from', dest='from_tag', default=None, help='起始标签，默认自动取比 --to 小的上一个标签')
    parser.add_argument(
        '--repo', default=os.environ.get('GITHUB_REPOSITORY', ''), help='OWNER/REPO，用于生成「完整变更」比对链接'
    )
    parser.add_argument('--version', default='', help='用于替换下载说明里的 <版本>，默认取 --to 去掉 v')
    parser.add_argument('--template', default='', help='下载说明模板路径（.github/templates/release-notes-tail.md）')
    parser.add_argument('--base-url', default='', help='Release 资产下载根地址，用于替换模板里的下载占位符')
    parser.add_argument('--out', default='', help='输出文件路径，默认打印到标准输出')
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    tags = sorted_tags()
    to_tag = args.to or os.environ.get('GITHUB_REF_NAME', '') or (tags[-1] if tags else 'HEAD')
    version = args.version or to_tag.lstrip('vV')

    from_tag = args.from_tag or resolve_from_tag(to_tag, tags)
    # 手动触发时目标 tag 可能还没创建（Release 发布时才由 gh 创建），此时以 HEAD 作为范围终点
    end_ref = to_tag if _ref_exists(to_tag) else 'HEAD'
    if end_ref != to_tag:
        print(f'提示：标签 {to_tag} 尚不存在，改为按 {end_ref} 统计提交范围', file=sys.stderr)
    range_spec = f'{from_tag}..{end_ref}' if from_tag else end_ref

    commits = collect_commits(range_spec)
    body = render_body(commits, from_tag, to_tag, args.repo)
    tail = render_tail(args.template, version, args.base_url)
    if tail:
        body = body.rstrip() + '\n\n' + tail

    if args.out:
        with open(args.out, 'w', encoding='utf-8', newline='\n') as f:
            f.write(body)
        print(f'更新日志已写入 {args.out}（{len(commits)} 条提交，范围 {range_spec}）')
    else:
        print(body)
    return 0


if __name__ == '__main__':
    sys.exit(main())
