"""YAML file loader for items."""

from pathlib import Path
import yaml
from typing import Any, Dict, List, Optional
from dhfkit.models.item import Item
from dhfkit.exceptions import ValidationError


# Fields that are always valid regardless of doc-type config.
# These are written exclusively by the saver — NOT user-defined business fields.
# All other allowed fields (lifecycle tracking, verification, etc.) are derived
# dynamically from the doc type's lifecycle config in _build_lifecycle_fields().
_SYSTEM_FIELDS = {
    # Written by the saver
    'id', 'doc_type', 'type', 'status', 'history', 'active', 'file_path', 'timestamp',
    # Explicit fields on the Item model — available for any doc type
    'reviewer', 'review_date',
}


class ItemLoader:
    """Load items from YAML files."""

    def __init__(self, specs_dir: Path, project_config=None):
        """
        Initialize loader.

        Args:
            specs_dir:      Path to the items directory.
            project_config: Optional ProjectConfig used for strict schema
                            validation.  When provided, every YAML file is
                            validated against the doc-type definition before
                            being parsed by Pydantic.
        """
        self.specs_dir = specs_dir
        self.project_config = project_config

    def load_all(self) -> List[Item]:
        """Load all items from the specifications directory."""
        items = []

        if not self.specs_dir.exists():
            print(f"Warning: Specifications directory {self.specs_dir} does not exist")
            return items

        for yaml_file in self.specs_dir.rglob("*.yaml"):
            item = self.load_file(yaml_file)
            if item:
                items.append(item)

        for yml_file in self.specs_dir.rglob("*.yml"):
            item = self.load_file(yml_file)
            if item:
                items.append(item)

        return items

    def load_file(self, file_path: Path) -> Optional[Item]:
        """
        Load a single item from a YAML file.

        Raises:
            ValidationError: If strict schema validation is enabled and the
                             file does not conform to its doc-type schema.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                return None

            # Strict schema validation (only when config is available)
            if self.project_config:
                self._validate_against_schema(data, file_path)

            item = Item.model_validate(data)
            item.file_path = str(file_path.absolute())  # type: ignore
            return item

        except ValidationError:
            raise  # propagate schema errors unchanged
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None

    def load_by_prefix(self, prefix: str) -> List[Item]:
        """Load items whose UID starts with *prefix*."""
        return [item for item in self.load_all() if item.uid.startswith(prefix)]

    def load_by_uid(self, uid: str) -> Optional[Item]:
        """Load a specific item by UID, or None if not found."""
        for item in self.load_all():
            if item.uid == uid:
                return item
        return None

    # ------------------------------------------------------------------
    # Schema validation helpers
    # ------------------------------------------------------------------

    def _validate_against_schema(self, data: Dict[str, Any], file_path: Path) -> None:
        """
        Validate raw YAML data against the doc-type definition in project_config.

        Checks:
          1. 'id' field is present.
          2. The doc type is recognised.
          3. No unknown fields are present.
          4. All required fields are present and non-empty.
          5. Field values conform to their format (select, multiselect, relationship).

        Raises:
            ValidationError: on the first violation found.
        """
        item_id = data.get('id')
        if not item_id:
            raise ValidationError(f"{file_path.name}: Missing required 'id' field")

        # Resolve doc-type code (first segment of the ID, e.g. "SYS" from "SYS-001")
        doc_type_code = item_id.split('-')[0]
        doc_type = self.project_config.get_doc_type(doc_type_code)
        if not doc_type:
            raise ValidationError(
                f"{file_path.name}: Unknown doc type '{doc_type_code}' for ID '{item_id}'"
            )

        # Build allowed / required field sets from the property definitions
        allowed_fields = set(_SYSTEM_FIELDS)
        allowed_fields |= self._build_lifecycle_fields(doc_type)
        required_fields: set = set()
        field_configs: Dict[str, Dict] = {}

        for prop in doc_type.properties:
            if isinstance(prop, dict):
                name = prop['name']
                allowed_fields.add(name)
                field_configs[name] = prop
                if prop.get('required'):
                    required_fields.add(name)
            elif isinstance(prop, str):
                allowed_fields.add(prop)
            else:
                # PropertyConfig object
                name = prop.name
                allowed_fields.add(name)

        # 3. Unknown fields
        for field in data:
            if field not in allowed_fields:
                raise ValidationError(
                    f"{file_path.name}: Unknown field '{field}' for doc type "
                    f"'{doc_type_code}'. Allowed: {sorted(allowed_fields)}"
                )

        # 4. Required fields
        for field in required_fields:
            if not data.get(field):
                raise ValidationError(
                    f"{file_path.name}: Required field '{field}' is missing or empty"
                )

        # 5. Field value formats
        for field_name, field_cfg in field_configs.items():
            if field_name in data and data[field_name] is not None:
                self._validate_field_value(data[field_name], field_cfg, file_path)

    def _build_lifecycle_fields(self, doc_type) -> set:
        """
        Derive the set of fields that the lifecycle engine and UI may write for
        this doc type, based on its lifecycle config.

        Covers:
          - {state}_by / {state}_date for every transition target state
          - review_by / review_date for the in_review state (reviewer kept as alias)
          - verification_status when the doc type has has_verification: true
          - field names referenced by field_not_empty criteria
        """
        fields: set = set()
        lifecycle = doc_type.lifecycle
        if lifecycle:
            for transition in lifecycle.get('transitions', []) or []:
                to_state = transition.get('to_state')
                if to_state:
                    if to_state == 'in_review':
                        fields.add('review_by')
                        fields.add('review_date')
                        fields.add('reviewer')  # legacy alias
                    else:
                        fields.add(f'{to_state}_by')
                        fields.add(f'{to_state}_date')

                for criterion in transition.get('criteria', []) or []:
                    check_type = criterion.get('check_type')
                    if check_type == 'field_not_empty':
                        field_name = criterion.get('field')
                        if field_name:
                            fields.add(field_name)

        if doc_type.has_verification:
            fields.add('verification_status')

        return fields

    def _validate_field_value(
        self, value: Any, field_config: Dict[str, Any], file_path: Path
    ) -> None:
        """Validate a single field value against its format configuration."""
        field_name = field_config['name']
        field_format = field_config.get('format', 'short_text')

        if field_format == 'select':
            options = field_config.get('options', [])
            if options and value not in options:
                raise ValidationError(
                    f"{file_path.name}: Invalid value '{value}' for field "
                    f"'{field_name}'. Must be one of: {options}"
                )

        elif field_format in ('multiselect', 'item_multiselect'):
            if not isinstance(value, list):
                raise ValidationError(
                    f"{file_path.name}: Field '{field_name}' must be a list, "
                    f"got {type(value).__name__}"
                )
            if field_format == 'multiselect':
                options = field_config.get('options', [])
                for v in value:
                    if options and v not in options:
                        raise ValidationError(
                            f"{file_path.name}: Invalid value '{v}' in field "
                            f"'{field_name}'. Must be one of: {options}"
                        )

        elif field_format == 'relationship':
            if not isinstance(value, (list, str)):
                raise ValidationError(
                    f"{file_path.name}: Field '{field_name}' must be a list or "
                    f"string, got {type(value).__name__}"
                )
