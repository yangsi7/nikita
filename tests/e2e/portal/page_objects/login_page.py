"""
Login Page Object for Portal E2E Tests

Handles magic link login flow.
"""

from dataclasses import dataclass
from typing import Optional

from .base_page import BasePage, PORTAL_URL


@dataclass
class LoginResult:
    """Result of login attempt."""
    magic_link_sent: bool
    message: Optional[str] = None
    error: Optional[str] = None


class LoginPage(BasePage):
    """
    Page object for the portal login page.

    Elements:
    - Email input: input[type="email"]
    - Submit button: button[type="submit"]
    - Success message: Contains "Check your email"
    - Error message: Has destructive styling
    """

    # ==================== Selectors ====================

    # Input elements
    EMAIL_INPUT = 'input[type="email"]'
    SUBMIT_BUTTON = 'button[type="submit"]'

    # Message elements
    SUCCESS_MESSAGE_TEXT = "Check your email"
    ERROR_CONTAINER = "[role='alert']"

    # Title/header elements
    PAGE_TITLE = "h1"  # "Nikita"
    CARD_TITLE = "text=Sign In"

    # Loading states
    LOADING_BUTTON_TEXT = "Sending..."

    def __init__(self, base_url: str = PORTAL_URL):
        """Initialize login page."""
        super().__init__(base_url)

    # ==================== Navigation ====================

    def navigate_to_login(self) -> dict:
        """Get navigation command for login page.

        Returns:
            Dict for mcp__playwright__playwright_navigate
        """
        return self.navigate_command("/")

    # ==================== Actions ====================

    def js_enter_email(self, email: str) -> str:
        """JavaScript to enter email and trigger events.

        Args:
            email: Email address to enter

        Returns:
            JavaScript code string
        """
        return f"""
            const input = document.querySelector('{self.EMAIL_INPUT}');
            if (input) {{
                input.focus();
                input.value = '{email}';
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                true;
            }} else {{
                false;
            }}
        """

    def js_click_submit(self) -> str:
        """JavaScript to click submit button.

        Returns:
            JavaScript code string
        """
        return f"document.querySelector('{self.SUBMIT_BUTTON}')?.click(); true;"

    def js_submit_form(self, email: str) -> str:
        """JavaScript to enter email and submit form.

        Args:
            email: Email address

        Returns:
            JavaScript code string
        """
        return f"""
            const input = document.querySelector('{self.EMAIL_INPUT}');
            const button = document.querySelector('{self.SUBMIT_BUTTON}');
            if (input && button) {{
                input.value = '{email}';
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                button.click();
                true;
            }} else {{
                false;
            }}
        """

    # ==================== Verification ====================

    def js_is_on_login_page(self) -> str:
        """JavaScript to verify we're on the login page.

        Returns:
            JavaScript code that returns boolean
        """
        return f"""
            document.querySelector('{self.EMAIL_INPUT}') !== null &&
            document.querySelector('{self.SUBMIT_BUTTON}') !== null
        """

    def js_get_success_message(self) -> str:
        """JavaScript to get success message if present.

        Returns:
            JavaScript code that returns message or null
        """
        return """
            const alert = document.querySelector("[role='alert']");
            if (alert && alert.textContent?.includes('Check your email')) {
                alert.textContent.trim();
            } else {
                null;
            }
        """

    def js_get_error_message(self) -> str:
        """JavaScript to get error message if present.

        Returns:
            JavaScript code that returns message or null
        """
        return """
            const alert = document.querySelector("[role='alert']");
            if (alert && !alert.textContent?.includes('Check your email')) {
                alert.textContent.trim();
            } else {
                null;
            }
        """

    def js_is_loading(self) -> str:
        """JavaScript to check if form is in loading state.

        Returns:
            JavaScript code that returns boolean
        """
        return f"""
            document.querySelector('{self.SUBMIT_BUTTON}')?.disabled === true ||
            document.querySelector('{self.SUBMIT_BUTTON}')?.textContent?.includes('Sending')
        """

    def js_wait_for_magic_link_sent(self, timeout_ms: int = 10000) -> str:
        """JavaScript to wait for magic link success message.

        Args:
            timeout_ms: Maximum wait time in milliseconds

        Returns:
            JavaScript code that returns a promise
        """
        return f"""
            new Promise((resolve, reject) => {{
                const startTime = Date.now();
                const check = () => {{
                    const alert = document.querySelector("[role='alert']");
                    if (alert) {{
                        if (alert.textContent?.includes('Check your email')) {{
                            resolve(true);
                            return;
                        }}
                        // Check for error
                        if (alert.classList.contains('text-destructive') ||
                            alert.textContent?.includes('error') ||
                            alert.textContent?.includes('failed')) {{
                            reject(new Error(alert.textContent));
                            return;
                        }}
                    }}
                    if (Date.now() - startTime > {timeout_ms}) {{
                        reject(new Error('Timeout waiting for magic link confirmation'));
                        return;
                    }}
                    setTimeout(check, 200);
                }};
                check();
            }});
        """

    # ==================== Composite Operations ====================

    def build_login_sequence(self, email: str) -> list:
        """Build sequence of operations for complete login flow.

        Args:
            email: Email to use for login

        Returns:
            List of steps with JS code for each operation
        """
        return [
            {
                "step": "navigate",
                "command": self.navigate_command("/"),
                "description": "Navigate to login page",
            },
            {
                "step": "verify_page",
                "js": self.js_is_on_login_page(),
                "description": "Verify login page loaded",
            },
            {
                "step": "enter_email",
                "js": self.js_enter_email(email),
                "description": f"Enter email: {email}",
            },
            {
                "step": "submit",
                "js": self.js_click_submit(),
                "description": "Click submit button",
            },
            {
                "step": "wait_for_result",
                "js": self.js_wait_for_magic_link_sent(),
                "description": "Wait for magic link confirmation",
            },
        ]
