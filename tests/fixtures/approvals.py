"""The signing project of `medharness.validation.signing`, skipped where `ssh-keygen` is missing."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from medharness.validation import signing
from medharness.validation.signing import Project


def build_project(tmp_path: Path, *, with_approvers: bool = True) -> Project:
    if shutil.which("ssh-keygen") is None:
        pytest.skip("ssh-keygen is not installed")
    return signing.build_project(tmp_path, with_approvers=with_approvers)
