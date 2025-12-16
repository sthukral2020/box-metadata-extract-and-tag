from __future__ import annotations

from typing import Any, Dict


def _build_patch_ops(metadata_dict: Dict[str, Any]) -> list[dict]:
    """
    Build JSON-Patch ops for Box metadata update (minimal).
    Uses 'add' for all keys; Box typically treats add as upsert for template fields.
    """

    ops: list[dict] = []
    for k, v in metadata_dict.items():
        # Box metadata uses JSON pointer paths like /field_key
        ops.append({"op": "add", "path": f"/{k}", "value": v})
    return ops


def write_metadata(
    client: Any,
    file_id: str,
    template_key: str,
    metadata_dict: Dict[str, Any],
) -> None:
    """
    Write extracted fields back to the file as Box metadata (enterprise template).

    Must match agents.md primary call:
      client.file_metadata.create_file_metadata_by_id(
        file_id,
        scope=CreateFileMetadataByIdScope.ENTERPRISE,
        template_key=template_key,
        request_body=metadata_dict,
      )

    If metadata already exists, handle gracefully:
    - attempt create; on conflict, try update; otherwise print a clear message.
    """

    try:
        from box_sdk_gen.managers.file_metadata import CreateFileMetadataByIdScope
    except Exception:  # pragma: no cover
        from box_sdk_gen.managers.file_metadata import (  # type: ignore
            CreateFileMetadataByIdScope,
        )

    try:
        client.file_metadata.create_file_metadata_by_id(
            file_id,
            scope=CreateFileMetadataByIdScope.ENTERPRISE,
            template_key=template_key,
            request_body=metadata_dict,
        )
        return
    except Exception as e:  # noqa: BLE001
        msg = str(e).lower()
        is_conflict = any(s in msg for s in ["conflict", "already exists", "409"])
        if not is_conflict:
            raise

    # Conflict path: try update if the SDK exposes it.
    update_fn = getattr(client.file_metadata, "update_file_metadata_by_id", None)
    if not callable(update_fn):
        print(
            "⚠️  Metadata already exists; update is not available in this SDK version. "
            "Skipping write-back."
        )
        return

    ops = _build_patch_ops(metadata_dict)
    try:
        update_fn(
            file_id,
            scope=CreateFileMetadataByIdScope.ENTERPRISE,
            template_key=template_key,
            request_body=ops,
        )
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  Metadata already exists but update failed: {e}")
