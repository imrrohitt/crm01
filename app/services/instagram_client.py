"""
Thin HTTP client for the Instagram API with Instagram Login (Business Login).
Kept separate from the service so tests can replace it.
"""

from typing import Any
from urllib.parse import urlencode

import httpx

from config.settings import get_settings

AUTHORIZE_URL = "https://www.instagram.com/oauth/authorize"
TOKEN_URL = "https://api.instagram.com/oauth/access_token"
GRAPH_URL = "https://graph.instagram.com"
FACEBOOK_GRAPH_URL = "https://graph.facebook.com"
TIMEOUT = 15.0


class InstagramApiError(Exception):
    """Raised when Instagram rejects a request. message is safe to show to users."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _error_message(data: Any, default: str) -> str:
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])
        return str(data.get("error_message") or data.get("error_description") or default)
    return default


class InstagramClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def configured(self) -> bool:
        s = self.settings
        return bool(s.INSTAGRAM_APP_ID and s.INSTAGRAM_APP_SECRET and s.INSTAGRAM_REDIRECT_URI)

    def authorize_url(self, state: str) -> str:
        s = self.settings
        params = {
            "enable_fb_login": "0",
            "force_authentication": "1",
            "client_id": s.INSTAGRAM_APP_ID,
            "redirect_uri": s.INSTAGRAM_REDIRECT_URI,
            "response_type": "code",
            "scope": s.INSTAGRAM_SCOPES,
            "state": state,
        }
        return f"{AUTHORIZE_URL}?{urlencode(params)}"

    def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        try:
            res = httpx.request(method, url, timeout=TIMEOUT, **kwargs)
        except httpx.HTTPError as e:
            raise InstagramApiError("Could not reach Instagram. Please try again.") from e
        try:
            data = res.json()
        except ValueError:
            data = {}
        if res.status_code >= 400 or (isinstance(data, dict) and data.get("error")):
            raise InstagramApiError(_error_message(data, f"Instagram returned an error ({res.status_code})"))
        return data

    def exchange_code(self, code: str) -> dict[str, Any]:
        """Authorization code -> short-lived token. Returns {access_token, user_id, permissions}."""
        s = self.settings
        data = self._request(
            "POST",
            TOKEN_URL,
            data={
                "client_id": s.INSTAGRAM_APP_ID,
                "client_secret": s.INSTAGRAM_APP_SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": s.INSTAGRAM_REDIRECT_URI,
                "code": code,
            },
        )
        # Newer responses wrap the payload in {"data": [ {...} ]}
        if isinstance(data.get("data"), list) and data["data"]:
            data = data["data"][0]
        return data

    def long_lived_token(self, short_token: str) -> dict[str, Any]:
        """Short-lived -> 60 day token. Returns {access_token, expires_in}."""
        return self._request(
            "GET",
            f"{GRAPH_URL}/access_token",
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": self.settings.INSTAGRAM_APP_SECRET,
                "access_token": short_token,
            },
        )

    def profile(self, token: str) -> dict[str, Any]:
        """The connected professional account. user_id is the id that webhooks use."""
        return self._request(
            "GET",
            f"{GRAPH_URL}/{self.settings.INSTAGRAM_API_VERSION}/me",
            params={"fields": "user_id,username,name,account_type,profile_picture_url", "access_token": token},
        )

    def business_profile(self, ig_id: str, token: str) -> dict[str, Any]:
        """Profile of a professional account, loaded with a Facebook user or system token."""
        url = f"{FACEBOOK_GRAPH_URL}/{self.settings.INSTAGRAM_API_VERSION}/{ig_id}"
        try:
            return self._request("GET", url, params={"fields": "id,username,name,profile_picture_url", "access_token": token})
        except InstagramApiError:
            return self._request("GET", url, params={"fields": "id,username,name", "access_token": token})
