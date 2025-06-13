"""
Project-wide helper utilities for
✅ CLI override handling
✅ Output-path resolution
✅ Lightweight type/structure safety

All pipeline modules are expected to:

    >>> from utils.cli_utils import apply_cli_overrides, resolve_output_path
    >>> cfg = apply_cli_overrides(cfg, overrides=args.set)          # --set key=value [...]
    >>> output_file = resolve_output_path(cfg['outputs']['foo'], cfg)

This file purposefully contains **zero** third-party dependencies beyond the
standard library + `PyYAML` (already used in utils.config).  It is therefore
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


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def _set_dotted(cfg: Dict[str, Any], dotted_key: str, value: Any) -> None:
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


def apply_cli_overrides(
    cfg: Dict[str, Any],
    overrides: Sequence[str] | None = None,
) -> Dict[str, Any]:
    if not overrides:
        return cfg

    merged = yaml.safe_load(yaml.safe_dump(cfg))  # deep copy via yaml round-trip

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

    return merged


def resolve_output_path(path: Union[str, Path], policy: str) -> Path:
    """Resolve an output path and apply overwrite policy."""
    logger = get_rotating_logger("overwrite_policy")

    path = Path(os.path.expandvars(os.path.expanduser(str(path)))).resolve()
    policy = policy.strip().lower()

    if path.exists():
        if policy == "error":
            raise FileExistsError(f"{path} already exists and overwrite policy is 'error'")
        elif policy == "warn":
            logger.warning(f"{path} already exists and will be overwritten due to 'warn' policy.")
        elif policy != "force":
            raise ValueError(f"Invalid overwrite policy: {policy}")
    return path


def extract_set_overrides(argv: List[str] | None = None) -> List[str]:
    argv = argv or sys.argv[1:]
    overrides: List[str] = []
    idx = 0
    while idx < len(argv):
        token = argv[idx]
        if token == "--set":
            try:
                overrides.append(argv[idx + 1])
            except IndexError:
                raise ValueError("--set flag provided without following KEY=VALUE")
            idx += 2
        elif token.startswith("--set="):
            overrides.append(token[len("--set="):])
            idx += 1
        else:
            idx += 1
    return overrides


def handle_overwrite(output_path: str | Path, cfg: dict) -> bool:
    output_path = Path(output_path)
    policy = cfg.get("overwrite_policy", "error").strip().lower()

    if output_path.exists():
        if policy == "error":
            raise FileExistsError(f"{output_path} exists and overwrite_policy=error")
        elif policy == "warn":
            LOGGER.warning(f"{output_path} exists — skipping due to overwrite_policy=warn")
            return False
        elif policy == "force":
            LOGGER.info(f"{output_path} exists — overwriting due to overwrite_policy=force")
            return True
        else:
            raise ValueError(f"Invalid overwrite_policy: {policy}")
    return True
