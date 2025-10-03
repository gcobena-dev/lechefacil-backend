from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.application.errors import PermissionDenied
from src.domain.models.animal_certificate import AnimalCertificate
from src.domain.value_objects.role import Role
from src.infrastructure.auth.context import AuthContext
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.animal_certificates import (
    AnimalCertificateCreate,
    AnimalCertificateResponse,
    AnimalCertificateUpdate,
)

router = APIRouter(tags=["animal-certificates"])


def ensure_can_write(role: Role) -> None:
    if not role.can_update():
        raise PermissionDenied("Role not allowed to modify certificates")


@router.post(
    "/animals/{animal_id}/certificate",
    status_code=status.HTTP_201_CREATED,
    response_model=AnimalCertificateResponse,
)
async def create_certificate(
    animal_id: UUID,
    payload: AnimalCertificateCreate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AnimalCertificateResponse:
    """Create a certificate for an animal.

    Only one certificate per animal is allowed.
    """
    ensure_can_write(context.role)

    async with uow:
        # Verify animal exists
        animal = await uow.animals.get(context.tenant_id, animal_id)
        if not animal:
            raise HTTPException(status_code=404, detail="Animal not found")

        # Check if certificate already exists
        existing = await uow.animal_certificates.get_by_animal(context.tenant_id, animal_id)
        if existing:
            raise HTTPException(
                status_code=409,
                detail="Certificate already exists for this animal. Use PUT to update.",
            )

        # Create certificate
        certificate = AnimalCertificate.create(
            tenant_id=context.tenant_id,
            animal_id=animal_id,
            registry_number=payload.registry_number,
            bolus_id=payload.bolus_id,
            tattoo_left=payload.tattoo_left,
            tattoo_right=payload.tattoo_right,
            issue_date=payload.issue_date,
            breeder=payload.breeder,
            owner=payload.owner,
            farm=payload.farm,
            data=payload.data,
        )

        created = await uow.animal_certificates.add(certificate)
        await uow.commit()

        return AnimalCertificateResponse.model_validate(created)


@router.get(
    "/animals/{animal_id}/certificate",
    response_model=AnimalCertificateResponse,
)
async def get_certificate(
    animal_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AnimalCertificateResponse:
    """Get the certificate for an animal."""
    async with uow:
        certificate = await uow.animal_certificates.get_by_animal(context.tenant_id, animal_id)
        if not certificate:
            raise HTTPException(status_code=404, detail="Certificate not found")

        response = AnimalCertificateResponse.model_validate(certificate)

        # Optionally enrich with animal data
        animal = await uow.animals.get(context.tenant_id, animal_id)
        if animal:
            response.animal_tag = animal.tag
            response.animal_name = animal.name

        return response


@router.put(
    "/animals/{animal_id}/certificate",
    response_model=AnimalCertificateResponse,
)
async def update_certificate(
    animal_id: UUID,
    payload: AnimalCertificateUpdate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AnimalCertificateResponse:
    """Update the certificate for an animal."""
    ensure_can_write(context.role)

    async with uow:
        certificate = await uow.animal_certificates.get_by_animal(context.tenant_id, animal_id)
        if not certificate:
            raise HTTPException(status_code=404, detail="Certificate not found")

        # Check version for optimistic locking
        if certificate.version != payload.version:
            raise HTTPException(
                status_code=409,
                detail="Certificate was modified by another user. Please refresh and try again.",
            )

        # Update fields
        if payload.registry_number is not None:
            certificate.registry_number = payload.registry_number
        if payload.bolus_id is not None:
            certificate.bolus_id = payload.bolus_id
        if payload.tattoo_left is not None:
            certificate.tattoo_left = payload.tattoo_left
        if payload.tattoo_right is not None:
            certificate.tattoo_right = payload.tattoo_right
        if payload.issue_date is not None:
            certificate.issue_date = payload.issue_date
        if payload.breeder is not None:
            certificate.breeder = payload.breeder
        if payload.owner is not None:
            certificate.owner = payload.owner
        if payload.farm is not None:
            certificate.farm = payload.farm
        if payload.data is not None:
            certificate.data = payload.data

        certificate.bump_version()

        updated = await uow.animal_certificates.update(certificate)
        await uow.commit()

        return AnimalCertificateResponse.model_validate(updated)


@router.delete(
    "/animals/{animal_id}/certificate",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_certificate(
    animal_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> Response:
    """Delete the certificate for an animal."""
    ensure_can_write(context.role)

    async with uow:
        deleted = await uow.animal_certificates.delete(context.tenant_id, animal_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Certificate not found")

        await uow.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
