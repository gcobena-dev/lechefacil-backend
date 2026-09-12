from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from src.application.errors import PermissionDenied
from src.application.patching import resolve_patch
from src.domain.models.animal_certificate import AnimalCertificate
from src.domain.models.attachment import Attachment
from src.domain.value_objects.owner_type import OwnerType
from src.domain.value_objects.role import Role
from src.infrastructure.auth.context import AuthContext
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.animal_certificates import (
    AnimalCertificateCreate,
    AnimalCertificateResponse,
    AnimalCertificateUpdate,
)
from src.interfaces.http.schemas.attachments import (
    AttachmentResponse,
    CreatePhotoRequest,
    PresignUploadRequest,
    PresignUploadResponse,
)

#: Every certificate column is nullable, so each one can be both written and
#: erased. `certificate_name`, `association_code` and `notes` used to be missing
#: from the create and update paths, which silently dropped whatever the client
#: typed into them.
CERTIFICATE_FIELDS = (
    "registry_number",
    "bolus_id",
    "tattoo_left",
    "tattoo_right",
    "issue_date",
    "breeder",
    "owner",
    "farm",
    "certificate_name",
    "association_code",
    "notes",
    "data",
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
            certificate_name=payload.certificate_name,
            association_code=payload.association_code,
            notes=payload.notes,
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

        # Only the fields the client sent, nulls included: every column here is
        # nullable, so sending one as null is how a certificate field is erased.
        for name, value in resolve_patch(
            payload,
            CERTIFICATE_FIELDS,
            sent=payload.model_fields_set,
            nullable=CERTIFICATE_FIELDS,
        ).items():
            setattr(certificate, name, value)

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


# --- Certificate files ------------------------------------------------------
# The scan of the paper certificate, image or PDF. It reuses the attachment
# machinery the animal photos already use — same presign, same S3 POST, same
# confirm — under its own `OwnerType`, the way the milk OCR photos do. That is
# what keeps a certificate out of the photo gallery, the herd list's photo
# count and the report, without a single existing query having to change.
#
# The owner is the animal, not the certificate row: a farmer can photograph the
# paper before anyone has typed its fields in.

#: What a phone camera and a scanner produce. Anything else is refused at
#: presign time, before a byte reaches the bucket.
ALLOWED_CERTIFICATE_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/heic",
        "image/heif",
        "application/pdf",
    }
)


def _ensure_supported_type(content_type: str) -> str:
    normalized = (content_type or "").split(";")[0].strip().lower()
    if normalized not in ALLOWED_CERTIFICATE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="El certificado debe ser una imagen (JPG, PNG, WEBP, HEIC) o un PDF",
        )
    return normalized


def _storage(request: Request):
    try:
        return request.app.state.storage_service
    except AttributeError as exc:
        raise RuntimeError("Storage service not configured") from exc


async def _to_response(svc, attachment) -> AttachmentResponse:
    return AttachmentResponse(
        id=attachment.id,
        url=await svc.get_public_url(attachment.storage_key),
        title=attachment.title,
        description=attachment.description,
        is_primary=attachment.is_primary,
        position=attachment.position,
        mime_type=attachment.mime_type,
        size_bytes=attachment.size_bytes,
        created_at=attachment.created_at,
    )


@router.post(
    "/animals/{animal_id}/certificate/files/uploads",
    response_model=PresignUploadResponse,
)
async def presign_certificate_file(
    animal_id: UUID,
    payload: PresignUploadRequest,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> PresignUploadResponse:
    """Hand the client a one-shot URL to post the file straight to the bucket."""
    ensure_can_write(context.role)
    content_type = _ensure_supported_type(payload.content_type)

    animal = await uow.animals.get(context.tenant_id, animal_id)
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")

    storage_key = f"tenants/{context.tenant_id}/animals/{animal_id}/certificate/{uuid4()}"
    presigned = await _storage(request).get_presigned_upload(storage_key, content_type)
    return PresignUploadResponse(
        upload_url=presigned.upload_url,
        storage_key=presigned.storage_key,
        fields=presigned.fields,
    )


@router.post(
    "/animals/{animal_id}/certificate/files",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_certificate_file(
    animal_id: UUID,
    payload: CreatePhotoRequest,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AttachmentResponse:
    """Record a file the client has already uploaded to the bucket."""
    ensure_can_write(context.role)
    mime_type = _ensure_supported_type(payload.mime_type)

    animal = await uow.animals.get(context.tenant_id, animal_id)
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")

    # The key is minted by the presign endpoint above, so a client cannot point
    # this at another tenant's or another animal's object.
    expected = f"tenants/{context.tenant_id}/animals/{animal_id}/certificate/"
    if expected not in payload.storage_key:
        raise HTTPException(status_code=400, detail="storage_key does not belong to this animal")

    attachment = Attachment.create(
        tenant_id=context.tenant_id,
        owner_type=OwnerType.ANIMAL_CERTIFICATE,
        owner_id=animal_id,
        kind="document",
        storage_key=payload.storage_key,
        mime_type=mime_type,
        size_bytes=payload.size_bytes,
        title=payload.title,
        description=payload.description,
        position=payload.position,
    )
    created = await uow.attachments.add(attachment)
    await uow.commit()

    return await _to_response(_storage(request), created)


@router.get(
    "/animals/{animal_id}/certificate/files",
    response_model=list[AttachmentResponse],
)
async def list_certificate_files(
    animal_id: UUID,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> list[AttachmentResponse]:
    svc = _storage(request)
    items = await uow.attachments.list_for_owner(
        context.tenant_id, OwnerType.ANIMAL_CERTIFICATE, animal_id
    )
    return [await _to_response(svc, a) for a in items]


@router.delete(
    "/animals/{animal_id}/certificate/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_certificate_file(
    animal_id: UUID,
    file_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> Response:
    if not context.role.can_delete():
        raise PermissionDenied("Role not allowed to delete certificate files")

    existing = await uow.attachments.get(context.tenant_id, file_id)
    if (
        not existing
        or existing.owner_id != animal_id
        or existing.owner_type != OwnerType.ANIMAL_CERTIFICATE
    ):
        raise HTTPException(status_code=404, detail="Certificate file not found")

    await uow.attachments.soft_delete(context.tenant_id, file_id)
    await uow.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
