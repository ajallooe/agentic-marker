#!/usr/bin/env python3
"""
System Configuration Loader

Loads system-wide defaults from config.yaml and models.yaml at the project root.
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


def get_models_config_path():
    """Get the path to the models.yaml file."""
    return get_project_root() / "configs" / "models.yaml"


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


def get_api_max_parallel():
    """
    Get the max parallel workers for API mode from system config.

    API mode can handle higher parallelism due to better rate limits
    compared to CLI tools.

    Returns:
        int: The max parallel workers for API mode (defaults to 32 if not configured).
    """
    config = load_system_config()
    return config.get("api_max_parallel", 32)


def is_verbose():
    """
    Get the verbose setting from system config.

    Returns:
        bool: Whether verbose mode is enabled (defaults to True if not configured).
    """
    config = load_system_config()
    return config.get("verbose", True)


def load_models_config():
    """
    Load models configuration from models.yaml.

    Returns:
        dict: Configuration dictionary with models and defaults.
              Returns empty dict if config file doesn't exist.
    """
    config_file = get_models_config_path()

    if not config_file.exists():
        return {}

    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            return config if config else {}
    except Exception as e:
        print(f"Warning: Failed to load models.yaml: {e}", file=sys.stderr)
        return {}


def get_available_models(section: str = None):
    """
    Get all available models grouped by provider.

    Args:
        section: Specific section to get models from ('api_models', 'cli_models', or None for both).

    Returns:
        dict: Dictionary mapping provider names to lists of model names.
    """
    config = load_models_config()

    # Group models by provider
    by_provider = {'claude': [], 'gemini': [], 'codex': []}

    sections_to_check = []
    if section:
        sections_to_check = [section]
    else:
        sections_to_check = ['api_models', 'cli_models']

    for sec in sections_to_check:
        models = config.get(sec, {})
        for model_name, provider in models.items():
            if provider in by_provider and model_name not in by_provider[provider]:
                by_provider[provider].append(model_name)

    return by_provider


def format_available_models():
    """
    Format available models for display in error messages.

    Returns:
        str: Formatted string listing all available models by provider.
    """
    config = load_models_config()
    lines = ["Available models (from configs/models.yaml):"]

    # API models
    lines.append("")
    lines.append("  API models (--api-model):")
    api_models = config.get('api_models', {})
    api_by_provider = {'claude': [], 'gemini': [], 'codex': []}
    for model_name, provider in api_models.items():
        if provider in api_by_provider:
            api_by_provider[provider].append(model_name)

    for provider in ['claude', 'gemini', 'codex']:
        models = api_by_provider.get(provider, [])
        if models:
            lines.append(f"    {provider}: {', '.join(sorted(models))}")
        else:
            lines.append(f"    {provider}: (none)")

    # CLI models
    lines.append("")
    lines.append("  CLI models (--model):")
    cli_models = config.get('cli_models', {})
    cli_by_provider = {'claude': [], 'gemini': [], 'codex': []}
    for model_name, provider in cli_models.items():
        if provider in cli_by_provider:
            cli_by_provider[provider].append(model_name)

    for provider in ['claude', 'gemini', 'codex']:
        models = cli_by_provider.get(provider, [])
        if models:
            lines.append(f"    {provider}: {', '.join(sorted(models))}")
        else:
            lines.append(f"    {provider}: (none)")

    lines.append("")
    lines.append("To add a new model, update configs/models.yaml")

    return '\n'.join(lines)


def resolve_provider_from_model(model_name: str, section: str = None) -> str | None:
    """
    Resolve provider from model name using models.yaml.

    Only returns a provider if the model is explicitly listed in models.yaml.
    This catches typos like 'gemini-pro-2.5' instead of 'gemini-2.5-pro'.

    Args:
        model_name: The model name to look up.
        section: Which section to look in ('api_models', 'cli_models', or None for both).
                 If None, checks api_models first, then cli_models.

    Returns:
        str or None: The provider name, or None if model not found in models.yaml.
    """
    config = load_models_config()

    # Determine which sections to check
    if section:
        sections = [section]
    else:
        # Check both sections, api_models first (most common for headless/API calls)
        sections = ['api_models', 'cli_models']

    for sec in sections:
        models = config.get(sec, {})
        if model_name in models:
            return models[model_name]

    # No fallback inference - model must be in models.yaml
    return None


def get_expensive_models() -> list:
    """
    Get the list of expensive models from models.yaml.

    Returns:
        list: List of model names that are marked as expensive.
    """
    config = load_models_config()
    return config.get('expensive', [])


def is_expensive_model(model_name: str) -> bool:
    """
    Check if a model is marked as expensive.

    Args:
        model_name: The model name to check.

    Returns:
        bool: True if the model is in the expensive list.
    """
    if not model_name:
        return False
    return model_name in get_expensive_models()


def validate_default_model(model_name: str, source: str = "config") -> tuple[bool, str]:
    """
    Validate that a model is allowed to be used as a default.

    Expensive models cannot be used as defaults in config.yaml or overview.md.
    They must be explicitly specified via CLI argument.

    Args:
        model_name: The model name to validate.
        source: Description of where the default was set (for error messages).

    Returns:
        tuple: (is_valid, error_message)
    """
    if not model_name:
        return True, ""

    if is_expensive_model(model_name):
        expensive_list = get_expensive_models()
        return False, (
            f"Error: '{model_name}' is an expensive model and cannot be used as default in {source}.\n"
            f"Expensive models ({', '.join(expensive_list)}) must be explicitly specified via CLI:\n"
            f"  --model {model_name}     (for CLI mode)\n"
            f"  --api-model {model_name} (for API mode)"
        )

    return True, ""


if __name__ == "__main__":
    # Test the configuration loader
    config = load_system_config()
    print("System configuration:")
    print(f"  config_path: {get_config_path()}")
    print(f"  default_provider: {config.get('default_provider', '(not set)')}")
    print(f"  default_model: {config.get('default_model', '(not set)')}")
    print(f"  max_parallel: {config.get('max_parallel', '(not set)')}")
    print(f"  verbose: {config.get('verbose', '(not set)')}")
    print()
    print(format_available_models())
