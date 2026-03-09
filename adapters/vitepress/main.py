from pathlib import Path
import re
import yaml
import shutil
import json
import os
from typing import Dict, Any, List, Optional

# === КОНФИГУРАЦИЯ ===
# Пути можно переопределить через переменные окружения (для CI)
doc_file_format = "md"
meta_file_format = "yml"
meta_file_name = ".meta"
vars_files_names = ["vars.yaml", "global_vars.yaml"]
ignore_files_or_folders = [".github"]
main_doc_path = Path(os.environ.get("DOCS_DIR", "/root/stormbpmn_doc_project/stormbpmn-docs"))
out_doc_path = Path(os.environ.get("VUEPRESS_DIR", "/root/stormbpmn_doc_project/vuepress/vuepress-starter/hope"))
vuepress_config_dir = out_doc_path / ".vuepress"
toc_file_name = "toc.yaml"
toc_file_path = main_doc_path / toc_file_name

env_pattern = r"\{\{(.*?)\}\}"


# ====================== ФУНКЦИИ ДЛЯ TOC → NAVBAR / SIDEBAR ======================

def read_toc(toc_path: Path) -> Dict[str, Any]:
    """Чтение toc.yaml"""
    if not toc_path.exists():
        print(f"⚠️  toc.yaml не найден: {toc_path}")
        return {}
    return load_yaml(toc_path)


def normalize_link(path: str) -> str:
    """Приводит путь из toc к формату VuePress (/section/ или /)"""
    if not path or str(path).strip() == "":
        return "/"
    p = str(path).strip().replace("\\", "/")
    if p.endswith(".md"):
        p = p[:-3]
    # index → корень секции
    parts = p.split("/")
    if parts[-1] in ("index", ""):
        parts = parts[:-1]
    p = "/".join(parts)
    if not p or p == "/":
        return "/"
    if not p.startswith("/"):
        p = "/" + p
    if not p.endswith("/"):
        p += "/"
    return p


def _section_index_link(content: Any) -> str:
    """Извлекает ссылку на индексную страницу секции из содержимого toc."""
    if isinstance(content, str):
        return normalize_link(content)
    if isinstance(content, list):
        for entry in content:
            if isinstance(entry, str):
                return normalize_link(entry)
    return "/"


def _section_children(content: Any) -> List[Dict[str, str]]:
    """
    Возвращает дочерние элементы секции для sidebar.
    Первый bare-string пропускается (это индекс секции).
    """
    children: List[Dict[str, str]] = []
    if not isinstance(content, list):
        return children
    skip_first_bare = True
    for entry in content:
        if isinstance(entry, str):
            if skip_first_bare:
                skip_first_bare = False
                continue
            # Дополнительная bare-строка — подстраница без явного заголовка
            children.append({
                "text": Path(entry.replace("index.md", "").rstrip("/")).name
                         .replace("_", " ").replace("-", " ").title() or entry,
                "link": normalize_link(entry),
            })
        elif isinstance(entry, dict):
            skip_first_bare = False  # после любого dict bare-строки уже не индекс
            for text, path in entry.items():
                children.append({
                    "text": str(text).strip(),
                    "link": normalize_link(str(path)),
                })
    return children


