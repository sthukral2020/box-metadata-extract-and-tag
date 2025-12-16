# agents.md — Box Metadata Extraction Workflow (Prescriptive Spec)

You are generating code for a small, production-style Python project that:
1) extracts structured metadata from Box files using Box AI Extract Structured, and
2) writes the extracted fields back to each file as Box metadata (enterprise template).

The goal is a reproducible workflow that a developer can generate and run locally with minimal changes.
Keep code minimal, readable, deterministic, and aligned to the import paths and schema types specified below.

---

## 0) Non-negotiables (must comply)

- Use the **Box Generated Python SDK**: `box_sdk_gen` (pip package: `box-sdk-gen`).
- Use **CCG (Client Credentials Grant)** enterprise auth.
- CLI-first, `argparse`, runnable from repo root using `python -m src.cli ...`.
- Never hardcode secrets. Use `.env` + environment variables.
- Keep dependencies minimal: `box-sdk-gen`, `python-dotenv`.

**Do NOT:**
- Use the legacy `boxsdk` package.
- Use raw `requests` for Box API calls.
- Add a database, web server, or UI.

---

## 1) Repo layout (target)

box-metadata-extract/
- agents.md
- README.md
- .env.example
- requirements.txt
- src/
  - __init__.py
  - box_client.py
  - extract.py
  - metadata.py
  - cli.py
- schemas/
  - metadata_template_fields.md
- samples/
  - README.md

---

## 2) Environment variables (required)

Required:
- BOX_CLIENT_ID
- BOX_CLIENT_SECRET
- BOX_ENTERPRISE_ID

Recommended configuration:
- BOX_METADATA_TEMPLATE_KEY
- BOX_METADATA_SCOPE (default should be derived as: enterprise_{BOX_ENTERPRISE_ID})
- BOX_AI_MODEL (optional)

---

## 3) The “Golden Path” workflow (must work)

Dry run (no writes):
- python -m src.cli run --file-id <FILE_ID> --dry-run

Real run (writes metadata to Box):
- python -m src.cli run --file-id <FILE_ID>

The CLI prints step-labeled output:
- [Step 1] Authenticating with Box (CCG)...
- [Step 2] Extracting structured metadata...
- [Step 3] Normalized extracted metadata:
- [Step 4] Writing metadata to Box...
- ✅ Done

---

## 4) Hard requirements: module responsibilities

### 4.1 src/box_client.py (env + auth)

**Must include:**
- A `BoxEnv` dataclass holding validated config:
  - client_id, client_secret, enterprise_id
  - metadata_template_key, metadata_scope
  - ai_model (optional)
- `load_env()`:
  - calls `dotenv.load_dotenv()`
  - validates required env vars
  - derives default metadata scope: enterprise_{enterprise_id}
- `get_box_client()`:
  - returns an authenticated `BoxClient` using CCG

**Exact import rule (do this, no alternatives):**
```py
from box_sdk_gen import BoxClient, BoxCCGAuth, CCGConfig
```

**Explicitly forbidden imports (these caused breakage):**
```py
# DO NOT DO THIS:
from box_sdk_gen.auth.ccg_auth import BoxCCGAuth
from box_sdk_gen.auth.ccg_config import CCGConfig
from box_sdk_gen.client import BoxClient
```

**Auth construction (must match):**
```py
config = CCGConfig(client_id=..., client_secret=..., enterprise_id=...)
auth = BoxCCGAuth(config=config)
client = BoxClient(auth=auth)
return client
```

---

### 4.2 src/extract.py (Extract Structured + normalization)

This module owns:
- `normalize_extracted_metadata(answer) -> dict`
- `extract_structured(client, file_id, template_key, scope, model=None) -> dict`

#### 4.2.1 normalize_extracted_metadata(answer)

Rules:
- If `answer` has `to_dict()`, call it.
- Else if dict, use it.
- Else best-effort dict via `answer.__dict__`.
- Strip `d_` key prefixes from top-level keys.
- Return a plain `dict[str, Any]` suitable for metadata write-back.

#### 4.2.2 Extract Structured call shape (must match)

You MUST call:
- `client.ai.create_ai_extract_structured(...)`

**Items (must be a file):**
```py
from box_sdk_gen.schemas.ai_item_base import AiItemBase
from box_sdk_gen.schemas.ai_item_base_type_field import AiItemBaseTypeField

items = [AiItemBase(id=file_id, type=AiItemBaseTypeField.FILE)]
```

**Metadata template object (IMPORTANT: use these exact schema types):**
```py
from box_sdk_gen.schemas.ai_extract_structured import (
  AiExtractStructuredMetadataTemplateField,
  AiExtractStructuredMetadataTemplateTypeField,
)

metadata_template = AiExtractStructuredMetadataTemplateField(
  type=AiExtractStructuredMetadataTemplateTypeField.METADATA_TEMPLATE,
  template_key=template_key,
  scope=scope,
)
```

**Explicitly forbidden template import (do not use; not present in some installs):**
```py
# DO NOT DO THIS:
from box_sdk_gen.schemas.create_ai_extract_structured_metadata_template import CreateAiExtractStructuredMetadataTemplate
```

