"""ItemStore — the item store: a DHF directory of YAML files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from dhfkit.exceptions import RefusedWrite, ValidationError
from dhfkit.models.config import ProjectConfig
from dhfkit.models.item import Item
from dhfkit.repository.loader import ItemLoader
from dhfkit.adapter import DHFAdapter, resolve_adapter
from dhfkit.id_generator import get_next_id

# What a branch changed, deleted items included: they stay named after they are gone.
_HISTORICAL_LINK_FIELDS = frozenset({"affected_items"})
_UID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*-\d+$")


class ItemStore:
    """The item store for a DHF directory: the project's config and documents on
    disk, and its items wherever the configured adapter keeps them."""

    def __init__(self, dhf_root: Path, adapter: DHFAdapter | None = None):
        self._dhf_root = Path(dhf_root)
        self._config = ProjectConfig.load(self._dhf_root / "config")
        self._adapter = adapter or resolve_adapter(self._config, self._dhf_root)
        # Checks an item's fields against its doc type, whatever holds the item.
        self._loader = ItemLoader(self._dhf_root / "items", project_config=self._config)


        # document_specifications lives in global config
        self._doc_specs = self._config.document_specifications

        # Lazy-fetch flag: set True once GitHub auto-fetch has been attempted this session
        self._results_fetched = False

        # Document index: stem → Path, built once at init to avoid per-call rglob scans
        self._doc_index: dict[str, Path] = {}
        self._rebuild_doc_index()

    def _template_dirs(self) -> list[Path]:
        """Where specification templates are looked up: the project, then the defaults.

        A project overrides one template by putting a file of the same name in
        `documents/specs/`; everything else comes from the package.
        """
        from dhfkit.paths import DEFAULT_SPECS_DIR

        project = self._dhf_root / "documents" / "specs"
        return ([project] if project.is_dir() else []) + [DEFAULT_SPECS_DIR]

    # ------------------------------------------------------------------
    # Item type metadata
    # ------------------------------------------------------------------

    def _item_type_dict(self, dt) -> dict:
        return {
            "display_name": dt.name or dt.code,
            "description": dt.description or "",
            "code": dt.code,
            "prefix": dt.prefix,
            "role": dt.role or dt.code,
            "has_verification": dt.has_verification,
            "lifecycle": dt.lifecycle,
            "fields": dt.properties or [],
        }

    def get_item_type(self, prefix: str) -> Optional[dict]:
        dt = self._config.get_doc_type_by_prefix(prefix)
        if dt is None:
            return None
        return self._item_type_dict(dt)

    def list_item_types(self) -> List[dict]:
        return [self._item_type_dict(dt) for dt in self._config.doc_types]

    def get_lifecycle_states(self) -> List[dict]:
        gl = self._config.global_lifecycle
        if gl is None:
            return []
        return [
            {
                "id": s.id,
                "label": s.label,
                "is_stable": s.is_stable,
                "action_label": s.action_label,
                "icon": s.icon,
                "color": s.color,
            }
            for s in gl.states
        ]

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------

    def _enrich_item_dict(self, item) -> dict:
        """Add medharness domain fields (type, all_linked_uids) to an item dict.

        `all_linked_uids` is every ID the item links to, through the link fields its
        doc type declares: a project's own relationship field is one of them. A type
        that declares none keeps the model's fixed list.
        """
        d = item.model_dump(by_alias=True, exclude_none=True)
        dt = self._config.doc_type_of(item.uid)
        d['type'] = dt.code if dt else item.uid.split('-')[0]
        declared = self._config.link_properties(dt.code) if dt else {}
        if declared:
            linked = set()
            for field in declared:
                value = d.get(field)
                linked.update(v for v in ([value] if isinstance(value, str) else value or []) if isinstance(v, str) and v)
            d['all_linked_uids'] = sorted(linked)
        else:
            d['all_linked_uids'] = item.all_linked_uids
        return d

    def get_item(self, uid: str) -> Optional[dict]:
        item = self._adapter.load_by_uid(uid)
        if item is None:
            return None
        return self._enrich_item_dict(item)

    def list_items(self, doc_type: Optional[str] = None) -> List[dict]:
        items = self._adapter.load_all()
        result = []
        for item in items:
            if doc_type:
                dt_cfg = self._config.get_doc_type(doc_type)
                prefix = dt_cfg.prefix if dt_cfg else f"{doc_type}-"
                if not item.uid.startswith(prefix):
                    continue
            result.append(self._enrich_item_dict(item))
        return result

    def _validate_item_links(self, data: dict, written: set[str] | None = None) -> None:
        """Raise ValidationError if a link field holds something that is not an item.

        Checks all known link fields (derives_from, implements, mitigates, etc.): each
        value must be a UID of a known type, of an item that exists. This guards against
        malformed LLM output being persisted silently. ``written`` limits the existence
        check to the fields an update writes, so an old dangling link elsewhere on the
        item does not block an unrelated edit.
        """
        known_prefixes = {dt.prefix for dt in self._config.doc_types}
        uid = data.get("id") or data.get("uid") or ""
        doc_type = self._config.doc_type_of(uid) if uid else None
        declared = tuple(self._config.link_properties(doc_type.code)) if doc_type else ()
        errors = []
        for field in declared:
            val = data.get(field)
            if not val:
                continue
            if isinstance(val, str):
                uids = [val]
            elif isinstance(val, (list, tuple)):
                uids = val
            else:
                errors.append(
                    f"{field}: expected list of UID strings, got {type(val).__name__} ({val!r})"
                )
                continue
            for uid in uids:
                if not isinstance(uid, str):
                    errors.append(f"{field}: expected string UID, got {type(uid).__name__} ({uid!r})")
                    continue
                if not _UID_PATTERN.match(uid):
                    errors.append(f"{field}: '{uid}' does not match expected UID pattern (e.g. SYS-001)")
                    continue
                prefix = uid.rsplit("-", 1)[0] + "-"
                if prefix not in known_prefixes:
                    errors.append(
                        f"{field}: '{uid}' has unknown prefix '{prefix}' "
                        f"(known: {sorted(known_prefixes)})"
                    )
                elif (field not in _HISTORICAL_LINK_FIELDS and (written is None or field in written)
                      and self._adapter.load_by_uid(uid) is None):
                    errors.append(f"{field}: '{uid}' does not exist; create it first, or leave it out")
        errors += self._link_type_errors(data)
        errors += self._status_errors(data)
        if errors:
            raise ValidationError("Item link validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    def _status_errors(self, data: dict) -> list[str]:
        """A `status` that is not a state of the item's type (`banana`)."""
        status = data.get("status")
        uid = data.get("id") or data.get("uid") or ""
        doc_type = self._config.doc_type_of(uid) if uid else None
        allowed = self._config.valid_states(doc_type.code) if doc_type else None
        if status and allowed is not None and status not in allowed:
            return [f"status: '{status}' is not a state of {doc_type.code} (one of {', '.join(sorted(allowed))})"]
        return []

    def _link_type_errors(self, data: dict) -> list[str]:
        """Links whose target is of a type the field does not accept (`satisfies` → CRS only)."""
        uid = data.get("id") or data.get("uid") or ""
        doc_type = self._config.doc_type_of(uid) if uid else None
        errors = []
        for field, allowed in (self._config.link_properties(doc_type.code) if doc_type else {}).items():
            if not allowed:
                continue
            value = data.get(field)
            for target in [value] if isinstance(value, str) else value or []:
                target_type = self._config.doc_type_of(target) if isinstance(target, str) else None
                if target_type is not None and target_type.code not in allowed:
                    errors.append(
                        f"{field}: '{target}' is a {target_type.code}, and {doc_type.code}.{field} "
                        f"accepts only {', '.join(allowed)}"
                    )
        return errors

    def create_item(self, data: dict) -> dict:
        # CR-006: ID is always auto-generated; any caller-supplied id is ignored
        data = {k: v for k, v in data.items() if k != 'id'}
        doc_type_code = data.get('type')
        if not doc_type_code:
            raise ValueError("Cannot auto-generate ID: document type not specified")
        dt_cfg = self._config.get_doc_type(doc_type_code)
        if not dt_cfg:
            raise ValueError(f"Unknown doc type: {doc_type_code}")
        # Every ID ever used, not only those present. Reusing a deleted ID makes
        # one identifier mean two different items over a project's life, and
        # every reference to it — a CR's affected_items, an approval record, a
        # test's dhf_links — silently retargets.
        existing_ids = self._adapter.used_ids()
        data['id'] = get_next_id(
            dt_cfg.prefix,
            [i for i in existing_ids if i.startswith(dt_cfg.prefix)],
        )

        doc_type_code = data['id'].split('-')[0]
        dt_cfg = self._config.get_doc_type(doc_type_code)
        if dt_cfg and dt_cfg.lifecycle:
            # Find initial state
            for t in dt_cfg.lifecycle.get('transitions', []):
                from_states = t.get('from_states', [])
                if None in from_states or 'null' in from_states:
                    data['status'] = t['to_state']
                    break

        self._validate_item_links(data)

        # Validate against doc-type schema before saving
        if self._loader.project_config:
            from pathlib import Path as _Path
            self._loader._validate_against_schema(data, _Path(f"{data['id']}.yaml"))

        item = Item.model_validate(data)
        self._adapter.save(item)
        return self._enrich_item_dict(item)

    def update_item(self, uid: str, data: dict) -> Optional[dict]:
        from dhfkit.lifecycle import get_initial_state, is_stable

        existing = self._adapter.load_by_uid(uid)
        if not existing:
            return None

        # Guard: ID is immutable — reject any attempt to change it
        incoming_id = data.get('id')
        if incoming_id is not None and incoming_id != existing.uid:
            raise ValidationError("Item ID is immutable and cannot be changed")

        # If the item has a lifecycle and is currently in a stable state,
        # reset it to the initial state and clear approval fields.
        doc_type_code = uid.split("-")[0]
        dt = self._config.get_doc_type_by_prefix(doc_type_code + "-")
        if dt and dt.lifecycle:
            # Only a *stable* state resets: editing an approved item returns it
            # for re-approval, but editing one mid-lifecycle must not discard its
            # progress — that made a CR's closure criteria unsatisfiable.
            old_status = existing.model_dump().get("status")
            if old_status and is_stable(self._config, old_status):
                initial = get_initial_state(self._config, doc_type_code)
                approval_fields = [
                    "approved_by", "approved_date", "reviewer", "review_date",
                    "verified_by", "verified_date", "released_by", "released_date",
                ]
                data = {k: v for k, v in data.items() if k not in approval_fields}
                data = {**data, "status": initial}
                for field in approval_fields:
                    data[field] = None

        updated_data = existing.model_dump(exclude_unset=True)
        # Strip computed/non-model keys that should not be persisted
        data = {k: v for k, v in data.items() if k != "all_linked_uids"}
        updated_data.update(data)
        # Remove keys explicitly set to None (signal to clear the field)
        updated_data = {k: v for k, v in updated_data.items() if v is not None}
        self._validate_item_links(updated_data, written=set(data))
        # What the loader would refuse must not be written: one unreadable item
        # makes the whole DHF unreadable, this command included.
        try:
            self._loader._validate_against_schema(
                {("id" if k == "uid" else k): v for k, v in updated_data.items()},
                Path(existing.file_path))
        except ValidationError as exc:
            raise RefusedWrite(f"{uid} not updated: {exc}") from exc
        item = Item.model_validate(updated_data)
        self._adapter.save(item)
        return self._enrich_item_dict(item)

    def get_available_transitions(self, item_id: str) -> List[Dict]:
        """Return available lifecycle transitions for an item."""
        from dhfkit.lifecycle import get_available_transitions
        item = self.get_item(item_id)
        if item is None:
            return []
        return get_available_transitions(self._config, item)

    def execute_transition(self, item_id: str, to_state: str) -> Dict:
        """Execute a lifecycle state transition for an item."""
        from dhfkit.lifecycle import execute_transition
        return execute_transition(
            config=self._config,
            get_item_fn=self.get_item,
            update_item_fn=self.update_item,
            item_id=item_id,
            to_state=to_state,
        )

    def delete_item(self, uid: str) -> bool:
        return self._adapter.delete(uid)

    def validate_schema(self) -> dict:
        """Validate all YAML files; returns {'valid': bool, 'errors': [...]}."""
        errors = []
        items = []
        try:
            items = self._adapter.load_all()
        except ValidationError as e:
            errors.append(str(e))
        errors.extend(self._adapter.integrity_errors())
        return {'valid': len(errors) == 0, 'errors': errors,
                'item_count': len(items) if not errors else 0}

    @property
    def store_type(self) -> str:
        """The `type` in `store:` of global.yaml."""
        return str((self._config.store or {}).get("type", "yaml"))

    @property
    def tracks_files(self) -> bool:
        """Whether items are files in Git, which `verify changes` and the build stages read."""
        return bool(getattr(self._adapter, "tracks_files", False))

    @property
    def config(self):
        """The project configuration this adapter was opened against.

        `medharness` read `self._config` from outside in ten places. `dhfkit`
        is meant to be usable standalone, so it has a public surface, and a
        consumer pinned to an underscore has no contract at all.
        """
        return self._config

    def config_file(self, name: str) -> Optional[Path]:
        """Path to a project config file, or None when it is absent.

        Config lives under the store's own layout, so a caller that joins the
        path itself is coupled to this adapter. `soup-sources.yaml` is the one
        a consumer needs by name.
        """
        from dhfkit.paths import config_file

        return config_file(self._dhf_root, name)

    # ------------------------------------------------------------------
    # Document generation
    # ------------------------------------------------------------------

    def get_available_doc_types(self) -> List[str]:
        return list(self._doc_specs.keys())

    def _generator(self):
        from dhfkit.document_generation import DocumentGenerator
        return DocumentGenerator(self._adapter, self._config, self._template_dirs())

    def render_spec(self, doc_type_code: str, fmt: str, out_dir: Path, version: str) -> dict:
        """Render a specification into ``out_dir`` at ``version``; the DHF is not written."""
        gen = self._generator()
        content = gen.render_markdown_spec(doc_type_code, self._doc_specs, version)
        path = gen.export(doc_type_code, content, fmt, out_dir, version)
        return {"doc_type": doc_type_code, "path": str(path), "version": version}

    # ------------------------------------------------------------------
    # Document access
    # ------------------------------------------------------------------

    def _rebuild_doc_index(self) -> None:
        """Scan documents/ once and populate self._doc_index (stem → Path)."""
        self._doc_index = {}
        docs_dir = self._dhf_root / "documents"
        if not docs_dir.exists():
            return
        for candidate in docs_dir.rglob("*"):
            if candidate.is_file() and not candidate.name.startswith("."):
                self._doc_index[candidate.stem] = candidate

    def get_document(self, doc_id: str) -> Optional[str]:
        """Return the text content of a DHF document by its logical ID (filename stem).

        Looks up doc_id in the pre-built index (no rglob per call).
        For example, get_document("development_plan") finds
        documents/plans/development_plan.md.

        Args:
            doc_id: Logical document identifier — the filename without extension
                    (e.g. 'development_plan', 'verification_plan', 'release_notes').

        Returns:
            File text content, or None if no matching document is found.
        """
        path = self._doc_index.get(doc_id)
        if path is None or not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    def list_documents(self, category: Optional[str] = None) -> List[str]:
        """Logical document IDs (filename stems) under documents/.

        `category` narrows to one subdirectory — `list_documents("plans")` gives
        the plan documents. Without it the subdirectory is invisible in the
        result, so a caller wanting only the plans had to go to the filesystem
        itself, which is how `verify plans` came to read `documents/plans/*.md`
        directly.
        """
        if category is None:
            return list(self._doc_index.keys())
        root = (self._dhf_root / "documents" / category).resolve()
        return [
            doc_id for doc_id, path in self._doc_index.items()
            if root in path.resolve().parents
        ]

    def document_path(self, doc_id: str) -> Optional[Path]:
        """Where a document lives, for a caller that must report the filename.

        `verify plans` names the file it is complaining about, and a stem is not
        a filename. Returning the path keeps that possible without a second
        filesystem walk in the caller.
        """
        return self._doc_index.get(doc_id)

    # ------------------------------------------------------------------
    # CR context
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Compliance run history (extension point — not persisted by default)
    # ------------------------------------------------------------------


