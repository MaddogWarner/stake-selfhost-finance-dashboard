"""Check the built nginx over HTTPS; run against a disposable Compose stack."""

import subprocess
import sys
from email.parser import Parser

BASE_URL = "https://127.0.0.1:3443"
HEADERS = {
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; base-uri 'self'; form-action 'self'; "
        "frame-ancestors 'none'; object-src 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def check(path: str, status: int, *, head: bool = False) -> None:
    command = ["curl", "-skS", "--max-time", "15", "-D", "-", "-o", "/dev/null"]
    if head:
        command.append("-I")
    result = subprocess.run(command + [BASE_URL + path], check=True, capture_output=True, text=True)
    # curl -I and -D together print the headers twice; parse just the first block.
    block = result.stdout.split("\n\n", 1)[0]
    first, fields = block.split("\n", 1)
    actual_status = int(first.split()[1])
    assert actual_status == status, (path, actual_status, status)
    parsed = Parser().parsestr(fields)
    for name, expected in HEADERS.items():
        assert parsed.get_all(name) == [expected], (path, name, parsed.get_all(name))
    assert parsed.get("Strict-Transport-Security") is None, "HSTS must stay disabled"
    print(f"{'HEAD' if head else 'GET'} {path}: {status}, all five security headers present")


if __name__ == "__main__":
    if sys.argv[1:] == ["--backend-stopped"]:
        check("/api/auth/status", 502)
    else:
        # /api/health is currently absent; unknown SPA routes fall back to index.html.
        for route, status in [("/", 200), ("/api/health", 404), ("/some-missing-path", 200),
                              ("/api/some-missing-path", 404), ("/api/holdings", 401)]:
            check(route, status)
            # FastAPI's GET routes don't automatically accept HEAD.
            check(route, 405 if route == "/api/holdings" else status, head=True)
