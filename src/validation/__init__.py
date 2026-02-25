"""
Validation module for ground truth verification.

This module provides independent validation of Red Team claims
using external static analysis tools.
"""

from .manifest_validator import (
    ManifestValidator,
    ManifestValidation,
    validation_to_dict,
)

__all__ = [
    "ManifestValidator",
    "ManifestValidation", 
    "validation_to_dict",
]
