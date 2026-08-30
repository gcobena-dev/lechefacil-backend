"""A PUT must tell "field not sent" apart from "field sent as null".

Collapsing the two is what made saves look like they had not been applied: a
field the user blanked out kept its old value, and fields the schema accepted
were dropped on the way to the database.
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def headers(app, seeded_memberships, tenant_id, token_factory):
    return {
        "Authorization": f"Bearer {token_factory(seeded_memberships['admin'])}",
        app.state.settings.tenant_header: str(tenant_id),
    }


async def _create_animal(client, headers, tag: str) -> str:
    resp = await client.post(
        "/api/v1/animals/",
        json={"tag": tag, "name": "Vaca", "status": "active"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_health_record_null_clears_and_omission_preserves(client, headers):
    animal_id = await _create_animal(client, headers, "PU-HR-1")
    created = await client.post(
        f"/api/v1/animals/{animal_id}/health",
        json={
            "event_type": "VET_OBSERVATION",
            "occurred_at": "2026-01-05T10:00:00Z",
            "veterinarian": "Dra. Paz",
            "notes": "Revisión de rutina",
        },
        headers=headers,
    )
    assert created.status_code in (200, 201), created.text
    record_id = created.json()["id"]

    omitted = await client.put(
        f"/api/v1/animals/{animal_id}/health/{record_id}",
        json={"veterinarian": "Dr. Ruiz"},
        headers=headers,
    )
    assert omitted.status_code == 200
    assert omitted.json()["notes"] == "Revisión de rutina"
    assert omitted.json()["veterinarian"] == "Dr. Ruiz"

    cleared = await client.put(
        f"/api/v1/animals/{animal_id}/health/{record_id}",
        json={"notes": None},
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["notes"] is None
    assert cleared.json()["veterinarian"] == "Dr. Ruiz"


async def test_certificate_persists_every_field_it_accepts(client, headers):
    animal_id = await _create_animal(client, headers, "PU-CERT-1")
    created = await client.post(
        f"/api/v1/animals/{animal_id}/certificate",
        json={
            "animal_id": animal_id,
            "registry_number": "REG-1",
            "certificate_name": "Sto Domingo",
            "association_code": "ASO-9",
            "notes": "Certificado original",
        },
        headers=headers,
    )
    assert created.status_code in (200, 201), created.text
    body = created.json()
    # These three reached the schema but never the database.
    assert body["certificate_name"] == "Sto Domingo"
    assert body["association_code"] == "ASO-9"
    assert body["notes"] == "Certificado original"

    updated = await client.put(
        f"/api/v1/animals/{animal_id}/certificate",
        json={
            "version": body["version"],
            "certificate_name": "Sto Domingo II",
            "notes": None,
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["certificate_name"] == "Sto Domingo II"
    assert updated.json()["notes"] is None
    assert updated.json()["association_code"] == "ASO-9"
    assert updated.json()["registry_number"] == "REG-1"


async def test_production_notes_are_written(client, headers):
    animal_id = await _create_animal(client, headers, "PU-PROD-1")
    created = await client.post(
        "/api/v1/milk-productions/",
        json={
            "date_time": "2026-01-05T06:00:00Z",
            "animal_id": animal_id,
            "input_unit": "l",
            "input_quantity": 12,
        },
        headers=headers,
    )
    assert created.status_code in (200, 201), created.text
    production_id = created.json()["id"]

    updated = await client.put(
        f"/api/v1/milk-productions/{production_id}",
        json={"version": created.json()["version"], "notes": "Ordeño corto"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["notes"] == "Ordeño corto"

    cleared = await client.put(
        f"/api/v1/milk-productions/{production_id}",
        json={"version": updated.json()["version"], "notes": None},
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["notes"] is None


async def test_lot_notes_can_be_cleared(client, headers):
    created = await client.post(
        "/api/v1/lots/",
        json={"name": "Lote Norte", "notes": "Pasto alto"},
        headers=headers,
    )
    assert created.status_code in (200, 201), created.text
    lot_id = created.json()["id"]

    renamed = await client.put(f"/api/v1/lots/{lot_id}", json={"name": "Lote Sur"}, headers=headers)
    assert renamed.status_code == 200
    assert renamed.json()["notes"] == "Pasto alto"

    cleared = await client.put(f"/api/v1/lots/{lot_id}", json={"notes": None}, headers=headers)
    assert cleared.status_code == 200
    assert cleared.json()["notes"] is None
    assert cleared.json()["name"] == "Lote Sur"
