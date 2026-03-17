"""
familysearch_quick_oauth.py

Minimal FamilySearch OAuth helper.

Flow:
1. Start a local callback HTTP listener
2. Open FamilySearch authorization page in the user's browser
3. Receive ?code=... on the callback URL
4. Exchange code for access token
5. Return token response

FamilySearch beta endpoints:
- Authorization: https://identbeta.familysearch.org/cis-web/oauth2/v3/authorization
- Token:         https://identbeta.familysearch.org/cis-web/oauth2/v3/token
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import threading
import urllib.parse
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional, Tuple

import requests


class OAuthError(Exception):
    pass


@dataclass
class FamilySearchOAuthConfig:
    client_id: str
    callback_url: str
    scope: str = "openid profile email"
    auth_url: str = "https://identbeta.familysearch.org/cis-web/oauth2/v3/authorization"
    token_url: str = "https://identbeta.familysearch.org/cis-web/oauth2/v3/token"
    timeout_seconds: int = 300


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _make_code_verifier(length: int = 64) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _make_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return _b64url(digest)


def _parse_callback(callback_url: str) -> Tuple[str, int, str]:
    parsed = urllib.parse.urlparse(callback_url)
    if parsed.scheme not in ("http", "https"):
        raise OAuthError("callback_url must use http or https")
    if not parsed.hostname:
        raise OAuthError("callback_url must include a hostname")
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    return host, port, path


class _CallbackState:
    def __init__(self) -> None:
        self.event = threading.Event()
        self.code: Optional[str] = None
        self.state: Optional[str] = None
        self.error: Optional[str] = None
        self.error_description: Optional[str] = None
        self.query: Dict[str, str] = {}


def _make_handler(cb_state: _CallbackState, expected_path: str):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)

            if parsed.path != expected_path:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Not found")
                return

            qs = urllib.parse.parse_qs(parsed.query)
            flat = {k: v[0] if v else "" for k, v in qs.items()}
            cb_state.query = flat
            cb_state.code = flat.get("code")
            cb_state.state = flat.get("state")
            cb_state.error = flat.get("error")
            cb_state.error_description = flat.get("error_description")
            cb_state.event.set()

            body = b"""
            <html>
              <body>
                <h1>Authentication complete</h1>
                <p>You may close this window.</p>
              </body>
            </html>
            """

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


def _start_server(callback_url: str, cb_state: _CallbackState):
    host, port, path = _parse_callback(callback_url)
    handler_cls = _make_handler(cb_state, path)
    server = HTTPServer((host, port), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _build_auth_url(
    config: FamilySearchOAuthConfig,
    user_id: Optional[str],
    state: str,
    code_challenge: str,
) -> str:
    params = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": config.callback_url,
        "scope": config.scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    # Optional hint; harmless if ignored by provider
    if user_id:
        params["login_hint"] = user_id

    return f"{config.auth_url}?{urllib.parse.urlencode(params)}"


def _exchange_code(
    config: FamilySearchOAuthConfig,
    code: str,
    code_verifier: str,
) -> Dict[str, Any]:
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": config.client_id,
        "redirect_uri": config.callback_url,
        "code_verifier": code_verifier,
    }

    resp = requests.post(
        config.token_url,
        data=form,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=30,
    )

    try:
        payload = resp.json()
    except Exception:
        payload = {"raw": resp.text}

    if not resp.ok:
        raise OAuthError(f"Token exchange failed: {resp.status_code} {payload}")

    return payload


def run_familysearch_oauth(
    client_id: str,
    callback_url: str,
    user_id: Optional[str] = None,
    scope: str = "openid profile email",
    timeout_seconds: int = 300,
) -> Dict[str, Any]:
    """
    Run FamilySearch beta OAuth flow and return the token response.
    """
    config = FamilySearchOAuthConfig(
        client_id=client_id,
        callback_url=callback_url,
        scope=scope,
        timeout_seconds=timeout_seconds,
    )

    cb_state = _CallbackState()
    code_verifier = _make_code_verifier()
    code_challenge = _make_code_challenge(code_verifier)
    expected_state = secrets.token_urlsafe(32)

    server, thread = _start_server(callback_url, cb_state)

    try:
        url = _build_auth_url(
            config=config,
            user_id=user_id,
            state=expected_state,
            code_challenge=code_challenge,
        )

        opened = webbrowser.open(url)
        if not opened:
            print("Open this URL manually:")
            print(url)

        if not cb_state.event.wait(timeout=timeout_seconds):
            raise OAuthError("Timed out waiting for callback")

        if cb_state.error:
            raise OAuthError(
                f"Provider returned error: {cb_state.error} {cb_state.error_description or ''}".strip()
            )

        if cb_state.state != expected_state:
            raise OAuthError("OAuth state mismatch")

        if not cb_state.code:
            raise OAuthError("No authorization code received")

        return _exchange_code(
            config=config,
            code=cb_state.code,
            code_verifier=code_verifier,
        )

    finally:
        try:
            server.shutdown()
        except Exception:
            pass
        try:
            server.server_close()
        except Exception:
            pass
        thread.join(timeout=2)


if __name__ == "__main__":
    token = run_familysearch_oauth(
        client_id="YOUR_FAMILYSEARCH_APP_KEY",
        callback_url="http://127.0.0.1:8765/callback",
        user_id="optional-user-id",
        scope="openid profile email",
    )
    print(json.dumps(token, indent=2))