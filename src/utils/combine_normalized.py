#!/usr/bin/env python3
"""
Combine normalized scoring files into combined JSON for dashboard.

Reads all A*_scoring.md files and creates:
- combined_scoring.json: Aggregated mistakes/positives across all activities
- student_mappings.json: Per-student mistake/positive mappings
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Any


def parse_scoring_markdown(filepath: Path) -> Dict[str, Any]:
    """
    Parse a normalized scoring markdown file.

    Expected format:
    ### Mistakes Table (or # Mistake Table)
    | Mistake ID | Description | Frequency | Severity (1-10) | Suggested Deduction | Notes |
    |------------|-------------|-----------|-----------------|---------------------|-------|
    | M1 | ... | ... | ... | ... | ... |

    ### Positive Points Table (or # Positive Table)
    | Positive ID | Description | Frequency | Quality (1-10) | Suggested Bonus | Notes |
    |-------------|-------------|-----------|----------------|-----------------|-------|
    | P1 | ... | ... | ... | ... | ... |

    Returns:
        Dict with 'mistakes' and 'positives' lists
    """
    with open(filepath, 'r') as f:
        content = f.read()

    mistakes = []
    positives = []

    # Parse mistakes table - more flexible pattern
    mistake_match = re.search(
        r'###?\s+Mistake.*?Table.*?\n\|.*?\|\n\|[-: |]+\|\n(.*?)(?=\n###?|\Z)',
        content,
        re.DOTALL | re.IGNORECASE
    )

    if mistake_match:
        rows = mistake_match.group(1).strip().split('\n')

        for row in rows:
            if not row.strip() or row.strip().startswith('#'):
                continue

            # Split by pipe and filter empty strings
            cells = [c.strip() for c in row.split('|')]
            cells = [c for c in cells if c]  # Remove empty cells from leading/trailing pipes

            if len(cells) >= 5:
                # Extract numeric values more robustly
                frequency_str = cells[2].split('/')[0].strip()  # "18/24 students" -> "18"
                severity_str = re.search(r'\d+', cells[3])  # Extract first number from "10 (Critical)"
                deduction_str = re.search(r'\d+\.?\d*', cells[4])  # Extract number from "**13 marks**" or "**0.5 marks**"

                mistakes.append({
                    'id': cells[0],
                    'description': cells[1],
                    'frequency': int(frequency_str) if frequency_str.isdigit() else 0,
                    'severity': int(severity_str.group()) if severity_str else 5,
                    'suggested_deduction': float(deduction_str.group()) if deduction_str else 0.0
                })

    # Parse positives table - more flexible pattern
    positive_match = re.search(
        r'###?\s+Positive.*?Table.*?\n\|.*?\|\n\|[-: |]+\|\n(.*?)(?=\n###?|\Z)',
        content,
        re.DOTALL | re.IGNORECASE
    )

    if positive_match:
        rows = positive_match.group(1).strip().split('\n')

        for row in rows:
            if not row.strip() or row.strip().startswith('#') or row.strip().startswith('*'):
                continue

            # Split by pipe and filter empty strings
            cells = [c.strip() for c in row.split('|')]
            cells = [c for c in cells if c]  # Remove empty cells from leading/trailing pipes

            if len(cells) >= 5:
                # Extract numeric values more robustly
                frequency_str = cells[2].split('/')[0].strip()  # "2/24 students" -> "2"
                quality_str = re.search(r'\d+', cells[3])  # Extract first number from "10 (Excellent)"
                bonus_str = re.search(r'\d+\.?\d*', cells[4])  # Extract number from "**+1 mark**" or "0 marks"

                positives.append({
                    'id': cells[0],
                    'description': cells[1],
                    'frequency': int(frequency_str) if frequency_str.isdigit() else 0,
                    'quality': int(quality_str.group()) if quality_str else 5,
                    'suggested_bonus': float(bonus_str.group()) if bonus_str else 0.0
                })

    return {
        'mistakes': mistakes,
        'positives': positives
    }


def combine_scoring_files(normalized_dir: Path) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Combine all A*_scoring.md files into unified data structures.

    Returns:
        Tuple of (combined_scoring, student_mappings)
    """
    all_mistakes = []
    all_positives = []
    student_mappings = {}

    # Find all A*_scoring.md files
    scoring_files = sorted(normalized_dir.glob('A*_scoring.md'))

    if not scoring_files:
        print(f"Warning: No A*_scoring.md files found in {normalized_dir}")
        return {
            'mistakes': [],
            'positives': [],
            'total_marks': 100
        }, {}

    # Process each activity's scoring file
    for scoring_file in scoring_files:
        activity_id = scoring_file.stem.replace('_scoring', '')  # e.g., "A1"
        print(f"Processing {scoring_file.name}...")

        data = parse_scoring_markdown(scoring_file)

        # Add activity prefix to IDs to avoid conflicts
        for mistake in data['mistakes']:
            mistake['id'] = f"{activity_id}_{mistake['id']}"
            mistake['activity'] = activity_id
            all_mistakes.append(mistake)

        for positive in data['positives']:
            positive['id'] = f"{activity_id}_{positive['id']}"
            positive['activity'] = activity_id
            all_positives.append(positive)

    # Create combined scoring
    combined_scoring = {
        'mistakes': all_mistakes,
        'positives': all_positives,
        'total_marks': 100  # TODO: Get from rubric
    }

    # Create student mappings (placeholder for now - would come from actual student data)
    # This would normally map each student to their specific mistakes/positives
    # For now, we create a simple structure
    student_mappings = {
        '_metadata': {
            'total_students': 0,
            'total_activities': len(scoring_files)
        }
    }

    return combined_scoring, student_mappings


def main():
    parser = argparse.ArgumentParser(
        description="Combine normalized scoring files into dashboard JSON"
    )
    parser.add_argument(
        '--normalized-dir',
        required=True,
        help="Directory containing A*_scoring.md files"
    )
    parser.add_argument(
        '--output',
        required=True,
        help="Output path for combined_scoring.json"
    )

    args = parser.parse_args()

    normalized_dir = Path(args.normalized_dir)
    output_path = Path(args.output)

    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Combine scoring files
    combined_scoring, student_mappings = combine_scoring_files(normalized_dir)

    # Save combined_scoring.json
    with open(output_path, 'w') as f:
        json.dump(combined_scoring, f, indent=2)

    print(f"✓ Saved combined scoring to {output_path}")
    print(f"  - {len(combined_scoring['mistakes'])} total mistake types")
    print(f"  - {len(combined_scoring['positives'])} total positive types")

    # Save student_mappings.json
    mappings_path = output_path.parent / 'student_mappings.json'
    with open(mappings_path, 'w') as f:
        json.dump(student_mappings, f, indent=2)

    print(f"✓ Saved student mappings to {mappings_path}")


if __name__ == "__main__":
    main()
