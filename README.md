# CompliantFlow

CompliantFlow is a Docs-as-Code Application Lifecycle Management (ALM) platform for Medical Devices.

## Project Structure

- `repo_root/`: Contains the project data (Requirements, Tests, Config). This is the "Single Source of Truth".
- `backend/`: Python FastAPI backend service.
- `frontend/`: React + Vite frontend application.

## How to Run

### Prerequisites
- Python 3.11+
- Node.js 18+

### 1. Start the Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.
API Docs: `http://localhost:8000/docs`

### 2. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```
The UI will be available at `http://localhost:5173`.

## How to Configure

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
