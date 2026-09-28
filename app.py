"""
Legacy standalone entrypoint kept for compatibility.
The canonical server is backend.main:app.
"""

from backend.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run("backend.main:app", host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8080")), reload=False)
