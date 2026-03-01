"""Custom exceptions for CompliantFlow."""


class ValidationError(Exception):
    """Raised when an item YAML file fails schema validation against project_config."""
    pass
