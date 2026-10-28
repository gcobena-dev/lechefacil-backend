from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from src.infrastructure.db.orm.animal_status import AnimalStatusORM
from src.infrastructure.db.orm.lot import LotORM
from src.infrastructure.db.orm.sire_catalog import SireCatalogORM

STATUS_CODES = ["LACTATING", "DRY", "PREGNANT_DRY", "HEIFER", "PREGNANT_HEIFER", "CALF"]


@pytest.fixture()
async def farm(app, client, seeded_memberships, tenant_id, token_factory):
    """Statuses, two lots and a catalog bull linked to a herd bull."""
    lots = {"Paridas": uuid4(), "Destete": uuid4()}
    headers = {
        "Authorization": f"Bearer {token_factory(seeded_memberships['admin'])}",
        "X-Tenant-ID": str(tenant_id),
    }
    response = await client.post(
        "/api/v1/animals/", json={"tag": "T-1", "name": "Toro", "sex": "MALE"}, headers=headers
    )
    assert response.status_code == 201
    bull_animal_id = UUID(response.json()["id"])

    statuses = {code: uuid4() for code in STATUS_CODES}
    catalog_only = uuid4()
    herd_bull_entry = uuid4()
    async with app.state.session_factory() as session:
        session.add_all(
            [
                AnimalStatusORM(
                    id=status_id,
                    tenant_id=None,
                    code=code,
                    translations={"es": {"name": code}},
                    is_system_default=True,
                )
                for code, status_id in statuses.items()
            ]
        )
        session.add_all(
            [LotORM(id=lot_id, tenant_id=tenant_id, name=name) for name, lot_id in lots.items()]
        )
        session.add_all(
            [
                SireCatalogORM(id=catalog_only, tenant_id=tenant_id, name="QUIXOTE DA JGVA"),
                SireCatalogORM(
                    id=herd_bull_entry,
                    tenant_id=tenant_id,
                    name="Toro de la finca",
                    animal_id=bull_animal_id,
                ),
            ]
        )
        await session.commit()
    return {
        "headers": headers,
        "lots": lots,
        "statuses": statuses,
        "catalog_only": str(catalog_only),
        "herd_bull_entry": str(herd_bull_entry),
        "bull_animal_id": str(bull_animal_id),
    }


