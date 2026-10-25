"""The list of people who may sign approvals: `DHF/config/approvers.yaml`.

The file is absent until a project turns approvals on, so a missing file is an answer
(`None`), not an error.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic import ValidationError as SchemaError

from dhfkit.exceptions import DHFDataError

APPROVERS_FILE = "approvers.yaml"


class Approver(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="The person, as an approval's `signer` names them")
    principal: str = Field(..., description="The identity ssh-keygen verifies the signature against; no whitespace")
    roles: List[str] = Field(..., description="The roles this person may sign for")
    keys: List[str] = Field(..., min_length=1, description="OpenSSH public keys, one line each")
    no_touch_required: bool = Field(False, description="Accept this person's signatures without a proven user-presence touch")

    @field_validator("principal")
    @classmethod
    def _no_whitespace(cls, value: str) -> str:
        if not value or any(c.isspace() for c in value):
            raise ValueError("must be a single word with no spaces")
        return value

    @field_validator("keys")
    @classmethod
    def _one_line_each(cls, value: List[str]) -> List[str]:
        if any(not k.strip() or "\n" in k.strip() for k in value):
            raise ValueError("each key is one OpenSSH public key line")
        return [k.strip() for k in value]


def approvers_path(dhf_root: Path | str) -> Path:
    """Where the list is, whether or not it exists yet."""
    return Path(dhf_root) / "config" / APPROVERS_FILE


def parse_approvers(text: str, source: str) -> List[Approver]:
    """The list in *text*, or a DHFDataError naming *source*."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise DHFDataError(f"{source} is not valid YAML: {exc}") from exc
    if not isinstance(data, list):
        raise DHFDataError(f"{source} must be a list of approvers, each with name, principal, roles and keys")
    try:
        return [Approver.model_validate(entry) for entry in data]
    except SchemaError as exc:
        raise DHFDataError(f"{source} is not a valid approvers list: {exc}") from exc


def load_approvers(dhf_root: Path | str) -> List[Approver] | None:
    """The project's approvers, or None when it keeps none (approvals are off)."""
    path = approvers_path(dhf_root)
    if not path.is_file():
        return None
    return parse_approvers(path.read_text(encoding="utf-8"), str(path))
