#!/usr/bin/env python3
"""
Error Summary Generator

Analyzes parallel task logs and generates a consolidated error report.
Shows which students/tasks failed and why.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional


def find_failed_tasks(output_dir: Path, expected_outputs: Optional[Path] = None) -> List[Dict]:
    """
    Find tasks that failed by checking stderr files and missing outputs.

    Args:
        output_dir: Directory containing parallel runner output (with subdirs like '1/')
        expected_outputs: Optional file listing expected output files

    Returns:
        List of dicts with failure information
    """
    failures = []

    # Find the results directory (usually named '1' by GNU parallel)
    results_dirs = [d for d in output_dir.iterdir() if d.is_dir() and d.name.isdigit()]
    if not results_dirs:
        results_dirs = [output_dir]

    for results_dir in results_dirs:
        # Iterate through task directories
        for task_dir in results_dir.iterdir():
            if not task_dir.is_dir():
                continue

            stderr_file = task_dir / "stderr"
            stdout_file = task_dir / "stdout"

            # Check for non-empty stderr
            stderr_content = ""
            if stderr_file.exists() and stderr_file.stat().st_size > 0:
                stderr_content = stderr_file.read_text(errors='replace').strip()

            # Check stdout for error indicators
            stdout_content = ""
            if stdout_file.exists():
                stdout_content = stdout_file.read_text(errors='replace').strip()

            # Determine if this task failed
            failed = False
            error_type = "unknown"
            error_message = ""

            # Check for various error patterns
            if stderr_content:
                failed = True
                error_message = stderr_content

                # Categorize error type
                stderr_lower = stderr_content.lower()

                # Look for specific error patterns and extract meaningful messages
                if any(p in stderr_lower for p in ['exhausted your capacity', 'quota', 'rate limit', 'too many requests', 'limit reached', 'usage limit']):
                    error_type = "quota/rate_limit"
                    # Try to extract the specific quota message
                    quota_match = re.search(r'\[API Error:.*?\]', stderr_content)
                    if quota_match:
                        error_message = quota_match.group(0)
                    else:
                        # Find line with quota/limit info
                        for line in stderr_content.split('\n'):
                            if any(p in line.lower() for p in ['quota', 'limit', 'capacity', 'reset']):
                                error_message = line.strip()
                                break
                elif any(p in stderr_lower for p in ['timeout', 'timed out']):
                    error_type = "timeout"
                elif any(p in stderr_lower for p in ['connection', 'network', 'socket']):
                    error_type = "network"
                elif any(p in stderr_lower for p in ['permission', 'access denied']):
                    error_type = "permission"
                elif 'failed' in stderr_lower or 'error' in stderr_lower:
                    error_type = "llm_failure"
                    # Try to extract the actual error, skip YOLO mode lines
                    for line in stderr_content.split('\n'):
                        line_lower = line.lower()
                        if 'yolo mode' in line_lower or 'automatically approved' in line_lower:
                            continue
                        if 'cached credentials' in line_lower:
                            continue
                        if 'error' in line_lower or 'failed' in line_lower:
                            error_message = line.strip()
                            break
                else:
                    # Check if it's just YOLO mode info without real errors
                    if 'yolo mode' in stderr_lower and 'failed' not in stderr_lower and 'error' not in stderr_lower:
                        continue  # Not actually an error
                    error_type = "other"

            # Check stdout for incomplete tasks (started but no success message)
            elif stdout_content:
                if "Creating final feedback" in stdout_content and "✓" not in stdout_content:
                    failed = True
                    error_type = "incomplete"
                    error_message = "Task started but did not complete successfully"
                elif "Marking student" in stdout_content and "✓" not in stdout_content:
                    failed = True
                    error_type = "incomplete"
                    error_message = "Task started but did not complete successfully"

            if failed:
                # Extract student name from task directory name
                student_name = extract_student_name(task_dir.name)

                failures.append({
                    "task_dir": str(task_dir),
                    "student_name": student_name,
                    "error_type": error_type,
                    "error_message": error_message[:500],  # Truncate long messages
                    "stdout_snippet": stdout_content[:200] if stdout_content else "",
                })

    return failures


def extract_student_name(task_dir_name: str) -> str:
    """Extract student name from task directory name."""
    # Task dir names look like: "python3 'path' --student 'Name' --submission ..."
    # Try to extract the student name

    match = re.search(r"--student\s+'([^']+)'", task_dir_name)
    if match:
        return match.group(1)

    match = re.search(r"--student\s+(\S+)", task_dir_name)
    if match:
        return match.group(1)

    # Fallback: return truncated dir name
    return task_dir_name[:50] + "..." if len(task_dir_name) > 50 else task_dir_name


def check_missing_outputs(final_dir: Path, manifest_path: Path) -> List[Dict]:
    """
    Check which students are missing feedback files.

    Args:
        final_dir: Directory where feedback files should be
        manifest_path: Path to submissions_manifest.json

    Returns:
        List of dicts with missing output information
    """
    missing = []

    if not manifest_path.exists():
        return missing

    with open(manifest_path) as f:
        manifest = json.load(f)

    for submission in manifest.get("submissions", []):
        student_name = submission.get("student_name", "")
        feedback_file = final_dir / f"{student_name}_feedback.md"

        if not feedback_file.exists():
            missing.append({
                "student_name": student_name,
                "expected_file": str(feedback_file),
                "submission_path": submission.get("path", ""),
            })

    return missing


def generate_report(
    stage: str,
    failures: List[Dict],
    missing_outputs: List[Dict],
    output_path: Path
) -> str:
    """Generate a human-readable error report."""

    lines = []
    lines.append("=" * 70)
    lines.append(f"ERROR SUMMARY REPORT - {stage.upper()}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    lines.append("")

    # Summary
    total_failures = len(failures) + len(missing_outputs)
    lines.append(f"SUMMARY: {total_failures} issue(s) found")
    lines.append(f"  - Task failures: {len(failures)}")
    lines.append(f"  - Missing outputs: {len(missing_outputs)}")
    lines.append("")

    if not failures and not missing_outputs:
        lines.append("✓ No errors detected!")
        lines.append("")
        return "\n".join(lines)

    # Group failures by error type
    if failures:
        lines.append("-" * 70)
        lines.append("FAILED TASKS BY ERROR TYPE")
        lines.append("-" * 70)
        lines.append("")

        by_type: Dict[str, List[Dict]] = {}
        for f in failures:
            error_type = f["error_type"]
            if error_type not in by_type:
                by_type[error_type] = []
            by_type[error_type].append(f)

        for error_type, type_failures in sorted(by_type.items()):
            lines.append(f"## {error_type.upper()} ({len(type_failures)} failures)")
            lines.append("")

            for f in type_failures:
                lines.append(f"  Student: {f['student_name']}")
                if f['error_message']:
                    # Show first line of error
                    first_line = f['error_message'].split('\n')[0][:100]
                    lines.append(f"  Error: {first_line}")
                lines.append("")

    # List missing outputs
    if missing_outputs:
        lines.append("-" * 70)
        lines.append("MISSING OUTPUT FILES")
        lines.append("-" * 70)
        lines.append("")

        for m in missing_outputs:
            lines.append(f"  Student: {m['student_name']}")
            lines.append(f"  Expected: {m['expected_file']}")
            lines.append("")

    # Recommendations
    lines.append("-" * 70)
    lines.append("RECOMMENDATIONS")
    lines.append("-" * 70)
    lines.append("")

    if any(f["error_type"] == "quota/rate_limit" for f in failures):
        lines.append("• QUOTA/RATE LIMIT errors detected:")
        lines.append("  - Wait for quota reset (check provider docs for reset time)")
        lines.append("  - Re-run the same command to retry only failed tasks")
        lines.append("")

    if any(f["error_type"] == "timeout" for f in failures):
        lines.append("• TIMEOUT errors detected:")
        lines.append("  - Try reducing --parallel to lower concurrency")
        lines.append("  - Check network connection stability")
        lines.append("")

    if any(f["error_type"] == "incomplete" for f in failures):
        lines.append("• INCOMPLETE tasks detected:")
        lines.append("  - LLM may have failed to generate output")
        lines.append("  - Re-run to retry - resume will skip completed tasks")
        lines.append("")

    if any(f["error_type"] == "llm_failure" for f in failures):
        lines.append("• LLM FAILURE errors detected:")
        lines.append("  - The LLM agent failed to complete the task")
        lines.append("  - This may be due to context length, API issues, or prompt problems")
        lines.append("  - Re-run to retry - resume will skip completed tasks")
        lines.append("")

    lines.append("To retry failed tasks:")
    lines.append("  ./mark_structured.sh <assignment_dir>  # Resume is automatic")
    lines.append("")

    # Save report
    report_content = "\n".join(lines)
    output_path.write_text(report_content)

    return report_content


def main():
    parser = argparse.ArgumentParser(
        description="Generate error summary from parallel task logs"
    )
    parser.add_argument(
        "--logs-dir",
        required=True,
        help="Directory containing task logs (e.g., processed/logs/marker_logs)"
    )
    parser.add_argument(
        "--stage",
        required=True,
        help="Stage name (e.g., 'marker', 'unifier')"
    )
    parser.add_argument(
        "--manifest",
        help="Path to submissions_manifest.json (for checking missing outputs)"
    )
    parser.add_argument(
        "--final-dir",
        help="Directory where final outputs should be (for checking missing)"
    )
    parser.add_argument(
        "--output",
        help="Path to save error report (default: logs_dir/error_summary.txt)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also output JSON format"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output if there are errors"
    )

    args = parser.parse_args()

    logs_dir = Path(args.logs_dir)
    if not logs_dir.exists():
        print(f"Logs directory not found: {logs_dir}", file=sys.stderr)
        sys.exit(1)

    # Find failures in logs
    failures = find_failed_tasks(logs_dir)

    # Check for missing outputs if paths provided
    missing_outputs = []
    if args.manifest and args.final_dir:
        manifest_path = Path(args.manifest)
        final_dir = Path(args.final_dir)
        if manifest_path.exists() and final_dir.exists():
            missing_outputs = check_missing_outputs(final_dir, manifest_path)

    # Determine output path
    output_path = Path(args.output) if args.output else logs_dir / "error_summary.txt"

    # Generate report
    report = generate_report(args.stage, failures, missing_outputs, output_path)

    # Output
    if not args.quiet or (failures or missing_outputs):
        print(report)

    # JSON output
    if args.json:
        json_path = output_path.with_suffix(".json")
        json_data = {
            "stage": args.stage,
            "timestamp": datetime.now().isoformat(),
            "failures": failures,
            "missing_outputs": missing_outputs,
            "summary": {
                "total_failures": len(failures),
                "total_missing": len(missing_outputs),
                "by_error_type": {}
            }
        }

        # Count by error type
        for f in failures:
            et = f["error_type"]
            json_data["summary"]["by_error_type"][et] = \
                json_data["summary"]["by_error_type"].get(et, 0) + 1

        json_path.write_text(json.dumps(json_data, indent=2))
        if not args.quiet:
            print(f"\nJSON report saved to: {json_path}")

    # Exit with error if there were failures
    if failures or missing_outputs:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
