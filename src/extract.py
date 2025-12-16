from __future__ import annotations

from typing import Any, Dict, Optional


def normalize_extracted_metadata(answer: Any) -> Dict[str, Any]:
    """
    Normalize Box AI Extract Structured response into a plain dict.

    Rules (per agents.md):
    - If `answer` has `to_dict()`, call it.
    - If it's already a dict, use it.
    - Strip any leading `d_` key prefixes (Box SDK Gen quirk).
    """

    if answer is None:
        return {}

    if hasattr(answer, "to_dict") and callable(getattr(answer, "to_dict")):
        raw = answer.to_dict()
    elif isinstance(answer, dict):
        raw = answer
    else:
        # Best-effort fallback: sometimes SDK objects can be cast to dict via vars()
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

    Must match agents.md call pattern:
    - client.ai.create_ai_extract_structured(...)
    - items=[AiItemBase(id=<file_id>, type=AiItemBaseTypeField.FILE)]
    - metadata_template=CreateAiExtractStructuredMetadataTemplate(template_key=<TEMPLATE_KEY>, scope=<SCOPE>)
    - ai_agent=AiAgentExtractStructured(type=..., long_text=..., basic_text=...)
    """

    # SDK import paths can vary slightly between versions; keep strict to box_sdk_gen.
    try:
        from box_sdk_gen.schemas.ai_item_base import AiItemBase
        from box_sdk_gen.schemas.ai_item_base_type_field import AiItemBaseTypeField
    except Exception:  # pragma: no cover
        from box_sdk_gen.schemas.ai_item_base import AiItemBase  # type: ignore
        from box_sdk_gen.schemas.ai_item_base import AiItemBaseTypeField  # type: ignore

    from box_sdk_gen.schemas.ai_extract_structured import (
        AiExtractStructuredMetadataTemplateField,
        AiExtractStructuredMetadataTemplateTypeField,
    )

    try:
        from box_sdk_gen.schemas.ai_agent_extract_structured import AiAgentExtractStructured
        from box_sdk_gen.schemas.ai_agent_extract_structured_type_field import (
            AiAgentExtractStructuredTypeField,
        )
        from box_sdk_gen.schemas.ai_agent_long_text_tool import AiAgentLongTextTool
        from box_sdk_gen.schemas.ai_agent_basic_text_tool import AiAgentBasicTextTool
    except Exception:  # pragma: no cover
        # Some SDK versions consolidate enums/classes; keep best-effort fallbacks.
        from box_sdk_gen.schemas.ai_agent_extract_structured import (  # type: ignore
            AiAgentExtractStructured,
        )
        from box_sdk_gen.schemas.ai_agent_extract_structured import (  # type: ignore
            AiAgentExtractStructuredTypeField,
        )
        from box_sdk_gen.schemas.ai_agent_long_text_tool import AiAgentLongTextTool  # type: ignore
        from box_sdk_gen.schemas.ai_agent_basic_text_tool import AiAgentBasicTextTool  # type: ignore

    items = [AiItemBase(id=file_id, type=AiItemBaseTypeField.FILE)]
    metadata_template = AiExtractStructuredMetadataTemplateField(
        type=AiExtractStructuredMetadataTemplateTypeField.METADATA_TEMPLATE,
        template_key=template_key,
        scope=scope,
    )

    ai_agent = None
    if model:
        ai_agent = AiAgentExtractStructured(
            type=AiAgentExtractStructuredTypeField.AI_AGENT_EXTRACT_STRUCTURED,
            long_text=AiAgentLongTextTool(model=model),
            basic_text=AiAgentBasicTextTool(model=model),
        )

    resp = client.ai.create_ai_extract_structured(
        items=items,
        metadata_template=metadata_template,
        ai_agent=ai_agent,
    )

    return normalize_extracted_metadata(getattr(resp, "answer", None))
