#!/usr/bin/env python3
"""
Create interactive adjustment dashboard for marking scheme approval.

Generates a Jupyter notebook with ipywidgets for instructor to adjust
mark deductions and see live distribution updates.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List


def create_dashboard_notebook(
    normalized_data_path: str,
    student_mappings_path: str,
    output_path: str,
    assignment_type: str = "structured"
) -> str:
    """
    Create an interactive Jupyter notebook dashboard.

    Args:
        normalized_data_path: Path to normalized scoring JSON
        student_mappings_path: Path to per-student mistake/positive mappings JSON
        output_path: Where to save the notebook
        assignment_type: "structured" or "freeform"

    Returns:
        Path to created notebook
    """
    # Load data
    with open(normalized_data_path, 'r') as f:
        normalized_data = json.load(f)

    with open(student_mappings_path, 'r') as f:
        student_mappings = json.load(f)

    # Create notebook structure
    notebook = {
        "cells": [],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.8.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }

    # Title cell
    notebook["cells"].append(_markdown_cell(f"""
# Marking Scheme Adjustment Dashboard

This interactive dashboard allows you to:
1. Review normalized mistake and positive point assessments
2. Adjust mark deductions and bonuses
3. See live mark distribution updates
4. Approve final marking scheme

**Assignment Type**: {assignment_type.title()}
    """.strip()))

    # Setup cell
    notebook["cells"].append(_code_cell("""
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from ipywidgets import interact, interactive, fixed, interact_manual, widgets
from IPython.display import display, clear_output
import ipywidgets as widgets
from pathlib import Path

# Set up plotting
%matplotlib inline
plt.style.use('seaborn-v0_8-darkgrid')

# Load data
with open('{normalized_data_path}', 'r') as f:
    normalized_data = json.load(f)

with open('{student_mappings_path}', 'r') as f:
    student_mappings = json.load(f)

# Extract mistakes and positives
mistakes = normalized_data.get('mistakes', [])
positives = normalized_data.get('positives', [])
total_marks = normalized_data.get('total_marks', 100)

print(f"Loaded {{len(mistakes)}} mistake types and {{len(positives)}} positive types")
print(f"Total marks available: {{total_marks}}")
    """.format(
        normalized_data_path=normalized_data_path,
        student_mappings_path=student_mappings_path
    )))

    # Mistakes table cell
    notebook["cells"].append(_markdown_cell("## Mistake Deductions\n\nAdjust the mark deductions for each mistake type:"))

    notebook["cells"].append(_code_cell("""
# Create DataFrame for mistakes
mistakes_df = pd.DataFrame(mistakes)
print(f"Total mistake types: {len(mistakes_df)}")
display(mistakes_df[['id', 'description', 'frequency', 'severity', 'suggested_deduction']])
    """))

    # Positives table cell
    notebook["cells"].append(_markdown_cell("## Positive Bonuses\n\nAdjust bonus points for positive achievements:"))

    notebook["cells"].append(_code_cell("""
# Create DataFrame for positives
positives_df = pd.DataFrame(positives)
print(f"Total positive types: {len(positives_df)}")
display(positives_df[['id', 'description', 'frequency', 'quality', 'suggested_bonus']])
    """))

    # Interactive adjustment cell
    notebook["cells"].append(_markdown_cell("""
## Interactive Mark Adjustment

Use the sliders below to adjust deductions and bonuses. The distribution will update automatically.
    """))

    notebook["cells"].append(_code_cell("""
# Create adjustment widgets
mistake_widgets = {}
for _, mistake in mistakes_df.iterrows():
    mistake_id = mistake['id']
    suggested = float(mistake['suggested_deduction'])
    mistake_widgets[mistake_id] = widgets.FloatSlider(
        value=suggested,
        min=0,
        max=min(suggested * 2, total_marks),
        step=0.5,
        description=f"{mistake_id}:",
        style={'description_width': '100px'},
        layout=widgets.Layout(width='500px')
    )

positive_widgets = {}
for _, positive in positives_df.iterrows():
    positive_id = positive['id']
    suggested = float(positive['suggested_bonus'])
    positive_widgets[positive_id] = widgets.FloatSlider(
        value=suggested,
        min=0,
        max=min(suggested * 2, 10),
        step=0.5,
        description=f"{positive_id}:",
        style={'description_width': '100px'},
        layout=widgets.Layout(width='500px')
    )

print("Adjustment widgets created")
    """))

    # Calculation function
    notebook["cells"].append(_code_cell("""
def calculate_marks(**kwargs):
    \"\"\"Calculate marks for all students based on current adjustments.\"\"\"
    marks = {}

    for student_name, mapping in student_mappings.items():
        student_mark = total_marks

        # Apply mistake deductions
        for mistake_id in mapping.get('mistakes', []):
            if mistake_id in kwargs:
                student_mark -= kwargs[mistake_id]

        # Apply positive bonuses
        for positive_id in mapping.get('positives', []):
            if positive_id in kwargs:
                student_mark += kwargs[positive_id]

        # Clamp to valid range
        student_mark = max(0, min(total_marks, student_mark))
        marks[student_name] = student_mark

    return marks

