#!/usr/bin/env python3
"""
Combine normalized scoring files into combined JSON for dashboard.

Reads all A*_scoring.md files and creates:
- combined_scoring.json: Aggregated mistakes/positives across all activities with mark allocations
- student_mappings.json: Per-student mistake/positive mappings
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Any


def parse_rubric_marks(rubric_path: Path) -> Dict[str, int]:
    """
    Parse activity mark allocations from rubric.md.

    Expected format in rubric:
    - **A1 – Data Splitting:** 15 marks
    - **A2 – Model Instantiation:** 10 marks

    Returns:
        Dict mapping activity ID to total marks (e.g., {'A1': 15, 'A2': 10})
    """
    activity_marks = {}

    if not rubric_path.exists():
        print(f"Warning: Rubric not found at {rubric_path}, using defaults")
        return {}

    with open(rubric_path, 'r') as f:
        content = f.read()

    # Parse lines like: "- **A1 – Data Splitting:** 15 marks"
    pattern = r'-\s+\*\*([A-Z]\d+)\s+[–-].*?:\*\*\s+(\d+)\s+marks'
    matches = re.findall(pattern, content)

    for activity_id, marks in matches:
        activity_marks[activity_id] = int(marks)

    return activity_marks


def parse_student_mappings(filepath: Path, activity_id: str) -> Dict[str, Dict[str, List[str]]]:
    """
    Parse per-student mistake/positive mappings from scoring file.

    Expected format (structured):
    ### Per-Student Mistake/Positive Mapping
    *   **Student 1 (Anthonia Offor)**: Mistakes: M1; Positives: P4
    *   **Student 2 (Name)**: Mistakes: M2, M3; Positives: P1

    Returns:
        Dict mapping student name to {'mistakes': [...], 'positives': [...]}
    """
    student_mappings = {}

    with open(filepath, 'r') as f:
        content = f.read()

    # Find the mapping section
    mapping_match = re.search(
        r'###?\s+Per-Student.*?Mapping(.*?)(?=\n###?|\n\n\*.*Total Students|\Z)',
        content,
        re.DOTALL | re.IGNORECASE
    )

    if not mapping_match:
        return student_mappings

    mapping_text = mapping_match.group(1)

    # Parse each student line
    # Pattern: *   **Student N (Name)**: Mistakes: M1, M2; Positives: P1, P2
    pattern = r'\*+\s+\*\*Student\s+\d+\s+\(([^)]+)\)\*\*:\s*Mistakes:\s*([^;]+);\s*Positives:\s*(.+)'

    for match in re.finditer(pattern, mapping_text):
        student_name = match.group(1).strip()
        mistakes_str = match.group(2).strip()
        positives_str = match.group(3).strip()

        # Parse mistakes
        mistakes = []
        if mistakes_str.lower() != 'none':
            mistakes = [f"{activity_id}_{m.strip()}" for m in mistakes_str.split(',') if m.strip()]

        # Parse positives
        positives = []
        if positives_str.lower() != 'none':
            positives = [f"{activity_id}_{p.strip()}" for p in positives_str.split(',') if p.strip()]

        student_mappings[student_name] = {
            'mistakes': mistakes,
            'positives': positives
        }

    return student_mappings


def parse_freeform_student_mappings(filepath: Path) -> Dict[str, Dict[str, List[str]]]:
    """
    Parse per-student mappings from freeform scoring.md file.

    Expected format:
    ## Per-Student Mapping

    ### Student 1: Akshit Bhandari
    - **Requirements Coverage**: ~85% (missing conceptual answers)
    - **Mistakes**: M001, M003, M004, M014
    - **Positives**: P001, P002, P003, P004, P005

    Returns:
        Dict mapping student name to {'mistakes': [...], 'positives': [...]}
    """
    student_mappings = {}

    with open(filepath, 'r') as f:
        content = f.read()

    # Find Per-Student Mapping section
    mapping_match = re.search(
        r'##\s+Per-Student Mapping(.*)',
        content,
        re.DOTALL | re.IGNORECASE
    )

    if not mapping_match:
        return student_mappings

    mapping_text = mapping_match.group(1)

    # Parse each student block
    # Pattern: ### Student N: Name
    student_pattern = r'###\s+Student\s+\d+:\s+(.+?)(?=\n###|\Z)'

    for match in re.finditer(student_pattern, mapping_text, re.DOTALL):
        block = match.group(1).strip()
        lines = block.split('\n')

        if not lines:
            continue

        # First line is student name
        student_name = lines[0].strip()

        # Parse mistakes and positives from the block
        mistakes = []
        positives = []

        for line in lines[1:]:
            line = line.strip()
            if line.startswith('- **Mistakes**:'):
                mistakes_str = line.replace('- **Mistakes**:', '').strip()
                if mistakes_str.lower() != 'none' and mistakes_str:
                    # Parse M001, M002, etc.
                    mistakes = [m.strip() for m in mistakes_str.split(',') if m.strip()]
            elif line.startswith('- **Positives**:'):
                positives_str = line.replace('- **Positives**:', '').strip()
                if positives_str.lower() != 'none' and positives_str:
                    # Parse P001, P002, etc.
                    positives = [p.strip() for p in positives_str.split(',') if p.strip()]

        if student_name:
            student_mappings[student_name] = {
                'mistakes': mistakes,
                'positives': positives
            }

    return student_mappings


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


def combine_scoring_files(normalized_dir: Path, rubric_path: Path = None, assignment_type: str = 'structured') -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Combine scoring files into unified data structures.

    For structured: combines all A*_scoring.md files
    For freeform: processes single scoring.md file

    Returns:
        Tuple of (combined_scoring, student_mappings)
    """
    all_mistakes = []
    all_positives = []
    all_student_mappings = {}

    # Parse rubric for activity marks (structured only)
    activity_marks = {}
    if rubric_path and rubric_path.exists() and assignment_type == 'structured':
        activity_marks = parse_rubric_marks(rubric_path)
        print(f"Loaded activity marks: {activity_marks}")

    # Find scoring files based on assignment type
    if assignment_type == 'freeform':
        # Freeform: single scoring.md file
        scoring_file = normalized_dir / 'scoring.md'
        if not scoring_file.exists():
            print(f"Warning: No scoring.md found in {normalized_dir}")
            return {
                'mistakes': [],
                'positives': [],
                'total_marks': 100,
                'activity_marks': {}
            }, {}

        print(f"Processing {scoring_file.name} (freeform)...")

        # Parse tables
        data = parse_scoring_markdown(scoring_file)

        # Add mistakes without activity prefix (freeform has no activities)
        for mistake in data['mistakes']:
            mistake['activity'] = 'ALL'
            mistake['activity_marks'] = 100
            all_mistakes.append(mistake)

        for positive in data['positives']:
            positive['activity'] = 'ALL'
            positive['activity_marks'] = 100
            all_positives.append(positive)

        # Parse freeform student mappings
        all_student_mappings = parse_freeform_student_mappings(scoring_file)

        scoring_files = [scoring_file]

    else:
        # Structured: multiple A*_scoring.md files
        scoring_files = sorted(normalized_dir.glob('A*_scoring.md'))

        if not scoring_files:
            print(f"Warning: No A*_scoring.md files found in {normalized_dir}")
            return {
                'mistakes': [],
                'positives': [],
                'total_marks': 100,
                'activity_marks': activity_marks
            }, {}

        # Process each activity's scoring file
        for scoring_file in scoring_files:
            activity_id = scoring_file.stem.replace('_scoring', '')  # e.g., "A1"
            print(f"Processing {scoring_file.name}...")

            # Parse tables
            data = parse_scoring_markdown(scoring_file)

            # Add activity prefix to IDs and add activity mark allocation
            for mistake in data['mistakes']:
                mistake['id'] = f"{activity_id}_{mistake['id']}"
                mistake['activity'] = activity_id
                mistake['activity_marks'] = activity_marks.get(activity_id, 0)
                all_mistakes.append(mistake)

            for positive in data['positives']:
                positive['id'] = f"{activity_id}_{positive['id']}"
                positive['activity'] = activity_id
                positive['activity_marks'] = activity_marks.get(activity_id, 0)
                all_positives.append(positive)

            # Parse student mappings
            student_mappings = parse_student_mappings(scoring_file, activity_id)

            # Merge into all_student_mappings
            for student_name, mapping in student_mappings.items():
                if student_name not in all_student_mappings:
                    all_student_mappings[student_name] = {
                        'mistakes': [],
                        'positives': []
                    }
                all_student_mappings[student_name]['mistakes'].extend(mapping['mistakes'])
                all_student_mappings[student_name]['positives'].extend(mapping['positives'])

    # Create combined scoring
    combined_scoring = {
        'mistakes': all_mistakes,
        'positives': all_positives,
        'total_marks': sum(activity_marks.values()) if activity_marks else 100,
        'activity_marks': activity_marks
    }

    # Create student mappings with metadata
    student_mappings_output = {
        '_metadata': {
            'total_students': len(all_student_mappings),
            'total_activities': len(scoring_files)
        }
    }
    student_mappings_output.update(all_student_mappings)

    return combined_scoring, student_mappings_output


