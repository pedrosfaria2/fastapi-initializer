"""Browser tests for the interactive UI."""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator

import pytest
import uvicorn
from playwright.sync_api import Page

from fastapi_initializr.main import create_app

pytestmark = pytest.mark.browser


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
