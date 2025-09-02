import yaml
from pathlib import Path

def load_yaml(path: str):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
