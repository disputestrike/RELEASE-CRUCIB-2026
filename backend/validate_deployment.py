"""
Validate deployment for CrucibAI — validates deployment config/output before deploy.
Reduces failed deploys, clearer errors for Vercel/Netlify/Railway.
"""
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]
    platform: str


def validate_vercel(files: Dict[str, str], config: Dict[str, Any]) -> ValidationResult:
    """Validate for Vercel: require package.json for Node, or output dir present."""
    errors = []
    warnings = []
    if not files:
        errors.append("No files to deploy")
    if "package.json" not in files and not any(k.endswith("package.json") for k in files):
        warnings.append("No package.json found; Vercel may need it for Node builds")
    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings, platform="vercel")


def validate_netlify(files: Dict[str, str], config: Dict[str, Any]) -> ValidationResult:
    """Validate for Netlify: recommend netlify.toml or _redirects."""
    errors = []
    warnings = []
    if not files:
        errors.append("No files to deploy")
    if not any("netlify" in k.lower() or "_redirects" in k for k in files):
        warnings.append("No netlify.toml or _redirects; default build may be used")
    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings, platform="netlify")


def validate_railway(files: Dict[str, str], config: Dict[str, Any]) -> ValidationResult:
    """Validate for Railway: recommend Procfile or package.json start script."""
    errors = []
    warnings = []
    if not files:
        errors.append("No files to deploy")
    if "Procfile" not in files and not any(k.endswith("Procfile") for k in files):
        if "package.json" in files:
            warnings.append("Railway can use npm start from package.json")
        else:
            warnings.append("No Procfile or package.json; set start command in Railway")
    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings, platform="railway")


def validate_deployment(platform: str, files: Dict[str, str], config: Optional[Dict[str, Any]] = None) -> ValidationResult:
    """Validate deployment for given platform. platform in ('vercel', 'netlify', 'railway')."""
    config = config or {}
    platform = (platform or "").lower()
    if platform == "vercel":
        return validate_vercel(files, config)
    if platform == "netlify":
        return validate_netlify(files, config)
    if platform == "railway":
        return validate_railway(files, config)
    return ValidationResult(valid=True, errors=[], warnings=[f"Unknown platform: {platform}"], platform=platform)
