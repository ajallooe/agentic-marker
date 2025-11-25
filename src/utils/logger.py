#!/usr/bin/env python3
"""
Logging and error tracking system for the agentic notebook marker.

Provides:
- Structured logging to console and file
- Error tracking with graceful failure
- Reproducibility via state files
- Student-level error reporting
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib


class MarkerLogger:
    """Enhanced logger with error tracking and state management."""

    def __init__(self, assignment_path: str, log_level: str = "INFO"):
        """
        Initialize the logger.

        Args:
            assignment_path: Path to the assignment directory
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.assignment_path = Path(assignment_path)
        self.processed_dir = self.assignment_path / "processed"
        self.logs_dir = self.processed_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.logs_dir / f"marking_run_{timestamp}.log"
        self.error_file = self.logs_dir / f"errors_{timestamp}.json"
        self.state_file = self.logs_dir / "state.json"

        # Initialize error tracking
        self.errors: List[Dict[str, Any]] = []
        self.failed_students: List[str] = []

        # Configure logging
        self._setup_logging(log_level)

        # Load or initialize state
        self.state = self._load_state()

    def _setup_logging(self, level: str):
        """Configure logging to console and file."""
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler (colorized if possible)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        # File handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(formatter)

        # Configure root logger
        self.logger = logging.getLogger("agentic_marker")
        self.logger.setLevel(getattr(logging, level.upper()))
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def _load_state(self) -> Dict[str, Any]:
        """Load previous state for reproducibility."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load state file: {e}")

        return {
            "started_at": datetime.now().isoformat(),
            "completed_activities": [],
            "completed_students": [],
            "checksums": {},
            "last_stage": None
        }

    def save_state(self):
        """Save current state for reproducibility."""
        self.state["updated_at"] = datetime.now().isoformat()
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save state: {e}")

    def compute_checksum(self, file_path: str) -> str:
        """Compute SHA256 checksum of a file."""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            self.logger.warning(f"Could not compute checksum for {file_path}: {e}")
            return ""

    def record_file_checksum(self, file_path: str, label: str):
        """Record checksum for reproducibility tracking."""
        checksum = self.compute_checksum(file_path)
        if checksum:
            self.state["checksums"][label] = {
                "path": str(file_path),
                "checksum": checksum,
                "recorded_at": datetime.now().isoformat()
            }
            self.save_state()

    def log_error(
        self,
        error_type: str,
        message: str,
        student: Optional[str] = None,
        activity: Optional[str] = None,
        file_path: Optional[str] = None,
        exception: Optional[Exception] = None,
        fatal: bool = False
    ):
        """
        Log an error with structured information.

        Args:
            error_type: Type of error (e.g., 'SCHEMA_VIOLATION', 'AGENT_FAILURE')
            message: Human-readable error message
            student: Student name if applicable
            activity: Activity identifier if applicable
            file_path: File path if applicable
            exception: Exception object if available
            fatal: Whether this error should stop execution
        """
        error_record = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": message,
            "student": student,
            "activity": activity,
            "file_path": file_path,
            "exception": str(exception) if exception else None,
            "fatal": fatal
        }

        self.errors.append(error_record)

        # Track failed students
        if student and student not in self.failed_students:
            self.failed_students.append(student)

        # Log to logger
        log_msg = f"[{error_type}] {message}"
        if student:
            log_msg += f" (Student: {student})"
        if activity:
            log_msg += f" (Activity: {activity})"

        if fatal:
            self.logger.critical(log_msg)
        else:
            self.logger.error(log_msg)

        if exception:
            self.logger.debug(f"Exception details: {exception}", exc_info=True)

        # Save errors to file
        self._save_errors()

        if fatal:
            self.logger.critical("Fatal error encountered. Stopping execution.")
            sys.exit(1)

    def _save_errors(self):
        """Save error log to JSON file."""
        try:
            with open(self.error_file, 'w') as f:
                json.dump({
                    "total_errors": len(self.errors),
                    "failed_students": self.failed_students,
                    "errors": self.errors
                }, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Could not save error file: {e}")

    def mark_stage_complete(self, stage: str):
        """Mark a processing stage as complete."""
        self.state["last_stage"] = stage
        self.state["completed_at"] = datetime.now().isoformat()
        self.logger.info(f"Stage completed: {stage}")
        self.save_state()

    def mark_activity_complete(self, activity: str):
        """Mark an activity as processed."""
        if activity not in self.state["completed_activities"]:
            self.state["completed_activities"].append(activity)
            self.save_state()

    def mark_student_complete(self, student: str, activity: Optional[str] = None):
        """Mark a student as processed for an activity or overall."""
        key = f"{student}:{activity}" if activity else student
        if key not in self.state["completed_students"]:
            self.state["completed_students"].append(key)
            self.save_state()

    def is_activity_complete(self, activity: str) -> bool:
        """Check if an activity has been processed."""
        return activity in self.state["completed_activities"]

    def is_student_complete(self, student: str, activity: Optional[str] = None) -> bool:
        """Check if a student has been processed."""
        key = f"{student}:{activity}" if activity else student
        return key in self.state["completed_students"]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of the marking run."""
        return {
            "total_errors": len(self.errors),
            "failed_students": len(self.failed_students),
            "failed_student_list": self.failed_students,
            "last_stage": self.state.get("last_stage"),
            "completed_activities": len(self.state["completed_activities"]),
            "completed_students": len(self.state["completed_students"])
        }

    def print_summary(self):
        """Print summary to console."""
        summary = self.get_summary()

        print("\n" + "="*60)
        print("MARKING RUN SUMMARY")
        print("="*60)
        print(f"Last stage completed: {summary['last_stage']}")
        print(f"Activities processed: {summary['completed_activities']}")
        print(f"Students processed: {summary['completed_students']}")
        print(f"Total errors: {summary['total_errors']}")
        print(f"Failed students: {summary['failed_students']}")

        if summary['failed_student_list']:
            print("\nFailed students:")
            for student in summary['failed_student_list']:
                print(f"  - {student}")

        print(f"\nLogs saved to: {self.log_file}")
        print(f"Errors saved to: {self.error_file}")
        print(f"State saved to: {self.state_file}")
        print("="*60 + "\n")

    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)

    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)

    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)

    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)


if __name__ == "__main__":
    # Test the logger
    logger = MarkerLogger("/tmp/test_assignment")
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.log_error(
        "TEST_ERROR",
        "This is a test error",
        student="John Doe",
        activity="A1"
    )
    logger.print_summary()
