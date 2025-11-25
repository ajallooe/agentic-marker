#!/usr/bin/env python3
"""
Pattern Designer Agent Wrapper

Interactive agent that creates marking criteria and rubric.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def load_prompt_template(assignment_type: str) -> str:
    """Load the appropriate pattern designer prompt template."""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    prompt_file = prompts_dir / f"pattern_designer_{assignment_type}.md"

    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_file}")

    with open(prompt_file, 'r') as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser(
        description="Pattern Designer agent for creating marking criteria"
    )
    parser.add_argument(
        "--base-notebook",
        help="Path to base notebook (structured assignments)"
    )
    parser.add_argument(
        "--overview",
        required=True,
        help="Path to assignment overview file"
    )
    parser.add_argument(
        "--processed-dir",
        required=True,
        help="Processed directory for output files"
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

    args = parser.parse_args()

    try:
        # Load prompt template
        prompt_template = load_prompt_template(args.type)

        # Load assignment overview
        with open(args.overview, 'r') as f:
            overview_content = f.read()

        # Check for existing rubric
        rubric_file = Path(args.processed_dir) / "rubric.md"
        if rubric_file.exists():
            with open(rubric_file, 'r') as f:
                existing_rubric = f"Existing rubric:\n\n{f.read()}"
            rubric_status = "Rubric exists - please review and validate"
        else:
            existing_rubric = ""
            rubric_status = "No rubric provided - you must create one"

        # Substitute variables in prompt
        prompt = prompt_template.format(
            base_notebook_path=args.base_notebook or "N/A (free-form assignment)",
            assignment_overview=overview_content,
            rubric_status=rubric_status,
            existing_rubric=existing_rubric,
            additional_materials="" if args.type == "structured" else "See overview file above"
        )

        # Save prompt for debugging
        prompt_debug_file = Path(args.session_log).with_suffix('.prompt.txt')
        with open(prompt_debug_file, 'w') as f:
            f.write(prompt)

        print("="*70)
        print("PATTERN DESIGNER - INTERACTIVE SESSION")
        print("="*70)
        print(f"Assignment type: {args.type}")
        print(f"Output directory: {args.processed_dir}")
        print(f"Session will be logged to: {args.session_log}")
        print()
        print("This agent will:")
        print("1. Analyze the assignment")
        print("2. Create or validate the rubric")
        print("3. Create detailed marking criteria")
        print()
        print("Please interact with the agent to complete the design process.")
        print("The agent will tell you when it's complete.")
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

        # Inherit stdin/stdout/stderr to preserve TTY access for interactive CLI
        result = subprocess.run(cmd, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)

        if result.returncode != 0:
            print(f"\n✗ Pattern design session ended with errors", file=sys.stderr)
            sys.exit(1)

        print("\n" + "="*70)
        print("✓ Pattern design session complete")
        print("="*70)
        print()
        print("Please verify the following files were created:")
        print(f"  - {args.processed_dir}/rubric.md")
        if args.type == "structured":
            print(f"  - {args.processed_dir}/activities/A*_criteria.md")
        else:
            print(f"  - {args.processed_dir}/marking_criteria.md")
        print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
