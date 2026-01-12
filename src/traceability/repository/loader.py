"""YAML file loader for items."""

from pathlib import Path
import yaml
from typing import List, Optional, Dict, Any
from ..models.item import Item
from ..exceptions import ValidationError


class ItemLoader:
    """Load items from YAML files."""
    
    def __init__(self, specs_dir: Path, project_config=None):
        """
        Initialize loader.
        
        Args:
            specs_dir: Path to specifications directory
            project_config: Optional ProjectConfig for schema validation
        """
        self.specs_dir = specs_dir
        self.project_config = project_config
    
    def load_all(self) -> List[Item]:
        """
        Load all items from specifications directory.
        
        Returns:
            List of loaded items
        """
        items = []
        
        if not self.specs_dir.exists():
            print(f"Warning: Specifications directory {self.specs_dir} does not exist")
            return items
        
        for yaml_file in self.specs_dir.rglob("*.yaml"):
            item = self.load_file(yaml_file)
            if item:
                items.append(item)
        
        # Also check for .yml extension
        for yml_file in self.specs_dir.rglob("*.yml"):
            item = self.load_file(yml_file)
            if item:
                items.append(item)
        
        return items
    
    def load_file(self, file_path: Path) -> Optional[Item]:
        """
        Load a single item from a YAML file.
        
        Args:
            file_path: Path to YAML file
            
        Returns:
            Loaded item or None if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                return None
            
            # Strict schema validation if config provided
            if self.project_config:
                self.validate_against_schema(data, file_path)
            
            # Pydantic v2 validation
            # The model will handle 'id' -> 'uid' and 'content' -> 'text' aliases
            item = Item.model_validate(data)
            
            # Add file_path as an extra field (model allows extra fields)
            # Store as string for JSON serialization
            item.file_path = str(file_path.absolute())  # type: ignore
            
            return item
            
        except ValidationError:
            # Re-raise validation errors (don't catch them)
            raise
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None
    
    def load_by_prefix(self, prefix: str) -> List[Item]:
        """
        Load items with a specific prefix.
        
        Args:
            prefix: Item prefix (e.g., 'SYS-')
            
        Returns:
            List of items with matching prefix
        """
        all_items = self.load_all()
        return [item for item in all_items if item.uid.startswith(prefix)]
    
    def load_by_uid(self, uid: str) -> Optional[Item]:
        """
        Load a specific item by UID.
        
        Args:
            uid: Item UID
            
        Returns:
            Item or None if not found
        """
        all_items = self.load_all()
        for item in all_items:
            if item.uid == uid:
                return item
        return None
    
    def validate_against_schema(
        self,
        data: Dict[str, Any],
        file_path: Path
    ) -> None:
        """
        Validate item data against project config schema.
        
        Args:
            data: Item data from YAML file
            file_path: Path to file being validated
            
        Raises:
            ValidationError: If validation fails
        """
        # 1. Extract doc type from ID
        item_id = data.get('id')
        if not item_id:
            raise ValidationError(f"{file_path.name}: Missing 'id' field")
        
        # Handle compound prefixes (e.g., TC-SYS-001 -> TC-SYS)
        doc_type_code = item_id.split('-')[0]
        
        # 2. Find doc type config
        doc_type = self.project_config.get_doc_type(doc_type_code)
        if not doc_type:
            raise ValidationError(
                f"{file_path.name}: Unknown doc type '{doc_type_code}' for ID '{item_id}'"
            )
        
        # 3. Build allowed and required fields from config
        allowed_fields = {'id', 'status', 'file_path', 'active', 'history'}  # System fields
        required_fields = set()
        field_configs = {}  # Store field configs for validation
        
        for prop in doc_type.properties:
            if isinstance(prop, dict):
                field_name = prop['name']
                allowed_fields.add(field_name)
                field_configs[field_name] = prop
                if prop.get('required'):
                    required_fields.add(field_name)
            else:
                # Simple string property name
                allowed_fields.add(prop)
        
        # Also allow relationship fields from Item model
        allowed_fields.update([
            'derives_from', 'implements', 'guided_by', 'informs',
            'design', 'mitigated_by', 'mitigates', 'satisfies',
            'verifies', 'validates', 'title', 'reviewer', 'review_date',
            'verification_status', 'approved_by', 'approved_date',
            'retired_by', 'retired_date', 'manual_verifications'
        ])
        
        # 4. Check for unknown fields
        for field in data.keys():
            if field not in allowed_fields:
                raise ValidationError(
                    f"{file_path.name}: Unknown field '{field}' for doc type '{doc_type_code}'. "
                    f"Allowed fields: {sorted(allowed_fields)}"
                )
        
        # 5. Check required fields
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == '':
                raise ValidationError(
                    f"{file_path.name}: Required field '{field}' is missing or empty"
                )
        
        # 6. Validate field types and values
        for field_name, field_config in field_configs.items():
            if field_name in data and data[field_name] is not None:
                self._validate_field_value(data[field_name], field_config, file_path)
    
    def _validate_field_value(
        self,
        value: Any,
        field_config: Dict[str, Any],
        file_path: Path
    ) -> None:
        """
        Validate a field value against its configuration.
        
        Args:
            value: Field value to validate
            field_config: Field configuration from project config
            file_path: Path to file being validated
            
        Raises:
            ValidationError: If validation fails
        """
        field_name = field_config['name']
        field_format = field_config.get('format', 'short_text')
        
        # Validate select fields
        if field_format == 'select':
            options = field_config.get('options', [])
            if value not in options:
                raise ValidationError(
                    f"{file_path.name}: Invalid value '{value}' for field '{field_name}'. "
                    f"Must be one of: {options}"
                )
        
        # Validate multiselect fields
        elif field_format in ['multiselect', 'item_multiselect']:
            if not isinstance(value, list):
                raise ValidationError(
                    f"{file_path.name}: Field '{field_name}' must be a list, got {type(value).__name__}"
                )
            
            # For regular multiselect, validate against options
            if field_format == 'multiselect':
                options = field_config.get('options', [])
                for item in value:
                    if item not in options:
                        raise ValidationError(
                            f"{file_path.name}: Invalid value '{item}' in field '{field_name}'. "
                            f"Must be one of: {options}"
                        )
        
        # Validate relationship fields
        elif field_format == 'relationship':
            if not isinstance(value, (list, str)):
                raise ValidationError(
                    f"{file_path.name}: Field '{field_name}' must be a list or string, "
                    f"got {type(value).__name__}"
                )
