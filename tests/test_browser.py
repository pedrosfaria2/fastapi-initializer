"""Browser tests for the interactive UI."""

from __future__ import annotations

import re
import socket
import threading
import time
import zipfile
from collections.abc import Iterator

import pytest
import uvicorn
from playwright.sync_api import Browser, Page, expect, sync_playwright

from fastapi_initializr.main import create_app

pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch()
        try:
            yield chromium
        finally:
            chromium.close()


@pytest.fixture
def page(browser: Browser) -> Iterator[Page]:
    context = browser.new_context()
    page = context.new_page()
    try:
        yield page
    finally:
        context.close()


@pytest.fixture(scope="module")
def live_server_url() -> Iterator[str]:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    config = uvicorn.Config(
        create_app(),
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if not thread.is_alive() or time.monotonic() > deadline:
            raise RuntimeError("Test server did not start")
        time.sleep(0.01)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def _open(page: Page, live_server_url: str, query: str = "") -> None:
    page.goto(f"{live_server_url}/{query}")
    page.wait_for_function("document.getElementById('preview-status').textContent.includes('file')")


def test_search_filters_dependencies(page: Page, live_server_url: str) -> None:
    _open(page, live_server_url)

    page.fill("#dependency-search", "graphql")
    page.wait_for_function(
        """() => {
            const graphql = document.querySelector('[data-dependency-id="graphql"]');
            const sqlalchemy = document.querySelector('[data-dependency-id="sqlalchemy"]');
            return graphql && !graphql.hidden && sqlalchemy && sqlalchemy.hidden;
        }"""
    )
    assert page.locator("#dependency-empty").is_hidden()

    page.fill("#dependency-search", "no-such-feature")
    page.wait_for_function("document.getElementById('dependency-empty').hidden === false")


def test_shift_click_selects_a_range(page: Page, live_server_url: str) -> None:
    _open(page, live_server_url)

    page.locator('[data-dependency-id="sqlalchemy"] input').click()
    page.locator('[data-dependency-id="postgres"] input').click(modifiers=["Shift"])

    assert page.locator("#selected-count").inner_text() == "3 selected"


def test_preset_applies_and_manual_edits_switch_to_custom(
    page: Page,
    live_server_url: str,
) -> None:
    _open(page, live_server_url)

    page.select_option("#preset", "worker")

    assert page.locator("#selected-count").inner_text() == "3 selected"
    assert page.locator('[data-dependency-id="arq"] input').is_checked()

    page.locator('[data-dependency-id="cache"] input').uncheck()
    assert page.input_value("#preset") == "custom"


def test_share_copies_the_current_url(page: Page, live_server_url: str) -> None:
    _open(page, live_server_url)
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])

    page.click("#share")
    page.wait_for_function("document.getElementById('share').textContent === 'Copied'")
    copied = page.evaluate("navigator.clipboard.readText()")

    assert copied.startswith(live_server_url)
    assert "preset=custom" in copied


def test_reset_restores_defaults(page: Page, live_server_url: str) -> None:
    _open(page, live_server_url)
    page.fill("#project-name", "changed-name")
    page.locator('[data-dependency-id="redis"] input').check()

    page.click("#reset")

    assert page.input_value("#project-name") == "my-service"
    assert page.input_value("#preset") == "custom"
    assert page.locator("#selected-count").inner_text() == "0 selected"


def test_keyboard_shortcut_generates_a_zip(page: Page, live_server_url: str) -> None:
    _open(page, live_server_url)

    with page.expect_download() as download_info:
        page.keyboard.press("Control+Enter")

    assert download_info.value.suggested_filename.endswith(".zip")


def test_explore_highlights_labels_and_scrolls(page: Page, live_server_url: str) -> None:
    page.set_viewport_size({"width": 1280, "height": 720})
    _open(page, live_server_url, "?name=scroll-service&preset=full")
    page.locator('button.file-button[data-path="pyproject.toml"]').click()
    page.wait_for_selector("#file-content .k")

    assert page.locator("#file-language").inner_text() == "TOML"
    metrics = page.evaluate(
        """() => {
            const content = document.getElementById('file-content');
            content.scrollTop = content.scrollHeight;
            return {
                scrollHeight: content.scrollHeight,
                clientHeight: content.clientHeight,
                scrollTop: content.scrollTop,
                treeOverflow: getComputedStyle(
                    document.querySelector('.file-tree')
                ).overflowY,
            };
        }"""
    )
    assert metrics["scrollHeight"] > metrics["clientHeight"]
    assert metrics["scrollTop"] > 0
    assert metrics["treeOverflow"] in {"auto", "scroll"}


