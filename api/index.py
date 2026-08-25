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
    
    # Try to get the original URL from Vercel headers if available
    # Vercel sends x-matched-path or x-invoke-path sometimes, but let's just fix the prefix
    for prefix in ["/api/index.py", "/api/index"]:
        if path.startswith(prefix):
            new_path = path[len(prefix):]
            if not new_path:
                new_path = "/"
            
            # If the original path was /api/gold/summary, Vercel might pass /api/index.py/gold/summary
            # We want the final path to be /api/gold/summary because that's what main.py expects.
            if new_path != "/" and not new_path.startswith("/api"):
                new_path = "/api" + new_path
                
            request.scope["path"] = new_path
            break
            
    return await call_next(request)
