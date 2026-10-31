"""
Thin HTTP client for the Instagram API with Instagram Login (Business Login).
Kept separate from the service so tests can replace it.
"""

import logging
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from config.settings import get_settings

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

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


def _token_header(url: str, params: dict[str, Any] | None, headers: dict[str, str] | None) -> tuple[str, dict[str, Any] | None, dict[str, str]]:
    """Facebook Graph accepts the token as a Bearer header, so it stays out of the URL."""
    parts = urlsplit(url)
    out = dict(headers or {})
    if parts.netloc != "graph.facebook.com":
        return url, params, out
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    merged = {**query, **(params or {})}
    token = merged.pop("access_token", None)
    clean = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(merged), parts.fragment))
    if token and "Authorization" not in out:
        out["Authorization"] = f"Bearer {token}"
    return clean, None, out


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
        url, params, headers = _token_header(url, kwargs.pop("params", None), kwargs.pop("headers", None))
        try:
            res = httpx.request(method, url, params=params, headers=headers, timeout=TIMEOUT, **kwargs)
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

    def message_threads(self, ig_id: str, token: str) -> list[dict[str, Any]]:
        """Every Instagram DM thread this token can read, with messages followed across pages."""
        version = self.settings.INSTAGRAM_API_VERSION
        fields = "id,updated_time,participants,messages.limit(25){id,created_time,from,message,is_unsupported}"
        url: str | None = f"{FACEBOOK_GRAPH_URL}/{version}/{ig_id}/conversations"
        params: dict[str, str] | None = {"platform": "instagram", "fields": fields, "limit": "25", "access_token": token}
        threads: list[dict[str, Any]] = []
        while url:
            data = self._request("GET", url, params=params) if params else self._request("GET", url)
            params = None
            for row in data.get("data") or []:
                bucket = row.get("messages") or {}
                messages = list(bucket.get("data") or [])
                next_messages = (bucket.get("paging") or {}).get("next")
                while next_messages:
                    more = self._request("GET", next_messages)
                    messages.extend(more.get("data") or [])
                    next_messages = (more.get("paging") or {}).get("next")
                participants = (row.get("participants") or {}).get("data") or []
                threads.append({
                    "id": row.get("id"),
                    "updated_time": row.get("updated_time"),
                    "participants": participants,
                    "messages": [
                        {
                            "id": item.get("id"),
                            "created_time": item.get("created_time"),
                            "from": item.get("from") or {},
                            "text": item.get("message") or "",
                            "is_unsupported": bool(item.get("is_unsupported")),
                        }
                        for item in messages
                        if isinstance(item, dict)
                    ],
                })
            url = (data.get("paging") or {}).get("next")
        return threads

    def send_text(self, ig_id: str, recipient_id: str, token: str, text: str, tag: str | None = None) -> dict[str, Any]:
        """Send one text DM from the professional account. Returns {recipient_id, message_id}.

        tag=HUMAN_AGENT is Instagram's way to reply up to 7 days after the customer's last message.
        """
        payload: dict[str, Any] = {"recipient": {"id": recipient_id}, "message": {"text": text}}
        if tag:
            payload["tag"] = tag
        return self._request(
            "POST",
            f"{FACEBOOK_GRAPH_URL}/{self.settings.INSTAGRAM_API_VERSION}/{ig_id}/messages",
            params={"access_token": token},
            json=payload,
        )

    def user_profile(self, igsid: str, token: str) -> dict[str, Any]:
        """Name, photo, and public stats for someone who messaged this account.

        Instagram only returns this when the professional account is linked to a Facebook Page.
        A missing page is an empty profile, not a failed sync.
        """
        fields = "name,username,profile_pic,follower_count,is_user_follow_business,is_business_follow_user,is_verified_user"
        try:
            data = self._request(
                "GET",
                f"{FACEBOOK_GRAPH_URL}/{self.settings.INSTAGRAM_API_VERSION}/{igsid}",
                params={"fields": fields, "access_token": token},
            )
        except InstagramApiError:
            return {}
        return data if isinstance(data, dict) and not data.get("error") else {}

    def business_profile(self, ig_id: str, token: str) -> dict[str, Any]:
        """Profile of a professional account, loaded with a Facebook user or system token."""
        url = f"{FACEBOOK_GRAPH_URL}/{self.settings.INSTAGRAM_API_VERSION}/{ig_id}"
        try:
            return self._request("GET", url, params={"fields": "id,username,name,profile_picture_url", "access_token": token})
        except InstagramApiError:
            return self._request("GET", url, params={"fields": "id,username,name", "access_token": token})
