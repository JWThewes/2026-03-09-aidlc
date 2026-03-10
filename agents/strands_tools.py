"""Strands agent tools for code review."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Optional
from strands import tool
from src.code_review.static_analysis import (
    run_static_analysis,
    StaticAnalysisRunner,
    FindingSeverity,
    FindingCategory
)


@tool
def run_security_scan(target_path: str) -> str:
    """
    Run security-focused static analysis using Bandit.
    
    Args:
        target_path: Path to the file or directory to scan
        
    Returns:
        JSON string containing security findings
    """
    result = run_static_analysis(target_path, tool_names=["bandit"])
    return _format_findings(result, "Security Scan")


@tool
def run_linting(target_path: str, tool_name: Optional[str] = None) -> str:
    """
    Run linting tools (ruff, flake8) on target code.
    
    Args:
        target_path: Path to the file or directory to scan
        tool_name: Specific tool to use (ruff, flake8). If None, runs all linters.
        
    Returns:
        JSON string containing linting findings
    """
    tools = [tool_name] if tool_name else ["ruff", "flake8"]
    result = run_static_analysis(target_path, tool_names=tools)
    return _format_findings(result, "Linting")


@tool
def run_type_checking(target_path: str) -> str:
    """
    Run type checking using MyPy.
    
    Args:
        target_path: Path to the file or directory to scan
        
    Returns:
        JSON string containing type checking findings
    """
    result = run_static_analysis(target_path, tool_names=["mypy"])
    return _format_findings(result, "Type Checking")


@tool
def run_full_static_analysis(target_path: str) -> str:
    """
    Run comprehensive static analysis using all available tools.
    
    This includes:
    - Bandit (security)
    - Ruff (linting)
    - Flake8 (linting)
    - MyPy (type checking)
    
    Args:
        target_path: Path to the file or directory to scan
        
    Returns:
        JSON string containing all findings
    """
    result = run_static_analysis(target_path)
    return _format_findings(result, "Full Static Analysis")


@tool
def list_available_tools() -> str:
    """
    List all available static analysis tools on the system.
    
    Returns:
        JSON string listing available tools
    """
    runner = StaticAnalysisRunner()
    available = runner.get_available_tools()
    return f'{{"available_tools": {available}}}'


def _format_findings(result: dict, scan_type: str) -> str:
    """Format static analysis results for display."""
    output = {
        "scan_type": scan_type,
        "target_path": result["target_path"],
        "summary": result["summary"],
        "findings_count": result["findings_count"],
        "findings": result["findings"]
    }
    return str(output)


def get_all_tools() -> list:
    """Return all static analysis tools for the Strands agent."""
    return [
        run_security_scan,
        run_linting,
        run_type_checking,
        run_full_static_analysis,
        list_available_tools
    ]
