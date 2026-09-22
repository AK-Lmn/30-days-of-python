import os
import pytest
from alembic import command
from alembic.config import Config


def test_alembic_migrations():
    ini_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "alembic.ini"
    )
    cfg = Config(ini_path)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
