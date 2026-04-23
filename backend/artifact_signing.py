"""
Artifact signing and integrity verification.

Implements:
- GPG signing for releases
- SHA-256 hash verification
- SBOM (Software Bill of Materials) generation
- Signature verification
- Artifact integrity checking
"""

import hashlib
import json
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Artifact:
    """Artifact with metadata."""

    name: str
    version: str
    path: str
    content_hash: str
    signature: Optional[str] = None
    created_at: Optional[str] = None
    signed_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "path": self.path,
            "content_hash": self.content_hash,
            "signature": self.signature,
            "created_at": self.created_at,
            "signed_by": self.signed_by,
        }


class ArtifactSigner:
    """Sign and verify artifacts."""

    def __init__(self):
        """Initialize artifact signer."""
        self.artifacts: Dict[str, Artifact] = {}

    def calculate_hash(self, content: bytes) -> str:
        """
        Calculate SHA-256 hash of content.

        Args:
            content: Content to hash

        Returns:
            Hex-encoded SHA-256 hash
        """
        return hashlib.sha256(content).hexdigest()

    def sign_artifact(
        self,
        name: str,
        version: str,
        path: str,
        content: bytes,
        signed_by: str = "CrucibAI",
    ) -> Artifact:
        """
        Sign an artifact.

        Args:
            name: Artifact name
            version: Artifact version
            path: Artifact path
            content: Artifact content
            signed_by: Who signed the artifact

        Returns:
            Signed artifact
        """
        # Calculate hash
        content_hash = self.calculate_hash(content)

        # Create signature (in production, use GPG)
        signature = self._create_signature(content_hash, signed_by)

        # Create artifact
        artifact = Artifact(
            name=name,
            version=version,
            path=path,
            content_hash=content_hash,
            signature=signature,
            created_at=datetime.utcnow().isoformat(),
            signed_by=signed_by,
        )

        # Store artifact
        artifact_id = f"{name}:{version}"
        self.artifacts[artifact_id] = artifact

        logger.info(
            f"Artifact signed",
            extra={
                "artifact": artifact_id,
                "hash": content_hash[:16],
                "signed_by": signed_by,
            },
        )

        return artifact

    def verify_artifact(
        self,
        name: str,
        version: str,
        content: bytes,
    ) -> bool:
        """
        Verify artifact signature and integrity.

        Args:
            name: Artifact name
            version: Artifact version
            content: Artifact content

        Returns:
            True if artifact is valid, False otherwise
        """
        artifact_id = f"{name}:{version}"

        # Check if artifact exists
        if artifact_id not in self.artifacts:
            logger.warning(f"Artifact not found: {artifact_id}")
            return False

        artifact = self.artifacts[artifact_id]

        # Calculate hash
        content_hash = self.calculate_hash(content)

        # Verify hash
        if content_hash != artifact.content_hash:
            logger.warning(
                f"Artifact hash mismatch: {artifact_id}",
                extra={
                    "expected": artifact.content_hash[:16],
                    "actual": content_hash[:16],
                },
            )
            return False

        # Verify signature
        if not self._verify_signature(artifact.signature, content_hash):
            logger.warning(f"Artifact signature invalid: {artifact_id}")
            return False

        logger.info(f"Artifact verified: {artifact_id}")
        return True

    def _create_signature(self, content_hash: str, signed_by: str) -> str:
        """
        Create signature for content.

        Args:
            content_hash: Content hash
            signed_by: Signer name

        Returns:
            Signature string
        """
        # In production, use GPG:
        # gpg --detach-sign --armor artifact.tar.gz
        # This is a placeholder
        return f"sig_{content_hash[:16]}_{signed_by}"

    def _verify_signature(self, signature: str, content_hash: str) -> bool:
        """
        Verify signature.

        Args:
            signature: Signature to verify
            content_hash: Content hash

        Returns:
            True if signature is valid
        """
        # In production, use GPG:
        # gpg --verify artifact.tar.gz.sig artifact.tar.gz
        # This is a placeholder
        return signature.startswith("sig_") and content_hash[:16] in signature

    def export_signatures(self) -> Dict[str, Dict[str, Any]]:
        """
        Export all artifact signatures.

        Returns:
            Dictionary of artifacts and signatures
        """
        return {
            artifact_id: artifact.to_dict()
            for artifact_id, artifact in self.artifacts.items()
        }


class SBOMGenerator:
    """Generate Software Bill of Materials (SBOM)."""

    def __init__(self):
        """Initialize SBOM generator."""
        self.components: Dict[str, Dict[str, Any]] = {}

    def add_component(
        self,
        name: str,
        version: str,
        component_type: str = "library",
        license: Optional[str] = None,
        purl: Optional[str] = None,
    ) -> None:
        """
        Add component to SBOM.

        Args:
            name: Component name
            version: Component version
            component_type: Type of component
            license: Component license
            purl: Package URL
        """
        component_id = f"{name}:{version}"

        self.components[component_id] = {
            "name": name,
            "version": version,
            "type": component_type,
            "license": license,
            "purl": purl or f"pkg:npm/{name}@{version}",
        }

        logger.info(f"Component added to SBOM: {component_id}")

    def generate_sbom(
        self,
        app_name: str,
        app_version: str,
    ) -> Dict[str, Any]:
        """
        Generate SBOM.

        Args:
            app_name: Application name
            app_version: Application version

        Returns:
            SBOM dictionary
        """
        sbom = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "version": 1,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "component": {
                    "name": app_name,
                    "version": app_version,
                    "type": "application",
                },
            },
            "components": list(self.components.values()),
        }

        logger.info(
            f"SBOM generated",
            extra={
                "app": app_name,
                "components": len(self.components),
            },
        )

        return sbom

    def export_sbom_json(
        self,
        app_name: str,
        app_version: str,
    ) -> str:
        """
        Export SBOM as JSON.

        Args:
            app_name: Application name
            app_version: Application version

        Returns:
            JSON string
        """
        sbom = self.generate_sbom(app_name, app_version)
        return json.dumps(sbom, indent=2)

    def export_sbom_xml(
        self,
        app_name: str,
        app_version: str,
    ) -> str:
        """
        Export SBOM as XML (CycloneDX format).

        Args:
            app_name: Application name
            app_version: Application version

        Returns:
            XML string
        """
        # In production, use cyclonedx-python-lib
        # This is a placeholder
        sbom = self.generate_sbom(app_name, app_version)

        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<bom xmlns="http://cyclonedx.org/schema/bom/1.4">\n'
        xml += f"  <metadata>\n"
        xml += f"    <timestamp>{sbom['metadata']['timestamp']}</timestamp>\n"
        xml += f"    <component>\n"
        xml += f"      <name>{app_name}</name>\n"
        xml += f"      <version>{app_version}</version>\n"
        xml += f"    </component>\n"
        xml += f"  </metadata>\n"
        xml += f"  <components>\n"

        for component in sbom["components"]:
            xml += f"    <component type=\"{component['type']}\">\n"
            xml += f"      <name>{component['name']}</name>\n"
            xml += f"      <version>{component['version']}</version>\n"
            if component.get("license"):
                xml += f"      <license>{component['license']}</license>\n"
            xml += f"    </component>\n"

        xml += f"  </components>\n"
        xml += f"</bom>\n"

        return xml


# Global instances
artifact_signer = ArtifactSigner()
sbom_generator = SBOMGenerator()
