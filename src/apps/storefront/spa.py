"""Serve the built Vue storefront SPA.

The SPA is built by Vite into ``apps/storefront/static/storefront-spa`` (see
``src/frontend``). Django serves the built ``index.html`` for the interactive
storefront routes while assets are served by the static files machinery. Until
the frontend is built, a short instruction page is returned instead of a 500.
"""

from pathlib import Path

from django.conf import settings
from django.http import HttpResponse

_UNBUILT_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>pyStore storefront not built</title></head>
<body style="font-family: system-ui, sans-serif; max-width: 40rem; margin: 4rem auto;">
  <h1>Storefront SPA not built</h1>
  <p>The Vue storefront has not been built yet. From the repository root run:</p>
  <pre>cd src/frontend
npm install
npm run build</pre>
  <p>Then reload this page. For live development use <code>npm run dev</code>.</p>
</body>
</html>
"""


def spa_dist_dir() -> Path:
    return Path(settings.STOREFRONT_SPA_DIR)


def spa_index(request, **kwargs) -> HttpResponse:
    index = spa_dist_dir() / "index.html"
    if not index.exists():
        return HttpResponse(_UNBUILT_HTML, status=503, content_type="text/html")
    return HttpResponse(index.read_text(encoding="utf-8"), content_type="text/html")
