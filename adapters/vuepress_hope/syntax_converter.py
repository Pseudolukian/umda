#!/usr/bin/env python3
"""
VuePress Hope syntax converter.

Converts mkdocs-style admonitions and emoji shortcodes to VuePress Hope hint containers.
Run as post-processing step on docs in src/ after copy.
"""
from __future__ import annotations

import re
from pathlib import Path


def convert_admonitions(content: str) -> str:
    """Convert mkdocs admonition syntax to VuePress Hope hint containers."""

    # 1. Emoji collapsible: ℹ️🔽 "Title" + indented body → ::: details Title\n body\n:::
    content = _convert_emoji_blocks(content, r'ℹ️🔽\s*"?(.+?)"?\s*$', 'details')

    # 2. Emoji info: ℹ️ "Title" → ::: info Title
    content = _convert_emoji_blocks(content, r'ℹ️\s*"?(.+?)"?\s*$', 'info')

    # 3. Emoji warning: ⚠️ "Title" → ::: warning Title  
    content = _convert_emoji_blocks(content, r'⚠️\s*"?(.+?)"?\s*$', 'warning')

    # 4. Emoji dropdown: 🔽 "Title" → ::: details Title
    content = _convert_emoji_blocks(content, r'🔽\s*"?(.+?)"?\s*$', 'details')

    # 5. mkdocs ??? note "Title" (collapsible) → ::: details Title
    content = _convert_mkdocs_admonition(content, r'^\?\?\?\+?\s+\w+\s+"?(.+?)"?\s*$', 'details')

    # 6. mkdocs !!! note/warning/notice "Title" → ::: info/warning Title
    content = _convert_mkdocs_admonition(content, r'^!!!\s+warning\s+"?(.+?)"?\s*$', 'warning')
    content = _convert_mkdocs_admonition(content, r'^!!!\s+note\s+"?(.+?)"?\s*$', 'info')
    content = _convert_mkdocs_admonition(content, r'^!!!\s+notice\s*$', 'info', default_title='')
    content = _convert_mkdocs_admonition(content, r'^!!!\s+\w+\s+"?(.+?)"?\s*$', 'info')

    return content


def _convert_emoji_blocks(content: str, pattern: str, container_type: str) -> str:
    """Convert emoji-prefixed blocks with indented body to ::: containers."""
    lines = content.split('\n')
    result = []
    i = 0

    regex = re.compile(pattern, re.MULTILINE)

    while i < len(lines):
        m = regex.match(lines[i])
        if m:
            title = m.group(1) if m.lastindex else ''
            result.append(f'::: {container_type} {title}'.rstrip())
            i += 1

            # Skip blank line after header
            if i < len(lines) and lines[i].strip() == '':
                result.append('')
                i += 1

            # Collect indented body (4 spaces or tab)
            while i < len(lines) and (lines[i].startswith('    ') or lines[i].startswith('\t') or lines[i].strip() == ''):
                line = lines[i]
                if line.strip() == '':
                    # Check if next non-empty line is still indented
                    j = i + 1
                    while j < len(lines) and lines[j].strip() == '':
                        j += 1
                    if j < len(lines) and (lines[j].startswith('    ') or lines[j].startswith('\t')):
                        result.append('')
                        i += 1
                    else:
                        break
                else:
                    # Remove 4-space indent
                    if line.startswith('    '):
                        result.append(line[4:])
                    elif line.startswith('\t'):
                        result.append(line[1:])
                    else:
                        result.append(line)
                    i += 1

            result.append(':::')
            result.append('')
        else:
            result.append(lines[i])
            i += 1

    return '\n'.join(result)