def main():
    parser = argparse.ArgumentParser(
        description="Combine normalized scoring files into dashboard JSON"
    )
    parser.add_argument(
        '--normalized-dir',
        required=True,
        help="Directory containing scoring files"
    )
    parser.add_argument(
        '--output',
        required=True,
        help="Output path for combined_scoring.json"
    )
    parser.add_argument(
        '--rubric',
        help="Path to rubric.md file (optional)"
    )
    parser.add_argument(
        '--type',
        choices=['structured', 'freeform'],
        default='structured',
        help="Assignment type (default: structured)"
    )

    args = parser.parse_args()

    normalized_dir = Path(args.normalized_dir)
    output_path = Path(args.output)
    rubric_path = Path(args.rubric) if args.rubric else normalized_dir.parent / 'rubric.md'

    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Combine scoring files
    combined_scoring, student_mappings = combine_scoring_files(normalized_dir, rubric_path, args.type)

    # Save combined_scoring.json
    with open(output_path, 'w') as f:
        json.dump(combined_scoring, f, indent=2)

    print(f"✓ Saved combined scoring to {output_path}")
    print(f"  - {len(combined_scoring['mistakes'])} total mistake types")
    print(f"  - {len(combined_scoring['positives'])} total positive types")
    print(f"  - {student_mappings['_metadata']['total_students']} students with mappings")

    # Save student_mappings.json
    mappings_path = output_path.parent / 'student_mappings.json'
    with open(mappings_path, 'w') as f:
        json.dump(student_mappings, f, indent=2)

    print(f"✓ Saved student mappings to {mappings_path}")


if __name__ == "__main__":
    main()
