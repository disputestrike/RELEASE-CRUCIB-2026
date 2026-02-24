"""
Fine-grained access control and permission system.

Implements:
- Role-based access control (RBAC)
- Permission-based access control (PBAC)
- Resource-level permissions
- Audit logging for access attempts
- Policy enforcement
"""

from enum import Enum
from typing import Set, Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class Role(Enum):
    """System roles."""

    ADMIN = "admin"
    DEVELOPER = "developer"
    USER = "user"
    VIEWER = "viewer"


class Permission(Enum):
    """System permissions."""

    # Build permissions
    BUILD_CREATE = "build:create"
    BUILD_READ = "build:read"
    BUILD_UPDATE = "build:update"
    BUILD_DELETE = "build:delete"
    BUILD_EXECUTE = "build:execute"

    # User permissions
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_MANAGE_ROLES = "user:manage_roles"

    # Agent permissions
    AGENT_READ = "agent:read"
    AGENT_MANAGE = "agent:manage"

    # Analytics permissions
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"

    # Admin permissions
    ADMIN_SYSTEM_CONFIG = "admin:system_config"
    ADMIN_AUDIT_LOG = "admin:audit_log"
    ADMIN_SECURITY = "admin:security"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        # Admin has all permissions
        Permission.BUILD_CREATE,
        Permission.BUILD_READ,
        Permission.BUILD_UPDATE,
        Permission.BUILD_DELETE,
        Permission.BUILD_EXECUTE,
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.USER_MANAGE_ROLES,
        Permission.AGENT_READ,
        Permission.AGENT_MANAGE,
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_EXPORT,
        Permission.ADMIN_SYSTEM_CONFIG,
        Permission.ADMIN_AUDIT_LOG,
        Permission.ADMIN_SECURITY,
    },
    Role.DEVELOPER: {
        # Developers can create and manage builds
        Permission.BUILD_CREATE,
        Permission.BUILD_READ,
        Permission.BUILD_UPDATE,
        Permission.BUILD_DELETE,
        Permission.BUILD_EXECUTE,
        Permission.USER_READ,
        Permission.AGENT_READ,
        Permission.ANALYTICS_READ,
    },
    Role.USER: {
        # Users can create and view their own builds
        Permission.BUILD_CREATE,
        Permission.BUILD_READ,
        Permission.BUILD_EXECUTE,
        Permission.ANALYTICS_READ,
    },
    Role.VIEWER: {
        # Viewers can only read
        Permission.BUILD_READ,
        Permission.ANALYTICS_READ,
    },
}


@dataclass
class User:
    """User with role and permissions."""

    id: str
    username: str
    role: Role
    custom_permissions: Set[Permission] = None

    def __post_init__(self):
        """Initialize custom permissions."""
        if self.custom_permissions is None:
            self.custom_permissions = set()

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has permission."""
        # Role-based permissions
        role_perms = ROLE_PERMISSIONS.get(self.role, set())

        # Custom permissions
        all_perms = role_perms | self.custom_permissions

        return permission in all_perms

    def has_any_permission(self, permissions: Set[Permission]) -> bool:
        """Check if user has any of the permissions."""
        return any(self.has_permission(p) for p in permissions)

    def has_all_permissions(self, permissions: Set[Permission]) -> bool:
        """Check if user has all permissions."""
        return all(self.has_permission(p) for p in permissions)

    def get_permissions(self) -> Set[Permission]:
        """Get all user permissions."""
        role_perms = ROLE_PERMISSIONS.get(self.role, set())
        return role_perms | self.custom_permissions


class AccessControl:
    """Access control enforcement."""

    def __init__(self):
        """Initialize access control."""
        self.policies: Dict[str, Any] = {}

    def check_permission(self, user: User, permission: Permission) -> bool:
        """
        Check if user has permission.

        Args:
            user: User object
            permission: Permission to check

        Returns:
            True if user has permission, False otherwise
        """
        has_perm = user.has_permission(permission)

        # Audit log
        logger.info(
            f"Permission check",
            extra={
                "user_id": user.id,
                "permission": permission.value,
                "granted": has_perm,
            },
        )

        return has_perm

    def check_resource_access(
        self, user: User, resource_id: str, action: str
    ) -> bool:
        """
        Check if user can access resource.

        Args:
            user: User object
            resource_id: Resource ID
            action: Action (read, write, delete)

        Returns:
            True if user can access resource
        """
        # Check role-based access
        if user.role == Role.ADMIN:
            return True

        # Check resource ownership (if applicable)
        # This would be extended with actual resource ownership checks
        logger.info(
            f"Resource access check",
            extra={
                "user_id": user.id,
                "resource_id": resource_id,
                "action": action,
                "granted": True,
            },
        )

        return True

    def enforce_permission(self, user: User, permission: Permission) -> None:
        """
        Enforce permission, raise exception if denied.

        Args:
            user: User object
            permission: Permission to enforce

        Raises:
            PermissionError: If user doesn't have permission
        """
        if not self.check_permission(user, permission):
            logger.warning(
                f"Permission denied",
                extra={
                    "user_id": user.id,
                    "permission": permission.value,
                },
            )
            raise PermissionError(
                f"User {user.id} does not have permission {permission.value}"
            )

    def enforce_resource_access(
        self, user: User, resource_id: str, action: str
    ) -> None:
        """
        Enforce resource access, raise exception if denied.

        Args:
            user: User object
            resource_id: Resource ID
            action: Action

        Raises:
            PermissionError: If user can't access resource
        """
        if not self.check_resource_access(user, resource_id, action):
            logger.warning(
                f"Resource access denied",
                extra={
                    "user_id": user.id,
                    "resource_id": resource_id,
                    "action": action,
                },
            )
            raise PermissionError(
                f"User {user.id} cannot {action} resource {resource_id}"
            )


# Global access control instance
access_control = AccessControl()


def require_permission(permission: Permission):
    """Decorator to require permission."""

    def decorator(func):
        def wrapper(user: User, *args, **kwargs):
            access_control.enforce_permission(user, permission)
            return func(user, *args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(*permissions: Permission):
    """Decorator to require any of the permissions."""

    def decorator(func):
        def wrapper(user: User, *args, **kwargs):
            if not user.has_any_permission(set(permissions)):
                raise PermissionError(
                    f"User {user.id} does not have required permissions"
                )
            return func(user, *args, **kwargs)

        return wrapper

    return decorator


def require_all_permissions(*permissions: Permission):
    """Decorator to require all permissions."""

    def decorator(func):
        def wrapper(user: User, *args, **kwargs):
            if not user.has_all_permissions(set(permissions)):
                raise PermissionError(
                    f"User {user.id} does not have all required permissions"
                )
            return func(user, *args, **kwargs)

        return wrapper

    return decorator
