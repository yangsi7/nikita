"""PII masking utilities for log output (SEC-005).

Prevents phone numbers and other PII from appearing in plain text in logs.
"""


def mask_phone(number: str) -> str:
    """Mask phone number for logging: +1234567890 -> ***7890.

    Args:
        number: Phone number string (any format).

    Returns:
        Masked string showing only last 4 digits.
    """
    if len(number) <= 4:
        return "***" + number
    return "***" + number[-4:]
