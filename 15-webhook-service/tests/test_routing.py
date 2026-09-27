import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from hookrelay.models.subscription import Subscription
from hookrelay.schemas.subscription import SubscriptionCreate
from hookrelay.services.subscription_service import SubscriptionService


def test_subscription_pattern_matching():
    wildcard_sub = Subscription(
        name="Wildcard",
        target_url="http://example.com/all",
        event_patterns=["*"],
        is_active=True,
    )
    assert SubscriptionService.matches_event(wildcard_sub, "order.created") is True
    assert SubscriptionService.matches_event(wildcard_sub, "payment.failed") is True

    prefix_sub = Subscription(
        name="Order Prefix",
        target_url="http://example.com/orders",
        event_patterns=["order.*"],
        is_active=True,
    )
    assert SubscriptionService.matches_event(prefix_sub, "order.created") is True
    assert SubscriptionService.matches_event(prefix_sub, "order.updated") is True
    assert SubscriptionService.matches_event(prefix_sub, "payment.succeeded") is False

    multi_sub = Subscription(
        name="Multi",
        target_url="http://example.com/multi",
        event_patterns=["payment.refunded", "customer.*"],
        is_active=True,
    )
    assert SubscriptionService.matches_event(multi_sub, "payment.refunded") is True
    assert SubscriptionService.matches_event(multi_sub, "customer.deleted") is True
    assert SubscriptionService.matches_event(multi_sub, "payment.created") is False

    inactive_sub = Subscription(
        name="Inactive",
        target_url="http://example.com/inactive",
        event_patterns=["*"],
        is_active=False,
    )
    assert SubscriptionService.matches_event(inactive_sub, "order.created") is False


@pytest.mark.asyncio
async def test_get_matching_subscriptions(db_session: AsyncSession):
    sub1 = await SubscriptionService.create(
        db_session,
        SubscriptionCreate(
            name="All Events",
            target_url="http://example.com/all",
            event_patterns=["*"],
        ),
    )
    sub2 = await SubscriptionService.create(
        db_session,
        SubscriptionCreate(
            name="Orders Only",
            target_url="http://example.com/orders",
            event_patterns=["order.*"],
        ),
    )
    sub3 = await SubscriptionService.create(
        db_session,
        SubscriptionCreate(
            name="Users Only (Inactive)",
            target_url="http://example.com/users",
            event_patterns=["user.*"],
            is_active=False,
        ),
    )

    matches_order = await SubscriptionService.get_matching_subscriptions(
        db_session, "order.shipped"
    )
    matched_ids = [s.id for s in matches_order]
    assert sub1.id in matched_ids
    assert sub2.id in matched_ids
    assert sub3.id not in matched_ids

    matches_user = await SubscriptionService.get_matching_subscriptions(
        db_session, "user.created"
    )
    user_matched_ids = [s.id for s in matches_user]
    assert sub1.id in user_matched_ids
    assert sub2.id not in user_matched_ids
    assert sub3.id not in user_matched_ids
