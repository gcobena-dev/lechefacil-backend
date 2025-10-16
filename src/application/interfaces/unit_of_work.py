from __future__ import annotations

from typing import Protocol

from src.application.interfaces.repositories.animal_certificates import (
    AnimalCertificatesRepository,
)
from src.application.interfaces.repositories.animal_events import AnimalEventsRepository
from src.application.interfaces.repositories.animal_parentage import (
    AnimalParentageRepository,
)
from src.application.interfaces.repositories.animals import AnimalRepository
from src.application.interfaces.repositories.buyers import BuyersRepository
from src.application.interfaces.repositories.lactations import LactationsRepository
from src.application.interfaces.repositories.memberships import MembershipRepository
from src.application.interfaces.repositories.milk_deliveries import MilkDeliveriesRepository
from src.application.interfaces.repositories.milk_prices import MilkPricesRepository
from src.application.interfaces.repositories.milk_productions import MilkProductionsRepository
from src.application.interfaces.repositories.tenant_config import TenantConfigRepository
from src.application.interfaces.repositories.users import UserRepository
from src.domain.ports.animal_statuses_repo import AnimalStatusesRepo
from src.infrastructure.repos.one_time_tokens_sqlalchemy import OneTimeTokenRepository


class UnitOfWork(Protocol):
    animals: AnimalRepository
    animal_statuses: AnimalStatusesRepo
    lactations: LactationsRepository
    animal_events: AnimalEventsRepository
    animal_parentage: AnimalParentageRepository
    animal_certificates: AnimalCertificatesRepository
    users: UserRepository
    memberships: MembershipRepository
    attachments: any
    buyers: BuyersRepository
    milk_prices: MilkPricesRepository
    milk_productions: MilkProductionsRepository
    milk_deliveries: MilkDeliveriesRepository
    tenant_config: TenantConfigRepository
    one_time_tokens: OneTimeTokenRepository
    # Domain events collected during the transaction
    events: list

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    # Record a domain event during the transaction
    def add_event(self, event: object) -> None: ...

    # Drain collected events (used for post-commit dispatch)
    def drain_events(self) -> list: ...
