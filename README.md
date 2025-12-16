# Box Metadata: Extract and Tag (Python)

This repo gives you two ways to get a working Box metadata extraction workflow:

1) **Vibecode your own app** using the included `agents.md` in Cursor (with copy/paste prompts), or  
2) **Run the included reference implementation** in `src/` (a complete, working example generated using the same `agents.md`).

Both paths produce the same outcome: extract structured fields from Box files via [Box AI Extract Structured](https://developer.box.com/guides/box-ai/ai-tutorials/extract-metadata-structured/) and [write them back as Box metadata](https://developer.box.com/reference/post-files-id-metadata-id-id/).

---

## What this workflow does

- Extracts structured metadata from **a single file** or **all files in a folder** (i.e., using a [metadata template](https://developer.box.com/guides/metadata/templates))
- Prints a normalized dict of extracted fields
- Optionally writes extracted fields back to each file as Box metadata
- Uses CCG ([Client Credentials Grant](https://developer.box.com/guides/authentication/client-credentials)) enterprise authentication
- Uses the [Box Generated Python SDK](https://github.com/box/box-python-sdk-gen) (`box-sdk-gen`)

---

## Why this workflow matters

In many organizations, important business information lives inside unstructured documents — invoices, contracts, statements, onboarding packets, and internal reports. While Box metadata is powerful for organizing content, enabling search, and driving automation, that metadata is often applied manually or through brittle, document-specific scripts.

This workflow shows how to use Box AI to extract structured data from real documents and write it back to Box as enterprise metadata. By grounding extraction in a shared metadata schema, teams can standardize how information is captured and applied across individual files or entire folders.

Common real-world use cases include:

- Invoices: extracting totals, dates, vendors, and payment terms
- Contracts: capturing effective dates, renewal terms, and counterparties
- Operations workflows: tagging files to trigger downstream automation
- Content governance: enforcing consistent metadata across teams and folders

The key idea is that Box content itself can become an input to downstream systems and processes. By extracting structured fields from documents and applying them as metadata, teams can improve discoverability, enable automation, and power business workflows.

Vibecoding combined with Box metadata extraction creates a fast feedback loop — moving from a shared schema, to a working application, to real metadata written back to Box, turning unstructured files into actionable data.

---

## Choose your path

This repo is intended for developers building content-driven workflows on Box, as well as platform teams looking to standardize metadata extraction at scale.

### Path A — Vibecode your own app in Cursor (recommended for learning)

You will:
- Start with `agents.md` as the specification/guardrails
- Use the prompts below in Cursor Chat to generate the code
- Run your generated CLI locally

→ Go to: [**Vibecoding in Cursor**](#vibecoding-in-cursor)

---

### Path B — Run the reference implementation in `src/` (recommended for testing)

You will:
- Set up a Python environment
- Configure `.env`
- Run the CLI that already exists in this repo

→ Go to: [**Run the reference implementation**](#run-the-reference-implementation)

---

# Vibecoding in Cursor

## 1) Create a new project folder
Create a new folder (or a new git repo), then copy `agents.md` into the **root** of that folder.

Your folder should start like:

```
your-project/
  agents.md
```

## 2) Use these Cursor prompts (in order)

### Prompt 1 — scaffold the project

Copy/paste exactly:

```
Using the instructions in agents.md, scaffold a minimal Python project for this demo.

Create:

- a requirements.txt
- a .env.example
- a basic repo structure under src/
- placeholder files (no full logic yet)

Keep it CLI-first and minimal.

(end)
```

Expected output:
- `requirements.txt`
- `.env.example`
- `src/` with placeholder modules (`box_client.py`, `extract.py`, `metadata.py`, `cli.py`)

---

### Prompt 2 — implement the single-file workflow

Copy/paste exactly:

```
Implement the single-file happy path end-to-end:

- Finish get_box_client() in src/box_client.py using CCG + python-dotenv
- Implement extract_structured(file_id, template_key, scope, model) in src/extract.py using client.ai.create_ai_extract_structured(...)
- Implement write_metadata(file_id, template_key, metadata_dict) in src/metadata.py using file metadata create (and handle “already exists” gracefully)
- Wire src/cli.py run --file-id ... to call extract → normalize → write-back, with clear step-labeled prints

Follow the guardrails in agents.md strictly (box_sdk_gen, AiItemBase, metadata template, normalization stripping d_ keys). Keep it minimal.

(end)
```

At this point you should be able to run:

```bash
python -m src.cli run --file-id <BOX_FILE_ID> --dry-run
```

---

### Prompt 3 — add folder support

Copy/paste exactly:

```
Using the rules in agents.md (including the “Optional: Folder (batch) processing” section), extend the existing CLI app to support processing a Box folder.

Requirements:
- Preserve the existing single-file flow exactly.
- Add an optional --folder-id flag to the run command.
- Require exactly one of --file-id or --folder-id.
- List folder items via client.folders.get_folder_items(...).
- Only process items where item.type == "file".
- For each file:
  - call extract_structured(...)
  - print the normalized dict
  - if not --dry-run, call write_metadata(...)
- Errors on one file must not stop the batch.
- Print progress like: [2/10] Processing file <id>.
- Keep it minimal and reuse existing functions.

(end)
```

After Prompt 3, both commands should work:

```bash
python -m src.cli run --file-id <BOX_FILE_ID> --dry-run
python -m src.cli run --folder-id <BOX_FOLDER_ID> --dry-run
```

---

# Run the reference implementation

If you just want a working example (or want to compare your vibecoded output), use the existing code already in `src/`.

## Requirements

- Python **3.10+**
- A Box application configured for **Client Credentials Grant (CCG)** enterprise auth
- A Box **enterprise metadata template** (e.g., `invoice`) whose field keys match extracted output

Dependencies:
- `box-sdk-gen`
- `python-dotenv`

## 1) Create and activate a virtual environment

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## 2) Install dependencies

```bash
pip install -r requirements.txt
```

## 3) Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set your real values:

- `BOX_CLIENT_ID`
- `BOX_CLIENT_SECRET`
- `BOX_ENTERPRISE_ID`
- `BOX_METADATA_TEMPLATE_KEY`
- `BOX_METADATA_SCOPE` (optional; defaults to `enterprise_{BOX_ENTERPRISE_ID}`)
- `BOX_AI_MODEL` (optional)

> ⚠️ Never commit real credentials. Treat `.env` as secret.

## 4) Run (single file)

Dry run (recommended first):

```bash
python -m src.cli run --file-id <BOX_FILE_ID> --dry-run
```

Write-back (i.e., tag file with metadata):

```bash
python -m src.cli run --file-id <BOX_FILE_ID>
```

## 5) Run (folder)

Dry run:

```bash
python -m src.cli run --folder-id <BOX_FOLDER_ID> --dry-run
```

Write-back (i.e., tag files with metadata):

```bash
python -m src.cli run --folder-id <BOX_FOLDER_ID>
```

Behavior:
- Only file items are processed
- Each file is handled independently
- Errors on one file do **not** stop the batch

---

## Notes on metadata templates

For write-back to succeed:
- The template key must exist in your Box enterprise
- Extracted keys must match the template’s field keys

If keys differ, adjust the template or add a mapping step.

---

## Troubleshooting

### Import errors (`ModuleNotFoundError`)
- Confirm your venv is activated
- Reinstall: `pip install -r requirements.txt`
- Upgrade: `pip install --upgrade box-sdk-gen`
- Ensure generated imports match `agents.md` (do not “guess” alternate module paths)

### Extraction works, but write-back fails
- Confirm template key and scope
- Ensure fields are not marked required unless they are always present
- Start with files that do not already have the template applied

---

## License

MIT (see `LICENSE`)
