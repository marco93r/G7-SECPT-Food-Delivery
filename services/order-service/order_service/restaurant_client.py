from __future__ import annotations

import httpx
from typing import List, Sequence


class RestaurantServiceError(Exception):
    """Raised when downstream restaurant interactions fail."""


class RestaurantClient:
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=5.0)

    def confirm_order(
        self, restaurant_id: str, order_id: str, items: Sequence[dict]
    ) -> dict:
        url = f"{self._base_url}/restaurants/{restaurant_id}/orders"
        payload = {"order_id": order_id, "items": items}

        try:
            response = self._client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise RestaurantServiceError(f"Restaurant-Service nicht erreichbar: {exc}") from exc

        if response.status_code >= 400:
            raise RestaurantServiceError(
                f"Restaurant hat Bestellung abgelehnt ({response.status_code}): {response.text}"
            )
        return response.json()

    def cancel_order(self, restaurant_id: str, order_id: str, reason: str | None) -> None:
        url = f"{self._base_url}/restaurants/{restaurant_id}/orders/{order_id}/cancel"
        payload = {"reason": reason}
        try:
            response = self._client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise RestaurantServiceError(f"Restaurant-Kompensation fehlgeschlagen: {exc}") from exc
        if response.status_code >= 400:
            raise RestaurantServiceError(
                f"Restaurant konnte Order nicht stornieren ({response.status_code}): {response.text}"
            )
