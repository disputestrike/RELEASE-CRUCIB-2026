"""
RBAC: role-based access control (owner, admin, developer, viewer).
"""

from enum import Enum
from typing import Optional


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class Permission(str, Enum):
    MANAGE_BILLING = "manage_billing"
    CREATE_PROJECT = "create_project"
    EDIT_PROJECT = "edit_project"
    DELETE_PROJECT = "delete_project"
    DEPLOY_PROJECT = "deploy_project"
    VIEW_PROJECT = "view_project"
    EDIT_SETTINGS = "edit_settings"
    VIEW_AUDIT = "view_audit"
    MANAGE_MFA = "manage_mfa"
    INVITE_MEMBERS = "invite_members"


ROLE_PERMISSIONS = {
    Role.OWNER: list(Permission),
    Role.ADMIN: [
        Permission.CREATE_PROJECT,
        Permission.EDIT_PROJECT,
        Permission.DELETE_PROJECT,
        Permission.DEPLOY_PROJECT,
        Permission.VIEW_PROJECT,
        Permission.EDIT_SETTINGS,
        Permission.VIEW_AUDIT,
        Permission.MANAGE_MFA,
        Permission.INVITE_MEMBERS,
    ],
    Role.DEVELOPER: [
        Permission.CREATE_PROJECT,
        Permission.EDIT_PROJECT,
        Permission.DEPLOY_PROJECT,
        Permission.VIEW_PROJECT,
        Permission.EDIT_SETTINGS,
        Permission.MANAGE_MFA,
    ],
    Role.VIEWER: [Permission.VIEW_PROJECT, Permission.VIEW_AUDIT],
}


def get_user_role(user: dict) -> Role:
    """Return user's role; default owner for backward compatibility."""
    r = (user or {}).get("role")
    if r in ("owner", "admin", "developer", "viewer"):
        return Role(r)
    return Role.OWNER


def has_permission(user: dict, permission: Permission) -> bool:
    """Check if user has permission."""
    role = get_user_role(user)
    return permission in ROLE_PERMISSIONS.get(role, [])
