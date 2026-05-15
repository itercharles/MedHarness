"""LocalDHFAdapter — wraps the dhf package to implement DHFAdapter for a local DHF directory."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from dhfkit.artifact_fetcher import GitHubArtifactFetcher, GitLabArtifactFetcher, JenkinsArtifactFetcher
from dhfkit.exceptions import ValidationError
from dhfkit.junit_parser import parse_junit_xml
from dhfkit.item_type import ItemType
from dhfkit.models.config import ProjectConfig
from dhfkit.models.item import Item
from dhfkit.repository.git import GitRepository
from dhfkit.repository.loader import ItemLoader
from dhfkit.repository.saver import ItemSaver
from dhfkit.result_store import ResultStore
from dhfkit.id_generator import get_next_id

_ITEM_LINK_FIELDS = (
    "derives_from", "implements", "mitigates", "satisfies",
    "guided_by", "informs", "design", "verifies", "validates",
    "mitigated_by",
    # CR and DEF built-in relationship fields
    "affected_items", "target_release", "found_in_release", "fixed_in_release",
)
_UID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*-\d+$")


class LocalDHFAdapter:
    """Implements DHFAdapter for a local filesystem DHF directory."""

    def __init__(self, dhf_root: Path, auto_commit: bool = False):
        self._dhf_root = Path(dhf_root)
        self._config = ProjectConfig.load(self._dhf_root / "config")
        items_dir = self._dhf_root / "items"
        self._git = GitRepository(self._dhf_root, auto_commit=auto_commit)
        self._loader = ItemLoader(items_dir, project_config=self._config)
        self._saver = ItemSaver(items_dir, git_repo=self._git, project_config=self._config)

        result_store_cfg = self._config.test_integration.get("result_store", {})
        self._result_store = ResultStore(self._dhf_root, result_store_cfg)

        # document_specifications lives in global config
        self._doc_specs = self._config.document_specifications

        # Lazy-fetch flag: set True once GitHub auto-fetch has been attempted this session
        self._results_fetched = False

        # Document index: stem → Path, built once at init to avoid per-call rglob scans
        self._doc_index: dict[str, Path] = {}
        self._rebuild_doc_index()

    def _resolve_template_dir(self) -> Path:
        """Resolve the Jinja2 template directory for spec generation.

        Only supports the flat documents/specs/ layout.
        Raises FileNotFoundError if .j2 templates are missing.
        """
        template_dir = self._dhf_root / "documents" / "specs"
        if template_dir.is_dir() and not any(template_dir.glob("*.j2")):
            raise FileNotFoundError(
                f"No .j2 templates found in {template_dir}. "
                "Add specification templates (e.g. requirements_specification.md.j2)."
            )
        return template_dir

    # ------------------------------------------------------------------
    # Item type metadata
    # ------------------------------------------------------------------

    def _item_type_dict(self, dt) -> dict:
        it = ItemType.from_code(dt.code)
        role = dt.role or (it.value.role if it else dt.code)
        parent_types = [r[1] for r in it.value.required_upstream] if it else []
        has_verification = (
            dt.has_verification if dt.has_verification is not None
            else (it.value.has_verification if it else False)
        )
        return {
            "name": dt.name or dt.code,
            "code": dt.code,
            "prefix": dt.prefix,
            "role": role,
            "parent_types": parent_types,
            "has_verification": bool(has_verification),
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
        """Add medharness domain fields (type, all_linked_uids) to an item dict."""
        d = item.model_dump(by_alias=True, exclude_none=True)
        d['all_linked_uids'] = item.all_linked_uids
        dt = self._config.get_doc_type_by_prefix(item.prefix)
        if dt:
            d['type'] = dt.code
        else:
            d['type'] = item.uid.split('-')[0]
        return d

    def get_item(self, uid: str) -> Optional[dict]:
        item = self._loader.load_by_uid(uid)
        if item is None:
            return None
        return self._enrich_item_dict(item)

    def list_items(self, doc_type: Optional[str] = None) -> List[dict]:
        items = self._loader.load_all()
        result = []
        for item in items:
            if doc_type:
                dt_cfg = self._config.get_doc_type(doc_type)
                prefix = dt_cfg.prefix if dt_cfg else f"{doc_type}-"
                if not item.uid.startswith(prefix):
                    continue
            result.append(self._enrich_item_dict(item))
        return result

    def _validate_item_links(self, data: dict) -> None:
        """Raise ValidationError if any relationship field references an unknown prefix.

        Checks all known link fields (derives_from, implements, mitigates, etc.)
        to ensure every UID value matches a known doc-type prefix. This guards
        against malformed LLM output being persisted silently.
        """
        known_prefixes = {dt.prefix for dt in self._config.doc_types}
        errors = []
        for field in _ITEM_LINK_FIELDS:
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
        if errors:
            raise ValidationError("Item link validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    def create_item(self, data: dict, author: str = "system", cr_id: Optional[str] = None) -> dict:
        # CR-006: ID is always auto-generated; any caller-supplied id is ignored
        data = {k: v for k, v in data.items() if k != 'id'}
        doc_type_code = data.get('type')
        if not doc_type_code:
            raise ValueError("Cannot auto-generate ID: document type not specified")
        dt_cfg = self._config.get_doc_type(doc_type_code)
        if not dt_cfg:
            raise ValueError(f"Unknown doc type: {doc_type_code}")
        all_items = self._loader.load_all()
        existing_ids = [i.uid for i in all_items if i.uid.startswith(dt_cfg.prefix)]
        data['id'] = get_next_id(dt_cfg.prefix, existing_ids)

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
        self._saver.save(item, author=author, cr_id=cr_id)
        return self._enrich_item_dict(item)

    def update_item(self, uid: str, data: dict, author: Optional[str] = None, cr_id: Optional[str] = None) -> Optional[dict]:
        from dhfkit.lifecycle import get_initial_state, is_stable

        existing = self._loader.load_by_uid(uid)
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
            if "status" not in data:
                initial = get_initial_state(self._config, doc_type_code)
                if initial:
                    data = {**data, "status": initial}
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
        self._validate_item_links(updated_data)
        item = Item.model_validate(updated_data)
        self._saver.save(item, author=author, cr_id=cr_id)
        return self._enrich_item_dict(item)

    def get_available_transitions(self, item_id: str) -> List[Dict]:
        """Return available lifecycle transitions for an item."""
        from dhfkit.lifecycle import get_available_transitions
        item = self.get_item(item_id)
        if item is None:
            return []
        return get_available_transitions(self._config, item)

    def execute_transition(
        self,
        item_id: str,
        to_state: str,
        performed_by: Optional[str] = None,
    ) -> Dict:
        """Execute a lifecycle state transition for an item."""
        from dhfkit.lifecycle import execute_transition
        return execute_transition(
            config=self._config,
            get_item_fn=self.get_item,
            update_item_fn=lambda uid, data: self.update_item(uid, data, author=performed_by),
            item_id=item_id,
            to_state=to_state,
            performed_by=performed_by,
        )

    def delete_item(self, uid: str, author: Optional[str] = None) -> bool:
        return self._saver.delete(uid, author=author)

    def validate_schema(self) -> dict:
        """Validate all YAML files; returns {'valid': bool, 'errors': [...]}."""
        errors = []
        try:
            items = self._loader.load_all()
        except ValidationError as e:
            errors.append(str(e))
        return {'valid': len(errors) == 0, 'errors': errors, 'item_count': len(self._loader.load_all()) if not errors else 0}

    def validate_traceability(self) -> dict:
        """Check required traceability, orphans, and coverage."""
        from dhfkit.traceability import check_traceability
        items = self._loader.load_all()
        _LINK_FIELDS = ("derives_from", "implements", "mitigates", "satisfies", "guided_by", "informs", "design", "verifies", "validates")
        item_dicts = [
            {
                "id": it.uid,
                "all_linked_uids": it.all_linked_uids,
                **{f: getattr(it, f) for f in _LINK_FIELDS if getattr(it, f, None)},
                **{k: v for k, v in it.model_extra.items() if v is not None},
            }
            for it in items
        ]
        return check_traceability(item_dicts, self._config)

    # ------------------------------------------------------------------
    # Document generation
    # ------------------------------------------------------------------

    def get_available_doc_types(self) -> List[str]:
        return list(self._doc_specs.keys())

    def generate_doc(self, doc_type_code: str) -> dict:
        from dhfkit.document_generation import DocumentGenerator
        template_dir = self._resolve_template_dir()
        gen = DocumentGenerator(self._loader, self._config, template_dir)
        content, output_path = gen.generate_markdown_spec(doc_type_code, self._doc_specs, self._dhf_root)
        version = "unknown"
        m = re.search(r'\|\s*\*\*Version\*\*\s*\|\s*([\d.]+)\s*\|', content)
        if m:
            version = m.group(1)
        self._rebuild_doc_index()
        return {"doc_type": doc_type_code, "output_path": str(output_path), "version": version}

    def export_pdf(self, doc_type_code: str) -> dict:
        spec_result = self.generate_doc(doc_type_code)
        from dhfkit.document_generation import DocumentGenerator
        template_dir = self._resolve_template_dir()
        gen = DocumentGenerator(self._loader, self._config, template_dir)
        pdf_path = gen.export_static_doc_to_pdf(doc_type_code, self._doc_specs, self._dhf_root)
        return {
            "doc_type": doc_type_code,
            "md_path": spec_result["output_path"],
            "pdf_path": str(pdf_path),
            "version": spec_result["version"],
        }

    # ------------------------------------------------------------------
    # Test results
    # ------------------------------------------------------------------

    def _ensure_results_loaded(self) -> None:
        """Auto-fetch from GitHub if local cache is absent and GITHUB_TOKEN is set.

        Called lazily by every read method so MedHarness never needs to know
        whether results come from a local file or the GitHub API — the DHF layer
        decides transparently.

        Only one attempt per adapter instance: if the fetch fails (no token,
        no matching run, network error) results remain empty for the session.
        Explicit ``pull_results_from_artifacts()`` resets the flag for a retry.
        """
        if self._results_fetched:
            return
        self._results_fetched = True

        # Local cache present — nothing to do
        if self._result_store._results_path.exists():
            return

        # No cache: try GitHub if a token is available
        import os
        if not os.environ.get("GITHUB_TOKEN"):
            return  # No token, degrade gracefully

        try:
            fetcher = GitHubArtifactFetcher.from_environment(self._dhf_root)
            # In CI, GITHUB_RUN_ID is the current run (may still be in progress,
            # so we can't rely on status=completed filter — pass run_id directly).
            run_id = os.environ.get("GITHUB_RUN_ID", "")
            fetch_result = fetcher.fetch(run_id=run_id)
            executions = []
            for r in fetch_result["results"]:
                if r.testing_status == "SKIP":
                    continue
                executions.append({
                    "tc_id": r.id,
                    "testing_status": r.testing_status,
                    "tester": "GitHub Actions",
                    "run_id": fetch_result["run_id"],
                    "run_url": fetch_result["run_url"],
                    "notes": r.error_message or "",
                    "links": r.links,
                    "title": r.title,
                    "reviewer": r.reviewer,
                    "review_date": r.review_date,
                    "review_status": r.review_status,
                })
            if executions:
                self._result_store.record_executions(executions)
        except Exception:
            pass  # Degrade gracefully — caller sees empty results

    def get_test_result(self, tc_id: str) -> Optional[dict]:
        self._ensure_results_loaded()
        return self._result_store.get(tc_id)

    def get_all_test_results(self, status_filter: Optional[str] = None) -> Dict[str, dict]:
        self._ensure_results_loaded()
        return self._result_store.get_all(status_filter)

    def record_test_result(
        self,
        tc_id: str,
        testing_status: str,
        tester: str = "",
        run_id: str = "",
        run_url: str = "",
        commit_sha: str = "",
        notes: str = "",
        links: Optional[List[str]] = None,
        title: str = "",
        reviewer: str = "",
        review_date: str = "",
        review_status: str = "",
    ) -> None:
        self._result_store.record_execution(
            tc_id=tc_id,
            testing_status=testing_status,
            tester=tester,
            run_id=run_id,
            run_url=run_url,
            commit_sha=commit_sha,
            notes=notes,
            links=links,
            title=title,
            reviewer=reviewer,
            review_date=review_date,
            review_status=review_status,
        )

    def get_test_result_items(self) -> List[dict]:
        self._ensure_results_loaded()
        items = self._result_store.as_tc_items()
        for item in items:
            item.setdefault('type', 'test_case')
        return items

    def import_results_from_file(
        self,
        xml_path,
        tester: str = "",
        run_id: str = "",
        run_url: str = "",
        commit_sha: str = "",
    ) -> dict:
        """Parse a JUnit XML file and record each non-SKIP result in the result store.

        Returns {"recorded": List[dict], "skipped": int} where each recorded dict
        contains tc_id, testing_status, and links.
        """
        from pathlib import Path as _Path
        results = parse_junit_xml(_Path(xml_path))
        recorded = []
        skipped = 0
        executions = []
        for r in results:
            if r.testing_status == "SKIP":
                skipped += 1
                continue
            executions.append({
                "tc_id": r.id,
                "testing_status": r.testing_status,
                "tester": tester,
                "run_id": run_id,
                "run_url": run_url,
                "commit_sha": commit_sha,
                "notes": r.error_message or "",
                "links": r.links,
                "title": r.title,
                "reviewer": r.reviewer,
                "review_date": r.review_date,
                "review_status": r.review_status,
            })
            recorded.append({
                "tc_id": r.id,
                "testing_status": r.testing_status,
                "links": r.links or [],
            })
        if executions:
            self._result_store.record_executions(executions)
        return {"recorded": recorded, "skipped": skipped}

    def pull_results_from_artifacts(
        self,
        run_id: str = "",
        commit_sha: str = "",
        provider: str = "github",
    ) -> dict:
        """Fetch test results from CI artifacts and cache locally.

        Delegates all CI API details to the appropriate fetcher class based on
        ``provider`` (``"github"``, ``"gitlab"``, or ``"jenkins"``).
        Non-SKIP results are written to the local ResultStore cache (git-ignored).

        Returns::

            {
                "recorded": List[{"tc_id", "testing_status", "links"}],
                "skipped":  int,
                "run_id":   str,
                "run_url":  str,
            }
        """
        # Force-refresh: reset flag so _ensure_results_loaded won't skip next time
        self._results_fetched = True

        if provider == "gitlab":
            fetcher = GitLabArtifactFetcher.from_environment(self._dhf_root)
        elif provider == "jenkins":
            fetcher = JenkinsArtifactFetcher.from_environment(self._dhf_root)
        else:
            fetcher = GitHubArtifactFetcher.from_environment(self._dhf_root)

        fetch_result = fetcher.fetch(run_id=run_id, commit_sha=commit_sha)

        actual_run_id = fetch_result["run_id"]
        run_url = fetch_result["run_url"]
        results = fetch_result["results"]

        recorded = []
        skipped = 0
        executions = []
        for r in results:
            if r.testing_status == "SKIP":
                skipped += 1
                continue
            executions.append({
                "tc_id": r.id,
                "testing_status": r.testing_status,
                "tester": "GitHub Actions",
                "run_id": actual_run_id,
                "run_url": run_url,
                "notes": r.error_message or "",
                "links": r.links,
                "title": r.title,
                "reviewer": r.reviewer,
                "review_date": r.review_date,
                "review_status": r.review_status,
            })
            recorded.append({
                "tc_id": r.id,
                "testing_status": r.testing_status,
                "links": r.links or [],
            })
        if executions:
            self._result_store.record_executions(executions)
        return {
            "recorded": recorded,
            "skipped": skipped,
            "run_id": actual_run_id,
            "run_url": run_url,
        }

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

    def list_documents(self) -> List[str]:
        """Return logical document IDs (filename stems) for all files under documents/."""
        return list(self._doc_index.keys())

    # ------------------------------------------------------------------
    # CR context
    # ------------------------------------------------------------------

    def get_implementation_context(self, cr_id: str) -> dict:
        """Return a structured context dict for a CR — items, traceability, spec."""
        cr = self.get_item(cr_id)
        items = self.list_items()
        trace = self.validate_traceability()
        coverage_summary = [
            {
                "parent": c["parent_type"],
                "child": c["child_type"],
                "covered": c["covered"],
                "total": c["total"],
            }
            for c in trace.get("coverage", [])
        ]
        spec_text = self.get_document(f"{cr_id}-Spec") or ""
        return {
            "cr": cr or {"id": cr_id, "found": False},
            "spec_text": spec_text,
            "item_count": len(items),
            "items": [
                {
                    "id": it["id"],
                    "type": it.get("type", ""),
                    "title": it.get("title", ""),
                    "status": it.get("status", ""),
                    "tracelinks": it.get("all_linked_uids", []),
                }
                for it in sorted(items, key=lambda x: x["id"])
            ],
            "traceability": {
                "valid": all(c["covered"] == c["total"] for c in coverage_summary),
                "coverage": coverage_summary,
                "orphan_count": len(trace.get("orphans", [])),
            },
        }

    # ------------------------------------------------------------------
    # Compliance run history (extension point — not persisted by default)
    # ------------------------------------------------------------------

    def record_compliance_run(
        self,
        group_id: str,
        report_dict: dict,
        commit_sha: str = "",
        trigger: str = "manual",
    ) -> None:
        """Record a compliance run. Override in subclasses to persist."""

    def get_compliance_runs(
        self,
        group_id: str,
        since_date: Optional[str] = None,
    ) -> List[Dict]:
        """Return compliance runs for a group. Override in subclasses to persist."""
        return []
