#!/usr/bin/env python3
"""
Progress reporting for the agentic notebook marker.

Displays real-time progress with activity/student counters and percentages.
"""

import sys
from typing import Optional


class ProgressReporter:
    """Progress reporting with activity and student tracking."""

    def __init__(
        self,
        total_activities: int,
        total_students: int,
        current_activity: int = 0,
        current_student: int = 0
    ):
        """
        Initialize progress reporter.

        Args:
            total_activities: Total number of activities
            total_students: Total number of students
            current_activity: Current activity index (0-based)
            current_student: Current student index (0-based)
        """
        self.total_activities = total_activities
        self.total_students = total_students
        self.current_activity = current_activity
        self.current_student = current_student

    def update(
        self,
        activity: Optional[int] = None,
        student: Optional[int] = None,
        message: str = ""
    ):
        """
        Update progress display.

        Args:
            activity: Current activity index (1-based) or None to keep current
            student: Current student index (1-based) or None to keep current
            message: Status message to display
        """
        if activity is not None:
            self.current_activity = activity
        if student is not None:
            self.current_student = student

        # Calculate progress
        if self.total_activities > 1:
            # Structured assignment: progress through activities then students
            total_tasks = self.total_activities * self.total_students
            current_task = (self.current_activity - 1) * self.total_students + self.current_student
            progress_pct = (current_task / total_tasks) * 100 if total_tasks > 0 else 0

            activity_str = f"[A{self.current_activity}/{self.total_activities}]"
            student_str = f"[Student {self.current_student}/{self.total_students}]"
        else:
            # Free-form assignment: just students
            progress_pct = (self.current_student / self.total_students) * 100 if self.total_students > 0 else 0
            activity_str = ""
            student_str = f"[Student {self.current_student}/{self.total_students}]"

        # Build progress bar
        bar_width = 30
        filled = int(bar_width * progress_pct / 100)
        bar = '█' * filled + '░' * (bar_width - filled)

        # Print progress line
        progress_line = f"\r{activity_str} {student_str} ({progress_pct:.1f}%) |{bar}| {message}"
        print(progress_line, end='', flush=True)

    def start_activity(self, activity: int, activity_name: str = ""):
        """Signal start of a new activity."""
        self.current_activity = activity
        self.current_student = 0
        name_str = f" - {activity_name}" if activity_name else ""
        print(f"\n\n{'='*60}")
        print(f"Starting Activity {activity}/{self.total_activities}{name_str}")
        print(f"{'='*60}")

    def start_student(self, student_name: str, student_idx: int):
        """Signal start of processing a student."""
        self.current_student = student_idx
        self.update(message=f"Processing {student_name}...")

    def complete_student(self, student_name: str):
        """Signal completion of a student."""
        self.update(message=f"✓ Completed {student_name}")
        print()  # New line

    def complete_activity(self, activity: int):
        """Signal completion of an activity."""
        print(f"\n✓ Activity {activity}/{self.total_activities} completed")

    def error_student(self, student_name: str, error_msg: str):
        """Signal an error with a student."""
        print(f"\n✗ Error with {student_name}: {error_msg}")

    def stage_complete(self, stage_name: str):
        """Signal completion of a major stage."""
        print(f"\n\n{'='*60}")
        print(f"✓ {stage_name} completed")
        print(f"{'='*60}\n")

    def newline(self):
        """Print a newline."""
        print()


class SimpleProgress:
    """Simple progress reporter for single-stage operations."""

    def __init__(self, total: int, prefix: str = "Progress"):
        """
        Initialize simple progress reporter.

        Args:
            total: Total number of items
            prefix: Prefix for progress display
        """
        self.total = total
        self.current = 0
        self.prefix = prefix

    def update(self, current: int, message: str = ""):
        """Update progress."""
        self.current = current
        progress_pct = (current / self.total) * 100 if self.total > 0 else 0

        bar_width = 30
        filled = int(bar_width * progress_pct / 100)
        bar = '█' * filled + '░' * (bar_width - filled)

        progress_line = f"\r{self.prefix}: [{self.current}/{self.total}] ({progress_pct:.1f}%) |{bar}| {message}"
        print(progress_line, end='', flush=True)

    def increment(self, message: str = ""):
        """Increment by one and update."""
        self.update(self.current + 1, message)

    def complete(self):
        """Signal completion."""
        print(f"\n✓ {self.prefix} completed ({self.total} items)")


if __name__ == "__main__":
    # Test progress reporter
    import time

    print("Testing ProgressReporter for structured assignment:")
    reporter = ProgressReporter(total_activities=3, total_students=5)

    for activity in range(1, 4):
        reporter.start_activity(activity, f"Activity {activity}")
        for student in range(1, 6):
            reporter.start_student(f"Student_{student}", student)
            time.sleep(0.2)
            reporter.complete_student(f"Student_{student}")

        reporter.complete_activity(activity)

    reporter.stage_complete("All Marking")

    print("\n\nTesting SimpleProgress:")
    simple = SimpleProgress(10, "Loading files")
    for i in range(1, 11):
        simple.increment(f"File {i}")
        time.sleep(0.1)
    simple.complete()
