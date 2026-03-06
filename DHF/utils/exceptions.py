"""Custom exceptions for DHF."""


class ValidationError(Exception):
    """Raised when an item YAML file fails schema validation against doc-type config."""
    pass
