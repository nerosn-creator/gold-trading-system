import sys
import os
import posixpath
from urllib.parse import parse_qs, urlencode

# Ensure backend and root directories are in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(root_dir, "backend")

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backend.main import app


def _sanitize_vercel_api_path(raw_segment: str) -> str:
    """Normalize and restrict rewritten Vercel path strictly under /api/."""
    cleaned = raw_segment.replace("\\", "/").lstrip("/")
    normalized = posixpath.normpath("/" + cleaned)
    if ".." in normalized.split("/"):
        return "/api/"
    return "/api" + normalized


@app.middleware("http")
async def fix_vercel_path(request, call_next):
    # Try to get the path from our custom query parameter passed by Vercel rewrite
    query_string = request.scope.get("query_string", b"").decode("utf-8", errors="ignore")
    qs = parse_qs(query_string, keep_blank_values=True)

    if "__vercel_path" in qs and qs["__vercel_path"]:
        # Reconstruct the original path safely under /api/
        request.scope["path"] = _sanitize_vercel_api_path(qs["__vercel_path"][0])

        # Remove __vercel_path and re-encode remaining parameters safely
        filtered_qs = {k: v for k, v in qs.items() if k != "__vercel_path"}
        request.scope["query_string"] = urlencode(filtered_qs, doseq=True).encode("utf-8")
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
