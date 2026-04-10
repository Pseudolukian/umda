import re
import shutil
from pathlib import Path
from PIL import Image

from data_models.umda_data_yml import UMDAData
from data_models.umda_config import AdapterConfig
from data_models.psd_config import PSDConfig
from psd_handler.psd_handler import PSDHandler

# Matches: ![alt]({{ media.path.var }})
_PSD_LINK_RE = re.compile(r'(!\[(.+?)\]\(\{\{\s*([\w.]+)\s*\}\}\))')

# Matches: ![alt](path/to/image.ext) — local image, not a {{ }} var, not http
_IMG_LINK_RE = re.compile(r'(!\[([^\]]*)\]\((?!https?://)(?!\{\{)([^)]+\.(?:png|jpg|jpeg|gif|webp|svg))\))', re.IGNORECASE)

# Parses alt: "Base;Focuses=[A,B];Frames=[C,D]"
_ARG_RE = re.compile(r'(\w+)=\[([^\]]*)\]')


class MDHandle:
    def __init__(
        self,
        data: UMDAData,
        docs_dir: Path,
        adapter_cfg: AdapterConfig,
        psd_handler: PSDHandler,
    ):
        self.data = data
        self.docs_dir = Path(docs_dir)
        self.adapter_cfg = adapter_cfg
        self.doc_output = Path(adapter_cfg.doc_output)
        self.media_storage_output = Path(adapter_cfg.media.media_storage_output)
        self.image_ext = adapter_cfg.media.image_extantion.lower().lstrip(".")
        self.media_base_url = adapter_cfg.media.media_base_url.rstrip("/")
        self.psd_handler = psd_handler

    def run(self):
        # Copy .meta.yml files preserving directory structure
        for meta_file in sorted(self.docs_dir.rglob(".meta.yml")):
            rel = meta_file.relative_to(self.docs_dir)
            dst = self.doc_output / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(meta_file.read_bytes())

        for md_file in sorted(self.docs_dir.rglob("*.md")):
            self.md_loader(md_file)

    def md_loader(self, md_file: Path):
        content = md_file.read_text(encoding="utf-8")
        new_content, count = self.md_process(content, md_file)

        rel = md_file.relative_to(self.docs_dir)
        out_file = self.doc_output / rel
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(new_content, encoding="utf-8")

        if count:
            print(f"[{rel}] updated {count} image(s)")

    def md_process(self, content: str, md_file: Path) -> tuple[str, int]:
        count = 0

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

        def img_replacer(m: re.Match) -> str:
            nonlocal count
            full_match = m.group(1)
            alt = m.group(2)
            img_path_str = m.group(3).strip()

            src = (md_file.parent / img_path_str).resolve()
            if not src.exists():
                print(f"  WARN: image not found '{src}' — skipping")
                return full_match

            try:
                rel_to_docs = src.relative_to(self.docs_dir)
            except ValueError:
                rel_to_docs = Path(src.name)

            dst = (self.media_storage_output / rel_to_docs).with_suffix(f".{self.image_ext}")
            dst.parent.mkdir(parents=True, exist_ok=True)

            src_ext = src.suffix.lower().lstrip(".")
            if src_ext == self.image_ext:
                shutil.copy2(src, dst)
            else:
                with Image.open(src) as img:
                    mode = "RGBA" if self.image_ext == "webp" else "RGB"
                    img.convert(mode).save(dst, format=self.image_ext)

            count += 1
            if self.media_base_url:
                url_path = dst.relative_to(self.media_storage_output)
                return f"![{alt}]({self.media_base_url}/{url_path})"
            return f"![{alt}]({dst})"

        content = _IMG_LINK_RE.sub(img_replacer, content)

        return content, count
