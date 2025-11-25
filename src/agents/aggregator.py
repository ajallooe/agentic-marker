#!/usr/bin/env python3
"""
Aggregator Agent Wrapper

Interactive agent that creates final CSV from all feedback cards.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def load_prompt_template() -> str:
    """Load the aggregator prompt template."""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    prompt_file = prompts_dir / "aggregator.md"

    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_file}")

    with open(prompt_file, 'r') as f:
        return f.read()


def count_feedback_cards(feedback_dir: Path) -> int:
    """Count the number of feedback cards."""
    return len(list(feedback_dir.glob("*_feedback.md")))


def main():
    parser = argparse.ArgumentParser(
        description="Aggregator agent for creating final grades CSV"
    )
    parser.add_argument(
        "--assignment-name",
        required=True,
        help="Name of the assignment"
    )
    parser.add_argument(
        "--feedback-dir",
        required=True,
        help="Directory containing student feedback cards"
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for CSV and reports"
    )
    parser.add_argument(
        "--base-csv",
        help="Optional base CSV file (e.g., Moodle gradebook export)"
    )
    parser.add_argument(
        "--session-log",
        required=True,
        help="Path to save session transcript"
    )
    parser.add_argument(
        "--provider",
        default="claude",
        help="LLM provider"
    )
    parser.add_argument(
        "--model",
        help="LLM model"
    )
    parser.add_argument(
        "--type",
        choices=["structured", "freeform"],
        default="structured",
        help="Assignment type"
    )
    parser.add_argument(
        "--total-marks",
        type=int,
        default=100,
        help="Total marks for the assignment"
    )

    args = parser.parse_args()

    try:
        # Load prompt template
        prompt_template = load_prompt_template()

        # Count feedback cards
        feedback_dir = Path(args.feedback_dir)
        total_students = count_feedback_cards(feedback_dir)

        if total_students == 0:
            print(f"✗ No feedback cards found in {feedback_dir}", file=sys.stderr)
            sys.exit(1)

        # Check for base CSV
        base_csv_info = ""
        if args.base_csv and Path(args.base_csv).exists():
            base_csv_info = f"Base CSV provided: {args.base_csv}\nPlease merge student data with this file."
        else:
            base_csv_info = "No base CSV provided. Create a new CSV from scratch."

        # Substitute variables in prompt
        prompt = prompt_template.format(
            assignment_name=args.assignment_name,
            assignment_type=args.type,
            total_students=total_students,
            total_marks=args.total_marks,
            feedback_cards_directory=str(feedback_dir),
            base_csv_info=base_csv_info,
            output_path=args.output_dir,
            current_date=subprocess.check_output(['date'], text=True).strip()
        )

        # Save prompt for debugging
        prompt_debug_file = Path(args.session_log).with_suffix('.prompt.txt')
        with open(prompt_debug_file, 'w') as f:
            f.write(prompt)

        print("="*70)
        print("AGGREGATOR - INTERACTIVE SESSION")
        print("="*70)
        print(f"Assignment: {args.assignment_name}")
        print(f"Students: {total_students}")
        print(f"Total marks: {args.total_marks}")
        print(f"Feedback cards: {feedback_dir}")
        print(f"Output directory: {args.output_dir}")
        if args.base_csv:
            print(f"Base CSV: {args.base_csv}")
        print()
        print("This agent will:")
        print("1. Read all feedback cards")
        print("2. Extract marks and feedback")
        print("3. Create properly formatted CSV")
        print("4. Generate statistics and reports")
        if args.base_csv:
            print("5. Merge with base CSV")
        print()
        print("Session will be logged to:", args.session_log)
        print("="*70)
        print()

        # Call LLM via unified caller in INTERACTIVE mode
        llm_caller = Path(__file__).parent.parent / "llm_caller.sh"

        cmd = [
            str(llm_caller),
            "--prompt", prompt,
            "--mode", "interactive",
            "--provider", args.provider,
            "--output", args.session_log
        ]

        if args.model:
            cmd.extend(["--model", args.model])

        result = subprocess.run(cmd)

        if result.returncode != 0:
            print(f"\n✗ Aggregation session ended with errors", file=sys.stderr)
            sys.exit(1)

        print("\n" + "="*70)
        print("✓ Aggregation complete")
        print("="*70)
        print()
        print("Please verify the following files were created:")
        print(f"  - {args.output_dir}/grades.csv")
        print(f"  - {args.output_dir}/summary_report.txt (optional)")
        print(f"  - {args.output_dir}/discrepancies.txt (if base CSV provided)")
        print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