def convert_toc_to_navbar(toc: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Первый уровень toc.yaml → navbar.
    Каждая секция — одна кнопка с ссылкой на индекс раздела.
    """
    result: List[Dict[str, str]] = []
    for title, content in toc.items():
        result.append({
            "text": str(title).strip(),
            "link": _section_index_link(content),
        })
    return result


def convert_toc_to_sidebar(toc: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    toc.yaml → sidebar для vuepress-theme-hope.
    Ключ — префикс маршрута секции, значение — список дочерних страниц.
    Секции без детей в sidebar не попадают.
    """
    result: Dict[str, List] = {}
    for title, content in toc.items():
        section_link = _section_index_link(content)
        children = _section_children(content)
        if children:
            result[section_link] = children
    return result


# --------------- генерация TypeScript-файлов ---------------

def _obj_to_ts(obj: Any, indent: int = 0) -> str:
    """Сериализует Python-объект в TypeScript-литерал (JSON-совместимый)."""
    pad = "  " * indent
    inner = "  " * (indent + 1)
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        items = [f'{inner}"{k}": {_obj_to_ts(v, indent + 1)}' for k, v in obj.items()]
        return "{\n" + ",\n".join(items) + f"\n{pad}}}"
    if isinstance(obj, list):
        if not obj:
            return "[]"
        items = [f"{inner}{_obj_to_ts(v, indent + 1)}" for v in obj]
        return "[\n" + ",\n".join(items) + f"\n{pad}]"
    if isinstance(obj, bool):
        return "true" if obj else "false"
    if isinstance(obj, (int, float)):
        return str(obj)
    # строка
    escaped = str(obj).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def write_navbar_ts(config_dir: Path, navbar: List[Dict]) -> None:
    """Генерирует navbar.ts для vuepress-theme-hope."""
    body = _obj_to_ts(navbar)
    ts = f'import {{ navbar }} from "vuepress-theme-hope";\n\nexport default navbar({body});\n'
    out = config_dir / "navbar.ts"
    out.write_text(ts, encoding="utf-8")
    print(f"✅ navbar.ts записан → {out}")


def write_sidebar_ts(config_dir: Path, sidebar: Dict) -> None:
    """Генерирует sidebar.ts для vuepress-theme-hope."""
    body = _obj_to_ts(sidebar)
    ts = f'import {{ sidebar }} from "vuepress-theme-hope";\n\nexport default sidebar({body});\n'
    out = config_dir / "sidebar.ts"
    out.write_text(ts, encoding="utf-8")
    print(f"✅ sidebar.ts записан → {out}")


# ====================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ======================

def deep_merge(target: Dict, source: Dict) -> None:
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            deep_merge(target[key], value)
        else:
            target[key] = value


def load_yaml(file_path: Path) -> Dict[str, Any]:
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Не удалось загрузить {file_path}: {e}")
    return {}


def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    if not content.strip().startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    fm_text = parts[1].strip()
    body = parts[2].lstrip()
    try:
        fm = yaml.safe_load(fm_text) or {}
    except Exception:
        fm = {}
        body = content
    return fm, body


def extract_used_vars(content: str) -> set[str]:
    matches = re.findall(env_pattern, content)
    return {m.strip() for m in matches if m.strip()}


_HTML_OR_MD_RE = re.compile(r'<[a-zA-Z]|\*\*|\*[^*]')

# Маппинг типов MkDocs admonition → VuePress hint-контейнер
_ADMONITION_TYPE_MAP = {
    "warning": "warning",
    "caution": "warning",
    "notice": "tip",
    "info": "info",
    "tip": "tip",
    "note": "note",
    "danger": "danger",
    "error": "danger",
    "success": "tip",
    "important": "warning",
    "abstract": "info",
    "question": "info",
    "example": "info",
    "quote": "note",
    "bug": "danger",
}


def convert_admonitions(content: str) -> str:
    """
    Конвертирует MkDocs admonition-блоки в VuePress hint-контейнеры.

    MkDocs:         !!! warning "Title"\n\n    Content\n
    VuePress:        ::: warning Title\nContent\n:::

    ??? type → ::: details
    """
    lines = content.split("\n")
    result: List[str] = []
    i = 0
    admon_re = re.compile(r'^([!?]{3})\s+(?:(\w+)(?:\s+"([^"]*)")?|"([^"]*)")\s*$')

    while i < len(lines):
        m = admon_re.match(lines[i])
        if m:
            marker = m.group(1)
            admon_type = m.group(2) or ""   # тип может отсутствовать
            title = m.group(3) or m.group(4) or ""  # заголовок из любой позиции
            if marker == "???" or not admon_type:
                vp_type = "details"
            else:
                vp_type = _ADMONITION_TYPE_MAP.get(admon_type.lower(), "tip")

            # Собираем тело блока: строки с 4-пробельным отступом
            # (между заголовком и содержимым может быть пустая строка)
            block: List[str] = []
            i += 1
            while i < len(lines):
                cl = lines[i]
                if cl.startswith("    "):
                    block.append(cl[4:])  # убираем 4 пробела отступа
                    i += 1
                elif cl.strip() == "":
                    # Пустая строка: включаем в блок только если следующая строка тоже с отступом
                    j = i + 1
                    while j < len(lines) and lines[j].strip() == "":
                        j += 1
                    if j < len(lines) and lines[j].startswith("    "):
                        block.append("")
                        i += 1
                    else:
                        i += 1  # пустая строка-разделитель между заголовком и телом
                        # но только если блок ещё пустой (пробел до первого контента)
                        if block:  # уже есть контент — конец блока
                            break
                else:
                    break

            # Удаляем хвостовые пустые строки внутри блока
            while block and block[-1] == "":
                block.pop()

            header = f"::: {vp_type} {title}".rstrip()
            result.append(header)
            result.extend(block)
            result.append(":::")
            result.append("")
        else:
            result.append(lines[i])
            i += 1

    return "\n".join(result)


def md_inline_to_html(text: str) -> str:
    """Конвертирует inline-markdown в HTML (bold, italic) для использования в v-html."""
    if not isinstance(text, str):
        return str(text) if text is not None else ""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    return text


def convert_fm_values_to_html(data: Any) -> Any:
    """Рекурсивно конвертирует все строки в dict/list frontmatter из inline-md в HTML."""
    if isinstance(data, dict):
        return {k: convert_fm_values_to_html(v) for k, v in data.items()}
    if isinstance(data, list):
        return [convert_fm_values_to_html(v) for v in data]
    if isinstance(data, str):
        return md_inline_to_html(data)
    return data


def replace_to_vitepress_vars(content: str, vars_data: Dict[str, Any] = None) -> str:
    def replacer(match: re.Match) -> str:
        var = match.group(1).strip()
        # MkDocs-специфика: page.meta.title → title из frontmatter (всегда plain text)
        if var == "page.meta.title":
            return "{{ $frontmatter.title }}"
        # Цепочки a.b.c → опциональная цепочка
        parts = var.split(".")
        chain = parts[0] + "".join(f"?.{p}" for p in parts[1:]) if len(parts) > 1 else var
        # Если значение содержит HTML или markdown → v-html, иначе mustache
        value = get_nested_value(vars_data, var) if vars_data else None
        if isinstance(value, str) and _HTML_OR_MD_RE.search(value):
            return f'<span v-html="$frontmatter.{chain} ?? \'\'"></span>'
        return f"{{{{ $frontmatter.{chain} }}}}"
    return re.sub(env_pattern, replacer, content)


def extract_resolved_title(body: str, vars_data: Dict[str, Any]) -> Optional[str]:
    """
    Извлекает текст первого h1-заголовка и резолвит {{ var }} в нём.
    Возвращает None если заголовка нет или он чистый (без шаблонов).
    """
    m = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
    if not m:
        return None
    heading = m.group(1).strip()
    if '{{' not in heading:
        return None

    def resolve(match: re.Match) -> str:
        var = match.group(1).strip()
        if var == "page.meta.title":
            return ""  # нечего резолвить без контекста
        value = get_nested_value(vars_data, var)
        return str(value) if value is not None else ""

    return re.sub(env_pattern, resolve, heading).strip()


def collect_vars_data(md_dir: Path) -> Dict[str, Any]:
    vars_data: Dict[str, Any] = {}
    current = md_dir
    while current.is_relative_to(main_doc_path):
        for fname in vars_files_names:
            data = load_yaml(current / fname)
            if data:
                deep_merge(vars_data, data)
        if current == main_doc_path:
            break
        current = current.parent
    return vars_data


def get_nested_value(data: Dict, path: str, default: Any = None) -> Any:
    keys = [k.strip() for k in path.split(".")]
    current = data
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k, default)
        else:
            return default
    return current


