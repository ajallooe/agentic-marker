#!/usr/bin/env bash
#
# Lock Assignment - Make assignment files read-only
#
# Protects assignment files from accidental modification during marking:
# - submissions/ directory and all contents (recursive)
# - .ipynb files in the assignment root
# - CSV files in gradebooks/ directory
# - overview.md (optional, enabled by default)
#
# Usage:
#   lock_assignment.sh <assignment_directory> [OPTIONS]
#

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage message
usage() {
    cat << EOF
Usage: $(basename "$0") <assignment_directory> [OPTIONS]

Make assignment files read-only to protect them during marking.

Arguments:
  assignment_directory    Path to the assignment directory

Options:
  --no-overview           Don't make overview.md read-only
  --lock-all              Lock ALL files in the assignment directory recursively
                          (directories remain writable for new file creation,
                          except submissions/ which is fully locked)
  --unlock                Remove read-only protection (make files writable again)
  --dry-run               Show what would be changed without making changes
  --verbose               Show each file being modified
  --help                  Show this help message

What gets locked (default):
  - submissions/ directory and all contents (recursive)
  - *.ipynb files in the assignment root directory
  - *.csv files in gradebooks/ directory
  - overview.md in the assignment root (unless --no-overview)

What gets locked (--lock-all):
  - ALL files in the assignment directory (recursive)
  - submissions/ directory itself (prevents new files)
  - Other directories remain writable (allows creating new files)

Examples:
  # Lock an assignment (default: includes overview.md)
  $(basename "$0") assignments/lab1

  # Lock without protecting overview.md
  $(basename "$0") assignments/lab1 --no-overview

  # Unlock an assignment (make writable again)
  $(basename "$0") assignments/lab1 --unlock

  # Preview changes without applying
  $(basename "$0") assignments/lab1 --dry-run --verbose

  # Lock everything (full protection)
  $(basename "$0") assignments/lab1 --lock-all

EOF
    exit 1
}

# Parse arguments
if [[ $# -lt 1 ]]; then
    usage
fi

ASSIGNMENT_DIR=""
LOCK_OVERVIEW=true
LOCK_ALL=false
UNLOCK_MODE=false
DRY_RUN=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-overview)
            LOCK_OVERVIEW=false
            shift
            ;;
        --lock-all)
            LOCK_ALL=true
            shift
            ;;
        --unlock)
            UNLOCK_MODE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            usage
            ;;
        -*)
            log_error "Unknown option: $1"
            usage
            ;;
        *)
            if [[ -z "$ASSIGNMENT_DIR" ]]; then
                ASSIGNMENT_DIR="$1"
            else
                log_error "Unexpected argument: $1"
                usage
            fi
            shift
            ;;
    esac
done

# Validate assignment directory
if [[ -z "$ASSIGNMENT_DIR" ]]; then
    log_error "Assignment directory is required"
    usage
fi

if [[ ! -d "$ASSIGNMENT_DIR" ]]; then
    log_error "Assignment directory not found: $ASSIGNMENT_DIR"
    exit 1
fi

# Resolve to absolute path
ASSIGNMENT_DIR="$(cd "$ASSIGNMENT_DIR" && pwd)"
ASSIGNMENT_NAME="$(basename "$ASSIGNMENT_DIR")"

# Determine chmod mode
if [[ "$UNLOCK_MODE" == true ]]; then
    MODE="u+w"
    ACTION="Unlocking"
    ACTION_PAST="unlocked"
else
    MODE="a-w"
    ACTION="Locking"
    ACTION_PAST="locked"
fi

echo "=================================================================="
echo "              $ACTION ASSIGNMENT"
echo "=================================================================="
echo
log_info "Assignment: $ASSIGNMENT_NAME"
log_info "Directory: $ASSIGNMENT_DIR"
if [[ "$LOCK_ALL" == true ]]; then
    log_info "Mode: LOCK ALL (full protection)"
fi
if [[ "$DRY_RUN" == true ]]; then
    log_warning "DRY RUN MODE - no changes will be made"
fi
echo

# Counters
FILES_MODIFIED=0
DIRS_MODIFIED=0

# Function to apply chmod
apply_chmod() {
    local target="$1"
    local description="$2"

    if [[ ! -e "$target" ]]; then
        return
    fi

    if [[ "$VERBOSE" == true ]]; then
        echo "  $description: $target"
    fi

    if [[ "$DRY_RUN" == false ]]; then
        chmod "$MODE" "$target"
    fi

    if [[ -d "$target" ]]; then
        ((DIRS_MODIFIED++)) || true
    else
        ((FILES_MODIFIED++)) || true
    fi
}

