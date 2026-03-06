"""LocalDHFAdapter — wraps the dhf package to implement DHFAdapter for a local DHF directory."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from utils.exceptions import ValidationError
from utils.models.config import ProjectConfig
from utils.models.item import Item
from utils.repository.git import GitRepository
from utils.repository.loader import ItemLoader
from utils.repository.saver import ItemSaver
from utils.result_store import ResultStore
from helpers.id_generator import get_next_id


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

    # ------------------------------------------------------------------
    # ProjectConfig
    # ------------------------------------------------------------------

    def get_project_config(self) -> ProjectConfig:
        return self._config

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------

    def get_item(self, uid: str) -> Optional[dict]:
        item = self._loader.load_by_uid(uid)
        if item is None:
            return None
        return item.model_dump(by_alias=True, exclude_none=True)

    def list_items(self, doc_type: Optional[str] = None) -> List[dict]:
        items = self._loader.load_all()
        result = []
        for item in items:
            if doc_type:
                dt_cfg = self._config.get_doc_type(doc_type)
                prefix = dt_cfg.prefix if dt_cfg else f"{doc_type}-"
                if not item.uid.startswith(prefix):
                    continue
            result.append(item.model_dump(by_alias=True, exclude_none=True))
        return result

    def create_item(self, data: dict, author: str = "system", cr_id: Optional[str] = None) -> dict:
        if 'id' not in data or not data['id']:
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

        # Validate against doc-type schema before saving
        if self._loader.project_config:
            from pathlib import Path as _Path
            self._loader._validate_against_schema(data, _Path(f"{data['id']}.yaml"))

        item = Item.model_validate(data)
        self._saver.save(item, author=author, cr_id=cr_id)
        return item.model_dump(by_alias=True, exclude_none=True)

    def update_item(self, uid: str, data: dict, author: Optional[str] = None, cr_id: Optional[str] = None) -> Optional[dict]:
        existing = self._loader.load_by_uid(uid)
        if not existing:
            return None
        updated_data = existing.model_dump(exclude_unset=True)
        # Strip computed/non-model keys that should not be persisted
        data = {k: v for k, v in data.items() if k != 'all_linked_uids'}
        updated_data.update(data)
        # Remove keys explicitly set to None (signal to clear the field)
        updated_data = {k: v for k, v in updated_data.items() if v is not None}
        item = Item.model_validate(updated_data)
        self._saver.save(item, author=author, cr_id=cr_id)
        return item.model_dump(by_alias=True, exclude_none=True)

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

    # ------------------------------------------------------------------
    # Document generation
    # ------------------------------------------------------------------

    def get_available_doc_types(self) -> List[str]:
        return list(self._doc_specs.keys())

    def generate_doc(self, doc_type_code: str) -> dict:
        from utils.document_generation import DocumentGenerator
        template_dir = self._dhf_root / "documents" / "specifications" / "templates"
        gen = DocumentGenerator(self._loader, self._config, template_dir)
        content, output_path = gen.generate_markdown_spec(doc_type_code, self._doc_specs, self._dhf_root)
        version = "unknown"
        m = re.search(r'\|\s*\*\*Version\*\*\s*\|\s*([\d.]+)\s*\|', content)
        if m:
            version = m.group(1)
        return {"doc_type": doc_type_code, "output_path": str(output_path), "version": version}

    def export_pdf(self, doc_type_code: str) -> dict:
        spec_result = self.generate_doc(doc_type_code)
        from utils.document_generation import DocumentGenerator
        template_dir = self._dhf_root / "documents" / "specifications" / "templates"
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

    def get_test_result(self, tc_id: str) -> Optional[dict]:
        return self._result_store.get(tc_id)

    def get_all_test_results(self, status_filter: Optional[str] = None) -> Dict[str, dict]:
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
        return self._result_store.as_tc_items()
