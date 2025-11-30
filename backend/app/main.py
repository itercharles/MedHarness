from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

# Import the new core library
from traceability import CompliantFlowCore

app = FastAPI(title="CompliantFlow API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core library
# Path structure: backend/app/main.py -> backend -> traceability -> repo_root
repo_root = Path(__file__).parent.parent.parent / "repo_root"
core = CompliantFlowCore(repo_root=repo_root, auto_commit=False)


# Request/Response models
class ItemCreate(BaseModel):
    """Model for creating an item."""
    id: str
    title: str
    content: str
    links: List[str] = []
    
    class Config:
        extra = "allow"


class ItemUpdate(BaseModel):
    """Model for updating an item."""
    title: Optional[str] = None
    content: Optional[str] = None
    links: Optional[List[str]] = None
    reviewer: Optional[str] = None
    review_date: Optional[str] = None
    
    class Config:
        extra = "allow"


@app.get("/")
def read_root():
    """Root endpoint."""
    return {"message": "CompliantFlow API", "version": "0.1.0"}


@app.get("/api/items")
def get_items():
    """Get all items."""
    try:
        items = core.get_all_items()
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/items/{uid}")
def get_item(uid: str):
    """Get a specific item by UID."""
    try:
        item = core.get_item(uid)
        if not item:
            raise HTTPException(status_code=404, detail=f"Item {uid} not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/items")
def create_item(item_data: ItemCreate):
    """Create a new item."""
    try:
        data = item_data.model_dump(exclude_none=True)
        item = core.create_item(data, author="API User")
        return item
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/items/{uid}")
def update_item(uid: str, item_data: ItemUpdate):
    """Update an existing item."""
    try:
        data = item_data.model_dump(exclude_none=True)
        item = core.update_item(uid, data, author="API User")
        if not item:
            raise HTTPException(status_code=404, detail=f"Item {uid} not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/items/{uid}")
def delete_item(uid: str):
    """Delete an item."""
    try:
        success = core.delete_item(uid, author="API User")
        if not success:
            raise HTTPException(status_code=404, detail=f"Item {uid} not found")
        return {"message": f"Item {uid} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph/stats")
def get_graph_stats():
    """Get graph statistics."""
    try:
        stats = core.get_graph_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph/validate")
def validate_graph():
    """Validate the graph."""
    try:
        validation = core.validate()
        return validation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config")
def get_config():
    """Get project configuration."""
    try:
        config = core.get_config()
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        return config
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/refresh")
def refresh():
    """Refresh items and rebuild graph."""
    try:
        core.refresh()
        return {"message": "Refreshed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis/matrix")
def get_traceability_matrix(source: str, target: str):
    """Get traceability matrix between two types."""
    try:
        matrix = core.get_traceability_matrix(source, target)
        return matrix
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
