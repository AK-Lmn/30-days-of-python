from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_key"), "projects", ["key"], unique=True)

    op.create_table(
        "environments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("api_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "key", name="uq_project_env_key"),
    )
    op.create_index(op.f("ix_environments_api_key"), "environments", ["api_key"], unique=True)
    op.create_index(op.f("ix_environments_project_id"), "environments", ["project_id"], unique=False)

    op.create_table(
        "tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tags_name"), "tags", ["name"], unique=True)

    op.create_table(
        "flags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("flag_type", sa.String(length=32), nullable=False),
        sa.Column("default_value", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "key", name="uq_project_flag_key"),
    )
    op.create_index(op.f("ix_flags_key"), "flags", ["key"], unique=False)
    op.create_index(op.f("ix_flags_project_id"), "flags", ["project_id"], unique=False)

    op.create_table(
        "flag_tags",
        sa.Column("flag_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["flag_id"], ["flags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("flag_id", "tag_id"),
    )

    op.create_table(
        "flag_environment_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("flag_id", sa.Uuid(), nullable=False),
        sa.Column("environment_id", sa.Uuid(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("percentage", sa.Integer(), nullable=False),
        sa.Column("variant_value", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["flag_id"], ["flags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("flag_id", "environment_id", name="uq_flag_environment"),
    )
    op.create_index(op.f("ix_flag_environment_states_environment_id"), "flag_environment_states", ["environment_id"], unique=False)
    op.create_index(op.f("ix_flag_environment_states_flag_id"), "flag_environment_states", ["flag_id"], unique=False)

    op.create_table(
        "targeting_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("flag_environment_id", sa.Uuid(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("serve_value", sa.JSON(), nullable=False),
        sa.Column("percentage", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["flag_environment_id"], ["flag_environment_states.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_targeting_rules_flag_environment_id"), "targeting_rules", ["flag_environment_id"], unique=False)

    op.create_table(
        "rule_conditions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("attribute", sa.String(length=64), nullable=False),
        sa.Column("operator", sa.String(length=32), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["targeting_rules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rule_conditions_rule_id"), "rule_conditions", ["rule_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_project_id"), "audit_logs", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("rule_conditions")
    op.drop_table("targeting_rules")
    op.drop_table("flag_environment_states")
    op.drop_table("flag_tags")
    op.drop_table("flags")
    op.drop_table("tags")
    op.drop_table("environments")
    op.drop_table("projects")
