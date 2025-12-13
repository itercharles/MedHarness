# CompliantFlow

CompliantFlow is a Docs-as-Code Application Lifecycle Management (ALM) platform for Medical Devices.

## Project Structure

- `repo_root/`: Contains the project data (Requirements, Tests, Config). This is the "Single Source of Truth".
- `backend/`: Python backend containing the core logic and Streamlit debug application.

## How to Run

### Prerequisites
- Python 3.11+

### Start the Traceability Debugger (Streamlit)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run debug_app.py
```
The app will be available at `http://localhost:8501`.

The project logic is defined in `repo_root/config/project_config.yaml`.

### Document Types
Define new document types (e.g., Risk Analysis) in `doc_types`:

```yaml
doc_types:
  - code: RISK
    name: "Risk Analysis"
    prefix: "RISK-"
    level: 3
```

### Policies
Define compliance policies in `policies`:

```yaml
policies:
  require_test_coverage: ["SRS", "RISK"]
```

## Usage

1.  **Dashboard**: View project health and compliance violations.
2.  **Traceability**: View the link between Requirements (SRS) and Tests (VER).
3.  **Stubs**: Register external documents (e.g., PDF plans) to track their existence.
