#!/usr/bin/env python3
"""
System Configuration Loader

Loads system-wide defaults from config.yaml at the project root.
These are fallback values when not specified in assignment overview.md.

IMPORTANT: No model names or provider defaults are hardcoded here.
All defaults come from configs/config.yaml. If that file is missing,
the caller must provide explicit values.
"""

import sys
from pathlib import Path
import yaml


def get_project_root():
    """Get the project root directory."""
    # Assume this file is in src/utils/, so project root is 2 levels up
    return Path(__file__).parent.parent.parent


def get_config_path():
    """Get the path to the config.yaml file."""
    return get_project_root() / "configs" / "config.yaml"


def load_system_config():
    """
    Load system-wide configuration from config.yaml.

    Returns:
        dict: Configuration dictionary with system defaults.
              Returns empty dict if config file doesn't exist.
    """
    config_file = get_config_path()

    if not config_file.exists():
        return {}

    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            return config if config else {}
    except Exception as e:
        print(f"Warning: Failed to load config.yaml: {e}", file=sys.stderr)
        return {}


def get_default_provider():
    """
    Get the default LLM provider from system config.

    Returns:
        str or None: The default provider, or None if not configured.
    """
    config = load_system_config()
    return config.get("default_provider")


def get_default_model():
    """
    Get the default model from system config.

    Returns:
        str or None: The default model, or None if not configured.
    """
    config = load_system_config()
    return config.get("default_model")


def get_max_parallel():
    """
    Get the default max parallel workers from system config.

    Returns:
        int: The max parallel workers (defaults to 4 if not configured).
    """
    config = load_system_config()
    return config.get("max_parallel", 4)


def is_verbose():
    """
    Get the verbose setting from system config.

    Returns:
        bool: Whether verbose mode is enabled (defaults to True if not configured).
    """
    config = load_system_config()
    return config.get("verbose", True)


if __name__ == "__main__":
    # Test the configuration loader
    config = load_system_config()
    print("System configuration:")
    print(f"  config_path: {get_config_path()}")
    print(f"  default_provider: {config.get('default_provider', '(not set)')}")
    print(f"  default_model: {config.get('default_model', '(not set)')}")
    print(f"  max_parallel: {config.get('max_parallel', '(not set)')}")
    print(f"  verbose: {config.get('verbose', '(not set)')}")
