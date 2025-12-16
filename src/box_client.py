from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class BoxEnv:
    """Validated environment config (scaffold)."""

    client_id: str
    client_secret: str
    enterprise_id: str

    metadata_template_key: str
    metadata_scope: str
    ai_model: Optional[str]


def load_env() -> BoxEnv:
    """
    Load `.env` and validate required variables.

    This is a scaffold; implementation should match agents.md:
    - load_dotenv()
    - validate required env vars
    - derive default scope: enterprise_{BOX_ENTERPRISE_ID}
    """

    load_dotenv()

    client_id = (os.getenv("BOX_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("BOX_CLIENT_SECRET") or "").strip()
    enterprise_id = (os.getenv("BOX_ENTERPRISE_ID") or "").strip()

    if not client_id or not client_secret or not enterprise_id:
        raise RuntimeError(
            "Missing required env vars: BOX_CLIENT_ID, BOX_CLIENT_SECRET, BOX_ENTERPRISE_ID. "
            "Copy `.env.example` to `.env` and fill values."
        )

    template_key = (os.getenv("BOX_METADATA_TEMPLATE_KEY") or "identifications").strip()
    scope = (os.getenv("BOX_METADATA_SCOPE") or f"enterprise_{enterprise_id}").strip()
    model = (os.getenv("BOX_AI_MODEL") or "").strip() or None

    return BoxEnv(
        client_id=client_id,
        client_secret=client_secret,
        enterprise_id=enterprise_id,
        metadata_template_key=template_key,
        metadata_scope=scope,
        ai_model=model,
    )


def get_box_client():
    """
    Return a BoxClient authenticated with CCG (enterprise).

    TODO: Implement using box_sdk_gen per agents.md:
      - CCGConfig(client_id, client_secret, enterprise_id)
      - BoxCCGAuth(config=...)
      - BoxClient(auth=auth)
    """
    # Local imports keep import-time side effects minimal for CLI help usage.
    from box_sdk_gen import BoxClient, BoxCCGAuth, CCGConfig

    env = load_env()
    config = CCGConfig(
        client_id=env.client_id,
        client_secret=env.client_secret,
        enterprise_id=env.enterprise_id,
    )
    auth = BoxCCGAuth(config=config)
    return BoxClient(auth=auth)
