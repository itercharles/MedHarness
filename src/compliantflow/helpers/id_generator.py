"""ID Generator — re-export from DHF layer for backward compatibility.

The canonical implementation lives in DHF/utils/id_generator.py.
"""
from utils.id_generator import get_next_id, validate_id_format, extract_number  # noqa: F401

__all__ = ["get_next_id", "validate_id_format", "extract_number"]
