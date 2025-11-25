#!/usr/bin/env python3
"""
Grade Aggregator - Deterministic CSV Generation

Reads all feedback cards and generates grades.csv with proper formatting.
This is a simple, deterministic script - no LLM needed.
"""

import argparse
import csv
import re
import statistics
from pathlib import Path
from datetime import datetime


def parse_feedback_card(content: str, filename: str) -> dict:
    """Extract student name, marks, and feedback from a feedback card."""

    # Extract student name from header
    name_match = re.search(r'ASSIGNMENT FEEDBACK - (.+?)$', content, re.MULTILINE)
    if not name_match:
        # Fallback: use filename without _feedback.md
        student_name = filename.replace('_feedback.md', '')
    else:
        student_name = name_match.group(1).strip()

    # Extract total mark
    total_match = re.search(r'Total Mark: ([\d.]+)', content)
    total_mark = float(total_match.group(1)) if total_match else 0.0

    # Extract activity marks
    activities = {}
    activity_matches = re.findall(r'Activity (\d+): ([\d.]+) / [\d.]+', content)
    for activity_num, mark in activity_matches:
        activities[f'Activity {activity_num}'] = float(mark)

    return {
        'name': student_name,
        'total_mark': total_mark,
        'activities': activities,
        'feedback': content
    }


def generate_csv(feedback_dir: Path, output_path: Path, total_marks: int, assignment_type: str):
    """Generate grades.csv from all feedback cards."""

    # Find all feedback files
    feedback_files = sorted(feedback_dir.glob('*_feedback.md'))

    if not feedback_files:
        print(f"Error: No feedback files found in {feedback_dir}")
        return False

    print(f"Found {len(feedback_files)} feedback cards")

    # Parse all feedback cards
    students = []
    all_activities = set()

    for feedback_file in feedback_files:
        with open(feedback_file, 'r', encoding='utf-8') as f:
            content = f.read()

        student_data = parse_feedback_card(content, feedback_file.name)
        students.append(student_data)
        all_activities.update(student_data['activities'].keys())

    # Sort activities numerically
    sorted_activities = sorted(all_activities, key=lambda x: int(re.search(r'\d+', x).group()))

    # Determine CSV headers based on assignment type
    if assignment_type == 'structured' and sorted_activities:
        headers = ['Student Name', 'Total Mark'] + sorted_activities + ['Feedback Card']
    else:
        headers = ['Student Name', 'Total Mark', 'Feedback Card']

    # Write CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
        writer.writerow(headers)

        for student in sorted(students, key=lambda s: s['name']):
            row = [student['name'], student['total_mark']]

            # Add activity marks if structured
            if assignment_type == 'structured' and sorted_activities:
                for activity in sorted_activities:
                    row.append(student['activities'].get(activity, 0.0))

            # Add feedback card
            row.append(student['feedback'])

            writer.writerow(row)

    # Generate statistics
    marks = [s['total_mark'] for s in students]
    stats = {
        'count': len(marks),
        'mean': statistics.mean(marks) if marks else 0,
        'median': statistics.median(marks) if marks else 0,
        'std': statistics.stdev(marks) if len(marks) > 1 else 0,
        'max': max(marks) if marks else 0,
        'min': min(marks) if marks else 0
    }

    # Distribution
    distribution = {
        '90-100%': sum(1 for m in marks if 90 <= m <= 100),
        '80-89%': sum(1 for m in marks if 80 <= m < 90),
        '70-79%': sum(1 for m in marks if 70 <= m < 80),
        '60-69%': sum(1 for m in marks if 60 <= m < 70),
        '50-59%': sum(1 for m in marks if 50 <= m < 60),
        '0-49%': sum(1 for m in marks if 0 <= m < 50),
    }

    # Print summary
    print(f"\n{'='*70}")
    print("CSV AGGREGATION REPORT")
    print('='*70)
    print(f"\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nSTATISTICS:")
    print(f"Total Students: {stats['count']}")
    print(f"Mean Mark: {stats['mean']:.2f} / {total_marks}")
    print(f"Median Mark: {stats['median']:.2f} / {total_marks}")
    print(f"Std Deviation: {stats['std']:.2f}")
    print(f"Highest Mark: {stats['max']:.2f} / {total_marks}")
    print(f"Lowest Mark: {stats['min']:.2f} / {total_marks}")
    print(f"\nDISTRIBUTION:")
    for range_name, count in distribution.items():
        print(f"{range_name}: {count} students")
    print(f"\n{'='*70}")
    print(f"✓ CSV saved to: {output_path}")
    print(f"{'='*70}\n")

    # Save summary report
    summary_path = output_path.parent / 'summary_report.txt'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"CSV AGGREGATION REPORT\n")
        f.write(f"{'='*70}\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"STATISTICS:\n")
        f.write(f"Total Students: {stats['count']}\n")
        f.write(f"Mean Mark: {stats['mean']:.2f} / {total_marks}\n")
        f.write(f"Median Mark: {stats['median']:.2f} / {total_marks}\n")
        f.write(f"Std Deviation: {stats['std']:.2f}\n")
        f.write(f"Highest Mark: {stats['max']:.2f} / {total_marks}\n")
        f.write(f"Lowest Mark: {stats['min']:.2f} / {total_marks}\n\n")
        f.write(f"DISTRIBUTION:\n")
        for range_name, count in distribution.items():
            f.write(f"{range_name}: {count} students\n")

    print(f"✓ Summary saved to: {summary_path}\n")

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Aggregate student feedback cards into grades.csv'
    )
    parser.add_argument('--feedback-dir', required=True, help='Directory containing feedback cards')
    parser.add_argument('--output', required=True, help='Output CSV path')
    parser.add_argument('--total-marks', type=int, required=True, help='Total marks for assignment')
    parser.add_argument('--type', choices=['structured', 'freeform'], required=True, help='Assignment type')

    args = parser.parse_args()

    feedback_dir = Path(args.feedback_dir)
    output_path = Path(args.output)

    if not feedback_dir.exists():
        print(f"Error: Feedback directory does not exist: {feedback_dir}")
        return 1

    success = generate_csv(feedback_dir, output_path, args.total_marks, args.type)
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
