from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID


def _round2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def test_worker_creates_milk_delivery_with_price(
    app, client, seeded_memberships, tenant_id: UUID, token_factory
):
    admin_token = token_factory(seeded_memberships["admin"])
    worker_token = token_factory(seeded_memberships["worker"])
    headers_admin = {
        "Authorization": f"Bearer {admin_token}",
        app.state.settings.tenant_header: str(tenant_id),
    }
    headers_worker = {
        "Authorization": f"Bearer {worker_token}",
        app.state.settings.tenant_header: str(tenant_id),
    }

    # Create buyer
    buyer_payload = {"name": "Acopiador Test", "code": "B-001", "contact": "contact@test"}
    buyer_resp = await client.post("/api/v1/buyers/", json=buyer_payload, headers=headers_admin)
    assert buyer_resp.status_code == 201, buyer_resp.text
    buyer = buyer_resp.json()

    # Create price for date and buyer
    price_payload = {
        "date": "2025-01-01",
        "price_per_l": 0.5,
        "currency": "USD",
        "buyer_id": buyer["id"],
    }
    price_resp = await client.post(
        "/api/v1/milk-prices/", json=price_payload, headers=headers_admin
    )
    assert price_resp.status_code == 201, price_resp.text

    # Create delivery as WORKER
    volume = Decimal("120.5")
    delivery_payload = {
        "date_time": "2025-01-01T08:00:00Z",
        "volume_l": float(volume),
        "buyer_id": buyer["id"],
        "notes": "Entrega matutina",
    }
    deliv_resp = await client.post(
        "/api/v1/milk-deliveries/", json=delivery_payload, headers=headers_worker
    )
    assert deliv_resp.status_code == 201, deliv_resp.text
    body = deliv_resp.json()
    assert body["buyer_id"] == buyer["id"]
    assert body["currency"] == "USD"
    assert body["price_snapshot"] == "0.5"
    expected_amount = _round2(volume * Decimal("0.5"))
    assert body["amount"] == str(expected_amount)
