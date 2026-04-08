import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from yml_handler.yml_handler import YMLHandler
from md_handler.md_handler import MDHandle
from psd_handler.psd_handler import PSDHandler


def main():
    docs_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

    yml_handler = YMLHandler(umda_yml_file=docs_dir / "umda.yml")
    output_dir = yml_handler.config.image_storage_output
    psd_handler = PSDHandler(output_dir=output_dir)
    md_handle = MDHandle(yml_handler=yml_handler, docs_dir=docs_dir, psd_handler=psd_handler)
    md_handle.run()
    psd_handler.terminate()


if __name__ == "__main__":
    main()
