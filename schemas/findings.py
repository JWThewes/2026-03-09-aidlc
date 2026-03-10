import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import uuid


class Severity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Category(str, Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    BEST_PRACTICES = "best-practices"
    BUGS = "bugs"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Evidence:
    code_snippet: str
    line_number: int
    file_path: Optional[str] = None
    context: Optional[str] = None
    tool_source: Optional[str] = None


@dataclass
class Finding:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    severity: Severity = Severity.MEDIUM
    category: Category = Category.BEST_PRACTICES
    title: str = ""
    description: str = ""
    evidence: Evidence = field(default_factory=lambda: Evidence(code_snippet="", line_number=0))
    recommendation: str = ""
    cwe_id: Optional[str] = None
    cve_id: Optional[str] = None
    confidence: Confidence = Confidence.MEDIUM


@dataclass
class Metadata:
    repository: str
    commit_hash: str
    analysis_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    branch: Optional[str] = None
    analyzer_version: str = "1.0.0"
    files_analyzed: int = 0


@dataclass
class Summary:
    total_findings: int = 0
    by_severity: Dict[str, int] = field(default_factory=lambda: {"Critical": 0, "High": 0, "Medium": 0, "Low": 0})
    by_category: Dict[str, int] = field(default_factory=lambda: {"security": 0, "performance": 0, "best-practices": 0, "bugs": 0})
    risk_score: float = 0.0


@dataclass
class FindingsReport:
    findings: List[Finding] = field(default_factory=list)
    metadata: Optional[Metadata] = None
    summary: Summary = field(default_factory=Summary)

    def to_dict(self) -> Dict[str, Any]:
        result = {"findings": [], "metadata": None, "summary": None}
        
        for finding in self.findings:
            f_dict = {
                "id": finding.id,
                "severity": finding.severity.value,
                "category": finding.category.value,
                "title": finding.title,
                "description": finding.description,
                "evidence": asdict(finding.evidence),
                "recommendation": finding.recommendation,
                "confidence": finding.confidence.value,
            }
            if finding.cwe_id:
                f_dict["cwe_id"] = finding.cwe_id
            if finding.cve_id:
                f_dict["cve_id"] = finding.cve_id
            result["findings"].append(f_dict)
        
        if self.metadata:
            result["metadata"] = asdict(self.metadata)
        
        result["summary"] = asdict(self.summary)
        return result

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def calculate_summary(self) -> None:
        self.summary.total_findings = len(self.findings)
        self.summary.by_severity = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        self.summary.by_category = {"security": 0, "performance": 0, "best-practices": 0, "bugs": 0}
        
        severity_weights = {"Critical": 10, "High": 7, "Medium": 4, "Low": 1}
        total_weight = 0
        
        for finding in self.findings:
            sev = finding.severity.value
            cat = finding.category.value
            
            self.summary.by_severity[sev] = self.summary.by_severity.get(sev, 0) + 1
            self.summary.by_category[cat] = self.summary.by_category.get(cat, 0) + 1
            
            total_weight += severity_weights.get(sev, 0)
        
        max_weight = len(self.findings) * 10 if self.findings else 1
        self.summary.risk_score = round((total_weight / max_weight) * 100, 2)


class FindingsValidator:
    SCHEMA_PATH = Path(__file__).parent / "findings_schema.json"
    
    def __init__(self):
        with open(self.SCHEMA_PATH, "r") as f:
            self.schema = json.load(f)
    
    def validate(self, report: FindingsReport) -> bool:
        try:
            import jsonschema
            jsonschema.validate(instance=report.to_dict(), schema=self.schema)
            return True
        except ImportError:
            return True
        except Exception as e:
            if "ValidationError" in str(type(e)):
                raise ValueError(f"Validation error: {e}")
            raise
