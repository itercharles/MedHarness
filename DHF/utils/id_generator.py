"""
Automatic ID Generator Utility

Provides functions for generating unique item IDs automatically.
Implements SRS-043: ID Generator Utility Implementation.
"""
import re
from typing import List


def get_next_id(prefix: str, existing_ids: List[str]) -> str:
    """
    Generate the next available ID for a given prefix.

    Args:
        prefix: Document type prefix (e.g., "SRS-", "SYS-")
        existing_ids: List of existing IDs with the same prefix

    Returns:
        Next available ID in format {PREFIX}{NUMBER} (e.g., "SRS-001")

    Examples:
        >>> get_next_id("SRS-", [])
        'SRS-001'
        >>> get_next_id("SRS-", ["SRS-001", "SRS-002"])
        'SRS-003'
        >>> get_next_id("SRS-", ["SRS-001", "SRS-005"])
        'SRS-006'
    """
    if not existing_ids:
        return f"{prefix}001"

    # Filter IDs that match the prefix
    matching_ids = [id for id in existing_ids if id.startswith(prefix)]

    if not matching_ids:
        return f"{prefix}001"

    # Extract numbers from matching IDs
    numbers = []
    for id in matching_ids:
        try:
            num = extract_number(id)
            numbers.append(num)
        except ValueError:
            # Skip invalid IDs
            continue

    if not numbers:
        return f"{prefix}001"

    # Get max number and add 1
    max_num = max(numbers)
    next_num = max_num + 1

    # Format with zero padding (3 digits)
    return f"{prefix}{next_num:03d}"


def validate_id_format(id: str, prefix: str) -> bool:
    """
    Validate that an ID matches the expected format.

    Args:
        id: ID to validate
        prefix: Expected prefix (e.g., "SRS-")

    Returns:
        True if ID is valid, False otherwise

    Examples:
        >>> validate_id_format("SRS-001", "SRS-")
        True
        >>> validate_id_format("SRS001", "SRS-")
        False
        >>> validate_id_format("SYS-001", "SRS-")
        False
    """
    if not id.startswith(prefix):
        return False

    # Pattern: PREFIX followed by digits
    pattern = f"^{re.escape(prefix)}\\d+$"
    return bool(re.match(pattern, id))


def extract_number(id: str) -> int:
    """
    Extract the numeric part from an ID.

    Args:
        id: ID string (e.g., "SRS-001")

    Returns:
        Numeric part as integer

    Raises:
        ValueError: If ID doesn't contain a valid number

    Examples:
        >>> extract_number("SRS-001")
        1
        >>> extract_number("SYS-042")
        42
    """
    # Find the last part after the last dash
    parts = id.split('-')
    if len(parts) < 2:
        raise ValueError(f"Invalid ID format: {id}")

    number_part = parts[-1]

    try:
        return int(number_part)
    except ValueError:
        raise ValueError(f"Invalid number in ID: {id}")
