import sys
import os

# Ensure backend and root directories are in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(root_dir, "backend")

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backend.main import app

@app.middleware("http")
async def fix_vercel_path(request, call_next):
    path = request.scope.get("path", "")
    for prefix in ["/api/index.py", "/api/index"]:
        if path.startswith(prefix):
            new_path = path[len(prefix):]
            if not new_path:
                new_path = "/"
            request.scope["path"] = new_path
            break
    return await call_next(request)
