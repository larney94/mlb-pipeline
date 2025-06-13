from pathlib import Path
import yaml
from pydantic import BaseModel


# Define structured sub-sections of the config
class InputsConfig(BaseModel):
    recent_gamelogs_csv: str
    static_player_csv: str


class OutputsConfig(BaseModel):
    context_dir: str
    full_feature_set: str


# Full config schema
class Config(BaseModel):
    inputs: InputsConfig
    outputs: OutputsConfig
    model: dict = {}
    paths: dict = {}
    cli: dict = {}
    flags: dict = {}


# Load and parse the YAML config
def load_config(path: str = "config.yaml") -> Config:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at: {path}")
    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)
    return Config(**raw)
