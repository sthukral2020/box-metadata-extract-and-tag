from __future__ import annotations

import argparse
from typing import Optional

from src.box_client import load_env, get_box_client
from src.extract import extract_structured
from src.metadata import write_metadata


def _add_run_args(p: argparse.ArgumentParser) -> None:
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("--file-id", help="Box file ID to process.")
    target.add_argument("--folder-id", help="Box folder ID to process (all files in folder).")
    p.add_argument(
        "--template-key",
        default=None,
        help="Metadata template key (defaults to env BOX_METADATA_TEMPLATE_KEY).",
    )
    p.add_argument(
        "--scope",
        default=None,
        help="Metadata template scope (defaults to env BOX_METADATA_SCOPE or enterprise_{BOX_ENTERPRISE_ID}).",
    )
    p.add_argument(
        "--model",
        default=None,
        help="Optional AI model override (defaults to env BOX_AI_MODEL).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and print metadata, but do not write to Box.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Folder listing page size (only used with --folder-id).",
    )


def _folder_items(client, folder_id: str, limit: int):
    """
    Yield items from a folder.

    Uses marker-based pagination if available; otherwise falls back to single page.
    """

    marker = None
    while True:
        try:
            if marker:
                resp = client.folders.get_folder_items(folder_id=folder_id, limit=limit, marker=marker)
            else:
                resp = client.folders.get_folder_items(folder_id=folder_id, limit=limit)
        except TypeError:
            # Some SDK versions may not accept marker; single-page fallback.
            resp = client.folders.get_folder_items(folder_id=folder_id, limit=limit)
            marker = None

        entries = getattr(resp, "entries", None)
        if entries is None:
            entries = getattr(resp, "items", None)
        if entries is None:
            entries = []

        for item in entries:
            yield item

        next_marker = getattr(resp, "next_marker", None) or getattr(resp, "nextMarker", None)
        if not next_marker or marker is None and marker is None:
            break
        marker = next_marker


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="box-extract-demo", add_help=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Extract structured metadata for one file and write it back to Box.")
    _add_run_args(run_p)

    args = parser.parse_args(argv)

    # Load env (fail fast on missing config)
    env = load_env()

    template_key = (args.template_key or env.metadata_template_key).strip()
    scope = (args.scope or env.metadata_scope).strip()
    model = (args.model or env.ai_model)

    print("[Step 1] Authenticating with Box (CCG)...")
    client = get_box_client()

    if args.file_id:
        file_id = args.file_id.strip()
        if not file_id:
            raise RuntimeError("--file-id cannot be empty")

        print("[Step 2] Extracting structured metadata...")
        extracted = extract_structured(
            client=client,
            file_id=file_id,
            template_key=template_key,
            scope=scope,
            model=model,
        )

        print("[Step 3] Normalized extracted metadata:")
        print(extracted)

        if args.dry_run:
            print("✅ Done (dry-run; not writing metadata).")
            return 0

        print("[Step 4] Writing metadata to Box...")
        write_metadata(
            client=client,
            file_id=file_id,
            template_key=template_key,
            metadata_dict=extracted,
        )

        print("✅ Done")
        return 0

    folder_id = args.folder_id.strip()
    if not folder_id:
        raise RuntimeError("--folder-id cannot be empty")

    print("[Step 2] Listing folder items...")
    items = list(_folder_items(client=client, folder_id=folder_id, limit=args.limit))
    file_items = [it for it in items if getattr(it, "type", None) == "file"]
    file_ids = [getattr(it, "id", None) for it in file_items if getattr(it, "id", None)]

    total = len(file_ids)
    print(f"[Step 3] Processing {total} file(s) in folder...")

    for i, fid in enumerate(file_ids, start=1):
        print(f"[{i}/{total}] Processing file {fid}")
        try:
            extracted = extract_structured(
                client=client,
                file_id=str(fid),
                template_key=template_key,
                scope=scope,
                model=model,
            )

            print(extracted)

            if args.dry_run:
                continue

            write_metadata(
                client=client,
                file_id=str(fid),
                template_key=template_key,
                metadata_dict=extracted,
            )
        except Exception as e:  # noqa: BLE001
            print(f"⚠️  Warning: failed processing file {fid}: {e}")
            continue

    if args.dry_run:
        print("✅ Done (dry-run; not writing metadata).")
    else:
        print("✅ Done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
