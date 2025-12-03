"""
Utility package for analyzing LinkedIn post performance.

Expose the main entry point so consumers can reuse the analysis logic
outside of the CLI.
"""

from .analysis import analyze_posts  # noqa: F401
from .cli import build_arg_parser, main  # noqa: F401

__all__ = [
    "analyze_posts",
    "build_arg_parser",
    "main",
]
