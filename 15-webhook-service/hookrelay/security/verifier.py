import hashlib
import hmac
import time
from typing import Any


class WebhookVerificationError(Exception):
    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def verify_hmac_sha256(raw_body: bytes, secret: str, signature: str) -> bool:
    if not secret or not signature:
        return False
    expected_hex = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    clean_signature = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected_hex, clean_signature)


def verify_github_signature(raw_body: bytes, secret: str, header_value: str | None) -> bool:
    if not header_value:
        return False
    return verify_hmac_sha256(raw_body, secret, header_value)


def verify_stripe_signature(
    raw_body: bytes,
    secret: str,
    header_value: str | None,
    tolerance_seconds: int = 300,
) -> bool:
    if not header_value or not secret:
        return False

    parsed_items: dict[str, list[str]] = {}
    for part in header_value.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            parsed_items.setdefault(k.strip(), []).append(v.strip())

    timestamps = parsed_items.get("t", [])
    signatures = parsed_items.get("v1", [])

    if not timestamps or not signatures:
        return False

    try:
        timestamp_int = int(timestamps[0])
    except ValueError:
        return False

    current_time = int(time.time())
    if abs(current_time - timestamp_int) > tolerance_seconds:
        return False

    signed_payload = f"{timestamp_int}.".encode("utf-8") + raw_body
    expected_hex = hmac.new(
        secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    return any(hmac.compare_digest(expected_hex, sig) for sig in signatures)


def verify_token_match(secret: str, provided_token: str | None) -> bool:
    if not secret or not provided_token:
        return False
    clean_token = provided_token.removeprefix("Bearer ").strip()
    return hmac.compare_digest(secret, clean_token)


def verify_endpoint_signature(
    strategy: str,
    secret: str,
    raw_body: bytes,
    headers: dict[str, Any],
) -> bool:
    normalized_headers = {k.lower(): str(v) for k, v in headers.items()}

    if strategy == "none":
        return True

    if not secret:
        return True

    if strategy == "token":
        candidate_token = (
            normalized_headers.get("x-webhook-token")
            or normalized_headers.get("x-api-key")
            or normalized_headers.get("authorization")
        )
        if not candidate_token:
            raise WebhookVerificationError("Missing authentication token header")
        if not verify_token_match(secret, candidate_token):
            raise WebhookVerificationError("Invalid authentication token")
        return True

    if strategy == "github":
        signature_header = normalized_headers.get("x-hub-signature-256")
        if not signature_header:
            raise WebhookVerificationError("Missing X-Hub-Signature-256 header")
        if not verify_github_signature(raw_body, secret, signature_header):
            raise WebhookVerificationError("Invalid GitHub webhook signature")
        return True

    if strategy == "stripe":
        signature_header = normalized_headers.get("stripe-signature")
        if not signature_header:
            raise WebhookVerificationError("Missing Stripe-Signature header")
        if not verify_stripe_signature(raw_body, secret, signature_header):
            raise WebhookVerificationError("Invalid or expired Stripe signature")
        return True

    if strategy == "hmac_sha256":
        signature_header = (
            normalized_headers.get("x-signature-256")
            or normalized_headers.get("x-hub-signature-256")
            or normalized_headers.get("x-webhook-signature")
            or normalized_headers.get("x-signature")
        )
        if not signature_header:
            raise WebhookVerificationError("Missing HMAC-SHA256 signature header")
        if not verify_hmac_sha256(raw_body, secret, signature_header):
            raise WebhookVerificationError("Invalid HMAC-SHA256 signature")
        return True

    raise WebhookVerificationError(f"Unsupported verification strategy: {strategy}")
