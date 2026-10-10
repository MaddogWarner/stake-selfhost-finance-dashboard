"""Headless smoke test with real auth/API and synthetic market data in Redis.

Run from docker/ against a fresh, disposable Compose project only. Requires
Playwright's Python package and Chromium; never uses a personal browser profile.
"""

import json
import re
import secrets
import subprocess

from playwright.sync_api import expect, sync_playwright

BASE_URL = "https://127.0.0.1:3443"
TICKER = "CSPTEST"


def seed_cache(key: str, value: object) -> None:
    subprocess.run(
        ["docker", "compose", "exec", "-T", "redis", "redis-cli", "-x", "SETEX", key, "600"],
        input=json.dumps(value), text=True, check=True, capture_output=True,
    )


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(ignore_https_errors=True)
    # Refuse to alter an existing dashboard. This harness is for a fresh CI stack.
    response = context.request.get(BASE_URL + "/api/auth/status")
    assert response.ok and response.json() == {"status": "setup_required"}
    seed_cache(f"price:{TICKER}", {
        "price": 102, "currency": "AUD", "day_change": 2, "day_change_pct": 2,
        "history": [{"date": "2026-10-01", "close": 100},
                    {"date": "2026-10-02", "close": 101},
                    {"date": "2026-10-03", "close": 102}],
        "week52_high": 110, "week52_low": 90, "moving_average_50": 99,
    })
    seed_cache(f"fundamentals:{TICKER}", {"name": "CSP smoke fixture", "sector": "Testing"})
    seed_cache(f"news:{TICKER}", [])
    page = context.new_page()
    console_violations = []
    errors = []
    page.on("console", lambda message: console_violations.append(message.text)
            if "content security policy" in message.text.lower()
            or "content-security-policy" in message.text.lower() else None)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.add_init_script("""window.cspViolations = [];
        document.addEventListener('securitypolicyviolation', event => {
            window.cspViolations.push({directive: event.effectiveDirective,
                blocked: event.blockedURI});
        });""")
    password = secrets.token_urlsafe(24) + "1!"
    page.goto(BASE_URL)
    page.get_by_label("Password", exact=True).fill(password)
    page.get_by_label("Confirm password", exact=True).fill(password)
    page.get_by_role("button", name="Complete setup").click()
    expect(page.get_by_role("button", name="Log out")).to_be_visible()
    page.get_by_role("button", name="Log out").click()
    expect(page.get_by_role("button", name="Log in")).to_be_visible()
    page.get_by_label("Password", exact=True).fill(password)
    with page.expect_response(lambda response: response.url.endswith("/api/auth/login")) as login:
        page.get_by_role("button", name="Log in").click()
    assert login.value.status == 200
    expect(page.get_by_role("button", name="Log out")).to_be_visible()
    created = context.request.post(BASE_URL + "/api/holdings", data={
        "ticker": TICKER, "exchange": "ASX", "quantity": 10, "avg_cost": 95,
    })
    assert created.status == 201
    with page.expect_response(lambda response: "/api/holdings" in response.url) as holdings:
        page.reload()
    assert holdings.value.ok
    expect(page.get_by_role("heading", name=TICKER, exact=True)).to_be_visible()
    expect(page.get_by_text(re.compile(r"Holding: 10(?:\.0+)? shares @ 95(?:\.0+)? avg"))).to_be_visible()
    line = page.locator(".recharts-line-curve")
    expect(line).to_be_visible()
    assert line.get_attribute("d"), "Chart must contain a populated line"
    page.locator(".recharts-wrapper").hover(position={"x": 80, "y": 30})
    expect(page.locator(".recharts-tooltip-wrapper")).to_be_visible()
    page.get_by_role("button", name="Manage", exact=True).click()
    expect(page.get_by_role("heading", name="Manage assets")).to_be_visible()
    # Let queued securitypolicyviolation events and chart updates settle.
    page.wait_for_timeout(500)
    violations = page.evaluate("window.cspViolations")
    assert not violations and not console_violations, (violations, console_violations)
    assert not errors, errors
    print("PASS: setup, logout, login, real holdings API, populated chart, tooltip and Manage; zero CSP violations")
    browser.close()
