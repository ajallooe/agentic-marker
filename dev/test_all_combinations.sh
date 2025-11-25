#!/usr/bin/env bash
#
# Quick marker test script
# Tests marker agents with: 2 assignments × 3 providers × 2 execution modes = 12 combinations
# Uses small subset of students (3 per assignment) for speed
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$PROJECT_ROOT/src"

cd "$PROJECT_ROOT"

# Test configuration
ASSIGNMENTS=(
    "assignments/sample-assignment"
    "assignments/Lab 02 - Decision Tree Classifier"
)

PROVIDERS=("claude" "gemini" "codex")
MODES=("parallel" "xargs")
MAX_STUDENTS=3  # Limit to 3 students per test for speed

# Results tracking
TEST_RESULTS_DIR="$PROJECT_ROOT/dev/test_results"
mkdir -p "$TEST_RESULTS_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_FILE="$TEST_RESULTS_DIR/test_run_${TIMESTAMP}.log"

# Counters
declare -A TEST_STATUS

echo "========================================"
echo "Marker Agent Quick Test Suite"
echo "Started: $(date)"
echo "Testing: 2 assignments × 3 providers × 2 modes = 12 tests"
echo "Max students per test: $MAX_STUDENTS"
echo "========================================"
echo ""

# Function to run a single marker test
run_marker_test() {
    local assignment="$1"
    local provider="$2"
    local mode="$3"
    local test_id="$4"

    local test_name="$(basename "$assignment" | sed 's/ /_/g')_${provider}_${mode}"
    local test_log="$TEST_RESULTS_DIR/${test_name}.log"
    local test_tasks="$TEST_RESULTS_DIR/${test_name}_tasks.txt"
    local test_output="$TEST_RESULTS_DIR/${test_name}_output"

    {
        echo "Test: $test_name"
        echo "Assignment: $assignment"
        echo "Provider: $provider"
        echo "Mode: $mode"
        echo "Started: $(date)"
        echo ""

        # Find submissions manifest
        local manifest="$assignment/processed/submissions_manifest.json"
        if [[ ! -f "$manifest" ]]; then
            echo "ERROR: Submissions manifest not found: $manifest"
            echo "Run mark_structured.sh first to generate manifest"
            exit 1
        fi

        # Create limited task list (first MAX_STUDENTS students, first activity only)
        > "$test_tasks"
        local count=0
        jq -r '.submissions[] | .path + "|" + .student_name' "$manifest" | while IFS='|' read -r submission_path student_name; do
            if [[ $count -ge $MAX_STUDENTS ]]; then
                break
            fi
            ((count++))

            local output_file="$test_output/${student_name}_A1.md"
            mkdir -p "$test_output"

            echo "python3 '$SRC_DIR/agents/marker.py' --activity A1 --student '$student_name' --submission '$submission_path' --output '$output_file' --provider '$provider'" >> "$test_tasks"
        done

        local task_count=$(wc -l < "$test_tasks" | tr -d ' ')
        echo "Generated $task_count marker tasks"
        echo ""

        # Run parallel_runner
        mkdir -p "$test_output/logs"
        local runner_args=(
            --tasks "$test_tasks"
            --concurrency 2
            --output-dir "$test_output/logs"
            --verbose
        )

        if [[ "$mode" == "xargs" ]]; then
            runner_args+=(--force-xargs)
        fi

        if bash "$SRC_DIR/parallel_runner.sh" "${runner_args[@]}"; then
            echo ""
            echo "✅ SUCCESS"

            # Count successes and errors
            local success_count=$(find "$test_output" -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
            local error_count=$(find "$test_output/logs" -name stderr -type f -size +0 2>/dev/null | wc -l | tr -d ' ')

            echo "Results: $success_count successful, $error_count errors"
            TEST_STATUS[$test_id]="PASS"
        else
            echo ""
            echo "❌ FAILED"
            TEST_STATUS[$test_id]="FAIL"
        fi

        echo "Completed: $(date)"
    } > "$test_log" 2>&1

    # Show progress
    if [[ "${TEST_STATUS[$test_id]}" == "PASS" ]]; then
        echo "[$test_id] ✅ $test_name"
    else
        echo "[$test_id] ❌ $test_name (see $test_log)"
    fi
}

# Export function for parallel execution
export -f run_marker_test
export SRC_DIR
export TEST_RESULTS_DIR
export MAX_STUDENTS
export -A TEST_STATUS

# Run all tests in parallel (max 4 at a time)
test_id=0
test_commands=()

for assignment in "${ASSIGNMENTS[@]}"; do
    for provider in "${PROVIDERS[@]}"; do
        for mode in "${MODES[@]}"; do
            ((test_id++))
            test_commands+=("run_marker_test \"$assignment\" \"$provider\" \"$mode\" $test_id")
        done
    done
done

# Run tests in parallel
printf '%s\n' "${test_commands[@]}" | xargs -P 4 -I {} bash -c '{}'

# Summary
echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"

PASSED=0
FAILED=0

for ((i=1; i<=12; i++)); do
    if [[ "${TEST_STATUS[$i]:-UNKNOWN}" == "PASS" ]]; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
done

echo "Total: 12 tests"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""
echo "Detailed logs in: $TEST_RESULTS_DIR"
echo "Summary saved to: $RESULTS_FILE"

# Save summary to file
{
    echo "Test Run: $TIMESTAMP"
    echo "Passed: $PASSED / 12"
    echo "Failed: $FAILED / 12"
    echo ""
    for ((i=1; i<=12; i++)); do
        echo "Test $i: ${TEST_STATUS[$i]:-UNKNOWN}"
    done
} > "$RESULTS_FILE"

if [[ $FAILED -gt 0 ]]; then
    exit 1
else
    exit 0
fi
