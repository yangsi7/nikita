"""
Evidence Collector for Full Journey E2E Tests

Captures screenshots, database snapshots, and logs throughout the journey.
Generates comprehensive test reports.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceItem:
    """Single piece of evidence."""
    type: str  # screenshot, db_snapshot, log, api_response
    phase: str
    step: str
    timestamp: datetime
    data: Any
    file_path: Optional[str] = None


@dataclass
class PhaseEvidence:
    """Evidence for a single phase."""
    phase_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    success: bool = False
    items: List[EvidenceItem] = field(default_factory=list)
    error: Optional[str] = None


class EvidenceCollector:
    """
    Collects and organizes evidence throughout E2E test journey.

    For Claude Code execution, evidence is collected via:
    - Screenshots: mcp__playwright__playwright_screenshot
    - DB Snapshots: mcp__supabase__execute_sql
    - Logs: Captured from test output

    Evidence is stored in a structured directory:
    reports/{test_id}/
    ├── screenshots/
    ├── db_snapshots/
    ├── logs/
    └── report.json
    """

    def __init__(
        self,
        test_id: str,
        output_dir: str = "tests/e2e/reports"
    ):
        """Initialize evidence collector.

        Args:
            test_id: Unique identifier for this test run
            output_dir: Base directory for evidence storage
        """
        self.test_id = test_id
        self.output_dir = Path(output_dir) / test_id
        self.phases: Dict[str, PhaseEvidence] = {}
        self.current_phase: Optional[str] = None
        self.start_time = datetime.utcnow()
        self.logs: List[str] = []

    def _ensure_dirs(self):
        """Create output directories if needed."""
        (self.output_dir / "screenshots").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "db_snapshots").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "logs").mkdir(parents=True, exist_ok=True)

    # ==================== Phase Management ====================

    def start_phase(self, phase_name: str):
        """Start a new phase.

        Args:
            phase_name: Name of the phase (e.g., "registration", "conversation")
        """
        self.current_phase = phase_name
        self.phases[phase_name] = PhaseEvidence(
            phase_name=phase_name,
            start_time=datetime.utcnow(),
        )
        self.log(f"Phase started: {phase_name}")

    def end_phase(self, success: bool = True, error: Optional[str] = None):
        """End the current phase.

        Args:
            success: Whether the phase completed successfully
            error: Error message if failed
        """
        if self.current_phase and self.current_phase in self.phases:
            phase = self.phases[self.current_phase]
            phase.end_time = datetime.utcnow()
            phase.success = success
            phase.error = error

            status = "SUCCESS" if success else f"FAILED: {error}"
            self.log(f"Phase ended: {self.current_phase} - {status}")

        self.current_phase = None

    # ==================== Evidence Collection ====================

    def log(self, message: str):
        """Add a log entry.

        Args:
            message: Log message
        """
        timestamp = datetime.utcnow().isoformat()
        entry = f"[{timestamp}] {message}"
        self.logs.append(entry)
        print(entry)  # Also print to console

    def add_screenshot(self, name: str, step: str = ""):
        """Record screenshot evidence (screenshot taken via Playwright MCP).

        Args:
            name: Screenshot name (as passed to playwright_screenshot)
            step: Step description
        """
        if not self.current_phase:
            self.current_phase = "unknown"

        item = EvidenceItem(
            type="screenshot",
            phase=self.current_phase,
            step=step or name,
            timestamp=datetime.utcnow(),
            data={"name": name},
            file_path=f"screenshots/{name}.png",
        )

        if self.current_phase in self.phases:
            self.phases[self.current_phase].items.append(item)

        self.log(f"Screenshot captured: {name}")

    def add_db_snapshot(
        self,
        name: str,
        query: str,
        result: Any,
        step: str = ""
    ):
        """Record database snapshot evidence.

        Args:
            name: Snapshot identifier
            query: SQL query executed
            result: Query result
            step: Step description
        """
        if not self.current_phase:
            self.current_phase = "unknown"

        item = EvidenceItem(
            type="db_snapshot",
            phase=self.current_phase,
            step=step or name,
            timestamp=datetime.utcnow(),
            data={
                "query": query,
                "result": result,
                "row_count": len(result) if isinstance(result, list) else 1,
            },
        )

        if self.current_phase in self.phases:
            self.phases[self.current_phase].items.append(item)

        self.log(f"DB snapshot: {name}")

    def add_api_response(
        self,
        name: str,
        endpoint: str,
        status_code: int,
        response: Any,
        step: str = ""
    ):
        """Record API response evidence.

        Args:
            name: Response identifier
            endpoint: API endpoint
            status_code: HTTP status code
            response: Response data
            step: Step description
        """
        if not self.current_phase:
            self.current_phase = "unknown"

        item = EvidenceItem(
            type="api_response",
            phase=self.current_phase,
            step=step or name,
            timestamp=datetime.utcnow(),
            data={
                "endpoint": endpoint,
                "status_code": status_code,
                "response": response[:500] if isinstance(response, str) else response,
            },
        )

        if self.current_phase in self.phases:
            self.phases[self.current_phase].items.append(item)

        self.log(f"API response: {name} ({status_code})")

    def add_verification(
        self,
        name: str,
        expected: Any,
        actual: Any,
        passed: bool,
        step: str = ""
    ):
        """Record verification result.

        Args:
            name: Verification name
            expected: Expected value
            actual: Actual value
            passed: Whether verification passed
            step: Step description
        """
        if not self.current_phase:
            self.current_phase = "unknown"

        item = EvidenceItem(
            type="verification",
            phase=self.current_phase,
            step=step or name,
            timestamp=datetime.utcnow(),
            data={
                "name": name,
                "expected": expected,
                "actual": actual,
                "passed": passed,
            },
        )

        if self.current_phase in self.phases:
            self.phases[self.current_phase].items.append(item)

        status = "PASS" if passed else "FAIL"
        self.log(f"Verification [{status}]: {name}")

    # ==================== Report Generation ====================

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report.

        Returns:
            Report dictionary
        """
        end_time = datetime.utcnow()

        # Calculate phase summaries
        phase_summaries = {}
        for name, phase in self.phases.items():
            duration = None
            if phase.end_time:
                duration = (phase.end_time - phase.start_time).total_seconds()

            phase_summaries[name] = {
                "success": phase.success,
                "duration_seconds": duration,
                "error": phase.error,
                "evidence_count": len(phase.items),
                "verifications": [
                    {
                        "name": item.data["name"],
                        "passed": item.data["passed"],
                    }
                    for item in phase.items
                    if item.type == "verification"
                ],
            }

        report = {
            "test_id": self.test_id,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - self.start_time).total_seconds(),
            "overall_success": all(p.success for p in self.phases.values()),
            "phases": phase_summaries,
            "total_verifications": sum(
                len([i for i in p.items if i.type == "verification"])
                for p in self.phases.values()
            ),
            "passed_verifications": sum(
                len([i for i in p.items if i.type == "verification" and i.data.get("passed")])
                for p in self.phases.values()
            ),
            "logs": self.logs[-100:],  # Last 100 logs
        }

        return report

    def save_report(self) -> str:
        """Save report to file.

        Returns:
            Path to saved report
        """
        self._ensure_dirs()

        report = self.generate_report()
        report_path = self.output_dir / "report.json"

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        # Also save logs
        log_path = self.output_dir / "logs" / "test.log"
        with open(log_path, "w") as f:
            f.write("\n".join(self.logs))

        self.log(f"Report saved: {report_path}")
        return str(report_path)

    def print_summary(self):
        """Print test summary to console."""
        report = self.generate_report()

        print("\n" + "=" * 60)
        print("E2E TEST SUMMARY")
        print("=" * 60)
        print(f"Test ID: {self.test_id}")
        print(f"Duration: {report['duration_seconds']:.1f} seconds")
        print(f"Overall: {'PASS' if report['overall_success'] else 'FAIL'}")
        print(f"Verifications: {report['passed_verifications']}/{report['total_verifications']}")
        print("-" * 60)

        for name, summary in report["phases"].items():
            status = "✅" if summary["success"] else "❌"
            duration = f"{summary['duration_seconds']:.1f}s" if summary["duration_seconds"] else "N/A"
            print(f"{status} {name}: {duration}")
            if summary["error"]:
                print(f"   Error: {summary['error']}")

        print("=" * 60)
