#!/usr/bin/env bash
#
# Show Errors - Display error summary for an assignment's marking run
#
# Usage:
#   show_errors.sh <assignment_directory> [--stage STAGE] [--json]
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
    cat << EOF
Usage: $(basename "$0") <assignment_directory> [OPTIONS]

Display a consolidated error summary for a marking run.

Arguments:
  assignment_directory    Path to the assignment directory

Options:
  --stage STAGE           Show errors for specific stage only (marker, unifier, all)
                          Default: all
  --json                  Also output JSON format
  --quiet                 Only show output if there are errors
  --help                  Show this help message

Examples:
  # Show all errors for an assignment
  $(basename "$0") assignments/lab1

  # Show only unifier errors
  $(basename "$0") assignments/lab1 --stage unifier

  # Export to JSON
  $(basename "$0") assignments/lab1 --json

EOF
    exit 1
}

# Parse arguments
if [[ $# -lt 1 ]]; then
    usage
fi

ASSIGNMENT_DIR=""
STAGE="all"
JSON_FLAG=""
QUIET_FLAG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --stage)
            STAGE="$2"
            shift 2
            ;;
        --json)
            JSON_FLAG="--json"
            shift
            ;;
        --quiet)
            QUIET_FLAG="--quiet"
            shift
            ;;
        --help)
            usage
            ;;
        -*)
            echo -e "${RED}[ERROR]${NC} Unknown option: $1" >&2
            usage
            ;;
        *)
            if [[ -z "$ASSIGNMENT_DIR" ]]; then
                ASSIGNMENT_DIR="$1"
            else
                echo -e "${RED}[ERROR]${NC} Unexpected argument: $1" >&2
                usage
            fi
            shift
            ;;
    esac
done

# Validate assignment directory
if [[ -z "$ASSIGNMENT_DIR" ]]; then
    echo -e "${RED}[ERROR]${NC} Assignment directory is required" >&2
    usage
fi

if [[ ! -d "$ASSIGNMENT_DIR" ]]; then
    echo -e "${RED}[ERROR]${NC} Assignment directory not found: $ASSIGNMENT_DIR" >&2
    exit 1
fi

# Resolve to absolute path
ASSIGNMENT_DIR="$(cd "$ASSIGNMENT_DIR" && pwd)"
PROCESSED_DIR="$ASSIGNMENT_DIR/processed"
LOGS_DIR="$PROCESSED_DIR/logs"
MANIFEST="$PROCESSED_DIR/submissions_manifest.json"
FINAL_DIR="$PROCESSED_DIR/final"

if [[ ! -d "$PROCESSED_DIR" ]]; then
    echo -e "${YELLOW}[WARNING]${NC} No processed directory found. Has marking been run?" >&2
    exit 0
fi

# Function to run error summary for a stage
run_summary() {
    local stage_name="$1"
    local logs_subdir="$2"
    local stage_logs="$LOGS_DIR/$logs_subdir"

    if [[ -d "$stage_logs" ]]; then
        echo ""
        python3 "$PROJECT_ROOT/src/utils/error_summary.py" \
            --logs-dir "$stage_logs" \
            --stage "$stage_name" \
            --manifest "$MANIFEST" \
            --final-dir "$FINAL_DIR" \
            $JSON_FLAG \
            $QUIET_FLAG || true
    fi
}

# Run for requested stages
case "$STAGE" in
    marker)
        run_summary "marker" "marker_logs"
        ;;
    unifier)
        run_summary "unifier" "unifier_logs"
        ;;
    all)
        # Check marker logs
        if [[ -d "$LOGS_DIR/marker_logs" ]]; then
            run_summary "marker" "marker_logs"
        fi

        # Check unifier logs
        if [[ -d "$LOGS_DIR/unifier_logs" ]]; then
            run_summary "unifier" "unifier_logs"
        fi

        # If no logs found
        if [[ ! -d "$LOGS_DIR/marker_logs" && ! -d "$LOGS_DIR/unifier_logs" ]]; then
            echo -e "${GREEN}[INFO]${NC} No parallel task logs found in $LOGS_DIR"
            echo "This may mean:"
            echo "  - Marking hasn't reached the parallel stages yet"
            echo "  - Or logs were cleaned up"
        fi
        ;;
    *)
        echo -e "${RED}[ERROR]${NC} Invalid stage: $STAGE (must be: marker, unifier, all)" >&2
        exit 1
        ;;
esac

echo ""
