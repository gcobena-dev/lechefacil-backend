from __future__ import annotations

from typing import Any, Container, Iterable


def resolve_patch(
    payload: Any,
    fields: Iterable[str | tuple[str, str]],
    *,
    sent: Container[str],
    nullable: Container[str] = (),
) -> dict[str, Any]:
    """Build the set of columns to write from a partial-update payload.

    A PUT body carries two different kinds of "no value": a field the client
    left out, which must stay as it is, and a field the client sent as ``null``,
    which means "blank this out". Both arrive as ``None``, so the only thing
    that tells them apart is the set of keys the client actually sent —
    ``model_fields_set`` on a Pydantic payload.

    Collapsing the two (``if value is not None``) is what made updates look like
    they had not been applied: clearing a field silently kept the old value.

    Args:
        payload: object holding the values, looked up by attribute.
        fields: field names to consider, or ``(payload_name, column_name)``
            pairs when the two differ.
        sent: names the client actually sent.
        nullable: names that may be written as ``NULL``. Anything outside this
            set is skipped when it is ``None``, so a null can never violate a
            ``NOT NULL`` column.
    """
    patch: dict[str, Any] = {}
    for field in fields:
        source_name, target_name = field if isinstance(field, tuple) else (field, field)
        if source_name not in sent:
            continue
        value = getattr(payload, source_name, None)
        if value is None and target_name not in nullable:
            continue
        patch[target_name] = value
    return patch
