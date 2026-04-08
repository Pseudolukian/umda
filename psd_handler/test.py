import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from psd_handler.psd_handler import PSDHandler
from data_models.psd_config import PSDConfig

psd_handler = PSDHandler(output_dir="/root/out_test_storage")
out = psd_handler.render(PSDConfig(
    psd_path="/root/media/screenshots/diagram/diagram.psd",
    base_layer="Errors",
    Frames=["Error_switcher","Error_layer"],
    Focuses=[],
    Crops=[]
))
print("Saved:", out)
