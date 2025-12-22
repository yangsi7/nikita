"""
Conversations Page Object for Portal E2E Tests

Handles conversation history viewing and verification.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from .base_page import BasePage, PORTAL_URL


@dataclass
class ConversationSummary:
    """Summary of a conversation."""
    id: Optional[str] = None
    date: Optional[str] = None
    message_count: Optional[int] = None
    preview: Optional[str] = None


@dataclass
class ConversationsData:
    """Conversations page data snapshot."""
    conversations: List[ConversationSummary] = None
    total_count: int = 0
    loading: bool = False
    error: Optional[str] = None

    def __post_init__(self):
        if self.conversations is None:
            self.conversations = []


class ConversationsPage(BasePage):
    """
    Page object for the portal conversations page.

    Key elements:
    - List of conversations
    - Conversation details view
    - Message history
    """

    # ==================== Selectors ====================

    # Navigation
    BACK_BUTTON = "text=Back"
    DASHBOARD_LINK = "text=Dashboard"

    # Loading states
    LOADING_INDICATOR = "text=Loading"
    ERROR_INDICATOR = "text=error"

    # Conversation list
    CONVERSATION_LIST = "[class*='conversation']"
    CONVERSATION_ITEM = "[class*='conversation-item']"

    def __init__(self, base_url: str = PORTAL_URL):
        """Initialize conversations page."""
        super().__init__(base_url)

    # ==================== Navigation ====================

    def navigate_to_conversations(self) -> dict:
        """Get navigation command for conversations page.

        Returns:
            Dict for mcp__playwright__playwright_navigate
        """
        return self.navigate_command("/conversations")

    # ==================== Page State ====================

    def js_is_loading(self) -> str:
        """JavaScript to check if page is loading.

        Returns:
            JavaScript code that returns boolean
        """
        return """
            document.body.textContent?.includes('Loading') ||
            document.querySelector('.animate-pulse') !== null
        """

    def js_is_loaded(self) -> str:
        """JavaScript to check if page is fully loaded.

        Returns:
            JavaScript code that returns boolean
        """
        return """
            !document.body.textContent?.includes('Loading') &&
            document.querySelector('header') !== null
        """

    def js_has_error(self) -> str:
        """JavaScript to check if page has error.

        Returns:
            JavaScript code that returns boolean
        """
        return """
            document.body.textContent?.toLowerCase().includes('error') ||
            document.body.textContent?.includes('failed')
        """

    # ==================== Data Extraction ====================

    def js_get_conversation_count(self) -> str:
        """JavaScript to count conversations.

        Returns:
            JavaScript code that returns number
        """
        return """
            // Look for conversation items or cards
            const items = document.querySelectorAll('[class*="conversation"], [class*="card"]');
            let count = 0;
            for (const item of items) {
                // Check if it looks like a conversation item (has date/time or message content)
                if (item.textContent?.match(/\\d{1,2}[\\/\\-]\\d{1,2}|ago|today|yesterday/i)) {
                    count++;
                }
            }
            return count;
        """

    def js_get_conversations_list(self) -> str:
        """JavaScript to extract conversation list.

        Returns:
            JavaScript code that returns array of conversation summaries
        """
        return """
            const conversations = [];
            // Look for conversation items
            const items = document.querySelectorAll('[class*="conversation"], article, [class*="card"]');

            for (const item of items) {
                const text = item.textContent || '';

                // Skip navigation/header items
                if (text.length < 20 || item.tagName === 'NAV' || item.tagName === 'HEADER') {
                    continue;
                }

                // Extract date
                const dateMatch = text.match(/(\\d{1,2}[\\/\\-]\\d{1,2}[\\/\\-]\\d{2,4}|today|yesterday|\\d+\\s+(hour|minute|day)s?\\s+ago)/i);

                // Extract message count
                const countMatch = text.match(/(\\d+)\\s*(message|msg)/i);

                // Get preview (first 100 chars of content)
                const preview = text.substring(0, 100).trim();

                if (dateMatch || countMatch) {
                    conversations.push({
                        date: dateMatch ? dateMatch[0] : null,
                        message_count: countMatch ? parseInt(countMatch[1]) : null,
                        preview: preview
                    });
                }
            }

            return conversations;
        """

    def js_get_all_conversations_data(self) -> str:
        """JavaScript to extract all conversations page data.

        Returns:
            JavaScript code that returns object
        """
        return """
            const data = {
                loading: false,
                error: null,
                conversations: [],
                total_count: 0
            };

            // Check loading state
            if (document.body.textContent?.includes('Loading')) {
                data.loading = true;
                return data;
            }

            // Check error state
            if (document.body.textContent?.toLowerCase().includes('error') ||
                document.body.textContent?.includes('failed')) {
                data.error = 'Failed to load conversations';
                return data;
            }

            // Extract conversations
            const items = document.querySelectorAll('[class*="conversation"], article, [class*="card"]');

            for (const item of items) {
                const text = item.textContent || '';

                // Skip navigation/header items
                if (text.length < 20 || item.tagName === 'NAV' || item.tagName === 'HEADER') {
                    continue;
                }

                const dateMatch = text.match(/(\\d{1,2}[\\/\\-]\\d{1,2}[\\/\\-]\\d{2,4}|today|yesterday|\\d+\\s+(hour|minute|day)s?\\s+ago)/i);
                const countMatch = text.match(/(\\d+)\\s*(message|msg)/i);

                if (dateMatch || countMatch) {
                    data.conversations.push({
                        date: dateMatch ? dateMatch[0] : null,
                        message_count: countMatch ? parseInt(countMatch[1]) : null,
                        preview: text.substring(0, 100).trim()
                    });
                }
            }

            data.total_count = data.conversations.length;
            return data;
        """

    # ==================== Actions ====================

    def js_click_first_conversation(self) -> str:
        """JavaScript to click first conversation item.

        Returns:
            JavaScript code string
        """
        return """
            const items = document.querySelectorAll('[class*="conversation"], [class*="card"]');
            for (const item of items) {
                const text = item.textContent || '';
                if (text.length > 20 && !['NAV', 'HEADER'].includes(item.tagName)) {
                    item.click();
                    return true;
                }
            }
            return false;
        """

    def js_go_back(self) -> str:
        """JavaScript to navigate back.

        Returns:
            JavaScript code string
        """
        return """
            // Try back button first
            const backBtn = document.querySelector('[class*="back"], button:has-text("Back")');
            if (backBtn) {
                backBtn.click();
                return true;
            }
            // Try dashboard link
            const dashLink = document.querySelector('a[href*="dashboard"]');
            if (dashLink) {
                dashLink.click();
                return true;
            }
            // Use browser back
            window.history.back();
            return true;
        """

    # ==================== Verification ====================

    def js_wait_for_conversations_loaded(self, timeout_ms: int = 15000) -> str:
        """JavaScript to wait for conversations to load.

        Args:
            timeout_ms: Maximum wait time in milliseconds

        Returns:
            JavaScript code that returns a promise
        """
        return f"""
            new Promise((resolve, reject) => {{
                const startTime = Date.now();
                const check = () => {{
                    // Check for error
                    if (document.body.textContent?.toLowerCase().includes('error') ||
                        document.body.textContent?.includes('failed')) {{
                        reject(new Error('Failed to load conversations'));
                        return;
                    }}
                    // Check for loaded state (not loading and has content)
                    if (!document.body.textContent?.includes('Loading') &&
                        document.querySelector('header') !== null) {{
                        resolve(true);
                        return;
                    }}
                    // Timeout check
                    if (Date.now() - startTime > {timeout_ms}) {{
                        reject(new Error('Timeout waiting for conversations to load'));
                        return;
                    }}
                    setTimeout(check, 200);
                }};
                check();
            }});
        """

    def js_verify_conversations_exist(self) -> str:
        """JavaScript to verify at least one conversation exists.

        Returns:
            JavaScript code that returns boolean
        """
        return """
            const items = document.querySelectorAll('[class*="conversation"], article, [class*="card"]');
            for (const item of items) {
                const text = item.textContent || '';
                if (text.length > 20 &&
                    !['NAV', 'HEADER'].includes(item.tagName) &&
                    (text.match(/\\d{1,2}[\\/\\-]\\d{1,2}/) || text.match(/\\d+\\s*msg/i))) {
                    return true;
                }
            }
            return false;
        """

    # ==================== Composite Operations ====================

    def build_verification_sequence(self) -> list:
        """Build sequence of operations to verify conversations.

        Returns:
            List of steps with JS code for each operation
        """
        return [
            {
                "step": "navigate",
                "command": self.navigate_command("/conversations"),
                "description": "Navigate to conversations page",
            },
            {
                "step": "wait_for_load",
                "js": self.js_wait_for_conversations_loaded(),
                "description": "Wait for conversations to load",
            },
            {
                "step": "verify_exists",
                "js": self.js_verify_conversations_exist(),
                "description": "Verify at least one conversation exists",
            },
            {
                "step": "extract_data",
                "js": self.js_get_all_conversations_data(),
                "description": "Extract conversations data",
            },
            {
                "step": "screenshot",
                "command": self.screenshot_command("conversations"),
                "description": "Take screenshot of conversations",
            },
        ]
