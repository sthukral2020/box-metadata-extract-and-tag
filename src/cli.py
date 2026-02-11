import argparse
import os
import sys
from typing import Optional

# Add the project root to sys.path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.box_client import load_env, get_box_client
from src.extract import extract_structured

def main():
    parser = argparse.ArgumentParser(description="Box AI Metadata Extraction CLI")
    parser.add_argument("--file-id", type=str, help="Single Box File ID to process")
    parser.add_argument("--folder-id", type=str, help="Box Folder ID to process all files within")
    parser.add_argument("--template-key", type=str, help="Metadata template key (optional; defaults from env)")
    parser.add_argument("--scope", type=str, help="Metadata template scope (optional)")
    parser.add_argument("--model", type=str, help="AI model to use (optional)")
    
    args = parser.parse_args()

    if not args.file_id and not args.folder_id:
        print("Error: You must provide either --file-id or --folder-id")
        return 1

    # Load credentials and authenticate
    print("[Step 1] Authenticating with Box (CCG)...")
    env = load_env()
    client = get_box_client(env)
    
    # Use Enterprise ID from environment configuration
    enterprise_id = env.enterprise_id
    scope = args.scope or env.metadata_scope
    template_key = args.template_key or env.metadata_template_key
    model = args.model or env.ai_model

    print(f"Using scope: {scope}")
    print(f"Using template key: {template_key}")

    # Determine which files to process
    file_ids = []
    if args.file_id:
        file_ids.append(args.file_id)
    elif args.folder_id:
        print(f"Listing files in folder {args.folder_id}...")
        items = client.folders.get_folder_items(args.folder_id)
        for item in items.entries:
            if item.type == "file":
                file_ids.append(item.id)
        print(f"Found {len(file_ids)} files to process.")

    # Process files
    for idx, f_id in enumerate(file_ids, 1):
        print(f"\n[{idx}/{len(file_ids)}] Processing file {f_id}...")
        try:
            # Step 2 & 3: Extract and Normalize
            print("[Step 2] Extracting structured metadata...")
            extracted = extract_structured(
                client=client,
                file_id=f_id,
                template_key=template_key,
                scope=scope,
                model=model
            )

            print("[Step 3] Normalized extracted metadata:")

            # NEW LOGIC: Check if we actually got data back
            if not extracted or all(v is None for v in extracted.values()):
                print(f"⚠️  Skipping: AI could not extract any data for file {f_id}.")
                continue

            print(f"Extracted Metadata: {extracted}")

            # Step 4: Write metadata to Box
            print("[Step 4] Writing metadata to Box...")
            client.file_metadata.create_file_metadata_by_id(
                file_id=f_id,
                scope=scope,
                template_key=template_key,
                data=extracted
            )
            print(f"✅ Successfully updated metadata for {f_id}")

        except Exception as e:
            # Check if error is because metadata already exists
            if "already_exists" in str(e).lower():
                print(f"ℹ️  Metadata already exists for file {f_id}. Updating instead...")
                client.file_metadata.update_file_metadata_by_id(
                    file_id=f_id,
                    scope=scope,
                    template_key=template_key,
                    update_operation=[{"op": "replace", "path": f"/{k}", "value": v} for k, v in extracted.items()]
                )
            else:
                print(f"❌ Error processing file {f_id}: {e}")

    print("\n✅ Done")
    return 0

if __name__ == "__main__":
    sys.exit(main())