**AI agent (optional; only construct if model is provided):**
```py
from box_sdk_gen.schemas.ai_agent_extract_structured import AiAgentExtractStructured
from box_sdk_gen.schemas.ai_agent_extract_structured_type_field import AiAgentExtractStructuredTypeField
from box_sdk_gen.schemas.ai_agent_long_text_tool import AiAgentLongTextTool
from box_sdk_gen.schemas.ai_agent_basic_text_tool import AiAgentBasicTextTool

ai_agent = None
if model:
  ai_agent = AiAgentExtractStructured(
    type=AiAgentExtractStructuredTypeField.AI_AGENT_EXTRACT_STRUCTURED,
    long_text=AiAgentLongTextTool(model=model),
    basic_text=AiAgentBasicTextTool(model=model),
  )
```

**Final call:**
```py
resp = client.ai.create_ai_extract_structured(
  items=items,
  metadata_template=metadata_template,
  ai_agent=ai_agent,
)
return normalize_extracted_metadata(getattr(resp, "answer", None))
```

**Prescriptive rule:**
- Avoid `try/except` import fallbacks for schema modules. Use the exact imports above.
- If an import fails, upgrade the SDK: `pip install --upgrade box-sdk-gen`.

---

### 4.3 src/metadata.py (write back to Box metadata)

This module owns:
- `write_metadata(client, file_id, template_key, metadata_dict) -> None`

Primary path:
- `client.file_metadata.create_file_metadata_by_id(...)` using enterprise scope enum.

**Exact import rule:**
```py
from box_sdk_gen.managers.file_metadata import CreateFileMetadataByIdScope
```

Write-back call:
```py
client.file_metadata.create_file_metadata_by_id(
  file_id,
  scope=CreateFileMetadataByIdScope.ENTERPRISE,
  template_key=template_key,
  request_body=metadata_dict,
)
```

Conflict handling (keep it safe and simple):
- If create fails with “already exists / conflict / 409”:
  - If `update_file_metadata_by_id` exists on the SDK client, attempt a minimal JSON Patch update.
  - Otherwise print a clear warning and skip.

If implementing patch:
- build ops like: `{"op": "add", "path": f"/{k}", "value": v}` for each key.

---

### 4.4 src/cli.py (argparse entry point)

This module owns:
- `main(argv: Optional[list[str]] = None) -> int`
- a `run` subcommand with required flags:
  - `--file-id` (required)
  - `--template-key` (optional; defaults from env)
  - `--scope` (optional; defaults from env-derived enterprise_{enterprise_id})
  - `--model` (optional; defaults from env)
  - `--dry-run` (optional)

Import rule:
- Import from `src.*` modules (not relative imports that break `python -m`).

Run flow:
1) load_env()
2) derive template_key, scope, model
3) get_box_client()
4) extract_structured(...)
5) print normalized dict
6) if dry-run: return
7) write_metadata(...)
8) done

---

## 5) Optional: Folder (batch) processing

This workflow may be extended to process **all files in a Box folder**.
The single-file path above must remain the core primitive; batch mode should only orchestrate iteration.

**Behavior:**
- Add an optional `--folder-id` flag to the CLI.
- If `--folder-id` is provided:
  - List items using `client.folders.get_folder_items(folder_id=..., limit=...)`
  - Only process items where `item.type == "file"`
  - For each file:
    - call `extract_structured(...)`
    - then `write_metadata(...)`
- Errors on one file must not stop the batch.
- Print progress per file (e.g., `[2/10] Processing file 12345`).

**Rules:**
- Do not duplicate extraction or write-back logic.
- Do not require batch mode for single-file usage.
- Pagination may be simplified for demos (single page) unless explicitly needed.

---

## 6) README expectations (must be included)

README.md should include:
- Create venv + install deps:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt
- Copy env:
  - cp .env.example .env
- Run dry run + real run commands:
  - python -m src.cli run --file-id <FILE_ID> --dry-run
  - python -m src.cli run --file-id <FILE_ID>
- Troubleshooting:
  - missing env vars
  - incorrect template key/scope
  - metadata already exists (and what the tool does)
  - import errors: upgrade `box-sdk-gen` and ensure imports match this spec

---

## 7) Code style constraints

- Type hints for public functions.
- Keep files short and single-purpose.
- Avoid unnecessary abstractions.
- Prefer clear prints over logging frameworks.
- No unused imports (keep lint clean).

---

## 8) Known sharp edges (design around them)

- Box SDK Gen schema module names are versioned/fragile.
  - This spec intentionally uses schema modules that exist in common installs:
    - ai_extract_structured
    - ai_agent_extract_structured
    - ai_item_base
- Do not “guess” alternate imports.
  - If an import fails, upgrade dependencies:
    - pip install --upgrade box-sdk-gen

---

## 9) Expected outcome

A developer should be able to:
- set `.env`
- run a dry run and see a clean dict of extracted fields
- run a real run and see metadata written back to the file in Box
- optionally extend the workflow to process a folder of files

Keep the workflow tight, reproducible, and aligned to the import rules above.