def set_nested_value(data: Dict, path: str, value: Any) -> None:
    if not path:
        return
    keys = [k.strip() for k in path.split(".")]
    current = data
    for k in keys[:-1]:
        if k not in current or not isinstance(current[k], dict):
            current[k] = {}
        current = current[k]
    current[keys[-1]] = value


# ====================== ГЛАВНАЯ ФУНКЦИЯ ======================

def prepare_doc_files() -> Path:
    """Подготавливает документацию + обновляет navbar (сохраняет .vuepress)"""

    # Файлы/папки, которые НЕ трогаем при очистке (инфраструктура репо)
    preserve_in_output = {
        ".vuepress", ".git", ".github",
        "package.json", "package-lock.json", "tsconfig.json",
        ".gitignore", "node_modules",
    }

    # === УМНАЯ ОЧИСТКА: УДАЛЯЕМ ВСЁ, КРОМЕ ИНФРАСТРУКТУРЫ РЕПО ===
    if out_doc_path.exists():
        print(f"Очищаем {out_doc_path} (сохраняем инфраструктуру репо)...")
        for item in list(out_doc_path.iterdir()):
            if item.name in preserve_in_output:
                continue
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            except Exception as e:
                print(f"  Не удалось удалить {item}: {e}")
    else:
        out_doc_path.mkdir(parents=True, exist_ok=True)

    # === КОПИРОВАНИЕ ДОКУМЕНТАЦИИ (поверх существующей папки) ===
    def ignore_func(directory, contents):
        return [c for c in contents if c in ignore_files_or_folders]

    shutil.copytree(
        main_doc_path,
        out_doc_path,
        ignore=ignore_func,
        dirs_exist_ok=True   # ← позволяет копировать в уже существующую папку
    )
    print(f"Структура документации скопирована в {out_doc_path}")

    # === Обработка всех .md файлов ===
    md_files = [
        p for p in main_doc_path.rglob(f"*.{doc_file_format}")
        if not any(ign in p.parts for ign in ignore_files_or_folders)
    ]

    processed = 0
    for md_path in md_files:
        rel_path = md_path.relative_to(main_doc_path)
        # VuePress использует README.md как индекс директории, не index.md
        if rel_path.name == "index.md":
            rel_path = rel_path.parent / "README.md"
        out_md = out_doc_path / rel_path

        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            md_dir = md_path.parent
            meta_file = md_dir / f"{meta_file_name}.{meta_file_format}"
            meta_data = load_yaml(meta_file)

            existing_fm, body = parse_frontmatter(content)
            vars_data = collect_vars_data(md_dir)
            used_vars = extract_used_vars(body)

            for var_path in used_vars:
                value = get_nested_value(vars_data, var_path)
                if value is not None:
                    set_nested_value(meta_data, var_path, value)

            # Конвертируем inline-md → HTML в значениях переменных (для v-html рендеринга)
            meta_data = convert_fm_values_to_html(meta_data)
            full_fm = {**meta_data, **existing_fm}

            # Явный title для VuePress: извлекаем из h1 и резолвим переменные,
            # иначе VuePress показывает сырые {{ }} в навигации и табе браузера
            if "title" not in full_fm:
                resolved_title = extract_resolved_title(body, vars_data)
                if resolved_title:
                    full_fm["title"] = resolved_title

            new_body = convert_admonitions(replace_to_vitepress_vars(body, vars_data))

            if full_fm:
                fm_yaml = yaml.safe_dump(
                    full_fm, allow_unicode=True, sort_keys=False, default_flow_style=False
                ).strip()
                new_content = f"---\n{fm_yaml}\n---\n\n{new_body}"
            else:
                new_content = new_body

            with open(out_md, "w", encoding="utf-8") as f:
                f.write(new_content)

            processed += 1

        except Exception as e:
            print(f"Ошибка при обработке {md_path}: {e}")

    # === УДАЛЕНИЕ ТЕХНИЧЕСКИХ ФАЙЛОВ (с защитой .vuepress) ===
    # index.md → уже переписаны как README.md, удаляем оригиналы
    for leftover in out_doc_path.rglob("index.md"):
        if not leftover.is_relative_to(out_doc_path / ".vuepress"):
            try:
                leftover.unlink()
            except Exception:
                pass

    for pattern in [f"{meta_file_name}.{meta_file_format}", *vars_files_names, toc_file_name]:
        for f in out_doc_path.rglob(pattern):
            if f.is_relative_to(out_doc_path / ".vuepress"):
                continue  # ← защита .vuepress
            try:
                f.unlink()
            except Exception:
                pass

    # === ОБНОВЛЕНИЕ NAVBAR И SIDEBAR ИЗ toc.yaml ===
    print("\nОбновляем навигацию из toc.yaml...")
    toc_data = read_toc(toc_file_path)
    if toc_data:
        vuepress_config_dir.mkdir(parents=True, exist_ok=True)
        write_navbar_ts(vuepress_config_dir, convert_toc_to_navbar(toc_data))
        write_sidebar_ts(vuepress_config_dir, convert_toc_to_sidebar(toc_data))
    else:
        print("toc.yaml пустой — навигация не обновлена")

    print(f"\nГОТОВО! Обработано {processed} MD-файлов.")
    print(f"Документация сохранена в: {out_doc_path}")
    print(f"   • Папка .vuepress сохранена и не тронута")
    return out_doc_path


# === ЗАПУСК ===
if __name__ == "__main__":
    prepare_doc_files()