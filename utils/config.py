# utils/config.py
from pathlib import Path
import yaml
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class ModelParams(BaseModel):
    max_depth: int
    n_estimators: int
    learning_rate: float

class Config(BaseModel):
    paths: dict
    inputs: dict
    model: dict
    cli: dict
    flags: dict

def load_config(path: str = "config.yaml") -> Config:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at: {path}")
    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)
    return Config(**raw)