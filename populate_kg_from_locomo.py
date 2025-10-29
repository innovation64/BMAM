#!/usr/bin/env python3
"""
批量回放 LoCoMo 历史会话，填充 Knowledge Graph。

步骤：
1. 加载本地 LoCoMo 数据集，提取前 19 个会话。
2. 通过海马体存储会话内容，触发实体/关系抽取。
3. 验证共享 KnowledgeGraphBuilder 与颞叶 SimpleKG 的数据量。
4. 保存 KG 数据快照，并执行一次 KG 联合检索冒烟测试。
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
import re

# ---------------------------------------------------------------------------
# 项目路径配置
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.coordination.brain_coordinator import BrainInspiredCoordinator  # noqa: E402
from src.utils.config import get_logger  # noqa: E402

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------

def _load_locomo_sessions() -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    从本地 LoCoMo JSON 数据集中提取会话文本。

    Returns:
        sessions: [{'id': int, 'timestamp': str, 'content': str}]
        error: None 或错误描述
    """
    candidate_paths = [
        PROJECT_ROOT.parent / "MemOS" / "evaluation" / "data" / "locomo" / "locomo10.json",  # testversion/MemOS
        PROJECT_ROOT / "MemOS" / "evaluation" / "data" / "locomo" / "locomo10.json",
        PROJECT_ROOT / "evaluation" / "data" / "locomo" / "locomo10.json",
        PROJECT_ROOT / "data" / "locomo10.json",
    ]

    data_path = next((p for p in candidate_paths if p.exists()), None)
    if not data_path:
        return [], f"LoCoMo dataset not found. Checked: {[str(p) for p in candidate_paths]}"

    try:
        with data_path.open("r", encoding="utf-8") as f:
            dataset = json.load(f)
    except Exception as exc:
        return [], f"Failed to read dataset: {exc}"

    if not dataset:
        return [], "Dataset is empty"

    sample = dataset[0]
    conversation = sample.get("conversation")
    if not isinstance(conversation, dict):
        return [], "Invalid conversation structure in dataset"

    sessions: List[Dict[str, Any]] = []
    primary_speaker = conversation.get("speaker_a")
    secondary_speaker = conversation.get("speaker_b")
    speakers = [name for name in (primary_speaker, secondary_speaker) if name]

    for idx in range(1, 36):  # 数据集中共有 35 场会话，先取前 19 场
        key = f"session_{idx}"
        if key not in conversation:
            continue

        entries = conversation.get(key, [])
        if not isinstance(entries, list):
            entries = []

        sessions.append(
            {
                "id": idx,
                "timestamp": conversation.get(f"{key}_date_time", ""),
                "turns": entries,
                "speakers": speakers,
            }
        )

        if len(sessions) >= 19:
            break

    if not sessions:
        return [], "No sessions extracted from dataset conversation block"

    return sessions, None


def _case_preserving_replacement(replacement: str):
    """Return a replacement function that preserves the original token casing."""

    def repl(match: re.Match) -> str:
        token = match.group(0)
        if token.isupper():
            return replacement.upper()
        if token[0].isupper():
            return replacement[0].upper() + replacement[1:]
        return replacement

    return repl


def _replace_pronouns(text: str, speaker: str, listener: Optional[str]) -> str:
    """Replace first/second-person pronouns with explicit speaker/listener names."""
    if not speaker:
        return text

    replacements = [
        (r"\bI'm\b", f"{speaker} is"),
        (r"\bI am\b", f"{speaker} is"),
        (r"\bI'd\b", f"{speaker} would"),
        (r"\bI would\b", f"{speaker} would"),
        (r"\bI'll\b", f"{speaker} will"),
        (r"\bI will\b", f"{speaker} will"),
        (r"\bI've\b", f"{speaker} has"),
        (r"\bI have\b", f"{speaker} has"),
        (r"\bI\b", speaker),
        (r"\bme\b", speaker),
        (r"\bmy\b", f"{speaker}'s"),
        (r"\bmine\b", f"{speaker}'s"),
        (r"\bmyself\b", speaker),
    ]

    if listener:
        replacements.extend(
            [
                (r"\byou're\b", f"{listener} are"),
                (r"\byou are\b", f"{listener} are"),
                (r"\byou'll\b", f"{listener} will"),
                (r"\byou will\b", f"{listener} will"),
                (r"\byou've\b", f"{listener} have"),
                (r"\byou have\b", f"{listener} have"),
                (r"\byou\b", listener),
                (r"\byour\b", f"{listener}'s"),
                (r"\byours\b", f"{listener}'s"),
                (r"\byourself\b", listener),
            ]
        )

    processed = text
    for pattern, replacement in replacements:
        processed = re.sub(
            pattern,
            _case_preserving_replacement(replacement),
            processed,
            flags=re.IGNORECASE,
        )
    return processed


