"""Tests for code review agent."""
import pytest
from unittest.mock import Mock, patch, MagicMock

from code_review_agent.models import (
    AnalysisSummary,
    Category,
    CodeAnalysisResult,
    Finding,
    Severity,
)
from code_review_agent.config import Config


class TestModels:
    """Tests for data models."""

    def test_finding_to_dict(self):
        """Test Finding to_dict conversion."""
        finding = Finding(
            id="test-1",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            file="src/main.py",
            line=42,
            description="Hardcoded password found",
            evidence='password = "secret123"',
            recommendation="Use environment variables",
        )

        result = finding.to_dict()

        assert result["id"] == "test-1"
        assert result["severity"] == "high"
        assert result["category"] == "security"
        assert result["file"] == "src/main.py"
        assert result["line"] == 42

    def test_analysis_summary_to_dict(self):
        """Test AnalysisSummary to_dict conversion."""
        summary = AnalysisSummary(
            total_files_analyzed=10,
            total_findings=5,
            risk_score=45.5,
            critical_count=1,
            high_count=2,
            medium_count=1,
            low_count=1,
        )

        result = summary.to_dict()

        assert result["total_files_analyzed"] == 10
        assert result["total_findings"] == 5
        assert result["risk_score"] == 45.5
        assert result["critical_count"] == 1

    def test_code_analysis_result_to_dict(self):
        """Test CodeAnalysisResult to_dict conversion."""
        finding = Finding(
            id="test-1",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            file="src/main.py",
            line=42,
            description="Test finding",
            evidence="code",
            recommendation="fix it",
        )

        result = CodeAnalysisResult(
            repository="test-repo",
            commit_hash="abc123",
            summary=AnalysisSummary(
                total_files_analyzed=1,
                total_findings=1,
            ),
            findings=[finding],
        ).to_dict()

        assert result["repository"] == "test-repo"
        assert result["commit_hash"] == "abc123"
        assert len(result["findings"]) == 1


class TestConfig:
    """Tests for configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()

        assert config.aws_region == "us-east-1"
        assert config.max_file_size_mb == 10
        assert config.temperature == 0.7

    def test_supported_languages(self):
        """Test supported languages list."""
        config = Config()

        assert "python" in config.supported_languages
        assert "javascript" in config.supported_languages
        assert "go" in config.supported_languages


class TestSeverityEnum:
    """Tests for Severity enum."""

    def test_severity_values(self):
        """Test severity enum values."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"


class TestCategoryEnum:
    """Tests for Category enum."""

    def test_category_values(self):
        """Test category enum values."""
        assert Category.SECURITY.value == "security"
        assert Category.PERFORMANCE.value == "performance"
        assert Category.BUG.value == "bug"
        assert Category.BEST_PRACTICE.value == "best_practice"
