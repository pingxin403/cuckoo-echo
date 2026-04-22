from typing import Any
from pydantic import BaseModel
from datetime import datetime
import difflib


class PromptVersion(BaseModel):
    version: str
    content: str
    created_at: datetime
    created_by: str | None = None
    changelog: str | None = None


class PromptVersionManager:
    def __init__(self):
        self._versions: dict[str, list[PromptVersion]] = {}

    def create_version(
        self,
        prompt_id: str,
        content: str,
        changelog: str | None = None,
        created_by: str | None = None,
    ) -> PromptVersion:
        if prompt_id not in self._versions:
            self._versions[prompt_id] = []
        
        version_num = len(self._versions[prompt_id]) + 1
        semver = f"1.{version_num}.0"
        
        version = PromptVersion(
            version=semver,
            content=content,
            created_at=datetime.now(),
            created_by=created_by,
            changelog=changelog,
        )
        
        self._versions[prompt_id].append(version)
        return version

    def get_version(self, prompt_id: str, version: str | None = None) -> PromptVersion | None:
        if prompt_id not in self._versions:
            return None
        
        versions = self._versions[prompt_id]
        
        if version:
            return next((v for v in versions if v.version == version), None)
        
        return versions[-1] if versions else None

    def rollback(self, prompt_id: str, target_version: str | None = None) -> PromptVersion | None:
        if prompt_id not in self._versions:
            return None
        
        versions = self._versions[prompt_id]
        if not versions:
            return None
        
        if target_version:
            target = next((v for v in versions if v.version == target_version), None)
            if target:
                new_version = PromptVersion(
                    version=f"1.{len(versions) + 1}.0",
                    content=target.content,
                    created_at=datetime.now(),
                    changelog=f"Rolled back to {target_version}",
                )
                versions.append(new_version)
                return new_version
        
        previous = versions[-2] if len(versions) > 1 else versions[-1]
        return self.create_version(
            prompt_id,
            previous.content,
            changelog="Rolled back to previous version",
        )

    def get_diff(self, prompt_id: str, version1: str, version2: str) -> str | None:
        v1 = self.get_version(prompt_id, version1)
        v2 = self.get_version(prompt_id, version2)
        
        if not v1 or not v2:
            return None
        
        diff = difflib.unified_diff(
            v1.content.splitlines(keepends=True),
            v2.content.splitlines(keepends=True),
            fromfile=version1,
            tofile=version2,
            lineterm="",
        )
        
        return "".join(diff)

    def list_versions(self, prompt_id: str) -> list[PromptVersion]:
        return self._versions.get(prompt_id, [])

    def get_latest(self, prompt_id: str) -> PromptVersion | None:
        return self.get_version(prompt_id)


_global_version_manager = PromptVersionManager()


def get_prompt_version_manager() -> PromptVersionManager:
    return _global_version_manager