# Function to apply chmod recursively to directory contents
apply_chmod_recursive() {
    local dir="$1"
    local description="$2"

    if [[ ! -d "$dir" ]]; then
        log_warning "$description directory not found: $dir"
        return
    fi

    log_info "$ACTION $description..."

    # Lock/unlock the directory itself
    apply_chmod "$dir" "directory"

    # Lock/unlock all contents recursively
    while IFS= read -r -d '' item; do
        apply_chmod "$item" "file/dir"
    done < <(find "$dir" -print0 2>/dev/null)
}

SUBMISSIONS_DIR="$ASSIGNMENT_DIR/submissions"

if [[ "$LOCK_ALL" == true ]]; then
    # =========================================================================
    # LOCK ALL MODE: Lock all files, but keep directories writable (except submissions)
    # =========================================================================

    # 1. Lock submissions directory fully (including the directory itself)
    if [[ -d "$SUBMISSIONS_DIR" ]]; then
        apply_chmod_recursive "$SUBMISSIONS_DIR" "submissions (full lock)"
    else
        log_warning "No submissions directory found"
    fi

    # 2. Lock all OTHER files in the assignment directory (but not directories)
    log_info "$ACTION all other files..."
    while IFS= read -r -d '' item; do
        # Skip the submissions directory (already handled above)
        if [[ "$item" == "$SUBMISSIONS_DIR" || "$item" == "$SUBMISSIONS_DIR"/* ]]; then
            continue
        fi

        # Only lock files, not directories (so new files can be created)
        if [[ -f "$item" ]]; then
            apply_chmod "$item" "file"
        fi
    done < <(find "$ASSIGNMENT_DIR" -print0 2>/dev/null)

else
    # =========================================================================
    # DEFAULT MODE: Lock specific files only
    # =========================================================================

    # 1. Lock submissions directory (recursive)
    if [[ -d "$SUBMISSIONS_DIR" ]]; then
        apply_chmod_recursive "$SUBMISSIONS_DIR" "submissions"
    else
        log_warning "No submissions directory found"
    fi

    # 2. Lock .ipynb files in assignment root
    log_info "$ACTION root notebook files..."
    for notebook in "$ASSIGNMENT_DIR"/*.ipynb; do
        if [[ -f "$notebook" ]]; then
            apply_chmod "$notebook" "notebook"
        fi
    done

    # 3. Lock CSV files in gradebooks directory
    GRADEBOOKS_DIR="$ASSIGNMENT_DIR/gradebooks"
    if [[ -d "$GRADEBOOKS_DIR" ]]; then
        log_info "$ACTION gradebook CSV files..."
        for csv in "$GRADEBOOKS_DIR"/*.csv; do
            if [[ -f "$csv" ]]; then
                apply_chmod "$csv" "gradebook"
            fi
        done
    else
        if [[ "$VERBOSE" == true ]]; then
            log_info "No gradebooks directory found (optional)"
        fi
    fi

    # 4. Lock overview.md (if enabled)
    OVERVIEW_FILE="$ASSIGNMENT_DIR/overview.md"
    if [[ "$LOCK_OVERVIEW" == true ]]; then
        if [[ -f "$OVERVIEW_FILE" ]]; then
            log_info "$ACTION overview.md..."
            apply_chmod "$OVERVIEW_FILE" "overview"
        else
            log_warning "No overview.md found"
        fi
    else
        if [[ "$VERBOSE" == true ]]; then
            log_info "Skipping overview.md (--no-overview)"
        fi
    fi
fi

# Summary
echo
echo "=================================================================="
if [[ "$DRY_RUN" == true ]]; then
    log_info "DRY RUN COMPLETE - would have $ACTION_PAST:"
else
    log_success "$ACTION COMPLETE"
fi
echo "=================================================================="
echo
log_info "Files $ACTION_PAST: $FILES_MODIFIED"
log_info "Directories $ACTION_PAST: $DIRS_MODIFIED"
echo

if [[ "$UNLOCK_MODE" == true ]]; then
    log_info "Assignment files are now writable"
else
    log_info "Assignment files are now read-only"
    log_info "Use --unlock to make them writable again"
fi
echo

exit 0
