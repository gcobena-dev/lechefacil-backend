"""Migrate existing SERVICE events to inseminations table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-15 12:00:00.000000

"""
from datetime import timedelta
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate SERVICE animal_events into inseminations + sire_catalog.

    For each SERVICE event that has no linked insemination yet:
    1. If external_sire_code exists, upsert into sire_catalog (with TRIM)
    2. Create insemination record linked to the SERVICE event
    3. If a CALVING event exists for the same animal after the service date,
       mark as CONFIRMED and link the calving event
    """
    conn = op.get_bind()

    # -----------------------------------------------------------------
    # Step 1: Find all SERVICE events not yet linked to an insemination
    # -----------------------------------------------------------------
    service_events = conn.execute(sa.text("""
        SELECT
            ae.id,
            ae.tenant_id,
            ae.animal_id,
            ae.occurred_at,
            ae.data,
            ae.created_at
        FROM animal_events ae
        WHERE ae.type = 'SERVICE'
          AND NOT EXISTS (
              SELECT 1 FROM inseminations i
              WHERE i.service_event_id = ae.id
          )
        ORDER BY ae.occurred_at
    """)).fetchall()

    if not service_events:
        return

    for ev in service_events:
        ev_id = ev.id
        tenant_id = ev.tenant_id
        animal_id = ev.animal_id
        service_date = ev.occurred_at
        data = ev.data or {}
        created_at = ev.created_at

        method = (data.get("method") or "AI").strip()
        technician = (data.get("technician") or "").strip() or None
        notes = (data.get("notes") or "").strip() or None
        ext_code = (data.get("external_sire_code") or "").strip() or None
        ext_registry = (data.get("external_sire_registry") or "").strip() or None
        sire_name = (data.get("sire_name") or "").strip() or None

        # -----------------------------------------------------------
        # Step 2: Resolve or create sire_catalog entry (with trimmed values)
        # -----------------------------------------------------------
        sire_catalog_id = None

        if ext_code:
            # Try to find existing sire by trimmed registry code within tenant
            existing_sire = conn.execute(sa.text("""
                SELECT id FROM sire_catalog
                WHERE tenant_id = :tenant_id
                  AND TRIM(registry_code) = :registry_code
                  AND deleted_at IS NULL
                LIMIT 1
            """), {
                "tenant_id": tenant_id,
                "registry_code": ext_code,
            }).fetchone()

            if existing_sire:
                sire_catalog_id = existing_sire.id
            else:
                # Create a new sire_catalog entry with clean values
                sire_catalog_id = conn.execute(sa.text("""
                    INSERT INTO sire_catalog (
                        id, tenant_id, name, registry_code, registry_name,
                        is_active, created_at, updated_at, version
                    ) VALUES (
                        gen_random_uuid(), :tenant_id, :name, :registry_code,
                        :registry_name, true, :created_at, :created_at, 1
                    )
                    RETURNING id
                """), {
                    "tenant_id": tenant_id,
                    "name": sire_name or ext_code,
                    "registry_code": ext_code,
                    "registry_name": ext_registry,
                    "created_at": created_at,
                }).fetchone().id

        # -----------------------------------------------------------
        # Step 3: Determine pregnancy status from subsequent events
        # -----------------------------------------------------------
        calving = conn.execute(sa.text("""
            SELECT id, occurred_at
            FROM animal_events
            WHERE tenant_id = :tenant_id
              AND animal_id = :animal_id
              AND type = 'CALVING'
              AND occurred_at > :service_date
            ORDER BY occurred_at ASC
            LIMIT 1
        """), {
            "tenant_id": tenant_id,
            "animal_id": animal_id,
            "service_date": service_date,
        }).fetchone()

        abortion = conn.execute(sa.text("""
            SELECT id, occurred_at
            FROM animal_events
            WHERE tenant_id = :tenant_id
              AND animal_id = :animal_id
              AND type = 'ABORTION'
              AND occurred_at > :service_date
            ORDER BY occurred_at ASC
            LIMIT 1
        """), {
            "tenant_id": tenant_id,
            "animal_id": animal_id,
            "service_date": service_date,
        }).fetchone()

        pregnancy_status = "PENDING"
        calving_event_id = None
        exp_calving = None

        if calving and (not abortion or calving.occurred_at < abortion.occurred_at):
            pregnancy_status = "CONFIRMED"
            calving_event_id = calving.id
            exp_calving = (service_date + timedelta(days=283)).date()
        elif abortion and (not calving or abortion.occurred_at < calving.occurred_at):
            pregnancy_status = "LOST"

        # -----------------------------------------------------------
        # Step 4: Insert insemination record
        # -----------------------------------------------------------
        conn.execute(sa.text("""
            INSERT INTO inseminations (
                id, tenant_id, animal_id, sire_catalog_id,
                service_event_id, service_date, method, technician,
                straw_count, heat_detected, pregnancy_status,
                expected_calving_date, calving_event_id, notes,
                created_at, updated_at, version
            ) VALUES (
                gen_random_uuid(), :tenant_id, :animal_id, :sire_catalog_id,
                :service_event_id, :service_date, :method, :technician,
                1, false, :pregnancy_status,
                :expected_calving_date, :calving_event_id, :notes,
                :created_at, :created_at, 1
            )
        """), {
            "tenant_id": tenant_id,
            "animal_id": animal_id,
            "sire_catalog_id": sire_catalog_id,
            "service_event_id": ev_id,
            "service_date": service_date,
            "method": method,
            "technician": technician,
            "pregnancy_status": pregnancy_status,
            "expected_calving_date": exp_calving,
            "calving_event_id": calving_event_id,
            "notes": notes,
            "created_at": created_at,
        })


def downgrade() -> None:
    """Remove migrated inseminations and auto-created sire_catalog entries."""
    conn = op.get_bind()

    conn.execute(sa.text("""
        DELETE FROM inseminations
        WHERE service_event_id IS NOT NULL
    """))

    conn.execute(sa.text("""
        DELETE FROM sire_catalog sc
        WHERE NOT EXISTS (
            SELECT 1 FROM inseminations i
            WHERE i.sire_catalog_id = sc.id
        )
    """))
