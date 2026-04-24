#!/usr/bin/env python3
"""
UMDA CLI entry point.

Usage:
    umda <adapter_name> [build]

Searches for umda.yml upward from the current directory.
"""
import sys
import shutil
import tempfile
import mimetypes
from urllib.parse import urlparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from yml_handler.yml_handler import YMLHandler, UMDA_ROOT
from md_handler.md_handler import MDHandle
from psd_handler.psd_handler import PSDHandler
from config_handler.config_handler import MkDocsConfigHandler, _load_with_includes
from data_models.umda_data_yml import UMDAData


def usage():
    print("Usage: umda <adapter_name> [build]")
    print("Example: umda mkdocs build")
    sys.exit(1)


def find_umda_yml(start: Path) -> Path:
    current = start.resolve()
    while True:
        candidate = current / "umda.yml"
        if candidate.exists():
            return candidate
        parent = current.parent
        if parent == current:
            print(f"ERROR: umda.yml not found in '{start}' or any parent directory.")
            sys.exit(1)
        current = parent


def ensure_dirs(adapter_cfg, s3_cfg=None):
    doc_out = str(adapter_cfg.doc_output)
    if not _is_s3_target(doc_out, s3_cfg):
        Path(adapter_cfg.doc_output).mkdir(parents=True, exist_ok=True)
    media_out = str(adapter_cfg.media.media_storage_output)
    if not _is_s3_target(media_out, s3_cfg):
        Path(media_out).mkdir(parents=True, exist_ok=True)


def _is_s3_target(raw_target: str, s3_cfg) -> bool:
    """Detect S3 media target.

    Supported forms:
    - s3://bucket[/prefix]
    - bucket-name (shorthand, only when S3 config is present)
    """
    raw = str(raw_target).strip()
    if raw.lower().startswith("s3://"):
        return True
    if not s3_cfg:
        return False
    if not raw:
        return False
    if "/" in raw or "\\" in raw:
        return False
    if raw.startswith((".", "~")):
        return False
    if Path(raw).is_absolute():
        return False
    return True


def _parse_s3_target(raw_target: str) -> tuple[str, str]:
    """Parse S3 target from s3://bucket[/prefix] or bucket-name shorthand."""
    raw = str(raw_target).strip()
    if raw.lower().startswith("s3://"):
        parsed = urlparse(raw)
        return parsed.netloc.strip(), parsed.path.strip("/")
    return raw.strip("/"), ""


def _build_s3_client(s3_cfg):
    if not s3_cfg:
        raise RuntimeError("S3 config section is required for S3 output targets")
    try:
        import boto3
    except ImportError as e:
        raise RuntimeError("boto3 is required for S3 output targets") from e

    kwargs = {}
    if s3_cfg.endpoint_url:
        kwargs["endpoint_url"] = s3_cfg.endpoint_url
    if s3_cfg.region_name:
        kwargs["region_name"] = s3_cfg.region_name
    if s3_cfg.aws_access_key_id:
        kwargs["aws_access_key_id"] = s3_cfg.aws_access_key_id
    if s3_cfg.aws_secret_access_key:
        kwargs["aws_secret_access_key"] = s3_cfg.aws_secret_access_key
    if s3_cfg.aws_session_token:
        kwargs["aws_session_token"] = s3_cfg.aws_session_token

    return boto3.client("s3", **kwargs)


def _upload_dir_to_s3(local_dir: Path, raw_target: str, s3_cfg, label: str) -> None:
    bucket, prefix = _parse_s3_target(raw_target)
    if not bucket:
        raise ValueError(f"S3 target for {label} must include bucket name")

    local_dir = Path(local_dir)
    if not local_dir.exists():
        print(f"[UMDA] WARN: local staging dir for {label} does not exist: {local_dir}")
        return

    client = _build_s3_client(s3_cfg)
    uploaded = 0
    for fp in sorted(local_dir.rglob("*")):
        if not fp.is_file():
            continue
        rel = fp.relative_to(local_dir).as_posix()
        key = f"{prefix}/{rel}" if prefix else rel
        content_type = mimetypes.guess_type(str(fp))[0]
        extra = {"ContentType": content_type} if content_type else None
        if extra:
            client.upload_file(str(fp), bucket, key, ExtraArgs=extra)
        else:
            client.upload_file(str(fp), bucket, key)
        uploaded += 1

    target = f"s3://{bucket}/{prefix}" if prefix else f"s3://{bucket}"
    print(f"[UMDA] uploaded {uploaded} file(s) for {label} -> {target}")


