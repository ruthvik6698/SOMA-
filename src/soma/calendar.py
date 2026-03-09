"""
Google Calendar integration via Composio (placeholder).
Poll events every 30 min for SOMA decision loop.
"""
import pytz

IST = pytz.timezone("Asia/Kolkata")


def get_today_events() -> list[dict]:
    """
    Fetch today's calendar events.
    Placeholder: returns [] until Composio OAuth + event polling is implemented.
    Each event: {"summary": str, "start": datetime, "end": datetime}
    """
    # TODO: Composio → Google Calendar OAuth + event polling
    return []
