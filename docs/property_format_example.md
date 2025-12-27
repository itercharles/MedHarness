# Property Format System - Example Configuration

This example shows how to use the new Property Format System with explicit property definitions.

## Example: Enhanced SYS Document Type

```yaml
doc_types:
  - code: SYS
    name: "System Requirement"
    prefix: "SYS-"
    directory: "02_req_sys"
    
    properties:
      - id
      - title
      
      - name: content
        format: long_text
        label: "Requirement Description"
        required: true
        height: 200
        placeholder: "Describe the system requirement in detail..."
        help: "Provide a clear, testable requirement statement"
      
      - name: rationale
        format: markdown
        label: "Rationale & Background"
        height: 250
        placeholder: "Use **markdown** for formatting..."
        help: "Explain the reasoning behind this requirement"
      
      - name: reference_url
        format: url
        label: "Reference Documentation"
        placeholder: "https://..."
        help: "Link to external specification or standard"
      
      - name: category
        format: select
        label: "Category"
        required: true
        options:
          - Functional
          - Performance
          - Security
          - Usability
          - Reliability
        default: Functional
        help: "Select the requirement category"
      
      - name: priority
        format: select
        label: "Priority"
        options:
          - Low
          - Medium
          - High
          - Critical
        default: Medium
      
      - name: complexity
        format: slider
        label: "Implementation Complexity"
        min_value: 1
        max_value: 10
        step: 1
        default: 5
        help: "Estimate implementation complexity (1=simple, 10=very complex)"
      
      - name: critical_safety
        format: checkbox
        label: "Safety-Critical Requirement"
        default: false
        help: "Check if this requirement is safety-critical"
      
      - name: derives_from
        format: item_multiselect
        label: "Derives From"
        target_types: [CRS]
        help: "Select parent customer requirements"
      
      - name: verification_method
        format: multiselect
        label: "Verification Methods"
        options:
          - Test
          - Inspection
          - Analysis
          - Demonstration
        help: "Select applicable verification methods"
    
    lifecycle:
      states:
        - {id: draft, label: "Draft", is_initial: true}
        - {id: under_review, label: "Under Review"}
        - {id: approved, label: "Approved", is_stable: true}
      transitions:
        - {from: draft, to: under_review, label: "Submit for Review"}
        - {from: under_review, to: approved, label: "Approve"}
        - {from: under_review, to: draft, label: "Reject"}
```

## Benefits Demonstrated

1. **Explicit Configuration**: No guessing widget types from field names
2. **Rich UI**: Markdown editor with preview, sliders, URL validation
3. **Better UX**: Labels, placeholders, help text for every field
4. **Type Safety**: Pydantic validates the configuration
5. **Backward Compatible**: Mix string and PropertyConfig in same doc type

## Supported Formats

- `short_text` - Single-line text input
- `long_text` - Multi-line textarea
- `markdown` - Markdown editor with live preview
- `url` - URL input with validation
- `select` - Dropdown selection
- `multiselect` - Multiple selection
- `radio` - Radio button group
- `checkbox` - Single checkbox
- `toggle` - Toggle switch
- `number` - Numeric input
- `slider` - Slider with min/max/step
- `date` - Date picker
- `datetime` - Date and time picker
- `item_reference` - Reference to single item
- `item_multiselect` - Reference to multiple items
- `file_upload` - File attachment
