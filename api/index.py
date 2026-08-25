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
    # Try to get the path from our custom query parameter passed by Vercel rewrite
    query_string = request.scope.get("query_string", b"").decode("utf-8")
    from urllib.parse import parse_qs
    qs = parse_qs(query_string)
    
    if "__vercel_path" in qs:
        # Reconstruct the original path
        original_path = "/api/" + qs["__vercel_path"][0]
        request.scope["path"] = original_path
        
        # Remove __vercel_path from query_string so it doesn't mess with endpoints
        new_qs = "&".join([f"{k}={v[0]}" for k, v in qs.items() if k != "__vercel_path"])
        request.scope["query_string"] = new_qs.encode("utf-8")
    else:
        # Fallback to the original logic
        invoke_path = request.headers.get("x-invoke-path")
        if invoke_path:
            request.scope["path"] = invoke_path
        else:
            path = request.scope.get("path", "")
            for prefix in ["/api/index.py", "/api/index"]:
                if path.startswith(prefix):
                    new_path = path[len(prefix):]
                    if not new_path:
                        new_path = "/"
                    request.scope["path"] = new_path
                    break
                    
    return await call_next(request)