def _select_listener(speaker: str, speakers: List[str]) -> Optional[str]:
    for candidate in speakers:
        if candidate and candidate != speaker:
            return candidate
    return None


def _prepare_session_content(
    session: Dict[str, Any],
    kg_builder,
    registered_speakers: Set[str],
) -> str:
    """Convert session turns into enriched text and register aliases."""
    turns = session.get("turns", [])
    speakers = session.get("speakers", [])
    lines: List[str] = []

    if not speakers:
        logger.debug("⚠️ Session %s has no speaker metadata; pronoun replacement limited", session.get("id"))

    for turn in turns:
        speaker = turn.get("speaker") or "Unknown"
        text = str(turn.get("text", ""))
        listener = _select_listener(speaker, speakers)
        enriched_text = _replace_pronouns(text, speaker, listener)
        lines.append(f"{speaker}: {enriched_text}")

        if kg_builder and speaker not in registered_speakers:
            kg_builder.register_known_person(speaker)
            # Register common pronoun aliases for this speaker (first-person)
            pronoun_aliases = [
                "i",
                "me",
                "my",
                "mine",
                "myself",
                f"{speaker.lower()}'s",
            ]
            for alias in pronoun_aliases:
                kg_builder.register_alias(alias, speaker)
            registered_speakers.add(speaker)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

