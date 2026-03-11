"""Static analysis tools for code review agent."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import json
import subprocess
import os


class FindingSeverity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class FindingCategory(str, Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    BEST_PRACTICES = "best-practices"
    BUGS = "bugs"


@dataclass
class Finding:
    """Represents a static analysis finding."""
    severity: FindingSeverity
    category: FindingCategory
    tool: str
    message: str
    file_path: str
    line_number: Optional[int] = None
    code_context: Optional[str] = None
    confidence: str = "high"

    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "tool": self.tool,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_context": self.code_context,
            "confidence": self.confidence
        }


class StaticAnalysisTool:
    """Base class for static analysis tools."""

    def __init__(self, name: str):
        self.name = name

    def run(self, target_path: str) -> list[Finding]:
        """Run the tool on the target path and return findings."""
        raise NotImplementedError

    def _check_tool_available(self, command: str) -> bool:
        """Check if a tool is available on the system."""
        result = subprocess.run(
            ["which", command],
            capture_output=True,
            text=True
        )
        return result.returncode == 0


class BanditTool(StaticAnalysisTool):
    """Bandit security analysis tool."""

    def __init__(self):
        super().__init__("bandit")

    def run(self, target_path: str) -> list[Finding]:
        findings = []
        if not self._check_tool_available("bandit"):
            return findings

        try:
            result = subprocess.run(
                ["bandit", "-r", target_path, "-f", "json", "-ll"],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode in [0, 1]:
                try:
                    data = json.loads(result.stdout)
                    for issue in data.get("results", []):
                        findings.append(Finding(
                            severity=self._map_severity(issue.get("issue_severity", "LOW")),
                            category=FindingCategory.SECURITY,
                            tool="bandit",
                            message=f"{issue.get('issue_text', '')} ({issue.get('issue_cwe', '')})",
                            file_path=issue.get("filename", ""),
                            line_number=issue.get("line_number"),
                            confidence=issue.get("issue_confidence", "high")
                        ))
                except json.JSONDecodeError:
                    pass
        except (subprocess.TimeoutExpired, Exception):
            pass

        return findings

    def _map_severity(self, severity: str) -> FindingSeverity:
        mapping = {
            "HIGH": FindingSeverity.HIGH,
            "MEDIUM": FindingSeverity.MEDIUM,
            "LOW": FindingSeverity.LOW
        }
        return mapping.get(severity.upper(), FindingSeverity.LOW)


class RuffTool(StaticAnalysisTool):
    """Ruff linter tool."""

    def __init__(self):
        super().__init__("ruff")

    def run(self, target_path: str) -> list[Finding]:
        findings = []
        if not self._check_tool_available("ruff"):
            return findings

        try:
            result = subprocess.run(
                ["ruff", "check", target_path, "--output-format", "json"],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode in [0, 1]:
                try:
                    data = json.loads(result.stdout)
                    for issue in data if isinstance(data, list) else []:
                        findings.append(Finding(
                            severity=self._map_severity(issue.get("severity", "E")),
                            category=self._map_category(issue.get("code", "")),
                            tool="ruff",
                            message=issue.get("message", ""),
                            file_path=issue.get("filename", ""),
                            line_number=issue.get("location", {}).get("row"),
                            confidence="high"
                        ))
                except json.JSONDecodeError:
                    pass
        except (subprocess.TimeoutExpired, Exception):
            pass

        return findings

    def _map_severity(self, severity: str) -> FindingSeverity:
        severity = str(severity).upper()
        if severity in ["E", "ERROR"]:
            return FindingSeverity.MEDIUM
        elif severity in ["W", "WARNING"]:
            return FindingSeverity.LOW
        return FindingSeverity.LOW

    def _map_category(self, code: str) -> FindingCategory:
        if code.startswith("F"):
            return FindingCategory.BEST_PRACTICES
        elif code.startswith("E"):
            return FindingCategory.BEST_PRACTICES
        elif code.startswith("W"):
            return FindingCategory.BEST_PRACTICES
        return FindingCategory.BEST_PRACTICES


class Flake8Tool(StaticAnalysisTool):
    """Flake8 linting tool."""

    def __init__(self):
        super().__init__("flake8")

    def run(self, target_path: str) -> list[Finding]:
        findings = []
        if not self._check_tool_available("flake8"):
            return findings

        try:
            result = subprocess.run(
                ["flake8", target_path, "--format", "json"],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode in [0, 1]:
                try:
                    data = json.loads(result.stdout)
                    for issue in data if isinstance(data, list) else []:
                        findings.append(Finding(
                            severity=FindingSeverity.LOW,
                            category=FindingCategory.BEST_PRACTICES,
                            tool="flake8",
                            message=issue.get("message", ""),
                            file_path=issue.get("filename", ""),
                            line_number=issue.get("line_number"),
                            confidence="high"
                        ))
                except json.JSONDecodeError:
                    pass
        except (subprocess.TimeoutExpired, Exception):
            pass

        return findings


class MyPyTool(StaticAnalysisTool):
    """MyPy type checking tool."""

    def __init__(self):
        super().__init__("mypy")

    def run(self, target_path: str) -> list[Finding]:
        findings = []
        if not self._check_tool_available("mypy"):
            return findings

        try:
            result = subprocess.run(
                ["mypy", target_path, "--json-report", "/tmp/mypy-report.json"],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.stdout:
                for line in result.stdout.split("\n"):
                    if ":" in line:
                        parts = line.split(":", 2)
                        if len(parts) >= 3:
                            findings.append(Finding(
                                severity=FindingSeverity.MEDIUM,
                                category=FindingCategory.BEST_PRACTICES,
                                tool="mypy",
                                message=parts[2].strip() if len(parts) > 2 else "",
                                file_path=parts[0],
                                line_number=int(parts[1]) if parts[1].isdigit() else None,
                                confidence="high"
                            ))
        except (subprocess.TimeoutExpired, Exception):
            pass

        return findings


class StaticAnalysisRunner:
    """Runs multiple static analysis tools and aggregates results."""

    def __init__(self):
        self.tools: list[StaticAnalysisTool] = [
            BanditTool(),
            RuffTool(),
            Flake8Tool(),
            MyPyTool()
        ]

    def run_all(self, target_path: str, tool_names: Optional[list[str]] = None) -> list[Finding]:
        """Run specified tools or all available tools."""
        findings = []

        tools_to_run = []
        if tool_names:
            tools_to_run = [t for t in self.tools if t.name in tool_names]
        else:
            tools_to_run = self.tools

        for tool in tools_to_run:
            tool_findings = tool.run(target_path)
            findings.extend(tool_findings)

        return findings

    def get_available_tools(self) -> list[str]:
        """Get list of available tools."""
        return [tool.name for tool in self.tools if tool._check_tool_available(tool.name)]


def run_static_analysis(target_path: str, tool_names: Optional[list[str]] = None) -> dict:
    """
    Main function to run static analysis on a target path.
    
    Args:
        target_path: Path to analyze (file or directory)
        tool_names: Optional list of specific tools to run
        
    Returns:
        Dictionary with findings and metadata
    """
    runner = StaticAnalysisRunner()
    findings = runner.run_all(target_path, tool_names)
    available_tools = runner.get_available_tools()

    return {
        "target_path": target_path,
        "tools_run": [t.name for t in runner.tools],
        "available_tools": available_tools,
        "findings_count": len(findings),
        "findings": [f.to_dict() for f in findings],
        "summary": {
            FindingSeverity.CRITICAL.value: len([f for f in findings if f.severity == FindingSeverity.CRITICAL]),
            FindingSeverity.HIGH.value: len([f for f in findings if f.severity == FindingSeverity.HIGH]),
            FindingSeverity.MEDIUM.value: len([f for f in findings if f.severity == FindingSeverity.MEDIUM]),
            FindingSeverity.LOW.value: len([f for f in findings if f.severity == FindingSeverity.LOW])
        }
    }
