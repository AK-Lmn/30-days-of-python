import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from nexuspg.db.models import (
    Environment,
    Flag,
    FlagEnvironmentState,
    Project,
    RuleCondition,
    TargetingRule,
)


@pytest.mark.asyncio
async def test_project_cascade_delete(client: AsyncClient, db_session: AsyncSession):
    proj_res = await client.post(
        "/api/v1/projects",
        json={"key": "cascade-proj", "name": "Cascade Project"},
    )
    assert proj_res.status_code == 201

    flag_res = await client.post(
        "/api/v1/projects/cascade-proj/flags",
        json={
            "key": "cascade-flag",
            "name": "Cascade Flag",
            "tags": ["temp"],
        },
    )
    assert flag_res.status_code == 201

    rule_res = await client.put(
        "/api/v1/projects/cascade-proj/flags/cascade-flag/environments/production",
        json={
            "enabled": True,
            "rules": [
                {
                    "name": "Cascade Rule",
                    "serve_value": True,
                    "conditions": [
                        {
                            "attribute": "role",
                            "operator": "equals",
                            "values": "admin",
                        }
                    ],
                }
            ],
        },
    )
    assert rule_res.status_code == 200

    del_res = await client.delete("/api/v1/projects/cascade-proj")
    assert del_res.status_code == 204

    db_session.expire_all()

    proj_count = (
        await db_session.execute(
            select(func.count(Project.id)).where(Project.key == "cascade-proj")
        )
    ).scalar()
    assert proj_count == 0

    flag_count = (
        await db_session.execute(
            select(func.count(Flag.id)).where(Flag.key == "cascade-flag")
        )
    ).scalar()
    assert flag_count == 0

    rule_count = (
        await db_session.execute(
            select(func.count(TargetingRule.id)).where(
                TargetingRule.name == "Cascade Rule"
            )
        )
    ).scalar()
    assert rule_count == 0
