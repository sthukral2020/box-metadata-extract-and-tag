from __future__ import annotations
from typing import Any, Dict, Optional

# --- SAFE IMPORT BLOCK ---
# We try multiple common locations for the options schema to handle SDK version 1.17.0
try:
    from box_sdk_gen.schemas.create_ai_extract_structured_options import CreateAiExtractStructuredOptions
except ImportError:
    try:
        from box_sdk_gen.managers.ai import CreateAiExtractStructuredOptions
    except ImportError:
        CreateAiExtractStructuredOptions = None 
# -------------------------

def normalize_extracted_metadata(answer: Any) -> Dict[str, Any]:
    """
    Normalize Box AI Extract Structured response into a plain dict.

    Rules:
    - If `answer` has `to_dict()`, call it.
    - If it's already a dict, use it.
    - Strip any leading `d_` key prefixes (a known Box SDK Gen quirk).
    """
    if answer is None:
        return {}

    if hasattr(answer, "to_dict") and callable(getattr(answer, "to_dict")):
        raw = answer.to_dict()
    elif isinstance(answer, dict):
        raw = answer
    else:
        raw = dict(getattr(answer, "__dict__", {}) or {})

    out: Dict[str, Any] = {}
    for k, v in (raw or {}).items():
        key = k[2:] if isinstance(k, str) and k.startswith("d_") else k
        out[key] = v
    return out


def extract_structured(
    client: Any,
    file_id: str,
    template_key: str,
    scope: str,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract structured metadata from a single Box file via Box AI.
    Includes confidence scores if the SDK version supports it.
    """

    # SDK internal imports for AI items
    try:
        from box_sdk_gen.schemas.ai_item_base import AiItemBase
        from box_sdk_gen.schemas.ai_item_base_type_field import AiItemBaseTypeField
    except Exception:
        from box_sdk_gen.schemas.ai_item_base import AiItemBase  # type: ignore
        from box_sdk_gen.schemas.ai_item_base import AiItemBaseTypeField  # type: ignore

    from box_sdk_gen.schemas.ai_extract_structured import (
        AiExtractStructuredMetadataTemplateField,
        AiExtractStructuredMetadataTemplateTypeField,
    )

    # SDK internal imports for AI Agents
    try:
        from box_sdk_gen.schemas.ai_agent_extract_structured import AiAgentExtractStructured
        from box_sdk_gen.schemas.ai_agent_extract_structured_type_field import (
            AiAgentExtractStructuredTypeField,
        )
        from box_sdk_gen.schemas.ai_agent_long_text_tool import AiAgentLongTextTool
        from box_sdk_gen.schemas.ai_agent_basic_text_tool import AiAgentBasicTextTool
    except Exception:
        from box_sdk_gen.schemas.ai_agent_extract_structured import AiAgentExtractStructured  # type: ignore
        from box_sdk_gen.schemas.ai_agent_extract_structured import AiAgentExtractStructuredTypeField  # type: ignore
        from box_sdk_gen.schemas.ai_agent_long_text_tool import AiAgentLongTextTool  # type: ignore
        from box_sdk_gen.schemas.ai_agent_basic_text_tool import AiAgentBasicTextTool  # type: ignore

    # Define the file to be processed
    items = [AiItemBase(id=file_id, type=AiItemBaseTypeField.FILE)]
    
    #