def build_umda_data(sections: list[Path]) -> UMDAData:
    """Merge all adapter sections (with include: support) into UMDAData."""
    merged: dict = {}
    paths = sections.values() if isinstance(sections, dict) else sections
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        merged.update(_load_with_includes(p))
    return UMDAData(**merged)


def build(adapter_name: str):
    umda_yml = find_umda_yml(Path.cwd())
    docs_dir = umda_yml.parent

    yml_handler = YMLHandler(umda_yml_file=umda_yml)

    if adapter_name not in yml_handler.adapters:
        available = list(yml_handler.adapters.keys())
        print(f"ERROR: adapter '{adapter_name}' not found in umda.yml. Available: {available}")
        sys.exit(1)

    adapter_cfg = yml_handler.adapters[adapter_name]
    ensure_dirs(adapter_cfg, yml_handler.config.s3)

    original_doc_output = str(adapter_cfg.doc_output)
    temp_doc_output_root = None
    use_s3_doc_output = _is_s3_target(original_doc_output, yml_handler.config.s3)
    if use_s3_doc_output:
        temp_doc_output_root = Path(tempfile.mkdtemp(prefix="umda_doc_output_"))
        adapter_cfg.doc_output = temp_doc_output_root

    docs_dir_target = None
    if adapter_cfg.config is not None:
        docs_dir_opt = adapter_cfg.config.options.get("docs_dir")
        if docs_dir_opt and _is_s3_target(str(docs_dir_opt), yml_handler.config.s3):
            docs_dir_target = str(docs_dir_opt)
            # Keep mkdocs docs_dir local and usable for the next mkdocs build step.
            adapter_cfg.config.options["docs_dir"] = str(adapter_cfg.doc_output)

    print(f"[UMDA] Building '{adapter_name}' adapter")
    print(f"  umda.yml:             {umda_yml}")
    print(f"  doc_input:            {yml_handler.config.doc_input}")
    print(f"  doc_output:           {adapter_cfg.doc_output}")
    print(f"  media_storage_output: {adapter_cfg.media.media_storage_output}")

    # 1. Config handler — patch and save mkdocs config (skipped if mkdocs_path not set)
    if adapter_cfg.mkdocs_path is not None and adapter_cfg.config is not None:
        config_handler = MkDocsConfigHandler(
            mkdocs_path=adapter_cfg.mkdocs_path,
            cfg=adapter_cfg.config,
        )
        config_handler.run()
        data = build_umda_data(adapter_cfg.config.sections)
    else:
        # Load vars if available (e.g. for vuepress_hope)
        if adapter_cfg.vars and Path(adapter_cfg.vars).exists():
            data = build_umda_data({"vars": adapter_cfg.vars})
        else:
            data = build_umda_data({})

    media_out = str(adapter_cfg.media.media_storage_output)
    use_s3 = _is_s3_target(media_out, yml_handler.config.s3)
    local_media_root = Path(media_out)
    temp_media_root = None
    if use_s3:
        temp_media_root = Path(tempfile.mkdtemp(prefix="umda_media_"))
        local_media_root = temp_media_root

    # 3. PSDHandler
    psd_handler = PSDHandler(
        output_dir=local_media_root,
        image_ext=adapter_cfg.media.image_extantion,
    )

    # 4. MDHandle — process MD files, convert images
    md_handle = MDHandle(
        data=data,
        docs_dir=docs_dir,
        adapter_cfg=adapter_cfg,
        psd_handler=psd_handler,
        s3_cfg=yml_handler.config.s3,
        local_media_root=local_media_root,
    )
    try:
        md_handle.run()
    finally:
        psd_handler.terminate()
        if temp_media_root and temp_media_root.exists():
            shutil.rmtree(temp_media_root, ignore_errors=True)

    # 4b. VuePress vars injection (if vars path is set)
    if adapter_cfg.vars is not None:
        from adapters.vuepress_hope.vars_injector import VuepressVarsInjector
        vars_data = _load_with_includes(adapter_cfg.vars)
        injector = VuepressVarsInjector(vars_data)
        count = injector.process_dir(Path(adapter_cfg.doc_output))
        print(f"[UMDA] VuePress vars injected into {count} file(s)")

    # 5. Adapter-specific post-processing (swap_list)
    _run_adapter(adapter_name, adapter_cfg, src_root=docs_dir)

    if use_s3_doc_output and temp_doc_output_root:
        _upload_dir_to_s3(temp_doc_output_root, original_doc_output, yml_handler.config.s3, "doc_output")

    if docs_dir_target:
        skip_docs_dir_upload = (
            use_s3_doc_output
            and _parse_s3_target(docs_dir_target) == _parse_s3_target(original_doc_output)
        )
        if not skip_docs_dir_upload:
            _upload_dir_to_s3(Path(adapter_cfg.doc_output), docs_dir_target, yml_handler.config.s3, "docs_dir")

    keep_doc_output_staging = bool(docs_dir_target)
    if temp_doc_output_root and temp_doc_output_root.exists() and not keep_doc_output_staging:
        shutil.rmtree(temp_doc_output_root, ignore_errors=True)
    elif temp_doc_output_root and keep_doc_output_staging:
        print(f"[UMDA] local docs staging kept for docs_dir: {temp_doc_output_root}")

    final_bundle = original_doc_output if use_s3_doc_output else str(adapter_cfg.doc_output)
    print(f"[UMDA] Done. Bundle ready at: {final_bundle}")


