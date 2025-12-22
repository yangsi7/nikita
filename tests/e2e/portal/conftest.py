"""
Portal E2E Tests Configuration

Provides fixtures and utilities for portal Playwright tests.
"""

import os

import pytest

from .page_objects import LoginPage, DashboardPage, ConversationsPage


# Portal URL configuration
PORTAL_URL = os.getenv(
    "PORTAL_URL",
    "https://portal-yangsi7s-projects.vercel.app"
)


@pytest.fixture
def login_page():
    """Create LoginPage instance."""
    return LoginPage(base_url=PORTAL_URL)


@pytest.fixture
def dashboard_page():
    """Create DashboardPage instance."""
    return DashboardPage(base_url=PORTAL_URL)


@pytest.fixture
def conversations_page():
    """Create ConversationsPage instance."""
    return ConversationsPage(base_url=PORTAL_URL)


@pytest.fixture
def test_email():
    """Get test email address."""
    return os.getenv("TEST_EMAIL", "simon.yang.ch@gmail.com")
