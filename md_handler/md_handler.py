import re
import shutil
from pathlib import Path

from yml_handler.yml_handler import YMLHandler
from data_models.umda_data_yml import UMDAData
from data_models.psd_config import PSDConfig
from psd_handler.psd_handler import PSDHandler

# Matches: ![alt]({{ media.path.var }})
_PSD_LINK_RE = re.compile(r'(!\[(.+?)\]\(\{\{\s*([\w.]+)\s*\}\}\))')

# Matches: ![alt](path/to/image.ext) — local image, not a {{ }} var, not http
_IMG_LINK_RE = re.compile(r'(!\[([^\]]*)\]\((?!https?://)(?!\{\{)([^)]+\.(?:png|jpg|jpeg|gif|webp|svg))\))', re.IGNORECASE)

# Parses alt: "Base;Focuses=[A,B];Frames=[C,D]"
_ARG_RE = re.compile(r'(\w+)=\[([^\]]*)\]')


class MDHandle:
    def __init__(self, yml_handler: YMLHandler, docs_dir: Path, psd_handler: PSDHandler):
        self.data: UMDAData = yml_handler.data
        self.docs_dir = Path(docs_dir)
        self.doc_output = Path(yml_handler.config.doc_output)
        self.image_storage_output = Path(yml_handler.config.image_storage_output)
        self.yml_handler_config_doc_ymls = yml_handler.config.doc_ymls
        self.psd_handler = psd_handler

    def run(self):
        # Copy specified ymls to doc_output
        for yml_name in self.yml_handler_config_doc_ymls:
            src = self.docs_dir / yml_name
            if src.exists():
                dst = self.doc_output / yml_name
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
                print(f"Copied yml: {yml_name}")
            else:
                print(f"WARN: doc_yml '{yml_name}' not found in {self.docs_dir}")

        for md_file in sorted(self.docs_dir.rglob("*.md")):
            self.md_loader(md_file)

    def md_loader(self, md_file: Path):
        content = md_file.read_text(encoding="utf-8")
        new_content, count = self.md_process(content, md_file)

        # Save to doc_output preserving directory structure
        rel = md_file.relative_to(self.docs_dir)
        out_file = self.doc_output / rel
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(new_content, encoding="utf-8")

        if count:
            print(f"[{rel}] updated {count} image(s)")

    def md_process(self, content: str, md_file: Path) -> tuple[str, int]:
        count = 0

        # 1. PSD links: ![alt]({{ media.var }})
        def psd_replacer(m: re.Match) -> str:
            nonlocal count
            full_match = m.group(1)
            alt = m.group(2).strip()
            var_path = m.group(3).strip()

            psd_path = self.data.resolve(var_path)
            if not psd_path:
                print(f"  WARN: cannot resolve '{var_path}' — skipping")
                return full_match

            parts = alt.split(";")
            base_layer = parts[0].strip()
            kwargs: dict[str, list[str]] = {}
            for part in parts[1:]:
                arg_m = _ARG_RE.match(part.strip())
                if arg_m:
                    kwargs[arg_m.group(1)] = [
                        v.strip().strip('"\'') for v in arg_m.group(2).split(",") if v.strip()
                    ]

            try:
                config = PSDConfig(psd_path=str(psd_path), base_layer=base_layer, **kwargs)
                out_path = self.psd_handler.render(config)
            except Exception as e:
                print(f"  ERROR rendering '{alt}': {e}")
                return full_match

            rel_path = Path(out_path).relative_to(self.docs_dir) if Path(out_path).is_relative_to(self.docs_dir) else Path(out_path)
            count += 1
            return f"![{alt}]({rel_path})"

        content = _PSD_LINK_RE.sub(psd_replacer, content)

        # 2. Local image links: ![alt](./img/file.png)
        def img_replacer(m: re.Match) -> str:
            nonlocal count
            full_match = m.group(1)
            alt = m.group(2)
            img_path_str = m.group(3).strip()

            # Resolve relative to md file's directory
            src = (md_file.parent / img_path_str).resolve()
            if not src.exists():
                print(f"  WARN: image not found '{src}' — skipping")
                return full_match

            # Preserve structure relative to docs_dir inside image_storage_output
            try:
                rel_to_docs = src.relative_to(self.docs_dir)
            except ValueError:
                rel_to_docs = Path(src.name)

            dst = self.image_storage_output / rel_to_docs
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

            count += 1
            return f"![{alt}]({dst})"

        content = _IMG_LINK_RE.sub(img_replacer, content)

        return content, count
