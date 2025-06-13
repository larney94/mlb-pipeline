"""
Project-wide helper utilities for
✅ CLI override handling
✅ Output-path resolution
✅ Lightweight type/structure safety

All pipeline modules are expected to:

    >>> from utils.cli_utils import apply_cli_overrides, resolve_output_path
    >>> cfg = apply_cli_overrides(cfg, overrides=args.set)   # --set key=value [...]
    >>> output_file = resolve_output_path(cfg['outputs']['foo'], cfg)

This file purposefully contains **zero** third-party dependencies beyond the
standard library + PyYAML (already used in utils.config).  It is therefore
safe to import in any execution environment (scripts, tests, CI).

Author: Pipeline-Core Team · 2025-06
"""
from __future__ import annotations

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Sequence, Union

import yaml  # PyYAML – already required by utils.config
from utils.logging_utils import get_rotating_logger

_LOG = logging.getLogger(__name__)
LOGGER = get_rotating_logger("cli_utils")


# --------------------------------------------------------------------------- #
# Generic helpers
# --------------------------------------------------------------------------- #
def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def _set_dotted(cfg: Dict[str, Any], dotted_key: str, value: Any) -> None:
    """Create nested keys on‐the‐fly and set the final value."""
    keys = dotted_key.split(".")
    target = cfg
    for key in keys[:-1]:
        if key not in target or not isinstance(target[key], dict):
            target[key] = {}
        target = target[key]
    target[keys[-1]] = value


def _get_base_outputs_dir(cfg: Dict[str, Any]) -> Path | None:
    outputs = cfg.get("outputs", {})
    if isinstance(outputs, dict):
        base = outputs.get("dir")
        if base:
            return Path(base).expanduser().resolve()
    return None


# --------------------------------------------------------------------------- #
# 🔑  Pydantic-safe CLI override merge
# --------------------------------------------------------------------------- #
def apply_cli_overrides(
    cfg,                          # Pydantic BaseModel *or* plain dict
    overrides: Sequence[str] | None = None,
):
    """
    Merge dotted KEY=VALUE overrides into `cfg`.

    * Works with Pydantic v1/v2 or plain nested dicts.
    * Returns the **same type** as provided (BaseModel or dict).
    """
    if not overrides:
        return cfg

    # 1️⃣  Convert cfg → plain dict so PyYAML can deep-copy it
    if hasattr(cfg, "model_dump"):          # Pydantic v2
        raw_dict = cfg.model_dump(mode="python")
    elif hasattr(cfg, "dict"):              # Pydantic v1
        raw_dict = cfg.dict()
    else:                                   # Already a dict
        raw_dict = cfg

    merged = yaml.safe_load(yaml.safe_dump(raw_dict))  # deep copy via YAML

    # 2️⃣  Apply each dotted override
    for raw in overrides:
        if "=" not in raw:
            raise ValueError(f"--set override must be KEY=VALUE (got '{raw}')")
        dotted_key, raw_val = raw.split("=", 1)
        try:
            parsed_val = yaml.safe_load(raw_val)
        except Exception:
            parsed_val = raw_val
        _LOG.debug("CLI override: %s = %r", dotted_key, parsed_val)
        _set_dotted(merged, dotted_key, parsed_val)

    # 3️⃣  Reconstruct original object type for validation
    if not isinstance(cfg, dict):
        return cfg.__class__(**merged)      # type: ignore[arg-type]
    return merged


# --------------------------------------------------------------------------- #
# Overwrite-policy resolver
# --------------------------------------------------------------------------- #
def resolve_output_path(path: Union[str, Path], policy: str) -> Path:
    """Return absolute path, enforcing overwrite-policy (`force|warn|error`)."""
    path = Path(os.path.expandvars(os.path.expanduser(str(path)))).resolve()
    policy = policy.strip().lower()

    if path.exists():
        if policy == "error":
            raise FileExistsError(f"{path} already exists and overwrite policy = error")
        if policy == "warn":
            LOGGER.warning("%s exists — overwriting (policy=warn)", path)
        elif policy != "force":
            raise ValueError(f"Invalid overwrite policy: {policy}")
    return path


# --------------------------------------------------------------------------- #
# Parse --set flags from arbitrary argv list
# --------------------------------------------------------------------------- #
def extract_set_overrides(argv: List[str] | None = None) -> List[str]:
    argv = argv or sys.argv[1:]
    overrides: List[str] = []
    idx = 0
    while idx < len(argv):
        token = argv[idx]
        if token == "--set":
            if idx + 1 >= len(argv):
                raise ValueError("--set flag provided without KEY=VALUE")
            overrides.append(argv[idx + 1])
            idx += 2
        elif token.startswith("--set="):
            overrides.append(token[len("--set="):])
            idx += 1
        else:
            idx += 1
    return overrides


# --------------------------------------------------------------------------- #
# Simple helper: should we write a file, based on overwrite_policy?
# --------------------------------------------------------------------------- #
def handle_overwrite(output_path: str | Path, cfg: dict) -> bool:
    output_path = Path(output_path)
    policy = cfg.get("overwrite_policy", "error").strip().lower()

    if output_path.exists():
        if policy == "error":
            raise FileExistsError(f"{output_path} exists (overwrite_policy=error)")
        if policy == "warn":
            LOGGER.warning("%s exists — skipping (overwrite_policy=warn)", output_path)
            return False
        if policy == "force":
            LOGGER.info("%s exists — overwriting (overwrite_policy=force)", output_path)
            return True
        raise ValueError(f"Invalid overwrite_policy: {policy}")
    return True
