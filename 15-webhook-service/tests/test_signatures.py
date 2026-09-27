import time
import pytest
from hookrelay.security.signer import (
    compute_hmac_sha256,
    generate_delivery_signature,
    sign_payload,
)
from hookrelay.security.verifier import (
    WebhookVerificationError,
    verify_endpoint_signature,
    verify_github_signature,
    verify_hmac_sha256,
    verify_stripe_signature,
    verify_token_match,
)


def test_hmac_sha256_verification():
    payload = b'{"hello": "world"}'
    secret = "super_secret"
    hex_digest = compute_hmac_sha256(payload, secret)

    assert verify_hmac_sha256(payload, secret, hex_digest) is True
    assert verify_hmac_sha256(payload, secret, f"sha256={hex_digest}") is True
    assert verify_hmac_sha256(payload, secret, "wrong_signature") is False
    assert verify_hmac_sha256(b'{"different": 1}', secret, hex_digest) is False


def test_github_signature_verification():
    payload = b'{"ref": "refs/heads/main"}'
    secret = "gh_secret_key"
    hex_digest = compute_hmac_sha256(payload, secret)
    header = f"sha256={hex_digest}"

    assert verify_github_signature(payload, secret, header) is True
    assert verify_github_signature(payload, secret, "sha256=invalid") is False
    assert verify_github_signature(payload, secret, None) is False


def test_stripe_signature_verification():
    payload = b'{"type": "payment_intent.succeeded"}'
    secret = "whsec_test_secret"
    now_ts = int(time.time())

    sig_header, _ = generate_delivery_signature(payload, secret, timestamp=now_ts)

    assert verify_stripe_signature(payload, secret, sig_header, tolerance_seconds=300) is True
    assert verify_stripe_signature(payload, "wrong_secret", sig_header) is False
    assert verify_stripe_signature(payload, secret, "t=bad,v1=bad") is False
    assert verify_stripe_signature(payload, secret, None) is False

    expired_ts = now_ts - 500
    expired_sig, _ = generate_delivery_signature(payload, secret, timestamp=expired_ts)
    assert verify_stripe_signature(payload, secret, expired_sig, tolerance_seconds=300) is False


def test_token_match_verification():
    secret = "token_secret_123"
    assert verify_token_match(secret, "token_secret_123") is True
    assert verify_token_match(secret, "Bearer token_secret_123") is True
    assert verify_token_match(secret, "Bearer wrong_token") is False
    assert verify_token_match(secret, None) is False


def test_endpoint_signature_dispatcher():
    payload = b'{"event": "ping"}'
    secret = "dispatcher_secret"

    assert verify_endpoint_signature("none", "", payload, {}) is True

    token_headers = {"X-Webhook-Token": secret}
    assert verify_endpoint_signature("token", secret, payload, token_headers) is True

    with pytest.raises(WebhookVerificationError):
        verify_endpoint_signature("token", secret, payload, {"X-Webhook-Token": "bad"})

    with pytest.raises(WebhookVerificationError):
        verify_endpoint_signature("token", secret, payload, {})

    hex_val = compute_hmac_sha256(payload, secret)

    hmac_headers = {"X-Signature": hex_val}
    assert verify_endpoint_signature("hmac_sha256", secret, payload, hmac_headers) is True

    gh_headers = {"X-Hub-Signature-256": f"sha256={hex_val}"}
    assert verify_endpoint_signature("github", secret, payload, gh_headers) is True

    stripe_sig, _ = generate_delivery_signature(payload, secret)
    stripe_headers = {"Stripe-Signature": stripe_sig}
    assert verify_endpoint_signature("stripe", secret, payload, stripe_headers) is True

    with pytest.raises(WebhookVerificationError):
        verify_endpoint_signature("unknown_strategy", secret, payload, {})


def test_sign_payload_creates_expected_headers():
    payload = b'{"msg": "forward"}'
    secret = "sub_secret"
    headers = sign_payload(
        raw_body=payload,
        secret=secret,
        event_id="evt_01",
        delivery_id="del_01",
        timestamp=1700000000,
    )

    assert headers["Content-Type"] == "application/json"
    assert headers["X-HookRelay-Event-Id"] == "evt_01"
    assert headers["X-HookRelay-Delivery-Id"] == "del_01"
    assert headers["X-HookRelay-Timestamp"] == "1700000000"
    assert headers["X-HookRelay-Signature"].startswith("t=1700000000,v1=")
