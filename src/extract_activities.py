#!/usr/bin/env python3
"""
Activity extractor for structured Jupyter notebook assignments.

Extracts student input sections per activity to minimize context for marker agents.
Handles schema violations gracefully.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse


class ActivityExtractionError(Exception):
    """Raised when activity extraction fails."""
    pass


class ActivityExtractor:
    """Extract activities from structured Jupyter notebooks."""

    # Markers for activities and student input
    ACTIVITY_PATTERN = r'\*\*\[A(\d+)\]\*\*'
    START_INPUT_PATTERN = r'\*Start student input\* ↓'
    END_INPUT_PATTERN = r'\*End student input ↑'

    def __init__(self, notebook_path: str, strict: bool = False):
        """
        Initialize extractor.

        Args:
            notebook_path: Path to the Jupyter notebook file
            strict: If True, raise errors on schema violations; if False, fail gracefully
        """
        self.notebook_path = Path(notebook_path)
        self.strict = strict
        self.notebook = None
        self.cells = []
        self.activities = {}
        self.errors = []

    def load_notebook(self) -> bool:
        """
        Load and validate the notebook file.

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.notebook_path, 'r', encoding='utf-8') as f:
                self.notebook = json.load(f)

            # Validate basic structure
            if 'cells' not in self.notebook:
                raise ActivityExtractionError("Notebook missing 'cells' field")

            self.cells = self.notebook['cells']
            return True

        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON: {e}")
            if self.strict:
                raise ActivityExtractionError(f"Invalid JSON: {e}")
            return False

        except Exception as e:
            self.errors.append(f"Could not load notebook: {e}")
            if self.strict:
                raise ActivityExtractionError(f"Could not load notebook: {e}")
            return False

    def extract_activities(self) -> Dict[str, List[Dict]]:
        """
        Extract activities from the notebook.

        Returns:
            Dictionary mapping activity IDs (e.g., 'A1') to lists of student input cells
        """
        if not self.cells:
            return {}

        current_activity = None
        capturing = False
        activities = {}

        for idx, cell in enumerate(self.cells):
            try:
                cell_type = cell.get('cell_type', 'unknown')
                source = self._get_cell_source(cell)

                # Check for activity marker
                activity_match = self._find_activity_marker(source)
                if activity_match:
                    current_activity = f"A{activity_match}"
                    if current_activity not in activities:
                        activities[current_activity] = []
                    capturing = False  # Reset capturing

                # Check for start of student input
                if self._is_start_marker(source):
                    if current_activity is None:
                        self.errors.append(
                            f"Found start marker at cell {idx} but no activity marker yet"
                        )
                        if self.strict:
                            raise ActivityExtractionError(
                                f"Start marker before activity marker at cell {idx}"
                            )
                    else:
                        capturing = True
                    continue

                # Check for end of student input
                if self._is_end_marker(source):
                    capturing = False
                    continue

                # Capture cells within student input sections
                if capturing and current_activity:
                    activities[current_activity].append({
                        'cell_type': cell_type,
                        'source': source,
                        'original_index': idx
                    })

            except Exception as e:
                self.errors.append(f"Error processing cell {idx}: {e}")
                if self.strict:
                    raise ActivityExtractionError(f"Error processing cell {idx}: {e}")

        self.activities = activities
        return activities

    def _get_cell_source(self, cell: Dict) -> str:
        """Extract source text from a cell."""
        source = cell.get('source', '')
        if isinstance(source, list):
            return ''.join(source)
        return str(source)

    def _find_activity_marker(self, text: str) -> Optional[str]:
        """Find activity marker in text and return activity number."""
        match = re.search(self.ACTIVITY_PATTERN, text)
        if match:
            return match.group(1)
        return None

    def _is_start_marker(self, text: str) -> bool:
        """Check if text contains start marker."""
        return bool(re.search(self.START_INPUT_PATTERN, text))

    def _is_end_marker(self, text: str) -> bool:
        """Check if text contains end marker."""
        return bool(re.search(self.END_INPUT_PATTERN, text))

    def validate_structure(self) -> Tuple[bool, List[str]]:
        """
        Validate that the notebook follows expected structure.

        Returns:
            Tuple of (is_valid, list of warnings)
        """
        warnings = []

        # Check if any activities were found
        if not self.activities:
            warnings.append("No activities found in notebook")

        # Check each activity has content
        for activity_id, cells in self.activities.items():
            if not cells:
                warnings.append(f"{activity_id} has no student input cells")

        # Check for balanced start/end markers
        start_count = sum(1 for cell in self.cells if self._is_start_marker(self._get_cell_source(cell)))
        end_count = sum(1 for cell in self.cells if self._is_end_marker(self._get_cell_source(cell)))

        if start_count != end_count:
            warnings.append(
                f"Unbalanced markers: {start_count} start markers, {end_count} end markers"
            )

        is_valid = len(warnings) == 0
        return is_valid, warnings

    def get_activity_summary(self) -> Dict[str, Dict]:
        """Get summary of extracted activities."""
        summary = {}
        for activity_id, cells in self.activities.items():
            code_cells = sum(1 for c in cells if c['cell_type'] == 'code')
            markdown_cells = sum(1 for c in cells if c['cell_type'] == 'markdown')

            summary[activity_id] = {
                'total_cells': len(cells),
                'code_cells': code_cells,
                'markdown_cells': markdown_cells,
                'has_content': len(cells) > 0
            }

        return summary

    def save_activities(self, output_dir: str):
        """
        Save extracted activities to separate JSON files.

        Args:
            output_dir: Directory to save activity files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for activity_id, cells in self.activities.items():
            activity_file = output_path / f"{activity_id}.json"

            activity_data = {
                'activity_id': activity_id,
                'student_notebook': str(self.notebook_path),
                'cells': cells,
                'summary': {
                    'total_cells': len(cells),
                    'code_cells': sum(1 for c in cells if c['cell_type'] == 'code'),
                    'markdown_cells': sum(1 for c in cells if c['cell_type'] == 'markdown')
                }
            }

            with open(activity_file, 'w', encoding='utf-8') as f:
                json.dump(activity_data, f, indent=2, ensure_ascii=False)

    def get_errors(self) -> List[str]:
        """Get list of errors encountered."""
        return self.errors


def extract_from_notebook(
    notebook_path: str,
    output_dir: Optional[str] = None,
    strict: bool = False
) -> Tuple[bool, Dict[str, List[Dict]], List[str]]:
    """
    Extract activities from a notebook.

    Args:
        notebook_path: Path to notebook file
        output_dir: Optional directory to save extracted activities
        strict: If True, raise errors on schema violations

    Returns:
        Tuple of (success, activities_dict, errors_list)
    """
    extractor = ActivityExtractor(notebook_path, strict=strict)

    # Load notebook
    if not extractor.load_notebook():
        return False, {}, extractor.get_errors()

    # Extract activities
    try:
        activities = extractor.extract_activities()
    except ActivityExtractionError as e:
        return False, {}, [str(e)]

    # Validate structure
    is_valid, warnings = extractor.validate_structure()
    errors = extractor.get_errors() + warnings

    # Save if output directory specified
    if output_dir and activities:
        try:
            extractor.save_activities(output_dir)
        except Exception as e:
            errors.append(f"Could not save activities: {e}")

    success = is_valid and len(extractor.get_errors()) == 0
    return success, activities, errors


def main():
    """CLI interface for activity extractor."""
    parser = argparse.ArgumentParser(
        description="Extract activities from structured Jupyter notebooks"
    )
    parser.add_argument(
        "notebook",
        help="Path to Jupyter notebook file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output directory for extracted activities"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any schema violation"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print summary of extracted activities"
    )

    args = parser.parse_args()

    # Extract activities
    success, activities, errors = extract_from_notebook(
        args.notebook,
        output_dir=args.output,
        strict=args.strict
    )

    # Print results
    if errors:
        print("Errors/Warnings:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)

    if args.summary or not success:
        extractor = ActivityExtractor(args.notebook)
        extractor.load_notebook()
        extractor.extract_activities()
        summary = extractor.get_activity_summary()

        print("\nActivity Summary:")
        for activity_id, info in summary.items():
            print(f"  {activity_id}: {info['total_cells']} cells "
                  f"({info['code_cells']} code, {info['markdown_cells']} markdown)")

    if success:
        print(f"\n✓ Successfully extracted {len(activities)} activities")
        sys.exit(0)
    else:
        print(f"\n✗ Extraction failed with {len(errors)} errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
