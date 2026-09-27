from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


ROLE_HIERARCHY: dict[Role, int] = {
    Role.ADMIN: 3,
    Role.MANAGER: 2,
    Role.USER: 1,
}

ROLE_SCOPES: dict[Role, list[str]] = {
    Role.ADMIN: ["*"],
    Role.MANAGER: [
        "users:read",
        "sessions:read",
        "audit:read",
        "profile:read",
        "profile:write",
        "sessions:read_self",
        "sessions:revoke_self",
    ],
    Role.USER: [
        "profile:read",
        "profile:write",
        "sessions:read_self",
        "sessions:revoke_self",
    ],
}


def get_scopes_for_role(role: str) -> list[str]:
    try:
        role_enum = Role(role)
        return ROLE_SCOPES.get(role_enum, ROLE_SCOPES[Role.USER])
    except ValueError:
        return ROLE_SCOPES[Role.USER]


def is_role_sufficient(user_role: str, required_role: str) -> bool:
    try:
        user_level = ROLE_HIERARCHY.get(Role(user_role), 0)
        required_level = ROLE_HIERARCHY.get(Role(required_role), 0)
        return user_level >= required_level
    except ValueError:
        return False


def has_required_scope(user_scopes: list[str], required_scope: str) -> bool:
    if "*" in user_scopes:
        return True
    if required_scope in user_scopes:
        return True
    return False
