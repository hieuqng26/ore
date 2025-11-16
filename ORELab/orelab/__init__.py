"""
ORELab - Excel to ORE Engine Converter

A Python package for converting Excel trade data to ORE XML format
and running ORE analytics.
"""

__version__ = "0.1.0"

from .engine import OREBuilder, ORERunner

__all__ = ["OREBuilder", "ORERunner"]
