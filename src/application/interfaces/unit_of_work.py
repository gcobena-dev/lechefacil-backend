from __future__ import annotations

from typing import Protocol

from src.application.interfaces.repositories.animals import AnimalRepository
from src.application.interfaces.repositories.buyers import BuyersRepository
from src.application.interfaces.repositories.memberships import MembershipRepository
from src.application.interfaces.repositories.milk_deliveries import MilkDeliveriesRepository
from src.application.interfaces.repositories.milk_prices import MilkPricesRepository
from src.application.interfaces.repositories.milk_productions import MilkProductionsRepository
from src.application.interfaces.repositories.tenant_config import TenantConfigRepository
from src.application.interfaces.repositories.users import UserRepository


class UnitOfWork(Protocol):
    animals: AnimalRepository
    users: UserRepository
    memberships: MembershipRepository
    attachments: any
    buyers: BuyersRepository
    milk_prices: MilkPricesRepository
    milk_productions: MilkProductionsRepository
    milk_deliveries: MilkDeliveriesRepository
    tenant_config: TenantConfigRepository

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
