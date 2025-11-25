#!/usr/bin/env python3
"""
Configuration parser for overview.md files.

Supports YAML front matter and key-value pairs.
"""

import re
import sys
from pathlib import Path
from typing import Dict, Any, Optional


def parse_overview(overview_path: str) -> Dict[str, Any]:
    """
    Parse overview.md file for configuration.

    Supports two formats:
    1. YAML front matter (between --- delimiters)
    2. Key: value pairs anywhere in the file

    Args:
        overview_path: Path to overview.md file

    Returns:
        Dictionary of configuration values with defaults
    """
    config = {
        'default_provider': 'claude',
        'default_model': '',
        'max_parallel': 4,
        'base_file': '',
        'assignment_type': 'structured',
        'total_marks': 100,
        'description': ''
    }

    if not Path(overview_path).exists():
        return config

    with open(overview_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Try to parse YAML front matter first
    yaml_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)

    if yaml_match:
        yaml_content = yaml_match.group(1)
        description = yaml_match.group(2).strip()

        # Parse YAML-like content (simple key: value pairs)
        for line in yaml_content.split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('#'):
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if value.startswith(('"', "'")) and value.endswith(('"', "'")):
                    value = value[1:-1]

                # Try to convert to appropriate type
                if key in config:
                    if isinstance(config[key], int):
                        try:
                            config[key] = int(value)
                        except ValueError:
                            config[key] = value
                    else:
                        config[key] = value

        config['description'] = description

    else:
        # Fallback: look for key-value pairs in the entire file
        config['description'] = content

        # Look for specific patterns
        patterns = {
            'default_provider': r'default_provider:\s*(.+)',
            'default_model': r'default_model:\s*(.+)',
            'max_parallel': r'max_parallel:\s*(\d+)',
            'base_file': r'base_file:\s*(.+)',
            'assignment_type': r'assignment_type:\s*(.+)',
            'total_marks': r'total_marks:\s*(\d+)',
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                value = match.group(1).strip()

                # Remove quotes
                if value.startswith(('"', "'")) and value.endswith(('"', "'")):
                    value = value[1:-1]

                # Convert to int if needed
                if isinstance(config[key], int):
                    try:
                        config[key] = int(value)
                    except ValueError:
                        pass
                else:
                    config[key] = value

    return config


def print_config(config: Dict[str, Any]):
    """Print configuration in a readable format."""
    print("Configuration:")
    for key, value in config.items():
        if key != 'description':
            print(f"  {key}: {value}")


def export_bash_vars(config: Dict[str, Any]) -> str:
    """
    Export configuration as bash variable assignments.

    Returns:
        String of bash export statements
    """
    bash_lines = []

    mapping = {
        'default_provider': 'DEFAULT_PROVIDER',
        'default_model': 'DEFAULT_MODEL',
        'max_parallel': 'MAX_PARALLEL',
        'base_file': 'BASE_FILE',
        'assignment_type': 'ASSIGNMENT_TYPE',
        'total_marks': 'TOTAL_MARKS'
    }

    for key, bash_var in mapping.items():
        value = config.get(key, '')
        if isinstance(value, str):
            bash_lines.append(f'{bash_var}="{value}"')
        else:
            bash_lines.append(f'{bash_var}={value}')

    return '\n'.join(bash_lines)


def main():
    """CLI interface for configuration parser."""
    if len(sys.argv) < 2:
        print("Usage: config_parser.py <overview.md> [--bash]")
        print("  --bash: Output as bash variable assignments")
        sys.exit(1)

    overview_path = sys.argv[1]
    output_bash = '--bash' in sys.argv

    config = parse_overview(overview_path)

    if output_bash:
        print(export_bash_vars(config))
    else:
        print_config(config)
        if config['description']:
            print(f"\nDescription preview:")
            preview = config['description'][:200]
            if len(config['description']) > 200:
                preview += "..."
            print(f"  {preview}")


if __name__ == "__main__":
    main()
