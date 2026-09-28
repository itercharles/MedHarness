"""CONTRACT_VERSION is asserted, so a downstream repo that pins it gets an
explicit failure on upgrade rather than a silent change in what it reads."""

from medharness.contracts import CONTRACT_VERSION


def test_contract_version_is_defined():
    assert isinstance(CONTRACT_VERSION, str) and CONTRACT_VERSION


def test_contract_version_is_stable():
    assert CONTRACT_VERSION == "19.0"
