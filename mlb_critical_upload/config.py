from pathlib import Path
from typing import List, Dict, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl
import yaml


# ───────────────────────────────────────────────────────────────
# Section: Sub-Configs
# ───────────────────────────────────────────────────────────────

class Metadata(BaseModel):
    project: str
    owner: str
    team: Optional[str]
    tags: List[str]
    release_channel: Literal["alpha", "beta", "stable"]
    notify_on_success: bool
    notify_on_failure: bool
    notify_emails: List[str]


class LoggingConfig(BaseModel):
    dir: str
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
    max_bytes: int
    backup_count: int
    log_to_stdout: bool
    format: str
    datefmt: str
    style: str


class CLIConfig(BaseModel):
    config_path: str
    modules: str
    concurrency: int
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
    overwrite_policy: Literal["safe", "force", "skip", "warn"]
    debug: bool


class PipelineConfig(BaseModel):
    concurrency: int
    continue_on_failure: bool
    fail_fast: bool
    strict_schema: bool
    retry_failed_modules: bool
    max_retry_attempts: int


class StaticCSV(BaseModel):
    name: str
    url: HttpUrl


class InputsConfig(BaseModel):
    seasons: List[int]
    gamelogs_source: str
    recent_gamelogs_csv: str
    static_player_csv: str
    static_team_csv: str
    true_lines_dir: str
    recent_predictions_dir: str
    combined_preds_dir: str
    context_features: str
    static_csvs: List[StaticCSV]


class OutputsConfig(BaseModel):
    gamelogs_dir: str
    static_dir: str
    context_dir: str
    merged_dir: str
    starters_dir: str
    full_feature_set: str
    consolidated_predictions: str
    model_dir: str
    model_predictions: str  # Required by module_i.py
    final_preds_csv: str
    final_preds_txt: str
    output_dir: str
    tmp_dir: str
    archive_dir: str
    root: Optional[str] = ""  # Required by pipeline.py

    class Config:
        protected_namespaces = ()  # suppress model_ warning


class RollingWindowSpec(BaseModel):
    days: int
    stats: List[str]


class RollingWindowConfig(BaseModel):
    windows: List[RollingWindowSpec]


class ModelParams(BaseModel):
    max_depth: int
    n_estimators: int
    learning_rate: float


class ModelConfig(BaseModel):
    model_type: str
    path: str
    params: ModelParams
    use_cross_validation: bool
    cross_val_folds: int
    early_stopping_rounds: int
    random_state: int
    eval_metric: str

    class Config:
        protected_namespaces = ()  # suppress model_ warning


class LLMConfig(BaseModel):
    endpoint: HttpUrl
    prompt_template: str
    model: str
    temperature: float
    max_tokens: int
    retry_on_error: bool
    max_retries: int
    delay_between_retries_sec: float
    enable_streaming: bool


class FlagsConfig(BaseModel):
    use_cached_data: bool
    save_predictions: bool
    validate_config_keys: bool
    profile_modules: bool
    dry_run: bool
    time_each_module: bool
    mock_llm: bool


# ───────────────────────────────────────────────────────────────
# Section: Full Schema
# ───────────────────────────────────────────────────────────────

class Config(BaseModel):
    version: str
    environment: Literal["dev", "test", "prod"]
    metadata: Metadata
    logging: LoggingConfig
    cli: CLIConfig
    pipeline: PipelineConfig
    overwrite_policy: Literal["safe", "force", "skip", "warn"]
    inputs: InputsConfig
    outputs: OutputsConfig
    rolling_windows: RollingWindowConfig
    model: ModelConfig
    llm: LLMConfig
    flags: FlagsConfig
    required_features: List[str]
    paths: Dict[str, str]

    model_config = {
        "protected_namespaces": (),
        "extra": "allow"
    }


# ───────────────────────────────────────────────────────────────
# Section: Loaders
# ───────────────────────────────────────────────────────────────

def load_config(path: str = "config.yaml") -> Config:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at: {path}")
    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)
    return Config(**raw)


def apply_cli_overrides(config: Config, overrides: List[str]) -> Config:
    """
    Apply CLI-style dotted key overrides.
    Example: ['pipeline.concurrency=4', 'flags.mock_llm=True']
    """
    if not overrides:
        return config
    config_dict = config.dict()
    for override in overrides:
        if "=" not in override:
            continue
        key_path, value = override.split("=", 1)
        keys = key_path.strip().split(".")
        ref = config_dict
        for k in keys[:-1]:
            ref = ref.setdefault(k, {})
        try:
            ref[keys[-1]] = eval(value, {}, {})  # safely evaluate int, float, bool
        except Exception:
            ref[keys[-1]] = value  # fallback to string
    return Config(**config_dict)
