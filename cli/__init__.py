"""CLI package for Calibre Companion"""
from .main import cli
from .commands.library import library

__all__ = ['cli', 'library']
