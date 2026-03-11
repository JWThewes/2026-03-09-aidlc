"""Main Strands Agent for code review using Bedrock."""
import json
import os
from pathlib import Path
from typing import Optional

from strands import Agent
from strands.models import BedrockModel
from strands.tools import Tool

from code_review_agent.config import config
from code_review_agent.models import (
    AnalysisSummary,
    Category,
    CodeAnalysisResult,
    Finding,
    Severity,
)
from code_review_agent.prompts import CODE_REVIEW_SYSTEM_PROMPT


class CodeReviewAgent:
    """Strands Agent for LLM-powered code analysis using Bedrock."""

    def __init__(
        self,
        model_id: Optional[str] = None,
        aws_region: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """Initialize the code review agent.

        Args:
            model_id: Bedrock model ID to use
            aws_region: AWS region for Bedrock
            temperature: LLM temperature setting
            max_tokens: Maximum tokens for LLM response
        """
        self.model_id = model_id or config.bedrock_model_id
        self.aws_region = aws_region or config.aws_region
        self.temperature = temperature or config.temperature
        self.max_tokens = max_tokens or config.max_tokens

        self._model = None
        self._agent = None
        self._tools: list[Tool] = []

    @property
    def model(self) -> BedrockModel:
        """Lazy initialization of Bedrock model."""
        if self._model is None:
            self._model = BedrockModel(
                model_id=self.model_id,
                region_name=self.aws_region,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        return self._model

    @property
    def agent(self) -> Agent:
        """Lazy initialization of Strands Agent."""
        if self._agent is None:
            self._agent = Agent(
                model=self.model,
                system_prompt=CODE_REVIEW_SYSTEM_PROMPT,
                tools=self._tools,
            )
        return self._agent

    def add_tool(self, tool: Tool) -> None:
        """Add a tool to the agent's toolkit.

        Args:
            tool: A Strands Tool to add
        """
        self._tools.append(tool)
        if self._agent is not None:
            self._agent = Agent(
                model=self.model,
                system_prompt=CODE_REVIEW_SYSTEM_PROMPT,
                tools=self._tools,
            )

    def analyze_file(self, file_path: str, content: str) -> list[Finding]:
        """Analyze a single file for issues.

        Args:
            file_path: Path to the file being analyzed
            content: Content of the file

        Returns:
            List of findings from the analysis
        """
        prompt = f"""Analyze the following code from file: {file_path}

```{self._get_file_extension(file_path)}
{content}
```

Provide a detailed analysis identifying any:
1. Security vulnerabilities
2. Performance issues
3. Bugs
4. Best practice violations

For each finding, provide:
- Severity (critical, high, medium, low)
- Category (security, performance, bug, best_practice)
- Line number
- Description
- Evidence
- Recommendation

Output your findings as a JSON array with the following structure:
[
  {{
    "severity": "<critical|high|medium|low>",
    "category": "<security|performance|bug|best_practice>",
    "line": <line_number>,
    "description": "<description>",
    "evidence": "<code_snippet>",
    "recommendation": "<fix_suggestion>"
  }}
]

If no issues found, return an empty array []."""

        response = self.agent(prompt)
        return self._parse_findings(response, file_path)

    def analyze_repository(
        self, repo_path: str, commit_hash: Optional[str] = None
    ) -> CodeAnalysisResult:
        """Analyze an entire repository.

        Args:
            repo_path: Path to the repository
            commit_hash: Optional commit hash to identify the version

        Returns:
            Complete analysis results
        """
        repo_name = Path(repo_path).name
        commit = commit_hash or self._get_current_commit(repo_path) or "unknown"

        findings = []
        files_analyzed = 0

        for file_path in self._get_files_to_analyze(repo_path):
            try:
                content = Path(file_path).read_text(encoding="utf-8")
                file_findings = self.analyze_file(file_path, content)
                findings.extend(file_findings)
                files_analyzed += 1
            except Exception as e:
                print(f"Warning: Could not analyze {file_path}: {e}")

        summary = self._create_summary(findings, files_analyzed)

        return CodeAnalysisResult(
            repository=repo_name,
            commit_hash=commit,
            summary=summary,
            findings=findings,
        )

    def _get_file_extension(self, file_path: str) -> str:
        """Get the file extension for syntax highlighting."""
        ext = Path(file_path).suffix.lstrip(".")
        extension_map = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "jsx": "javascript",
            "tsx": "typescript",
            "java": "java",
            "go": "go",
            "rs": "rust",
            "c": "c",
            "cpp": "cpp",
            "h": "c",
            "hpp": "cpp",
        }
        return extension_map.get(ext, ext)

    def _get_files_to_analyze(self, repo_path: str) -> list[str]:
        """Get list of files to analyze in the repository."""
        exclude_dirs = {
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            ".pytest_cache",
            ".mypy_cache",
            "dist",
            "build",
            ".tox",
        }
        exclude_extensions = {".pyc", ".pyo", ".so", ".dll", ".exe"}

        files = []
        repo = Path(repo_path)

        for path in repo.rglob("*"):
            if path.is_file():
                if any(excl in path.parts for excl in exclude_dirs):
                    continue
                if path.suffix in exclude_extensions:
                    continue
                if path.stat().st_size > config.max_file_size_mb * 1024 * 1024:
                    continue
                files.append(str(path))

        return files

    def _get_current_commit(self, repo_path: str) -> Optional[str]:
        """Get current git commit hash."""
        try:
            import subprocess

            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception:
            return None

    def _create_summary(self, findings: list[Finding], files_analyzed: int) -> AnalysisSummary:
        """Create analysis summary from findings."""
        severity_counts = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 0,
            Severity.MEDIUM: 0,
            Severity.LOW: 0,
        }

        for finding in findings:
            severity_counts[finding.severity] += 1

        critical_weight = 10
        high_weight = 5
        medium_weight = 2
        low_weight = 1

        max_score = files_analyzed * 10 if files_analyzed > 0 else 1
        risk_score = min(
            (
                severity_counts[Severity.CRITICAL] * critical_weight
                + severity_counts[Severity.HIGH] * high_weight
                + severity_counts[Severity.MEDIUM] * medium_weight
                + severity_counts[Severity.LOW] * low_weight
            )
            / max_score
            * 100,
            100.0,
        )

        return AnalysisSummary(
            total_files_analyzed=files_analyzed,
            total_findings=len(findings),
            risk_score=round(risk_score, 2),
            critical_count=severity_counts[Severity.CRITICAL],
            high_count=severity_counts[Severity.HIGH],
            medium_count=severity_counts[Severity.MEDIUM],
            low_count=severity_counts[Severity.LOW],
        )

    def _parse_findings(self, response: str, file_path: str) -> list[Finding]:
        """Parse LLM response into Finding objects."""
        findings = []

        try:
            import re

            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                for idx, item in enumerate(data):
                    finding = Finding(
                        id=f"{Path(file_path).name}-{idx}",
                        severity=Severity(item.get("severity", "low")),
                        category=Category(item.get("category", "best_practice")),
                        file=file_path,
                        line=item.get("line", 0),
                        description=item.get("description", ""),
                        evidence=item.get("evidence", ""),
                        recommendation=item.get("recommendation", ""),
                    )
                    findings.append(finding)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Warning: Could not parse findings from response: {e}")

        return findings


def create_agent(
    model_id: Optional[str] = None,
    aws_region: Optional[str] = None,
    tools: Optional[list[Tool]] = None,
) -> CodeReviewAgent:
    """Factory function to create a configured code review agent.

    Args:
        model_id: Bedrock model ID to use
        aws_region: AWS region for Bedrock
        tools: Optional list of additional tools

    Returns:
        Configured CodeReviewAgent instance
    """
    agent = CodeReviewAgent(model_id=model_id, aws_region=aws_region)

    if tools:
        for tool in tools:
            agent.add_tool(tool)

    return agent
