from __future__ import annotations


async def test_label_suggestions_cover_the_whole_herd(
    app, client, seeded_memberships, tenant_id, token_factory
):
    """Labels must show up regardless of how many animals the tenant has.

    The endpoint used to walk the paginated listing 10 animals at a time, and
    the cursor advanced by `id` while the rows came back ordered by `tag`, so
    most of the herd was never visited and their labels went missing from the
    filter dropdowns.
    """
    admin_token = token_factory(seeded_memberships["admin"])
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "X-Tenant-ID": str(tenant_id),
    }

    expected = []
    for i in range(25):
        label = f"LABEL {i:02d}"
        expected.append(label)
        response = await client.post(
            "/api/v1/animals/",
            json={"tag": f"A-{i:03d}", "name": f"Vaca {i}", "labels": [label]},
            headers=headers,
        )
        assert response.status_code == 201

    response = await client.get("/api/v1/animals/labels/suggestions", headers=headers)
    assert response.status_code == 200
    assert response.json() == sorted(expected)


async def test_label_suggestions_filter_by_query(
    app, client, seeded_memberships, tenant_id, token_factory
):
    admin_token = token_factory(seeded_memberships["admin"])
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "X-Tenant-ID": str(tenant_id),
    }

    for tag, labels in [("A-1", ["TANIA", "GABRIEL"]), ("A-2", ["ESNEIDA"])]:
        response = await client.post(
            "/api/v1/animals/",
            json={"tag": tag, "name": tag, "labels": labels},
            headers=headers,
        )
        assert response.status_code == 201

    response = await client.get(
        "/api/v1/animals/labels/suggestions", params={"q": "ani"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json() == ["TANIA"]
