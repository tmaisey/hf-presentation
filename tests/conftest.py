"""Pytest config: deck selection (``--deck v1|v2``) and one headless Chromium per worker.

Tests run against one deck per session. A module or test marked ``@pytest.mark.deck("v1")``
(or ``"v2"``) only runs against that deck; unmarked tests are generic and run against either.
"""

import os

import pytest
from playwright.sync_api import sync_playwright

DECKS = ("v1", "v2")


def pytest_addoption(parser):
    """Register ``--deck``: which deck file the suite targets (default v2, the live build)."""
    parser.addoption("--deck", choices=DECKS, default="v2",
                     help="deck under test: v1 = deck/deck.html (frozen), v2 = deck/deck-v2.html")


def pytest_configure(config):
    """Expose the chosen deck to helpers (env survives into xdist workers) and the marker."""
    os.environ["HF_DECK"] = config.getoption("--deck")
    config.addinivalue_line("markers", "deck(*names): run only when --deck is one of names")


def pytest_collection_modifyitems(config, items):
    """Deselect tests whose ``deck`` marker excludes the deck under test."""
    chosen = config.getoption("--deck")
    keep, drop = [], []
    for item in items:
        m = item.get_closest_marker("deck")
        (keep if m is None or chosen in m.args else drop).append(item)
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep


@pytest.fixture(scope="session")
def browser():
    """Launch headless Chromium once per session (per xdist worker).

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
