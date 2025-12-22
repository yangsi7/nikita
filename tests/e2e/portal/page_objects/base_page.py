"""
Base Page Object for Portal E2E Tests

Provides common functionality for all page objects.
Uses Playwright for browser automation.
"""

import os
from typing import Optional
from dataclasses import dataclass


# Portal URL configuration
PORTAL_URL = os.getenv(
    "PORTAL_URL",
    "https://portal-yangsi7s-projects.vercel.app"
)


@dataclass
class PageLoadResult:
    """Result of page load operation."""
    success: bool
    url: str
    title: str
    error: Optional[str] = None


class BasePage:
    """
    Base page object with common Playwright operations.

    For Claude Code execution, this provides method signatures
    that map to Playwright MCP tool calls.

    Usage in Claude Code:
        page = BasePage(base_url=PORTAL_URL)
        # Navigate via MCP:
        # mcp__playwright__playwright_navigate(url=page.url("/dashboard"))
        # Screenshot via MCP:
        # mcp__playwright__playwright_screenshot(name="dashboard")
    """

    DEFAULT_TIMEOUT = 30000  # 30 seconds

    def __init__(self, base_url: str = PORTAL_URL):
        """Initialize base page.

        Args:
            base_url: Base URL of the portal (e.g., https://portal.example.com)
        """
        self.base_url = base_url.rstrip('/')

    def url(self, path: str = "/") -> str:
        """Get full URL for a path.

        Args:
            path: Path relative to base URL (e.g., "/dashboard")

        Returns:
            Full URL (e.g., "https://portal.example.com/dashboard")
        """
        if not path.startswith('/'):
            path = '/' + path
        return f"{self.base_url}{path}"

    # ==================== Playwright MCP Helpers ====================

    def navigate_command(self, path: str = "/") -> dict:
        """Build mcp__playwright__playwright_navigate command.

        Args:
            path: Path to navigate to

        Returns:
            Dict with URL for Playwright navigate command
        """
        return {"url": self.url(path)}

    def screenshot_command(self, name: str) -> dict:
        """Build mcp__playwright__playwright_screenshot command.

        Args:
            name: Name for the screenshot

        Returns:
            Dict with name for Playwright screenshot command
        """
        return {"name": name}

    def evaluate_command(self, script: str) -> dict:
        """Build mcp__playwright__playwright_evaluate command.

        Args:
            script: JavaScript to evaluate

        Returns:
            Dict with script for Playwright evaluate command
        """
        return {"script": script}

    # ==================== Common Selectors ====================

    @staticmethod
    def selector_text(text: str) -> str:
        """Build text content selector.

        Args:
            text: Text to find

        Returns:
            Selector string (e.g., "text=Loading")
        """
        return f"text={text}"

    @staticmethod
    def selector_role(role: str, name: Optional[str] = None) -> str:
        """Build ARIA role selector.

        Args:
            role: ARIA role (e.g., "button", "textbox")
            name: Optional accessible name

        Returns:
            Selector string
        """
        if name:
            return f"role={role}[name='{name}']"
        return f"role={role}"

    @staticmethod
    def selector_testid(testid: str) -> str:
        """Build data-testid selector.

        Args:
            testid: Test ID value

        Returns:
            Selector string
        """
        return f"[data-testid='{testid}']"

    # ==================== Common JavaScript Snippets ====================

    @staticmethod
    def js_get_text(selector: str) -> str:
        """JavaScript to get text content of element.

        Args:
            selector: CSS selector

        Returns:
            JavaScript code string
        """
        return f"document.querySelector('{selector}')?.textContent?.trim() || ''"

    @staticmethod
    def js_element_exists(selector: str) -> str:
        """JavaScript to check if element exists.

        Args:
            selector: CSS selector

        Returns:
            JavaScript code string
        """
        return f"!!document.querySelector('{selector}')"

    @staticmethod
    def js_get_input_value(selector: str) -> str:
        """JavaScript to get input value.

        Args:
            selector: CSS selector for input

        Returns:
            JavaScript code string
        """
        return f"document.querySelector('{selector}')?.value || ''"

    @staticmethod
    def js_fill_input(selector: str, value: str) -> str:
        """JavaScript to fill input value.

        Args:
            selector: CSS selector for input
            value: Value to fill

        Returns:
            JavaScript code string
        """
        return f"""
            const input = document.querySelector('{selector}');
            if (input) {{
                input.value = '{value}';
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        """

    @staticmethod
    def js_click(selector: str) -> str:
        """JavaScript to click element.

        Args:
            selector: CSS selector

        Returns:
            JavaScript code string
        """
        return f"document.querySelector('{selector}')?.click()"

    @staticmethod
    def js_wait_for_network_idle() -> str:
        """JavaScript to wait for network to be idle.

        Returns:
            JavaScript code that returns a promise
        """
        return """
            new Promise(resolve => {
                let pending = 0;
                const observer = new PerformanceObserver(list => {
                    for (const entry of list.getEntries()) {
                        if (entry.entryType === 'resource') {
                            pending--;
                        }
                    }
                });
                observer.observe({ entryTypes: ['resource'] });

                // Check every 100ms, resolve after 500ms of no activity
                let lastPending = pending;
                let stableCount = 0;
                const check = () => {
                    if (pending === lastPending) {
                        stableCount++;
                        if (stableCount >= 5) {
                            observer.disconnect();
                            resolve(true);
                            return;
                        }
                    } else {
                        stableCount = 0;
                        lastPending = pending;
                    }
                    setTimeout(check, 100);
                };
                setTimeout(check, 100);
            });
        """
