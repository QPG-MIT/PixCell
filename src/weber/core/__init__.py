"""
Weber Core Module

Contains the main functionality for analyzing GDSFactory scripts and generating
interactive explorers.
"""

from .analyzer import ScriptAnalysis, analyze_script
from .default_slots import generate_default_slots, SlotConfig

__all__ = [
    "ScriptAnalysis",
    "analyze_script",
    "generate_default_slots",
    "SlotConfig",
]
