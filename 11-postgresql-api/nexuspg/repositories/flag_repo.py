from __future__ import annotations
from typing import Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from nexuspg.core.errors import EntityAlreadyExistsError, EntityNotFoundError
from nexuspg.db.models import (
    Environment,
    Flag,
    FlagEnvironmentState,
    RuleCondition,
    Tag,
    TargetingRule,
    flag_tags,
)
from nexuspg.schemas.flag import (
    FlagCreate,
    FlagEnvironmentStateUpdate,
    FlagUpdate,
)


class FlagRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_tags(self, tag_names: list[str]) -> list[Tag]:
        cleaned_names = [t.strip().lower() for t in tag_names if t.strip()]
        if not cleaned_names:
            return []

        stmt = select(Tag).where(Tag.name.in_(cleaned_names))
        res = await self.session.execute(stmt)
        existing_tags = {tag.name: tag for tag in res.scalars().all()}

        result_tags: list[Tag] = []
        for name in set(cleaned_names):
            if name in existing_tags:
                result_tags.append(existing_tags[name])
            else:
                new_tag = Tag(name=name)
                self.session.add(new_tag)
                result_tags.append(new_tag)

        await self.session.flush()
        return result_tags

    async def get_by_key(self, project_id: uuid.UUID, key: str) -> Optional[Flag]:
        stmt = (
            select(Flag)
            .where(Flag.project_id == project_id, Flag.key == key)
            .options(selectinload(Flag.tags))
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_detail(self, project_id: uuid.UUID, key: str) -> Optional[Flag]:
        stmt = (
            select(Flag)
            .where(Flag.project_id == project_id, Flag.key == key)
            .options(
                selectinload(Flag.tags),
                selectinload(Flag.flag_states)
                .selectinload(FlagEnvironmentState.rules)
                .selectinload(TargetingRule.conditions),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list(
        self,
        project_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
        tag: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[list[Flag], int]:
        base_query = select(Flag).where(Flag.project_id == project_id)

        if tag:
            base_query = base_query.where(
                Flag.tags.any(Tag.name == tag.strip().lower())
            )

        if search:
            pattern = f"%{search.strip().lower()}%"
            base_query = base_query.where(
                func.lower(Flag.key).like(pattern) | func.lower(Flag.name).like(pattern)
            )

        count_stmt = select(func.count()).select_from(base_query.subquery())
        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            base_query.options(selectinload(Flag.tags))
            .order_by(Flag.name.asc())
            .offset(offset)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        flags = list(res.scalars().all())
        return flags, total

    async def create(self, project_id: uuid.UUID, flag_in: FlagCreate) -> Flag:
        existing = await self.get_by_key(project_id, flag_in.key)
        if existing:
            raise EntityAlreadyExistsError("Flag", "key", flag_in.key)

        tags = await self.get_or_create_tags(flag_in.tags)

        flag = Flag(
            project_id=project_id,
            key=flag_in.key,
            name=flag_in.name,
            description=flag_in.description,
            flag_type=flag_in.flag_type,
            default_value=flag_in.default_value,
            tags=tags,
        )
        self.session.add(flag)
        await self.session.flush()

        env_stmt = select(Environment).where(Environment.project_id == project_id)
        env_res = await self.session.execute(env_stmt)
        envs = env_res.scalars().all()

        for env in envs:
            state = FlagEnvironmentState(
                flag_id=flag.id,
                environment_id=env.id,
                enabled=False,
                percentage=100,
            )
            self.session.add(state)

        await self.session.flush()
        await self.session.refresh(flag, ["tags", "flag_states"])
        return flag

    async def update(self, project_id: uuid.UUID, key: str, flag_in: FlagUpdate) -> Flag:
        flag = await self.get_by_key(project_id, key)
        if not flag:
            raise EntityNotFoundError("Flag", key)

        if flag_in.name is not None:
            flag.name = flag_in.name
        if flag_in.description is not None:
            flag.description = flag_in.description
        if flag_in.default_value is not None:
            flag.default_value = flag_in.default_value
        if flag_in.tags is not None:
            flag.tags = await self.get_or_create_tags(flag_in.tags)

        await self.session.flush()
        await self.session.refresh(flag, ["tags"])
        return flag

    async def delete(self, project_id: uuid.UUID, key: str) -> bool:
        flag = await self.get_by_key(project_id, key)
        if not flag:
            return False

        await self.session.delete(flag)
        await self.session.flush()
        return True

    async def get_environment_state(
        self,
        flag_id: uuid.UUID,
        environment_id: uuid.UUID,
    ) -> Optional[FlagEnvironmentState]:
        stmt = (
            select(FlagEnvironmentState)
            .where(
                FlagEnvironmentState.flag_id == flag_id,
                FlagEnvironmentState.environment_id == environment_id,
            )
            .options(
                selectinload(FlagEnvironmentState.rules)
                .selectinload(TargetingRule.conditions)
            )
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def update_environment_state(
        self,
        flag_id: uuid.UUID,
        environment_id: uuid.UUID,
        state_in: FlagEnvironmentStateUpdate,
    ) -> FlagEnvironmentState:
        state = await self.get_environment_state(flag_id, environment_id)
        if not state:
            raise EntityNotFoundError("FlagEnvironmentState", f"{flag_id}:{environment_id}")

        if state_in.enabled is not None:
            state.enabled = state_in.enabled
        if state_in.percentage is not None:
            state.percentage = state_in.percentage
        if state_in.variant_value is not None:
            state.variant_value = state_in.variant_value

        if state_in.rules is not None:
            state.rules.clear()
            await self.session.flush()

            for rule_data in state_in.rules:
                rule = TargetingRule(
                    flag_environment_id=state.id,
                    priority=rule_data.priority,
                    name=rule_data.name,
                    serve_value=rule_data.serve_value,
                    percentage=rule_data.percentage,
                )
                for cond_data in rule_data.conditions:
                    cond = RuleCondition(
                        attribute=cond_data.attribute,
                        operator=cond_data.operator,
                        values=cond_data.values,
                    )
                    rule.conditions.append(cond)
                state.rules.append(rule)

        await self.session.flush()
        await self.session.refresh(state, ["rules"])
        return state

    async def list_for_evaluation(
        self,
        project_id: uuid.UUID,
        environment_id: uuid.UUID,
        flag_keys: Optional[list[str]] = None,
    ) -> list[tuple[Flag, FlagEnvironmentState]]:
        stmt = (
            select(Flag, FlagEnvironmentState)
            .join(FlagEnvironmentState, Flag.id == FlagEnvironmentState.flag_id)
            .where(
                Flag.project_id == project_id,
                FlagEnvironmentState.environment_id == environment_id,
            )
            .options(
                selectinload(FlagEnvironmentState.rules)
                .selectinload(TargetingRule.conditions)
            )
        )
        if flag_keys:
            stmt = stmt.where(Flag.key.in_(flag_keys))

        res = await self.session.execute(stmt)
        return list(res.all())
