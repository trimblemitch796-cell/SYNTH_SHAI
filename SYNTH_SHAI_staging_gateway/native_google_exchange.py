"""In-process staging WSGI application. Deployment and live key management require review."""
import base64
import hashlib
import json
import os
import secrets
import time

from . import google_oidc_preflight as oidc
from .google_jwks_rotation import verify_with_cached_google_keys
from .google_login_challenge import consume_challenge, issue_challenge
from .pilot_security import revoke_session, verify_session_token


def segment(value):
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class NativeExchange:
    """Host, audience, account allowlist, signer, key cache and limiter are operator-owned."""

    def __init__(self, *, host, client, android_client, allowed_subjects, store, cache, signer, limiter):
        self.host = host
        self.client = client
        self.android_client = android_client
        self.allowed_subjects = frozenset(allowed_subjects)
        self.store = store
        self.cache = cache
        self.signer = signer
        self.limiter = limiter

    def __call__(self, env, start_response):
        try:
            status, body = self.dispatch(env)
        except (ValueError, UnicodeError, RecursionError):
            status, body = "400 Bad Request", {}
        except Exception:
            # An unavailable trusted dependency must never authorize a caller.
            status, body = "503 Service Unavailable", {}
        raw = b"" if status.startswith("204") else json.dumps(body).encode()
        start_response(status, [("Content-Type", "application/json"),
                                ("Cache-Control", "no-store"), ("Content-Length", str(len(raw)))])
        return [raw]

    def dispatch(self, env):
        if (env.get("wsgi.url_scheme") != "https" or env.get("HTTP_HOST") != self.host
                or env.get("QUERY_STRING") or env.get("REQUEST_METHOD") != "POST"
                or env.get("CONTENT_TYPE") != "application/json"):
            return "400 Bad Request", {}
        route = env.get("PATH_INFO")
        if route not in ("/auth/challenge", "/auth/google", "/auth/logout"):
            return "404 Not Found", {}
        if not self.limiter(env.get("REMOTE_ADDR"), route):
            return "429 Too Many Requests", {}
        size = int(env["CONTENT_LENGTH"])
        if not 0 < size <= 12288:
            return "400 Bad Request", {}
        raw = env["wsgi.input"].read(size)
        if len(raw) != size:
            return "400 Bad Request", {}
        body = json.loads(raw.decode("utf-8"), object_pairs_hook=oidc._unique_fields,
                          parse_constant=oidc._reject_non_json_number)
        if type(body) is not dict:
            return "400 Bad Request", {}
        if route == "/auth/logout":
            auth = env.get("HTTP_AUTHORIZATION", "")
            identity = verify_session_token(auth[7:]) if auth.startswith("Bearer ") else None
            if body or not identity:
                return "401 Unauthorized", {}
            revoke_session(os.environ["SHAI_GATEWAY_DB"], identity.jti)
            return "204 No Content", {}
        if route == "/auth/challenge":
            if body != {"flow": "google-id-token-v1", "platform": "android"}:
                return "400 Bad Request", {}
            bearer = secrets.token_urlsafe(32)
            pending = issue_challenge(self.store, digest(bearer))
            if pending is None:
                return "503 Service Unavailable", {}
            return "201 Created", {"challenge_id": pending.transaction_id, "nonce": pending.nonce,
                                   "completion_token": bearer, "expires_in": 300}
        if set(body) != {"challenge_id", "completion_token", "google_id_token"}:
            return "400 Bad Request", {}
        token = body["google_id_token"]
        bearer = body["completion_token"]
        nonce = None
        if type(token) is str and len(token) <= 8192:
            try:
                _, payload, _ = token.split(".")
                # Candidate only. Atomic consume matches its digest to server-issued state.
                nonce = oidc._json_object(payload).get("nonce")
            except (ValueError, RecursionError, UnicodeError):
                pass
        binding = digest(bearer) if type(bearer) is str and len(bearer) == 43 else None
        if not consume_challenge(self.store, body["challenge_id"], nonce, binding):
            return "401 Unauthorized", {}
        identity = verify_with_cached_google_keys(token, self.cache, client_id=self.client,
                                                  authorized_party=self.android_client,
                                                  expected_nonce=nonce)
        if identity is None or identity.subject not in self.allowed_subjects:
            return "401 Unauthorized", {}
        now = int(time.time())
        claims = {"iss": os.environ["SHAI_SESSION_ISSUER"], "aud": os.environ["SHAI_SESSION_AUDIENCE"],
                  "sub": "google:" + digest(identity.subject), "jti": secrets.token_urlsafe(32),
                  "iat": now, "nbf": now, "exp": now + 900}
        unsigned = segment({"alg": "EdDSA", "typ": "JWT"}) + "." + segment(claims)
        signature = self.signer.sign(unsigned.encode("ascii"))
        session = unsigned + "." + base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
        if verify_session_token(session) is None:
            return "503 Service Unavailable", {}
        return "200 OK", {"token_type": "Bearer", "access_token": session, "expires_in": 900}
