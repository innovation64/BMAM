#!/usr/bin/env python3
"""
Phase 4 P1 Track 2 - KG Telemetry Module
Observability for KG fact usage in retrieval pipeline
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any


class Phase4P1Telemetry:
    """
    Telemetry module to track KG fact surfacing and usage
    Dumps per-query JSON logs to logs/phase4_p1_track2/
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.log_dir = Path("logs/phase4_p1_track2")

        if self.enabled:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.query_count = 0

    def log_retrieval(
        self,
        query: str,
        top_k_memories: List[Dict[str, Any]],
        kg_facts_extracted: List[Dict[str, Any]],
        final_answer: str = None,
        question_num: int = None
    ):
        """
        Log retrieval telemetry for a single query

        Args:
            query: The user query/question
            top_k_memories: Top-k memories returned after ranking
            kg_facts_extracted: KG facts extracted before merging
            final_answer: The final LLM answer (if available)
            question_num: Question number for benchmarks
        """
        if not self.enabled:
            return

        self.query_count += 1

        # Analyze KG facts in top-k
        kg_in_top3 = []
        kg_in_top10 = []
        kg_facts_count = len(kg_facts_extracted)

        for i, mem in enumerate(top_k_memories[:10]):
            mem_id = mem.get('id', '')
            is_kg = mem_id.startswith('kg_fact_') or mem.get('source') == 'knowledge_graph'

            if is_kg:
                kg_info = {
                    'rank': i + 1,
                    'id': mem_id,
                    'content': mem.get('content', ''),
                    'plasticity_score': mem.get('plasticity_score'),
                    'score': mem.get('score')
                }

                if i < 3:
                    kg_in_top3.append(kg_info)
                kg_in_top10.append(kg_info)

        # Build telemetry record
        telemetry_record = {
            'session_id': self.session_id,
            'query_num': self.query_count,
            'timestamp': datetime.now().isoformat(),
            'question_num': question_num,
            'query': query,
            'kg_facts_extracted': kg_facts_count,
            'kg_in_top3_count': len(kg_in_top3),
            'kg_in_top10_count': len(kg_in_top10),
            'kg_in_top3': kg_in_top3,
            'kg_in_top10': kg_in_top10,
            'top_k_memories': [
                {
                    'rank': i + 1,
                    'id': mem.get('id', ''),
                    'source': mem.get('source', 'unknown'),
                    'content_preview': mem.get('content', '')[:100],
                    'plasticity_score': mem.get('plasticity_score'),
                    'score': mem.get('score'),
                    'is_kg': mem.get('id', '').startswith('kg_fact_') or mem.get('source') == 'knowledge_graph'
                }
                for i, mem in enumerate(top_k_memories[:10])
            ],
            'final_answer': final_answer
        }

        # Write to JSON file
        filename = f"q{question_num:03d}_query{self.query_count:03d}.json" if question_num else f"query{self.query_count:03d}.json"
        filepath = self.log_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(telemetry_record, f, indent=2, ensure_ascii=False)

        # Also append to summary log
        summary_file = self.log_dir / f"session_{self.session_id}_summary.jsonl"
        with open(summary_file, 'a', encoding='utf-8') as f:
            summary = {
                'q': question_num,
                'kg_extracted': kg_facts_count,
                'kg_top3': len(kg_in_top3),
                'kg_top10': len(kg_in_top10),
                'query': query[:80]
            }
            f.write(json.dumps(summary, ensure_ascii=False) + '\n')

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics for the session"""
        summary_file = self.log_dir / f"session_{self.session_id}_summary.jsonl"

        if not summary_file.exists():
            return {}

        total_queries = 0
        queries_with_kg = 0
        kg_in_top3_count = 0

        with open(summary_file, 'r') as f:
            for line in f:
                record = json.loads(line)
                total_queries += 1
                if record['kg_extracted'] > 0:
                    queries_with_kg += 1
                if record['kg_top3'] > 0:
                    kg_in_top3_count += 1

        return {
            'total_queries': total_queries,
            'queries_with_kg_extracted': queries_with_kg,
            'queries_with_kg_in_top3': kg_in_top3_count,
            'kg_surfacing_rate': kg_in_top3_count / total_queries if total_queries > 0 else 0
        }


# Global telemetry instance (can be enabled via environment variable)
_telemetry_enabled = os.getenv('BMAM_ENABLE_P4P1_TELEMETRY', '').lower() in ('1', 'true', 'yes')
telemetry = Phase4P1Telemetry(enabled=_telemetry_enabled)
