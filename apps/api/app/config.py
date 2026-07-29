"""
Configuration — re-exports from shared config.

All validation lives in packages.core.config.
"""

from packages.core.config import Config, load_config

__all__ = ["Config", "load_config"]
