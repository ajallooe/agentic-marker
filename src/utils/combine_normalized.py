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
    # Mistake Table
    | ID | Description | Frequency | Severity | Suggested Deduction |
    |... |

    # Positive Table
    | ID | Description | Frequency | Quality | Suggested Bonus |
    |... |

    Returns:
        Dict with 'mistakes' and 'positives' lists
    """
    with open(filepath, 'r') as f:
        content = f.read()

    mistakes = []
    positives = []

    # Parse mistakes table
    mistake_match = re.search(
        r'# Mistake Table.*?\n\|(.*?)\|\n\|[-: |]+\|\n(.*?)(?=\n#|\Z)',
        content,
        re.DOTALL
    )

    if mistake_match:
        headers = [h.strip() for h in mistake_match.group(1).split('|')]
        rows = mistake_match.group(2).strip().split('\n')

        for row in rows:
            if not row.strip() or row.strip().startswith('#'):
                continue

            cells = [c.strip() for c in row.split('|')]
            if len(cells) >= 5:
                mistakes.append({
                    'id': cells[0],
                    'description': cells[1],
                    'frequency': int(cells[2]) if cells[2].isdigit() else 0,
                    'severity': int(cells[3]) if cells[3].isdigit() else 5,
                    'suggested_deduction': float(cells[4]) if cells[4].replace('.', '').isdigit() else 0.0
                })

    # Parse positives table
    positive_match = re.search(
        r'# Positive Table.*?\n\|(.*?)\|\n\|[-: |]+\|\n(.*?)(?=\n#|\Z)',
        content,
        re.DOTALL
    )

    if positive_match:
        headers = [h.strip() for h in positive_match.group(1).split('|')]
        rows = positive_match.group(2).strip().split('\n')

        for row in rows:
            if not row.strip() or row.strip().startswith('#'):
                continue

            cells = [c.strip() for c in row.split('|')]
            if len(cells) >= 5:
                positives.append({
                    'id': cells[0],
                    'description': cells[1],
                    'frequency': int(cells[2]) if cells[2].isdigit() else 0,
                    'quality': int(cells[3]) if cells[3].isdigit() else 5,
                    'suggested_bonus': float(cells[4]) if cells[4].replace('.', '').isdigit() else 0.0
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
