#!/usr/bin/env python3
import yaml, json
from pathlib import Path

NAV_PATH = Path('/root/stormbpmn_doc_project/stormbpmn-docs/nav.yaml')
UMDA_YML = Path('/root/stormbpmn_doc_project/stormbpmn-docs/umda.yml')

nav = yaml.safe_load(NAV_PATH.read_text(encoding='utf-8'))
umda = yaml.safe_load(UMDA_YML.read_text(encoding='utf-8'))
vuepress_path = Path(
    umda.get('adapers', {}).get('vuepress_hope', {}).get('vuepress_path')
    or '/root/stormbpmn_doc_project/vuepress/vuepress-starter/hope/.vuepress'
)
vuepress_path.mkdir(parents=True, exist_ok=True)


def to_link(path: str) -> str:
    """Convert 'section/index.md' -> '/section/', 'section/page.md' -> '/section/page/'"""
    p = path.strip('/')
    if p.endswith('/index.md'):
        return '/' + p[:-len('index.md')]
    elif p == 'index.md':
        return '/'
    elif p.endswith('.md'):
        return '/' + p[:-3] + '/'
    return '/' + p + '/'


def first_file(val) -> str | None:
    """Return the first file path found in a nav value."""
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        for item in val:
            if isinstance(item, str):
                return item
            if isinstance(item, dict):
                for v in item.values():
                    r = first_file(v)
                    if r:
                        return r
    if isinstance(val, dict):
        for v in val.values():
            r = first_file(v)
            if r:
                return r
    return None


def collect_sidebar_children(val) -> list:
    """Collect sidebar children — all non-index items from a nav section."""
    out = []
    items = val if isinstance(val, list) else (list(val.items()) if isinstance(val, dict) else [])

    if isinstance(val, list):
        for item in val:
            if isinstance(item, str):
                # skip bare index.md at top level (it's the section root)
                if item.endswith('index.md') and item.count('/') <= 0:
                    continue
                out.append({'text': Path(item).stem, 'link': to_link(item)})
            elif isinstance(item, dict):
                for k2, v2 in item.items():
                    entry = {'text': k2}
                    first = first_file(v2)
                    if first:
                        entry['link'] = to_link(first)
                    children = collect_sidebar_children(v2)
                    if children:
                        entry['children'] = children
                    out.append(entry)
    elif isinstance(val, dict):
        for k2, v2 in val.items():
            entry = {'text': k2}
            first = first_file(v2)
            if first:
                entry['link'] = to_link(first)
            children = collect_sidebar_children(v2)
            if children:
                entry['children'] = children
            out.append(entry)
    elif isinstance(val, str):
        pass  # scalar — no children

    return out


# --- Build navbar ---
navbar = []
for key, val in nav.items():
    first = first_file(val)
    navbar.append({
        'text': key,
        'link': to_link(first) if first else '/'
    })

# --- Build sidebar ---
sidebar = {}
for key, val in nav.items():
    first = first_file(val)
    prefix = to_link(first) if first else '/'
    # sidebar key = prefix directory (e.g. /admins/)
    # for root sections (index.md at top), key is "/"
    if prefix == '/':
        sidebar_key = '/'
    else:
        # e.g. /admins/index/ -> /admins/
        parts = prefix.strip('/').split('/')
        sidebar_key = '/' + parts[0] + '/'

    children = collect_sidebar_children(val)
    if children:
        sidebar[sidebar_key] = children

# --- Write navbar.ts ---
navbar_ts = 'import { navbar } from "vuepress-theme-hope";\n\n'
navbar_ts += 'export default navbar(' + json.dumps(navbar, ensure_ascii=False, indent=2) + ');\n'
(vuepress_path / 'navbar.ts').write_text(navbar_ts, encoding='utf-8')

# --- Write sidebar.ts ---
sidebar_ts = 'import { sidebar } from "vuepress-theme-hope";\n\n'
sidebar_ts += 'export default sidebar(' + json.dumps(sidebar, ensure_ascii=False, indent=2) + ');\n'
(vuepress_path / 'sidebar.ts').write_text(sidebar_ts, encoding='utf-8')

# --- Write theme.ts (from template, fully preserved) ---
theme_ts = '''\
import { hopeTheme } from "vuepress-theme-hope";

import navbar from "./navbar.js";
import sidebar from "./sidebar.js";

export default hopeTheme({
  hostname: "https://stormbpmn.github.io",

  logo: "/assets/logo.svg",

  repo: "stormbpmn/stormbpmn-docs",

  docsDir: ".",

  // navbar
  navbar,

  // sidebar
  sidebar,

  displayFooter: false,

  markdown: {
    align: true,
    attrs: true,
    figure: true,
    gfm: true,
    hint: true,
    imgLazyload: true,
    imgSize: true,
    include: true,
    mark: true,
    tabs: true,
    tasklist: true,
    vPre: true,
  },

  plugins: {
    components: {
      components: ["Badge"],
    },

    icon: {
      prefix: "fa6-solid:",
    },
  },
});
'''
(vuepress_path / 'theme.ts').write_text(theme_ts, encoding='utf-8')

# --- Write config.ts (from template) ---
config_ts = '''\
import { defineUserConfig } from "vuepress";

import theme from "./theme.js";

export default defineUserConfig({
  base: "/",

  lang: "ru-RU",
  title: "Stormbpmn",
  description: "Документация Stormbpmn",

  theme,
});
'''
(vuepress_path / 'config.ts').write_text(config_ts, encoding='utf-8')

print('Rendered to', str(vuepress_path))
print('navbar entries:', len(navbar))
print('sidebar keys:', list(sidebar.keys()))