async def _cow(client, farm, tag: str, status: str) -> dict:
    response = await client.post(
        "/api/v1/animals/",
        json={
            "tag": tag,
            "sex": "FEMALE",
            "status_id": str(farm["statuses"][status]),
            "lot_id": str(farm["lots"]["Destete"]),
        },
        headers=farm["headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _get(client, farm, animal_id: str) -> dict:
    response = await client.get(f"/api/v1/animals/{animal_id}", headers=farm["headers"])
    assert response.status_code == 200
    return response.json()


async def _serve(client, farm, cow_id: str, days_ago: int, sire: str | None) -> str:
    response = await client.post(
        "/api/v1/reproduction/inseminations",
        json={
            "animal_id": cow_id,
            "service_date": (datetime.now(UTC) - timedelta(days=days_ago)).isoformat(),
            "method": "AI",
            "sire_catalog_id": sire,
        },
        headers=farm["headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_calving_moves_the_cow_opens_lactation_and_creates_the_calf(client, farm):
    cow = await _cow(client, farm, "V-1", "PREGNANT_DRY")
    await _serve(client, farm, cow["id"], days_ago=283, sire=farm["catalog_only"])

    response = await client.post(
        f"/api/v1/animals/{cow['id']}/events",
        json={
            "type": "CALVING",
            "occurred_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            "data": {
                "mother_lot_id": str(farm["lots"]["Paridas"]),
                "calf": {"tag": "C-1", "sex": "FEMALE", "lot_id": str(farm["lots"]["Destete"])},
            },
        },
        headers=farm["headers"],
    )
    assert response.status_code == 201, response.text
    effects = response.json()
    assert effects["lactation_opened"]
    assert effects["new_status_code"] == "LACTATING"
    assert effects["calf_created"]

    mother = await _get(client, farm, cow["id"])
    assert mother["status_code"] == "LACTATING"
    assert mother["lot_id"] == str(farm["lots"]["Paridas"])
    assert mother["lot"] == "Paridas"

    # The calf's sire is the bull of the service credited with the calving,
    # and the genealogy can link to it in the reproduction catalog.
    calf = await _get(client, farm, effects["calf_created"])
    assert calf["dam_id"] == cow["id"]
    assert calf["status_code"] == "CALF"
    assert calf["lot"] == "Destete"
    assert calf["sire_catalog_id"] == farm["catalog_only"]
    assert calf["sire_catalog_name"] == "QUIXOTE DA JGVA"
    assert calf["sire_id"] is None


async def test_calving_without_lot_or_calf_keeps_the_cow_in_her_lot(client, farm):
    # e.g. the cow goes to "Destete" for a while first, or the calf died
    cow = await _cow(client, farm, "V-2", "PREGNANT_DRY")

    response = await client.post(
        f"/api/v1/animals/{cow['id']}/events",
        json={"type": "CALVING", "occurred_at": datetime.now(UTC).isoformat()},
        headers=farm["headers"],
    )
    assert response.status_code == 201, response.text
    assert response.json()["calf_created"] is None

    mother = await _get(client, farm, cow["id"])
    assert mother["status_code"] == "LACTATING"
    assert mother["lot"] == "Destete"


async def test_herd_bull_in_the_catalog_links_to_both(client, farm):
    cow = await _cow(client, farm, "V-3", "PREGNANT_DRY")
    await _serve(client, farm, cow["id"], days_ago=280, sire=farm["herd_bull_entry"])

    response = await client.post(
        f"/api/v1/animals/{cow['id']}/events",
        json={
            "type": "CALVING",
            "occurred_at": datetime.now(UTC).isoformat(),
            "data": {"calf": {"tag": "C-3", "sex": "MALE"}},
        },
        headers=farm["headers"],
    )
    assert response.status_code == 201, response.text

    calf = await _get(client, farm, response.json()["calf_created"])
    assert calf["sire_id"] == farm["bull_animal_id"]
    assert calf["sire_tag"] == "T-1"
    assert calf["sire_catalog_id"] == farm["herd_bull_entry"]


async def test_pregnant_lactating_cow_is_dried_off_as_pregnant_dry(client, farm):
    cow = await _cow(client, farm, "V-4", "LACTATING")
    service_id = await _serve(client, farm, cow["id"], days_ago=60, sire=None)
    response = await client.post(
        f"/api/v1/reproduction/inseminations/{service_id}/pregnancy-check",
        json={"result": "CONFIRMED", "check_date": datetime.now(UTC).isoformat()},
        headers=farm["headers"],
    )
    assert response.status_code == 200, response.text
    # Still in milk: the pregnancy is tracked by reproduction, not the status
    assert (await _get(client, farm, cow["id"]))["status_code"] == "LACTATING"

    response = await client.post(
        f"/api/v1/animals/{cow['id']}/events",
        json={"type": "DRY_OFF", "occurred_at": datetime.now(UTC).isoformat()},
        headers=farm["headers"],
    )
    assert response.status_code == 201, response.text
    assert response.json()["new_status_code"] == "PREGNANT_DRY"


async def test_pregnancy_check_moves_heifer_status_both_ways(client, farm):
    heifer = await _cow(client, farm, "N-1", "HEIFER")
    service_id = await _serve(client, farm, heifer["id"], days_ago=45, sire=None)
    url = f"/api/v1/reproduction/inseminations/{service_id}/pregnancy-check"

    response = await client.post(
        url,
        json={"result": "CONFIRMED", "check_date": datetime.now(UTC).isoformat()},
        headers=farm["headers"],
    )
    assert response.status_code == 200, response.text
    assert (await _get(client, farm, heifer["id"]))["status_code"] == "PREGNANT_HEIFER"

    response = await client.post(
        url,
        json={"result": "LOST", "check_date": datetime.now(UTC).isoformat()},
        headers=farm["headers"],
    )
    assert response.status_code == 200, response.text
    assert (await _get(client, farm, heifer["id"]))["status_code"] == "HEIFER"


async def test_naive_event_time_is_ecuador_time(client, farm):
    """A calving typed as 00:30 must not land on the previous day."""
    cow = await _cow(client, farm, "V-5", "PREGNANT_DRY")
    response = await client.post(
        f"/api/v1/animals/{cow['id']}/events",
        json={"type": "CALVING", "occurred_at": "2026-10-22T00:30"},
        headers=farm["headers"],
    )
    assert response.status_code == 201, response.text
    assert response.json()["event"]["occurred_at"].startswith("2026-10-22T05:30")

    response = await client.get(f"/api/v1/animals/{cow['id']}/lactations", headers=farm["headers"])
    assert response.status_code == 200
    body = response.json()
    items = body["items"] if isinstance(body, dict) else body
    assert items[0]["start_date"] == "2026-10-22"
