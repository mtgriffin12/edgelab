"""Future Alpaca paper trading adapter.

Placeholder only.
No API calls.
No credentials.
No orders.
Future paper trading adapter.
"""

from typing import Any

from edgelab.brokers.interface import BrokerAdapter


class AlpacaPaperAdapter(BrokerAdapter):
    """Placeholder Alpaca paper adapter."""

    def health_check(self) -> dict[str, Any]:
        """Return placeholder status without external calls."""

        return {
            "status": "placeholder",
            "api_calls": "disabled",
            "orders": "disabled",
        }
