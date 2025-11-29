#!/usr/bin/env bash
#
# Wrapper script for create_overview.py
# Generates overview.md from a Jupyter notebook using LLM analysis
#
# Usage:
#   ./create_overview.sh <notebook_path> --model <model_name>
#
# Examples:
#   ./create_overview.sh assignments/lab1/notebook.ipynb --model claude-sonnet-4-5
#   ./create_overview.sh notebook.ipynb --model gemini-2.5-pro
#   ./create_overview.sh notebook.ipynb --model gpt-5.1
#

set -e  # Exit on error

# Get the directory where this script is located and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Activate virtual environment if it exists
if [[ -f "$PROJECT_ROOT/.venv/bin/activate" ]]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

# Call the Python script with all arguments passed through
python3 "$PROJECT_ROOT/src/create_overview.py" "$@"