@pytest.mark.parametrize(("width", "height"), [(1440, 900), (1280, 720)])
def test_desktop_workspace_keeps_generation_accessible(
    page: Page, live_server_url: str, width: int, height: int
) -> None:
    page.set_viewport_size({"width": width, "height": height})
    _open(page, live_server_url)
    expect(page.locator("#selected-file")).to_have_text("pyproject.toml")

    metrics = page.evaluate(
        """() => {
            const settings = document.querySelector('.settings-panel').getBoundingClientRect();
            const catalog = document.querySelector('.dependency-section').getBoundingClientRect();
            const preview = document.getElementById('preview').getBoundingClientRect();
            const scroll = document.querySelector('.catalog-scroll');
            scroll.scrollTop = scroll.scrollHeight;
            const code = document.getElementById('file-content');
            code.scrollTop = code.scrollHeight;
            const generate = document.getElementById('generate').getBoundingClientRect();
            return {
                settingsRight: settings.right, catalogLeft: catalog.left,
                catalogRight: catalog.right, previewLeft: preview.left,
                catalogScroll: scroll.scrollTop, codeScroll: code.scrollTop,
                documentWidth: document.documentElement.scrollWidth,
                documentScroll: window.scrollY,
                generateTop: generate.top, generateBottom: generate.bottom,
            };
        }"""
    )
    assert metrics["settingsRight"] <= metrics["catalogLeft"]
    assert metrics["catalogRight"] <= metrics["previewLeft"]
    assert metrics["catalogScroll"] > 0
    assert metrics["codeScroll"] > 0
    assert metrics["documentWidth"] <= width
    assert metrics["documentScroll"] == 0
    assert 0 <= metrics["generateTop"] < metrics["generateBottom"] <= height

    with page.expect_download() as download_info:
        page.click("#generate")
    assert download_info.value.suggested_filename == "my-service.zip"


def test_dependency_filters_combine_and_clear(page: Page, live_server_url: str) -> None:
    _open(page, live_server_url)
    page.locator('[data-dependency-id="sqlalchemy"] input').check()
    page.select_option("#dependency-category", "Database")
    page.click("#selected-count")
    page.fill("#dependency-search", "sqlalchemy")

    expect(page.locator(".dependency-option:visible")).to_have_count(1)
    expect(page.locator('[data-dependency-id="sqlalchemy"]')).to_be_visible()
    expect(page.locator("#selected-count")).to_have_attribute("aria-pressed", "true")

    page.fill("#dependency-search", "redis")
    expect(page.locator("#dependency-empty")).to_be_visible()
    page.click("#clear-search")

    expect(page.locator("#dependency-search")).to_have_value("")
    expect(page.locator("#dependency-category")).to_have_value("")
    expect(page.locator("#selected-count")).to_have_attribute("aria-pressed", "false")
    expect(page.locator('[data-dependency-id="redis"]')).to_be_visible()
    expect(page.locator('[data-dependency-id="sqlalchemy"] input')).to_be_checked()


def test_reset_clears_dependency_filters(page: Page, live_server_url: str) -> None:
    _open(page, live_server_url)
    page.locator('[data-dependency-id="sqlalchemy"] input').check()
    page.select_option("#dependency-category", "Database")
    page.fill("#dependency-search", "sqlalchemy")
    page.click("#selected-count")

    page.click("#reset")

    expect(page.locator("#dependency-category")).to_have_value("")
    expect(page.locator("#dependency-search")).to_have_value("")
    expect(page.locator("#selected-count")).to_have_attribute("aria-pressed", "false")
    expect(page.locator("#selected-count")).to_have_text("0 selected")
    expect(page.locator('[data-dependency-id="redis"]')).to_be_visible()


def test_dependency_selection_updates_url_and_preview(page: Page, live_server_url: str) -> None:
    _open(page, live_server_url)
    redis_file = page.locator('button.file-button[data-path="src/my_service/core/cache.py"]')
    expect(redis_file).to_have_count(0)

    page.locator('[data-dependency-id="redis"] input').check()

    expect(page).to_have_url(re.compile(r"[?&]dependencies=redis(?:&|$)"))
    expect(redis_file).to_have_count(1)
    redis_file.click()
    expect(page.locator("#selected-file")).to_have_text("src/my_service/core/cache.py")
    expect(page.locator("#file-content")).to_contain_text("redis")


def test_native_form_downloads_without_javascript(browser: Browser, live_server_url: str) -> None:
    context = browser.new_context(java_script_enabled=False)
    try:
        page = context.new_page()
        page.goto(live_server_url)
        page.locator('[data-dependency-id="redis"] input').check()

        with page.expect_download() as download_info:
            page.click("#generate")

        assert download_info.value.suggested_filename == "my-service.zip"
        with zipfile.ZipFile(download_info.value.path()) as archive:
            assert "my-service/src/my_service/core/cache.py" in archive.namelist()
    finally:
        context.close()