def _convert_mkdocs_admonition(content: str, pattern: str, container_type: str, default_title: str | None = None) -> str:
    """Convert mkdocs !!! / ??? admonition with indented body to ::: containers."""
    lines = content.split('\n')
    result = []
    i = 0

    regex = re.compile(pattern, re.MULTILINE)

    while i < len(lines):
        m = regex.match(lines[i])
        if m:
            title = m.group(1) if m.lastindex else (default_title if default_title is not None else '')
            result.append(f'::: {container_type} {title}'.rstrip())
            i += 1

            # Skip blank line after header
            if i < len(lines) and lines[i].strip() == '':
                result.append('')
                i += 1

            # Collect indented body
            while i < len(lines) and (lines[i].startswith('    ') or lines[i].startswith('\t') or lines[i].strip() == ''):
                line = lines[i]
                if line.strip() == '':
                    j = i + 1
                    while j < len(lines) and lines[j].strip() == '':
                        j += 1
                    if j < len(lines) and (lines[j].startswith('    ') or lines[j].startswith('\t')):
                        result.append('')
                        i += 1
                    else:
                        break
                else:
                    if line.startswith('    '):
                        result.append(line[4:])
                    elif line.startswith('\t'):
                        result.append(line[1:])
                    else:
                        result.append(line)
                    i += 1

            result.append(':::')
            result.append('')
        else:
            result.append(lines[i])
            i += 1

    return '\n'.join(result)


def process_includes(content: str, md_file: Path, src_root: Path) -> str:
    """
    Replace ➡️ (path/to/file.md) with the actual file content.
    Resolves path relative to src_root (the doc source root, e.g. stormbpmn_new_doc/).
    """
    pattern = re.compile(r'^➡️\s*\((.+?)\)\s*$', re.MULTILINE)

    def replacer(m):
        file_path = m.group(1).strip()
        # Resolve relative to src_root
        target = src_root / file_path
        if not target.exists():
            # Try case-insensitive match
            parent = target.parent
            if parent.exists():
                for f in parent.iterdir():
                    if f.name.lower() == target.name.lower():
                        target = f
                        break
        if target.exists():
            included = target.read_text(encoding='utf-8').rstrip()
            return included
        else:
            print(f"  [include] WARNING: file not found: {target} (referenced in {md_file})")
            return m.group(0)  # leave unchanged

    return pattern.sub(replacer, content)


def convert_frontmatter_refs(content: str) -> str:
    """Replace {{ $frontmatter.xxx }} with <Fm p="xxx" /> for VuePress v-html rendering."""
    pattern = r'\{\{\s*\$frontmatter\.([\w.]+)\s*\}\}'
    return re.sub(pattern, r'<Fm p="\1" />', content)


def convert_fontawesome(content: str) -> str:
    """Replace :fontawesome-xxx:{ .class } shortcodes with HTML <i> tags."""
    # Map prefix to FA class prefix
    def _fa_replacer(m):
        style = m.group(1)   # solid, brands, regular
        name = m.group(2)    # arrow-right, youtube, etc.
        prefix = 'fa-' + style
        return f'<i class="{prefix} fa-{name}"></i>'

    # Match :fontawesome-solid-xxx:{ .class } or :fontawesome-solid-xxx:
    pattern = r':fontawesome-(solid|brands|regular)-([a-z0-9-]+):(\{[^}]*\}\s*)?'
    return re.sub(pattern, _fa_replacer, content)


def process_dir(src_dir: Path, src_root: Path = None) -> int:
    """Process all MD files. Returns count of modified files.
    src_root: root of the original doc source (for resolving include paths).
    If not set, defaults to src_dir.
    """
    if src_root is None:
        src_root = src_dir
    count = 0
    for md_file in sorted(src_dir.rglob("*.md")):
        if '.vuepress' in str(md_file):
            continue
        content = md_file.read_text(encoding="utf-8")
        # Process includes first (before admonition conversion)
        new_content = process_includes(content, md_file, src_root)
        new_content = convert_admonitions(new_content)
        new_content = convert_frontmatter_refs(new_content)
        new_content = convert_fontawesome(new_content)
        if new_content != content:
            md_file.write_text(new_content, encoding="utf-8")
            count += 1
    return count
