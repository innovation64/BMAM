"""
Feedback Stats Logger
Quantifies the effectiveness of the feedback loop by logging feedback events and outcomes.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..utils.config import get_logger
from ..utils.paths import BMAMPaths

logger = get_logger(__name__)

class FeedbackStatsLogger:
    """
    Logs feedback loop statistics to a JSONL file.
    Tracks:
    - Feedback signals generated
    - Facts/Triples extracted from feedback
    - Effectiveness scores
    """
    
    def __init__(self, log_dir: str = None):
        # Use unified paths by default
        self.log_dir = Path(log_dir) if log_dir else BMAMPaths.DATA_DIR / "feedback_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "feedback_stats.jsonl"
        
    def log_feedback_event(self, event_data: Dict[str, Any]):
        """
        Log a feedback event.
        
        Args:
            event_data: {
                'timestamp': str,
                'query': str,
                'feedback_type': str,
                'signals_processed': int,
                'facts_extracted': int,
                'triples_extracted': int,
                'effectiveness': float,
                'errors': int
            }
        """
        try:
            if 'timestamp' not in event_data:
                event_data['timestamp'] = datetime.now().isoformat()
                
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event_data, ensure_ascii=False) + '\n')
                
            logger.debug(f"📊 Logged feedback stats: effectiveness={event_data.get('effectiveness', 0):.2f}")
            
        except Exception as e:
            logger.error(f"Failed to log feedback stats: {e}")

    def get_recent_stats(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent feedback stats"""
        stats = []
        if not self.log_file.exists():
            return stats
            
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in reversed(lines[-limit:]):
                    try:
                        stats.append(json.loads(line))
                    except:
                        pass
        except Exception as e:
            logger.error(f"Failed to read feedback stats: {e}")
            
        return stats