def plot_distribution(marks_dict):
    \"\"\"Plot histogram of mark distribution.\"\"\"
    marks = list(marks_dict.values())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Histogram
    ax1.hist(marks, bins=20, edgecolor='black', alpha=0.7)
    ax1.set_xlabel('Marks')
    ax1.set_ylabel('Number of Students')
    ax1.set_title('Mark Distribution')
    ax1.axvline(np.mean(marks), color='red', linestyle='--', label=f'Mean: {np.mean(marks):.1f}')
    ax1.axvline(np.median(marks), color='green', linestyle='--', label=f'Median: {np.median(marks):.1f}')
    ax1.legend()

    # Grade bands
    grade_bands = {
        'A (90-100%)': len([m for m in marks if m >= total_marks * 0.9]),
        'B (80-89%)': len([m for m in marks if total_marks * 0.8 <= m < total_marks * 0.9]),
        'C (70-79%)': len([m for m in marks if total_marks * 0.7 <= m < total_marks * 0.8]),
        'D (60-69%)': len([m for m in marks if total_marks * 0.6 <= m < total_marks * 0.7]),
        'F (<60%)': len([m for m in marks if m < total_marks * 0.6]),
    }

    ax2.bar(grade_bands.keys(), grade_bands.values(), edgecolor='black', alpha=0.7)
    ax2.set_xlabel('Grade Band')
    ax2.set_ylabel('Number of Students')
    ax2.set_title('Grade Distribution')
    ax2.tick_params(axis='x', rotation=45)

    plt.tight_layout()
    plt.show()

    # Statistics
    print("\\nStatistics:")
    print(f"  Mean: {np.mean(marks):.2f} / {total_marks}")
    print(f"  Median: {np.median(marks):.2f} / {total_marks}")
    print(f"  Std Dev: {np.std(marks):.2f}")
    print(f"  Min: {np.min(marks):.2f} / {total_marks}")
    print(f"  Max: {np.max(marks):.2f} / {total_marks}")
    print(f"\\nGrade Distribution:")
    for band, count in grade_bands.items():
        print(f"  {band}: {count} students ({count/len(marks)*100:.1f}%)")

def update_display(**kwargs):
    \"\"\"Update marks and distribution based on current widget values.\"\"\"
    clear_output(wait=True)
    marks = calculate_marks(**kwargs)
    plot_distribution(marks)
    return marks

print("Calculation functions defined")
    """))

    # Display widgets
    notebook["cells"].append(_markdown_cell("### Mistake Deductions"))

    notebook["cells"].append(_code_cell("""
for mistake_id, widget in mistake_widgets.items():
    display(widget)
    """))

    notebook["cells"].append(_markdown_cell("### Positive Bonuses"))

    notebook["cells"].append(_code_cell("""
for positive_id, widget in positive_widgets.items():
    display(widget)
    """))

    # Interactive display
    notebook["cells"].append(_markdown_cell("""
## Mark Distribution

The chart below updates as you adjust sliders above. Click "Update Distribution" to refresh.
    """))

    notebook["cells"].append(_code_cell("""
# Create update button
update_button = widgets.Button(description="Update Distribution")
output = widgets.Output()

def on_update_click(b):
    with output:
        kwargs = {k: w.value for k, w in {**mistake_widgets, **positive_widgets}.items()}
        current_marks = update_display(**kwargs)

update_button.on_click(on_update_click)
display(update_button)
display(output)

# Initial display
with output:
    kwargs = {k: w.value for k, w in {**mistake_widgets, **positive_widgets}.items()}
    current_marks = update_display(**kwargs)
    """))

    # Save scheme cell
    notebook["cells"].append(_markdown_cell("""
## Save Approved Scheme

Once you're satisfied with the mark distribution, run the cell below to save the approved scheme.
    """))

    notebook["cells"].append(_code_cell("""
def save_approved_scheme(output_path='approved_scheme.json'):
    \"\"\"Save the approved marking scheme.\"\"\"
    scheme = {
        'total_marks': total_marks,
        'mistakes': {},
        'positives': {},
        'timestamp': pd.Timestamp.now().isoformat()
    }

    for mistake_id, widget in mistake_widgets.items():
        scheme['mistakes'][mistake_id] = float(widget.value)

    for positive_id, widget in positive_widgets.items():
        scheme['positives'][positive_id] = float(widget.value)

    with open(output_path, 'w') as f:
        json.dump(scheme, f, indent=2)

    print(f"✓ Approved scheme saved to: {output_path}")
    print(f"\\nYou may now close this notebook and continue the marking process.")

    return scheme

# Run this cell to save
approved_scheme = save_approved_scheme('approved_scheme.json')
    """))

    # Write notebook to file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(notebook, f, indent=2)

    return str(output_file)


def _markdown_cell(text: str) -> Dict:
    """Create a markdown cell."""
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": text.split('\n')
    }


def _code_cell(code: str) -> Dict:
    """Create a code cell."""
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": code.split('\n')
    }


def main():
    """CLI interface."""
    parser = argparse.ArgumentParser(
        description="Create interactive marking adjustment dashboard"
    )
    parser.add_argument(
        "normalized_data",
        help="Path to normalized scoring JSON"
    )
    parser.add_argument(
        "student_mappings",
        help="Path to student mistake/positive mappings JSON"
    )
    parser.add_argument(
        "-o", "--output",
        default="adjustment_dashboard.ipynb",
        help="Output notebook path"
    )
    parser.add_argument(
        "-t", "--type",
        choices=["structured", "freeform"],
        default="structured",
        help="Assignment type"
    )

    args = parser.parse_args()

    notebook_path = create_dashboard_notebook(
        args.normalized_data,
        args.student_mappings,
        args.output,
        args.type
    )

    print(f"✓ Dashboard created: {notebook_path}")
    print(f"\nTo use:")
    print(f"  jupyter notebook \"{notebook_path}\"")


if __name__ == "__main__":
    main()
