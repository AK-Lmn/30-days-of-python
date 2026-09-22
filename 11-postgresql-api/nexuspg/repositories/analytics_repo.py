from __future__ import annotations
import uuid
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from nexuspg.core.errors import EntityNotFoundError
from nexuspg.db.models import (
    Environment,
    Flag,
    FlagEnvironmentState,
    Project,
    Tag,
    TargetingRule,
    flag_tags,
)
from nexuspg.schemas.analytics import (
    EnvironmentHealthItem,
    ProjectAnalyticsResponse,
    TagDistributionItem,
)


class AnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_project_analytics(self, project_id: uuid.UUID) -> ProjectAnalyticsResponse:
        project_stmt = select(Project).where(Project.id == project_id)
        proj_res = await self.session.execute(project_stmt)
        project = proj_res.scalars().first()
        if not project:
            raise EntityNotFoundError("Project", project_id)

        flags_count_stmt = select(func.count(Flag.id)).where(Flag.project_id == project_id)
        total_flags = (await self.session.execute(flags_count_stmt)).scalar() or 0

        envs_count_stmt = select(func.count(Environment.id)).where(Environment.project_id == project_id)
        total_envs = (await self.session.execute(envs_count_stmt)).scalar() or 0

        type_stmt = (
            select(Flag.flag_type, func.count(Flag.id))
            .where(Flag.project_id == project_id)
            .group_by(Flag.flag_type)
        )
        type_res = await self.session.execute(type_stmt)
        flag_types = {row[0]: row[1] for row in type_res.all()}

        tag_stmt = (
            select(Tag.name, func.count(flag_tags.c.flag_id))
            .join(flag_tags, Tag.id == flag_tags.c.tag_id)
            .join(Flag, Flag.id == flag_tags.c.flag_id)
            .where(Flag.project_id == project_id)
            .group_by(Tag.name)
            .order_by(func.count(flag_tags.c.flag_id).desc())
        )
        tag_res = await self.session.execute(tag_stmt)
        tag_distribution = [
            TagDistributionItem(tag_name=row[0], flag_count=row[1])
            for row in tag_res.all()
        ]

        env_stmt = select(Environment).where(Environment.project_id == project_id).order_by(Environment.name.asc())
        envs_res = await self.session.execute(env_stmt)
        environments = envs_res.scalars().all()

        environments_health: list[EnvironmentHealthItem] = []
        for env in environments:
            state_stmt = (
                select(
                    func.count(FlagEnvironmentState.id),
                    func.sum(case((FlagEnvironmentState.enabled == True, 1), else_=0)),
                    func.sum(case((FlagEnvironmentState.enabled == False, 1), else_=0)),
                )
                .where(FlagEnvironmentState.environment_id == env.id)
            )
            state_res = await self.session.execute(state_stmt)
            total_st, enabled_st, disabled_st = state_res.first() or (0, 0, 0)

            rules_count_stmt = (
                select(func.count(TargetingRule.id))
                .join(FlagEnvironmentState, TargetingRule.flag_environment_id == FlagEnvironmentState.id)
                .where(FlagEnvironmentState.environment_id == env.id)
            )
            rule_count = (await self.session.execute(rules_count_stmt)).scalar() or 0

            environments_health.append(
                EnvironmentHealthItem(
                    environment_key=env.key,
                    environment_name=env.name,
                    total_flags=total_st or 0,
                    enabled_flags=enabled_st or 0,
                    disabled_flags=disabled_st or 0,
                    rule_count=rule_count,
                )
            )

        return ProjectAnalyticsResponse(
            project_id=project.id,
            project_key=project.key,
            project_name=project.name,
            total_flags=total_flags,
            total_environments=total_envs,
            flag_types=flag_types,
            tag_distribution=tag_distribution,
            environments_health=environments_health,
        )
