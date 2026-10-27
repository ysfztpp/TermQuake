"""End-to-end checks of the built web app in a real browser.

Run against a served build:
    cd site && npm run build && npx vite preview --port 4173 --base /termquake/ &
    E2E_URL=http://localhost:4173/termquake/ pytest tests/e2e

Skipped unless E2E_URL is set, so the normal test run stays fast and offline.
Assertions use Playwright's `expect`, which retries until the UI has updated:
the app re-renders asynchronously, so reading the DOM right after an action is flaky.
"""

from __future__ import annotations

import os

import pytest

URL = os.environ.get("E2E_URL")
pytestmark = pytest.mark.skipif(not URL, reason="set E2E_URL to run browser tests")


@pytest.fixture(scope="module")
def pw():
    return pytest.importorskip("playwright.sync_api")


@pytest.fixture(scope="module")
def chromium(pw):
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def expect(pw):
    return pw.expect


@pytest.fixture
def app(chromium):
    ctx = chromium.new_context(locale="tr-TR", viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    page.errors = []
    page.on("console", lambda m: m.type == "error" and page.errors.append(m.text))
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    yield page
    ctx.close()


def test_loads_all_entries_without_errors(app, expect):
    app.goto(URL)
    expect(app.locator(".row").first).to_be_visible()
    count = app.locator(".results-count").inner_text()
    assert int(count.split()[0]) > 100
    assert app.errors == []


def test_search_without_turkish_keyboard(app, expect):
    app.goto(URL)
    app.fill("#q", "sargi")
    expect(app.locator(".row").first).to_contain_text("sargı bezi")


def test_show_mode_opens_and_closes(app, expect):
    app.goto(URL)
    app.fill("#q", "enkaz")
    expect(app.locator(".row").first).to_contain_text("enkaz")
    app.locator(".row-head").first.click()
    app.locator(".detail .button--primary").click()
    dialog = app.locator(".show")
    expect(dialog).to_be_visible()
    expect(dialog.locator(".show-main")).not_to_be_empty()
    app.keyboard.press("Escape")
    expect(dialog).to_have_count(0)


def test_deep_link_opens_entry(app, expect):
    app.goto(URL + "#/e/5")
    expect(app.locator("#entry-5")).to_contain_text("enkaz")


def test_works_offline_after_first_visit(app, expect):
    app.goto(URL)
    expect(app.locator(".row").first).to_be_visible()
    app.evaluate("navigator.serviceWorker.ready.then(() => true)")
    app.reload()  # now controlled by the service worker
    app.wait_for_function("navigator.serviceWorker.controller !== null")
    app.context.set_offline(True)
    app.reload()
    expect(app.locator(".row").first).to_be_visible()
    app.fill("#q", "deprem")
    expect(app.locator(".row").first).to_contain_text("deprem")
    expect(app.locator(".status")).to_be_visible()  # tells the user they're offline
    app.context.set_offline(False)
