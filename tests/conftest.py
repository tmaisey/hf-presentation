"""Pytest fixtures: one headless Chromium shared across the session."""

import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def browser():
    """Launch headless Chromium once per test session.

    Yields:
        A Playwright ``Browser``.
    """
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")  # system Chrome: no browser download
        yield b
        b.close()


@pytest.fixture
def page(browser):
    """Fresh page per test.

    Yields:
        A Playwright ``Page``.
    """
    ctx = browser.new_context()
    pg = ctx.new_page()
    yield pg
    ctx.close()
