"""
Build reproducibility system for CrucibAI.

Ensures builds are deterministic and reproducible.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class BuildManifest:
    """Manifest of a build for reproducibility."""

    build_id: str
    timestamp: datetime
    crucibai_version: str
    agent_versions: Dict[str, str]
    dependencies: Dict[str, str]
    configuration: Dict[str, Any]
    input_hash: str
    output_hash: str
    manifest_hash: str

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "build_id": self.build_id,
            "timestamp": self.timestamp.isoformat(),
            "crucibai_version": self.crucibai_version,
            "agent_versions": self.agent_versions,
            "dependencies": self.dependencies,
            "configuration": self.configuration,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "manifest_hash": self.manifest_hash,
        }


class BuildReproducibilityManager:
    """Manages build reproducibility and versioning."""

    def __init__(self):
        """Initialize reproducibility manager."""
        self.manifests: Dict[str, BuildManifest] = {}
        self.build_cache: Dict[str, Dict] = {}

    def calculate_hash(self, data: Any) -> str:
        """Calculate SHA256 hash of data."""
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)

        return hashlib.sha256(data_str.encode()).hexdigest()

    def create_manifest(
        self,
        build_id: str,
        crucibai_version: str,
        agent_versions: Dict[str, str],
        dependencies: Dict[str, str],
        configuration: Dict[str, Any],
        input_data: Dict,
        output_data: Dict,
    ) -> BuildManifest:
        """Create a build manifest."""
        input_hash = self.calculate_hash(input_data)
        output_hash = self.calculate_hash(output_data)

        manifest_data = {
            "build_id": build_id,
            "timestamp": datetime.utcnow().isoformat(),
            "crucibai_version": crucibai_version,
            "agent_versions": agent_versions,
            "dependencies": dependencies,
            "configuration": configuration,
            "input_hash": input_hash,
            "output_hash": output_hash,
        }

        manifest_hash = self.calculate_hash(manifest_data)

        manifest = BuildManifest(
            build_id=build_id,
            timestamp=datetime.utcnow(),
            crucibai_version=crucibai_version,
            agent_versions=agent_versions,
            dependencies=dependencies,
            configuration=configuration,
            input_hash=input_hash,
            output_hash=output_hash,
            manifest_hash=manifest_hash,
        )

        self.manifests[build_id] = manifest
        return manifest

    def verify_reproducibility(
        self,
        build_id: str,
        new_output_data: Dict,
    ) -> bool:
        """Verify if a build is reproducible."""
        if build_id not in self.manifests:
            return False

        manifest = self.manifests[build_id]
        new_output_hash = self.calculate_hash(new_output_data)

        return new_output_hash == manifest.output_hash

    def get_build_dependencies(self, build_id: str) -> Optional[Dict[str, str]]:
        """Get dependencies for a specific build."""
        if build_id not in self.manifests:
            return None

        return self.manifests[build_id].dependencies

    def get_agent_versions(self, build_id: str) -> Optional[Dict[str, str]]:
        """Get agent versions for a specific build."""
        if build_id not in self.manifests:
            return None

        return self.manifests[build_id].agent_versions

    def export_manifest(self, build_id: str) -> Optional[Dict]:
        """Export manifest as JSON."""
        if build_id not in self.manifests:
            return None

        return self.manifests[build_id].to_dict()

    def import_manifest(self, manifest_data: Dict) -> BuildManifest:
        """Import manifest from JSON."""
        manifest = BuildManifest(
            build_id=manifest_data["build_id"],
            timestamp=datetime.fromisoformat(manifest_data["timestamp"]),
            crucibai_version=manifest_data["crucibai_version"],
            agent_versions=manifest_data["agent_versions"],
            dependencies=manifest_data["dependencies"],
            configuration=manifest_data["configuration"],
            input_hash=manifest_data["input_hash"],
            output_hash=manifest_data["output_hash"],
            manifest_hash=manifest_data["manifest_hash"],
        )

        self.manifests[manifest.build_id] = manifest
        return manifest

    def cache_build_output(self, build_id: str, output_data: Dict):
        """Cache build output for quick retrieval."""
        self.build_cache[build_id] = output_data

    def get_cached_output(self, build_id: str) -> Optional[Dict]:
        """Get cached build output."""
        return self.build_cache.get(build_id)

    def get_reproducibility_report(self) -> Dict:
        """Get reproducibility report."""
        total_builds = len(self.manifests)
        cached_builds = len(self.build_cache)
        reproducible_builds = sum(
            1 for manifest in self.manifests.values()
            if manifest.output_hash is not None
        )

        return {
            "total_builds": total_builds,
            "cached_builds": cached_builds,
            "reproducible_builds": reproducible_builds,
            "reproducibility_rate": (
                reproducible_builds / total_builds * 100 if total_builds > 0 else 0
            ),
            "cache_hit_rate": (
                cached_builds / total_builds * 100 if total_builds > 0 else 0
            ),
        }

    def get_build_lineage(self, build_id: str) -> Optional[Dict]:
        """Get build lineage and dependencies."""
        if build_id not in self.manifests:
            return None

        manifest = self.manifests[build_id]
        return {
            "build_id": build_id,
            "timestamp": manifest.timestamp.isoformat(),
            "crucibai_version": manifest.crucibai_version,
            "dependencies": manifest.dependencies,
            "agent_versions": manifest.agent_versions,
            "input_hash": manifest.input_hash,
            "output_hash": manifest.output_hash,
        }


class BuildVersionManager:
    """Manages build versions and rollback."""

    def __init__(self):
        """Initialize version manager."""
        self.versions: Dict[str, BuildManifest] = {}
        self.version_tags: Dict[str, str] = {}  # tag -> build_id

    def tag_build(self, build_id: str, tag: str, manifest: BuildManifest):
        """Tag a build version."""
        self.versions[build_id] = manifest
        self.version_tags[tag] = build_id

    def get_version(self, tag: str) -> Optional[BuildManifest]:
        """Get build by version tag."""
        build_id = self.version_tags.get(tag)
        if build_id:
            return self.versions.get(build_id)
        return None

    def list_versions(self) -> List[Dict]:
        """List all versions."""
        return [
            {
                "tag": tag,
                "build_id": build_id,
                "timestamp": self.versions[build_id].timestamp.isoformat(),
            }
            for tag, build_id in self.version_tags.items()
        ]

    def rollback_to_version(self, tag: str) -> Optional[BuildManifest]:
        """Rollback to a specific version."""
        return self.get_version(tag)


# Global instances
reproducibility_manager = BuildReproducibilityManager()
version_manager = BuildVersionManager()
