"""Custom exceptions for DHF."""


class ValidationError(Exception):
    """Raised when an item YAML file fails schema validation against doc-type config."""
    pass


class RefusedWrite(ValidationError):
    """A write was refused because the item would not load; nothing was written."""


class DHFDataError(Exception):
    """The DHF's own data could not be read.

    Distinct from a finding: a gate reports findings, but it cannot run at all
    against a DHF whose items do not load. One mistyped field used to raise
    ValidationError out of nine of thirteen commands as a traceback.
    """
