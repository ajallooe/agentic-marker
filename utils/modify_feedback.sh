#!/usr/bin/env bash
#
# Feedback Modifier - Apply specific modifications to feedback in CSV files
#
# Usage:
#   ./utils/modify_feedback.sh <grades.csv> --instruction "Remove all mentions of X" [OPTIONS]
#
# This script applies a specific instruction to modify feedback for each student,
# without changing anything else in the feedback.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$PROJECT_ROOT/src"

# Activate virtual environment if it exists
if [[ -f "$PROJECT_ROOT/.venv/bin/activate" ]]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

usage() {
    cat << EOF
Usage: $(basename "$0") <grades.csv> --instruction "..." [OPTIONS]

Apply a specific modification to feedback in a CSV file.
Only makes the requested changes - preserves everything else.

Arguments:
  grades.csv              Path to the CSV file with feedback

Required:
  -i, --instruction       The modification to apply (in quotes)

Options:
  --output <file>         Output CSV file (default: <input>_modified.csv)
  --provider <provider>   LLM provider: claude, gemini, codex (default: claude)
  --model <model>         Specific model to use (optional)
  --feedback-col <name>   Name of feedback column (auto-detected if not specified)
  --in-place              Modify file in-place (creates .bak backup)
  --dry-run               Preview without calling LLM
  --help                  Show this help message

Examples:
  # Remove all encouragements about random_state
  ./utils/modify_feedback.sh grades.csv -i "Remove all encouragements to use random_state"

  # Remove specific text patterns
  ./utils/modify_feedback.sh grades.csv -i "Remove any sentences mentioning 'bonus points'"

  # Add a note to all feedback
  ./utils/modify_feedback.sh grades.csv -i "Add 'Late submission: -10%' at the end"

  # Fix a common error in feedback
  ./utils/modify_feedback.sh grades.csv -i "Replace 'Activity 5' with 'Activity 6' everywhere"

  # Preview changes first
  ./utils/modify_feedback.sh grades.csv -i "Remove mentions of random_state" --dry-run

  # Modify in-place with backup
  ./utils/modify_feedback.sh grades.csv -i "Remove random_state comments" --in-place

EOF
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

# Parse arguments
CSV_FILE=""
INSTRUCTION=""
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            usage
            ;;
        -i|--instruction)
            INSTRUCTION="$2"
            shift 2
            ;;
        --output|--provider|--model|--feedback-col)
            EXTRA_ARGS+=("$1" "$2")
            shift 2
            ;;
        --dry-run|--in-place)
            EXTRA_ARGS+=("$1")
            shift
            ;;
        -*)
            echo -e "${RED}[ERROR]${NC} Unknown option: $1" >&2
            usage
            ;;
        *)
            if [[ -z "$CSV_FILE" ]]; then
                CSV_FILE="$1"
            else
                echo -e "${RED}[ERROR]${NC} Unexpected argument: $1" >&2
                usage
            fi
            shift
            ;;
    esac
done

# Validate required arguments
if [[ -z "$CSV_FILE" ]]; then
    echo -e "${RED}[ERROR]${NC} CSV file is required" >&2
    usage
fi

if [[ ! -f "$CSV_FILE" ]]; then
    echo -e "${RED}[ERROR]${NC} CSV file not found: $CSV_FILE" >&2
    exit 1
fi

if [[ -z "$INSTRUCTION" ]]; then
    echo -e "${RED}[ERROR]${NC} --instruction is required" >&2
    usage
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    FEEDBACK MODIFIER${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Instruction:${NC} $INSTRUCTION"
echo ""

# Run the Python script
python3 "$SRC_DIR/utils/modify_feedback.py" "$CSV_FILE" --instruction "$INSTRUCTION" "${EXTRA_ARGS[@]}"

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    MODIFICATION COMPLETE${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════════${NC}"
