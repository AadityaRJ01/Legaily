import sys
from pathlib import Path

# Ensure server root is on path (project_paths, ingest scripts, etc.)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from apps.main import app

if __name__ == "__main__":
    import uvicorn
    from apps.config.settings import get_settings

    s = get_settings()
    uvicorn.run(app, host=s.host, port=s.port)