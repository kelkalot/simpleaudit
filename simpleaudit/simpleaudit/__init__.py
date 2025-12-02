"""
SimpleAudit - Lightweight AI Safety Auditing Framework

A simple, effective tool for red-teaming AI systems using Claude as auditor and judge.

Usage:
    from simpleaudit import Auditor
    
    auditor = Auditor(target="http://localhost:8000/v1/chat/completions")
    results = auditor.run("safety")
    results.summary()
"""

__version__ = "0.1.0"
__author__ = "SimpleAudit Contributors"

from .auditor import Auditor
from .results import AuditResults, AuditResult
from .scenarios import get_scenarios, list_scenario_packs

__all__ = [
    "Auditor",
    "AuditResults", 
    "AuditResult",
    "get_scenarios",
    "list_scenario_packs",
]
