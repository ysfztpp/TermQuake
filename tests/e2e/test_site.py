"""End-to-end checks of the built web app in a real browser.

Run against a served build:
    cd site && npm run build && npx vite preview --port 4173 --base /termquake/ &
    E2E_URL=http://localhost:4173/termquake/ pytest tests/e2e

Skipped unless E2E_URL is set, so the normal test run stays fast and offline.
"""

from __future__ import annotations

import os

import pytest

URL = os.environ.get("E2E_URL")
pytestmark = pytest.mark.skipif(not URL, reason="set E2E_URL to run browser tests")


@pytest.fixture(scope="module")
def chromium():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def app(chromium):
    ctx = chromium.new_context(locale="tr-TR", viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    page.errors = []
    page.on("console", lambda m: m.type == "error" and page.errors.append(m.text))
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    yield page
    ctx.close()


def test_loads_all_entries_without_errors(app):
    app.goto(URL)
    app.wait_for_selector(".row")
    count = app.locator(".results-count").inner_text()
    assert int(count.split()[0]) > 100
    assert app.errors == []


def test_search_without_turkish_keyboard(app):
    app.goto(URL)
    app.fill("#q", "sargi")
    first = app.locator(".row").first
    assert "sargı bezi" in first.inner_text()


def test_show_mode_opens_and_closes(app):
    app.goto(URL)
    app.fill("#q", "enkaz")
    app.locator(".row-head").first.click()
    app.locator(".detail .button--primary").click()
    dialog = app.locator(".show")
    assert dialog.is_visible()
    assert dialog.locator(".show-main").inner_text().strip()
    app.keyboard.press("Escape")
    assert app.locator(".show").count() == 0


def test_deep_link_opens_entry(app):
    app.goto(URL + "#/e/5")
    app.wait_for_selector("#entry-5")
    assert "enkaz" in app.locator("#entry-5").inner_text()


def test_works_offline_after_first_visit(app):
    app.goto(URL)
    app.wait_for_selector(".row")
    app.evaluate("navigator.serviceWorker.ready")
    app.reload()  # now controlled by the service worker
    app.wait_for_function("navigator.serviceWorker.controller !== null")
    app.context.set_offline(True)
    app.reload()
    app.wait_for_selector(".row")
    app.fill("#q", "deprem")
    assert "deprem" in app.locator(".row").first.inner_text()
    assert app.locator(".status").inner_text().strip()  # tells the user they're offline
    app.context.set_offline(False)
