"""Data models for code review findings."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    """Severity levels for findings."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Category(str, Enum):
    """Categories for findings."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    BUG = "bug"
    BEST_PRACTICE = "best_practice"


@dataclass
class Finding:
    """Represents a single code review finding."""
    id: str
    severity: Severity
    category: Category
    file: str
    line: int
    description: str
    evidence: str
    recommendation: str

    def to_dict(self) -> dict:
        """Convert finding to dictionary."""
        return {
            "id": self.id,
            "severity": self.severity.value,
            "category": self.category.value,
            "file": self.file,
            "line": self.line,
            "description": self.description,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
        }


@dataclass
class AnalysisSummary:
    """Summary of the code analysis."""
    total_files_analyzed: int = 0
    total_findings: int = 0
    risk_score: float = 0.0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    def to_dict(self) -> dict:
        """Convert summary to dictionary."""
        return {
            "total_files_analyzed": self.total_files_analyzed,
            "total_findings": self.total_findings,
            "risk_score": self.risk_score,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
        }


@dataclass
class CodeAnalysisResult:
    """Result of code analysis."""
    repository: str
    commit_hash: str
    summary: AnalysisSummary = field(default_factory=AnalysisSummary)
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert result to dictionary."""
        return {
            "repository": self.repository,
            "commit_hash": self.commit_hash,
            "analysis_summary": self.summary.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
        }
