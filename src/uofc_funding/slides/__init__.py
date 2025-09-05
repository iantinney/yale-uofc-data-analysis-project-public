"""
Slide generation package.

This package provides PowerPoint presentation building functionality.
"""

from .builder import PresentationBuilder
from .layouts import Position, SlideLayouts, SlideType

__all__ = [
    "Position",
    "PresentationBuilder",
    "SlideLayouts",
    "SlideType",
]