async def populate_kg_from_locomo() -> None:
    """将 LoCoMo 会话回放到系统中，填充知识图谱。"""

    logger.info("=" * 80)
    logger.info("📦 LoCoMo Knowledge Graph Population")
    logger.info("=" * 80)

    logger.info("📦 Loading LoCoMo sessions from local dataset...")
    sessions, error = _load_locomo_sessions()
    if error:
        logger.error(f"❌ {error}")
        return

    logger.info(f"📝 Extracted {len(sessions)} sessions from dataset")

    logger.info("🧠 Initializing BrainInspiredCoordinator with shared KG...")
    os.environ["BMAM_TEST_MODE"] = "true"  # 禁用后台循环，避免干扰

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    if not hasattr(coordinator, "knowledge_graph_builder"):
        logger.error("❌ Coordinator missing knowledge_graph_builder!")
        return

    logger.info("✅ Coordinator initialized with shared KnowledgeGraphBuilder")

    logger.info("=" * 80)
    logger.info("🔄 Processing sessions through Hippocampus (KG extraction enabled)")
    logger.info("=" * 80)

    stored_count = 0
    failed_count = 0

    kg_builder = getattr(coordinator, "knowledge_graph_builder", None)
    registered_speakers: Set[str] = set()

    for session in sessions:
        try:
            logger.info(f"📝 Processing session {session['id']}/{len(sessions)}...")

            content = _prepare_session_content(session, kg_builder, registered_speakers)

            metadata = {
                "session_id": session["id"],
                "dataset": "LoCoMo",
                "replay": True,
                "session_timestamp": session.get("timestamp", ""),
                "speakers": session.get("speakers", []),
            }

            result = await coordinator.hippocampus.store_memory(
                content=content,
                metadata=metadata,
                auto_extract_kg=True,
            )

            if result and result.get("stored"):
                stored_count += 1
                logger.info(
                    f"  ✅ Session {session['id']} stored (ID: {result.get('memory_id', 'N/A')})"
                )
            else:
                failed_count += 1
                logger.warning(f"  ⚠️ Session {session['id']} storage returned no success")

        except Exception as exc:
            failed_count += 1
            logger.error(f"  ❌ Session {session['id']} failed: {exc}")

    logger.info("=" * 80)
    logger.info(f"📊 Storage complete: {stored_count} success, {failed_count} failed")
    logger.info("=" * 80)

    logger.info("🔍 Verifying Knowledge Graph population...")

    kg_builder = getattr(coordinator, "knowledge_graph_builder", None)
    temporal_kg = getattr(coordinator, "temporal_lobe", None).kg if hasattr(
        coordinator, "temporal_lobe"
    ) else None

    if kg_builder:
        try:
            stats = kg_builder.get_statistics() or {}
            logger.info("📊 KnowledgeGraphBuilder stats:")
            logger.info(f"   Entities: {stats.get('entity_count', 0)}")
            logger.info(f"   Relations: {stats.get('relation_count', 0)}")
            logger.info(f"   Triples: {stats.get('triple_count', 0)}")

            if hasattr(kg_builder, "get_all_triples"):
                triples = kg_builder.get_all_triples()
                logger.info(f"   Total triples in Builder: {len(triples)}")
                if triples:
                    logger.info("   Sample triples:")
                    for subj, pred, obj in triples[:5]:
                        logger.info(f"      ({subj}, {pred}, {obj})")
        except Exception as exc:
            logger.error(f"❌ Failed to read builder stats: {exc}")

    if temporal_kg:
        try:
            entity_count = len(temporal_kg.graph.keys())
            logger.info("📊 TemporalLobe SimpleKG:")
            logger.info(f"   Entities: {entity_count}")
            if temporal_kg.graph:
                logger.info("   Sample entities:")
                for entity in list(temporal_kg.graph.keys())[:5]:
                    relations = temporal_kg.graph[entity]
                    logger.info(f"      {entity} → {len(relations)} relations")
        except Exception as exc:
            logger.error(f"❌ Failed to read temporal KG stats: {exc}")

    logger.info("🔍 Checking for key entities...")
    key_entities = ["Caroline", "Melanie", "LGBTQ", "adoption", "transgender"]

    kg_entities: set[str] = set()
    try:
        if hasattr(coordinator.temporal_lobe, "get_kg_entities"):
            entity_list = await coordinator.temporal_lobe.get_kg_entities()
            if entity_list:
                kg_entities.update(entity_list)
        elif temporal_kg:
            kg_entities.update(temporal_kg.graph.keys())
    except Exception as exc:
        logger.error(f"❌ Failed to gather KG entities: {exc}")

    for entity in key_entities:
        status = "✅" if entity in kg_entities else "❌"
        logger.info(f"   {status} {entity}: {'FOUND' if entity in kg_entities else 'NOT FOUND'}")

    logger.info("💾 Saving Knowledge Graph snapshot to disk...")
    try:
        kg_save_path = PROJECT_ROOT / "data" / "locomo_kg.json"
        kg_save_path.parent.mkdir(parents=True, exist_ok=True)

        triple_list: List[Tuple[str, str, str]] = (
            kg_builder.get_all_triples() if kg_builder and hasattr(kg_builder, "get_all_triples") else []
        )

        kg_data = {
            "builder_triples": [
                {"subject": s, "predicate": p, "object": o} for s, p, o in triple_list
            ],
            "temporal_entities": list(temporal_kg.graph.keys()) if temporal_kg else [],
            "metadata": {
                "source": "LoCoMo",
                "sessions_processed": stored_count,
                "timestamp": time.time(),
            },
        }

        with kg_save_path.open("w", encoding="utf-8") as f:
            json.dump(kg_data, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ KG saved to {kg_save_path}")
        logger.info(f"   Builder triples: {len(kg_data['builder_triples'])}")
        logger.info(f"   Temporal entities: {len(kg_data['temporal_entities'])}")
    except Exception as exc:
        logger.error(f"❌ Failed to save KG snapshot: {exc}")

    logger.info("=" * 80)
    logger.info("🧪 Testing KG Joint Search with 'Caroline identity' query")
    logger.info("=" * 80)

    try:
        result = await coordinator.temporal_lobe.search_kg_memory_joint(
            query="What is Caroline's identity?",
            start_entity="Caroline",
            k=10,
            kg_depth=1,
            beta=0.6,
        )

        if result:
            memories = result.get("memories", [])
            logger.info(f"✅ KG Search returned {len(memories)} memories")
            logger.info(f"   KG expansion: {result.get('kg_expansion', {})}")
            logger.info(f"   KG triples found: {len(result.get('kg_triples', []))}")

            triples = result.get("kg_triples", [])
            if triples:
                logger.info("   Sample KG triples:")
                for triple in triples[:3]:
                    logger.info(f"      {triple}")
        else:
            logger.warning("⚠️ KG Search returned no results")
    except Exception as exc:
        logger.error(f"❌ KG Search test failed: {exc}")

    await coordinator.stop_system()

    logger.info("=" * 80)
    logger.info("✅ Knowledge Graph population complete!")
    logger.info("=" * 80)
    logger.info("")
    logger.info("📋 Next steps:")
    logger.info("   1. Review KG data in data/locomo_kg.json")
    logger.info("   2. export BMAM_TEST_MODE=true && python3 BMAM/run_locomo_test.py small")
    logger.info("   3. Confirm Q5 score recovers with KG enabled")


if __name__ == "__main__":
    try:
        asyncio.run(populate_kg_from_locomo())
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrupted by user")
    except Exception as exc:  # pragma: no cover
        logger.error(f"❌ Fatal error: {exc}", exc_info=True)
        sys.exit(1)
