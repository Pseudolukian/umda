import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from yml_handler.yml_handler import YMLHandler
from md_handler.md_handler import MDHandle
from psd_handler.psd_handler import PSDHandler

DOCS_DIR = Path("/root/stormbpmn_doc_project/stormbpmn-docs")

yml_handler = YMLHandler(umda_yml_file=DOCS_DIR / "umda.yml")
output_dir = yml_handler.config.image_storage_output
psd_handler = PSDHandler(output_dir=output_dir)
md_handle = MDHandle(yml_handler=yml_handler, docs_dir=DOCS_DIR, psd_handler=psd_handler)
md_handle.run()
psd_handler.terminate()
