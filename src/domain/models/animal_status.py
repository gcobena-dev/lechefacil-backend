from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

# Statuses that take an animal out of the herd ("dado de baja"). Kept here so
# the API, the repositories and the reports all agree on what "active" means.
INACTIVE_STATUS_CODES: frozenset[str] = frozenset({"SOLD", "DEAD", "CULLED"})


@dataclass(slots=True)
class AnimalStatus:
    id: UUID
    tenant_id: UUID | None
    code: str
    translations: dict
    is_system_default: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        code: str,
        translations: dict,
        tenant_id: UUID | None = None,
        is_system_default: bool = False,
    ) -> AnimalStatus:
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            code=code,
            translations=translations,
            is_system_default=is_system_default,
            created_at=datetime.now(timezone.utc),
        )

    @property
    def is_active(self) -> bool:
        """False for statuses that take the animal out of the herd."""
        return self.code not in INACTIVE_STATUS_CODES

    def get_translation(self, language_code: str = "es") -> dict:
        """Get translation for specific language, fallback to 'es' if not found"""
        return self.translations.get(language_code, self.translations.get("es", {}))

    def get_name(self, language_code: str = "es") -> str:
        """Get translated name"""
        translation = self.get_translation(language_code)
        return translation.get("name", self.code)

    def get_description(self, language_code: str = "es") -> str | None:
        """Get translated description"""
        translation = self.get_translation(language_code)
        return translation.get("description")
