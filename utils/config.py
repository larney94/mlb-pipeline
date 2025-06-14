from pathlib import Path
import yaml
from pydantic import BaseModel

# --------------------------------------------------------------------------- #
# Structured sub-sections of the config
# --------------------------------------------------------------------------- #
class InputsConfig(BaseModel):
    recent_gamelogs_csv: str = ""
    static_player_csv: str = ""
    static_team_csv: str = ""
    true_lines_dir: str = ""
    recent_predictions_dir: str = ""
    combined_preds_dir: str = ""
    gamelogs_source: str = ""
    context_features: str = ""  # Required by module_i

class OutputsConfig(BaseModel):
    context_dir: str = ""
    full_feature_set: str = ""
    model_predictions: str = ""  # Required for module_i
    root: str = ""               # Required by pipeline

class LogsConfig(BaseModel):
    pipeline_log: str = ""       # Required by pipeline.py

class PipelineConfig(BaseModel):
    concurrency: int = 1
    continue_on_failure: bool = False

# --------------------------------------------------------------------------- #
# Imports
# --------------------------------------------------------------------------- #
from pydantic import BaseModel, Field          # ← make sure Field is imported
# (keep the rest of the existing imports)

# --------------------------------------------------------------------------- #
# Full Config schema
# --------------------------------------------------------------------------- #
class Config(BaseModel):
    logs: dict = Field(default_factory=dict)        # optional
    inputs: InputsConfig
    outputs: OutputsConfig
    pipeline: dict = Field(default_factory=dict)    # optional
    overwrite_policy: str = ""
    model_path: str = ""                            # Used by module_i
    required_features: list[str] = []               # Used by module_i
    model: dict = {}
    paths: dict = {}
    cli: dict = {}
    flags: dict = {}

    model_config = {
        "protected_namespaces": (),   # suppress Pydantic warning
        "extra": "allow",             # ignore unknown keys
    }

# --------------------------------------------------------------------------- #
# Load and parse the YAML config into a validated Config object
# --------------------------------------------------------------------------- #
def load_config(path: str = "config.yaml") -> Config:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at: {path}")
    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)
    return Config(**raw)

# --------------------------------------------------------------------------- #
# Apply dotted CLI overrides to the config dict (legacy support only)
# --------------------------------------------------------------------------- #
def apply_cli_overrides(config: dict, overrides: list[str]) -> dict:
    """
    Apply CLI dotted overrides to a nested config dict.
    Example override: 'pipeline.concurrency=4'
    """
    for override in overrides:
        if '=' not in override:
            continue
        path, value = override.split('=', 1)
        keys = path.strip().split('.')
        ref = config
        for k in keys[:-1]:
            ref = ref.setdefault(k, {})
        try:
            ref[keys[-1]] = eval(value, {}, {})
        except:
            ref[keys[-1]] = value
    return config
