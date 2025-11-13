from __future__ import annotations

import os
from functools import wraps
from pathlib import Path
from typing import List, Tuple
import subprocess

from flask import Flask, Response, redirect, render_template_string, request, url_for


LOG_DIR = Path(os.getenv("LOG_DIR", "/logs"))
LOG_USER = os.getenv("LOG_USER", "admin")
LOG_PASSWORD = os.getenv("LOG_PASSWORD", "admin")
MAX_LINES = int(os.getenv("LOG_MAX_LINES", "200"))

LOG_FILES: List[Tuple[str, str]] = [
    ("WAF Access Log", "access.log"),
    ("WAF Error Log", "error.log"),
]

app = Flask(__name__)


def tail(path: Path, max_lines: int) -> str:
    try:
        result = subprocess.run(
            ["tail", "-n", str(max_lines), str(path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        output = exc.stderr.decode("utf-8", errors="ignore").strip()
        return output or f"[Fehler beim Lesen: {exc}]"
    except FileNotFoundError:
        return "[Datei nicht gefunden]"
    except Exception as exc:  # pragma: no cover
        return f"[Fehler beim Lesen: {exc}]"

    text = result.stdout.decode("utf-8", errors="ignore").strip()
    return text or "[Keine Einträge]"


def check_auth(auth) -> bool:
    return bool(auth and auth.username == LOG_USER and auth.password == LOG_PASSWORD)


def authenticate() -> Response:
    return Response(
        "Authentifizierung benötigt",
        401,
        {"WWW-Authenticate": 'Basic realm="Log Viewer"'},
    )


def requires_auth(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        auth = request.authorization
        if not check_auth(auth):
            return authenticate()
        return view_func(*args, **kwargs)

    return wrapped


@app.get("/")
def root() -> Response:
    return redirect(url_for("show_logs"))


@app.get("/logs")
@requires_auth
def show_logs() -> str:
    sections = []
    for title, filename in LOG_FILES:
        content = tail(LOG_DIR / filename, MAX_LINES)
        sections.append((title, filename, content))

    return render_template_string(
        TEMPLATE,
        sections=sections,
        max_lines=MAX_LINES,
        user=LOG_USER,
    )


TEMPLATE = """
<!doctype html>
<html lang=\"de\">
<head>
  <meta charset=\"utf-8\" />
  <title>miFOS Log Viewer</title>
  <style>
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
    header { padding: 1.5rem 2rem; background: linear-gradient(135deg, #6366f1, #a855f7); }
    h1 { margin: 0 0 0.5rem; font-size: 1.8rem; }
    .subtitle { margin: 0; opacity: 0.85; }
    main { padding: 1.5rem; display: grid; gap: 1.5rem; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
    section { background: rgba(15, 23, 42, 0.7); border-radius: 0.8rem; border: 1px solid rgba(148, 163, 184, 0.25); box-shadow: 0 15px 45px rgba(15, 23, 42, 0.45); }
    section h2 { margin: 0; padding: 1rem 1.25rem; font-size: 1rem; letter-spacing: 0.04em; border-bottom: 1px solid rgba(148, 163, 184, 0.25); text-transform: uppercase; color: #a5b4fc; }
    pre { margin: 0; padding: 1rem 1.25rem; max-height: 360px; overflow-y: auto; font-size: 0.85rem; line-height: 1.3; background: transparent; color: #e2e8f0; }
    .filename { display: block; font-size: 0.75rem; letter-spacing: 0.08em; opacity: 0.6; margin-top: 0.4rem; }
  </style>
</head>
<body>
  <header>
    <h1>miFOS Log Viewer</h1>
    <p class=\"subtitle\">Letzte {{ max_lines }} Zeilen · Benutzer {{ user }}</p>
  </header>
  <main>
    {% for title, filename, content in sections %}
    <section>
      <h2>{{ title }} <span class=\"filename\">{{ filename }}</span></h2>
      <pre>{{ content }}</pre>
    </section>
    {% endfor %}
  </main>
</body>
</html>
"""


if __name__ == "__main__":  # pragma: no cover
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
