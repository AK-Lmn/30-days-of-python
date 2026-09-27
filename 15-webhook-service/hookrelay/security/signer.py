import hashlib
import hmac
import time


def compute_hmac_sha256(raw_body: bytes, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()


def generate_delivery_signature(
    raw_body: bytes,
    secret: str,
    timestamp: int | None = None,
) -> tuple[str, int]:
    if timestamp is None:
        timestamp = int(time.time())

    signed_payload = f"{timestamp}.".encode("utf-8") + raw_body
    hex_digest = hmac.new(
        secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    signature_header = f"t={timestamp},v1={hex_digest}"
    return signature_header, timestamp


def sign_payload(
    raw_body: bytes,
    secret: str,
    event_id: str,
    delivery_id: str,
    timestamp: int | None = None,
) -> dict[str, str]:
    sig_header, ts = generate_delivery_signature(raw_body, secret, timestamp)
    return {
        "Content-Type": "application/json",
        "X-HookRelay-Event-Id": event_id,
        "X-HookRelay-Delivery-Id": delivery_id,
        "X-HookRelay-Timestamp": str(ts),
        "X-HookRelay-Signature": sig_header,
    }