def _run_adapter(adapter_name: str, adapter_cfg, src_root=None):
    adapter_dir = UMDA_ROOT / "adapters" / adapter_name
    adapter_main = adapter_dir / "main.py"

    if not adapter_main.exists():
        print(f"WARN: no adapter module found at {adapter_main}, skipping post-processing")
        return

    import importlib.util
    spec = importlib.util.spec_from_file_location(f"adapters.{adapter_name}.main", adapter_main)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class_name = adapter_name.capitalize() + "Adapter"
    adapter_class = getattr(mod, "MKdocsAdapter", None) or getattr(mod, class_name, None)

    if adapter_class is None:
        print(f"WARN: adapter class not found in {adapter_main}, skipping")
        return

    swap_list_path = adapter_cfg.swap_list or (adapter_dir / "swap_list.yml")

    # Build kwargs for adapter constructor
    kwargs = {
        "doc_output": adapter_cfg.doc_output,
        "swap_list_path": swap_list_path,
    }
    # Pass nav_path for vuepress_hope (from config.sections.nav or standalone nav field)
    if adapter_cfg.nav:
        kwargs["nav_path"] = adapter_cfg.nav
    elif adapter_cfg.config and adapter_cfg.config.sections:
        nav_path = adapter_cfg.config.sections.get("nav")
        if nav_path:
            kwargs["nav_path"] = nav_path
    if adapter_cfg.vuepress_path:
        kwargs["vuepress_path"] = adapter_cfg.vuepress_path
    if hasattr(adapter_cfg, 'media') and adapter_cfg.media:
        kwargs["media_base_url"] = adapter_cfg.media.media_base_url
    if src_root:
        kwargs["src_root"] = str(src_root)
    # Pass base path for VuePress
    if hasattr(adapter_cfg, 'base') and adapter_cfg.base:
        kwargs["base"] = adapter_cfg.base

    instance = adapter_class(**kwargs)
    instance.run()


def main():
    args = sys.argv[1:]
    if not args:
        usage()

    adapter_name = args[0]
    subcommand = args[1] if len(args) > 1 else "build"

    if subcommand not in ("build",):
        print(f"ERROR: unknown subcommand '{subcommand}'. Supported: build")
        sys.exit(1)

    build(adapter_name)


if __name__ == "__main__":
    main()
