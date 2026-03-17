"""
======================================================================
 Project: gedcomtools
 File:    quick_oauth.py
 Author:  David J. Cartwright
 Purpose: Generic OAuth 2.0 PKCE authorization-code flow helper for desktop/CLI tools

 Created: 2025-07-01
 Updated:

======================================================================
"""
"""
quick_oauth.py

A small OAuth2 helper that:
1. Starts a local HTTP callback listener
2. Opens the user's browser to the OAuth authorization URL
3. Waits for the provider to redirect back with ?code=...
4. Exchanges the code for an access token
5. Returns the token response as a dictionary

Designed for desktop/local apps and CLI tools.

Example:
    from quick_oauth import OAuthConfig, run_oauth_flow

    cfg = OAuthConfig(
        auth_url="https://provider.example.com/oauth/authorize",
        token_url="https://provider.example.com/oauth/token",
        client_id="YOUR_CLIENT_ID",
        scope="openid profile email",
        callback_url="http://127.0.0.1:8765/callback",
    )

    token = run_oauth_flow(cfg, user_id="user123")
    print(token)
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import threading
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional, Tuple

import requests


@dataclass
class OAuthConfig:
    auth_url: str
    token_url: str
    client_id: str
    scope: str
    callback_url: str
    client_secret: Optional[str] = None
    timeout_seconds: int = 300


class OAuthError(Exception):
    """Raised when the OAuth flow fails."""


def _urlsafe_b64_no_padding(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _generate_code_verifier(length: int = 64) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _generate_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return _urlsafe_b64_no_padding(digest)


def _parse_callback_listener(callback_url: str) -> Tuple[str, int, str]:
    parsed = urllib.parse.urlparse(callback_url)

    if parsed.scheme not in ("http", "https"):
        raise OAuthError("callback_url must be http:// or https://")

    if not parsed.hostname:
        raise OAuthError("callback_url must include a hostname")

    host = parsed.hostname
    port = parsed.port
    path = parsed.path or "/"

    if port is None:
        port = 443 if parsed.scheme == "https" else 80

    return host, port, path


class _OAuthCallbackState:
    def __init__(self) -> None:
        self.event = threading.Event()
        self.code: Optional[str] = None
        self.error: Optional[str] = None
        self.error_description: Optional[str] = None
        self.received_state: Optional[str] = None
        self.full_query: Dict[str, Any] = {}


def _make_handler(
    state_holder: _OAuthCallbackState,
    expected_path: str,
) -> type[BaseHTTPRequestHandler]:
    class OAuthCallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)

            if parsed.path != expected_path:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Not found")
                return

            params = urllib.parse.parse_qs(parsed.query)
            flat_params = {k: v[0] if v else "" for k, v in params.items()}

            state_holder.full_query = flat_params
            state_holder.code = flat_params.get("code")
            state_holder.error = flat_params.get("error")
            state_holder.error_description = flat_params.get("error_description")
            state_holder.received_state = flat_params.get("state")
            state_holder.event.set()

            if state_holder.error:
                body = f"""
                <html>
                  <body>
                    <h1>OAuth Failed</h1>
                    <p>{state_holder.error}</p>
                    <p>{state_holder.error_description or ""}</p>
                    <p>You may close this window.</p>
                  </body>
                </html>
                """.encode("utf-8")
            else:
                body = b"""
                <html>
                  <body>
                    <h1>Login complete</h1>
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

    return OAuthCallbackHandler


def _start_callback_server(callback_url: str, state_holder: _OAuthCallbackState) -> Tuple[HTTPServer, threading.Thread]:
    host, port, path = _parse_callback_listener(callback_url)

    handler_cls = _make_handler(state_holder, path)
    server = HTTPServer((host, port), handler_cls)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _build_authorization_url(
    config: OAuthConfig,
    user_id: str,
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
        "login_hint": user_id,
    }

    query = urllib.parse.urlencode(params)
    sep = "&" if "?" in config.auth_url else "?"
    return f"{config.auth_url}{sep}{query}"


def _exchange_code_for_token(
    config: OAuthConfig,
    code: str,
    code_verifier: str,
) -> Dict[str, Any]:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.callback_url,
        "client_id": config.client_id,
        "code_verifier": code_verifier,
    }

    if config.client_secret:
        data["client_secret"] = config.client_secret

    response = requests.post(
        config.token_url,
        data=data,
        timeout=30,
        headers={"Accept": "application/json"},
    )

    content_type = response.headers.get("Content-Type", "")
    if not response.ok:
        try:
            payload = response.json()
        except Exception:
            payload = {"raw": response.text}
        raise OAuthError(f"Token exchange failed: {response.status_code} {payload}")

    if "application/json" in content_type.lower():
        return response.json()

    try:
        return json.loads(response.text)
    except Exception:
        return {"raw": response.text}


def run_oauth_flow(config: OAuthConfig, user_id: str) -> Dict[str, Any]:
    """
    Run the OAuth authorization-code flow with PKCE.

    Args:
        config: OAuth endpoint/settings configuration.
        user_id: A user identifier passed as login_hint to the provider.

    Returns:
        The token response dictionary from the token endpoint.

    Raises:
        OAuthError: If the flow fails, times out, or returns an error.
    """
    callback_state = _OAuthCallbackState()
    code_verifier = _generate_code_verifier()
    code_challenge = _generate_code_challenge(code_verifier)
    state = secrets.token_urlsafe(32)

    server, thread = _start_callback_server(config.callback_url, callback_state)

    try:
        auth_request_url = _build_authorization_url(
            config=config,
            user_id=user_id,
            state=state,
            code_challenge=code_challenge,
        )

        opened = webbrowser.open(auth_request_url)
        if not opened:
            print(f"Open this URL manually:\n{auth_request_url}")

        if not callback_state.event.wait(timeout=config.timeout_seconds):
            raise OAuthError("Timed out waiting for OAuth callback")

        if callback_state.error:
            raise OAuthError(
                f"OAuth provider returned error: {callback_state.error} "
                f"{callback_state.error_description or ''}".strip()
            )

        if callback_state.received_state != state:
            raise OAuthError("State mismatch in OAuth callback")

        if not callback_state.code:
            raise OAuthError("Callback did not include an authorization code")

        token_response = _exchange_code_for_token(
            config=config,
            code=callback_state.code,
            code_verifier=code_verifier,
        )
        return token_response

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
    # Example usage
    # Replace these with your real provider details.
    config = OAuthConfig(
        auth_url="https://provider.example.com/oauth/authorize",
        token_url="https://provider.example.com/oauth/token",
        client_id="YOUR_CLIENT_ID",
        scope="openid profile email",
        callback_url="http://127.0.0.1:8765/callback",
        client_secret=None,  # Optional
        timeout_seconds=300,
    )

    try:
        token = run_oauth_flow(config, user_id="someone@example.com")
        print(json.dumps(token, indent=2))
    except OAuthError as exc:
        print(f"OAuth failed: {exc}")