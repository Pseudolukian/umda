#!/usr/bin/env python3
"""
Migrate .meta.yml → index.md frontmatter.

For each .meta.yml found under the docs root:
1. Read the YAML content from .meta.yml
2. Find index.md in the same directory
3. Inject the meta as YAML frontmatter (--- block) at the top of index.md
4. Replace `# {{ page.meta.title }}` with `# <actual title from meta>`
5. Delete .meta.yml

Usage:
    python3 migrate_meta.py /root/stormbpmn_project/stormbpmn_new_doc
"""
import sys
import re
from pathlib import Path

import yaml


def migrate(docs_dir: Path):
    meta_files = sorted(docs_dir.rglob(".meta.yml"))
    print(f"Found {len(meta_files)} .meta.yml files\n")

    for meta_path in meta_files:
        dir_path = meta_path.parent
        index_md = dir_path / "index.md"
        rel = meta_path.relative_to(docs_dir)

        # Load meta
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}

        if not meta:
            print(f"[SKIP] {rel} — empty meta")
            continue

        title = meta.get("title", "")

        # Build frontmatter block
        frontmatter = yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False).rstrip()

        if not index_md.exists():
            # Create index.md with just frontmatter + title
            content = f"---\n{frontmatter}\n---\n"
            if title:
                content += f"\n# {title}\n"
            index_md.write_text(content, encoding="utf-8")
            print(f"[CREATE] {index_md.relative_to(docs_dir)} — created with frontmatter")
        else:
            content = index_md.read_text(encoding="utf-8")

            # Check if frontmatter already exists
            if content.startswith("---"):
                # Merge into existing frontmatter
                fm_end = content.index("---", 3)
                existing_fm = content[3:fm_end].strip()
                existing_meta = yaml.safe_load(existing_fm) or {}
                # meta from .meta.yml takes precedence
                merged = {**existing_meta, **meta}
                new_fm = yaml.dump(merged, default_flow_style=False, allow_unicode=True, sort_keys=False).rstrip()
                body = content[fm_end + 3:].lstrip("\n")
                content = f"---\n{new_fm}\n---\n\n{body}"
            else:
                # Prepend frontmatter
                content = f"---\n{frontmatter}\n---\n\n{content}"

            # Replace # {{ page.meta.title }} with actual title
            if title:
                content = re.sub(
                    r'^#\s*\{\{\s*page\.meta\.title\s*\}\}\s*$',
                    f'# {title}',
                    content,
                    count=1,
                    flags=re.MULTILINE,
                )

            index_md.write_text(content, encoding="utf-8")
            print(f"[UPDATE] {index_md.relative_to(docs_dir)} — injected frontmatter" +
                  (f', title → "{title}"' if title else ""))

        # Remove .meta.yml
        meta_path.unlink()
        print(f"[DELETE] {rel}")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 migrate_meta.py <docs_dir>")
        sys.exit(1)
    docs_dir = Path(sys.argv[1])
    if not docs_dir.is_dir():
        print(f"ERROR: {docs_dir} is not a directory")
        sys.exit(1)
    migrate(docs_dir)
