"""End-to-end checks of the built web app in a real browser.

Run against a served build:
    cd site && npm run build && npx vite preview --port 4173 --base /TermQuake/ &
    E2E_URL=http://localhost:4173/TermQuake/ pytest tests/e2e

Skipped unless E2E_URL is set, so the normal test run stays fast and offline.
Assertions use Playwright's `expect`, which retries until the UI has updated:
the app re-renders asynchronously, so reading the DOM right after an action is flaky.
"""

from __future__ import annotations

import os
import re

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
    # Focus moves into the dialog (keyboard and screen-reader users land on Close).
    expect(dialog.locator(".icon-button")).to_be_focused()
    app.keyboard.press("Tab")  # focus stays trapped inside the dialog
    assert app.evaluate("document.querySelector('.show').contains(document.activeElement)")
    app.keyboard.press("Escape")
    expect(dialog).to_have_count(0)
    # Focus returns to the button that opened it.
    expect(app.locator(".detail .button--primary")).to_be_focused()


def test_deep_link_opens_entry(app, expect):
    app.goto(URL + "#/e/5")
    expect(app.locator("#entry-5")).to_contain_text("enkaz")


def test_long_list_renders_in_batches(app, expect):
    app.goto(URL)
    expect(app.locator(".row").first).to_be_visible()
    assert app.locator(".row").count() == 60  # not all 523 at once
    expect(app.locator(".results-count")).to_contain_text("523")
    app.locator(".more").scroll_into_view_if_needed()  # scrolling near the end loads more
    expect(app.locator(".row")).to_have_count(120)


def test_interface_language_menu(app, expect):
    app.goto(URL)
    expect(app.locator(".ui-lang")).to_contain_text("TR")
    app.select_option(".ui-lang select", "en")
    expect(app.locator(".ui-lang")).to_contain_text("EN")
    expect(app.locator("#q")).to_have_attribute("placeholder", re.compile("Type in"))


def test_touch_targets_are_large_enough(app, expect):
    """Everything tappable in the header and filters is at least 40 px tall (phone)."""
    app.goto(URL)
    expect(app.locator(".row").first).to_be_visible()
    small = app.evaluate(
        """() => [...document.querySelectorAll('.top button, .top select, .ui-lang, .finder button, .finder input')]
              .filter(el => el.closest('.ui-lang') === null || el.classList.contains('ui-lang'))
              .map(el => [el.className || el.tagName, Math.round(el.getBoundingClientRect().height)])
              .filter(([, h]) => h < 40)"""
    )
    assert small == []


def test_link_to_missing_entry_explains(app, expect):
    app.goto(URL + "#/e/99999")
    expect(app.locator("p.empty[role=status]")).to_contain_text("99999")
    expect(app.locator(".row").first).to_be_visible()  # the list is still usable


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
