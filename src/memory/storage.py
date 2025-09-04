import sqlite3
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import os

class MemoryStorage:
    """Persistent storage backend for conditional memory"""
    
    def __init__(self, db_path: str = "ma-cmm/data/memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create conditions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conditions (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                text TEXT NOT NULL,
                source_turn INTEGER,
                confidence TEXT,
                importance_score REAL,
                timestamp TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                metadata TEXT
            )
        ''')
        
        # Create conflicts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                condition1_id TEXT,
                condition2_id TEXT,
                conflict_type TEXT,
                resolution TEXT,
                FOREIGN KEY (condition1_id) REFERENCES conditions(id),
                FOREIGN KEY (condition2_id) REFERENCES conditions(id)
            )
        ''')
        
        # Create sessions table for dialogue history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                start_time TEXT,
                end_time TEXT,
                dialogue_history TEXT,
                memory_snapshot TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_condition(self, condition: Dict[str, Any], category: str) -> bool:
        """Save a condition to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO conditions 
                (id, category, text, source_turn, confidence, importance_score, 
                 timestamp, access_count, last_accessed, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                condition.get('id'),
                category,
                condition.get('text', ''),
                condition.get('source_turn', -1),
                condition.get('confidence', 'medium'),
                condition.get('importance_score', 0.5),
                condition.get('timestamp', datetime.now().isoformat()),
                condition.get('access_count', 0),
                condition.get('last_accessed', datetime.now().isoformat()),
                json.dumps(condition.get('metadata', {}))
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving condition: {e}")
            return False
        finally:
            conn.close()
    
    def load_condition(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """Load a condition from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM conditions WHERE id = ?
        ''', (condition_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_condition(row)
        return None
    
    def load_all_conditions(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load all conditions, optionally filtered by category"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if category:
            cursor.execute('SELECT * FROM conditions WHERE category = ?', (category,))
        else:
            cursor.execute('SELECT * FROM conditions')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_condition(row) for row in rows]
    
    def delete_condition(self, condition_id: str) -> bool:
        """Delete a condition from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM conditions WHERE id = ?', (condition_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def save_conflict(self, conflict: Dict[str, Any]) -> int:
        """Save a conflict record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO conflicts 
            (timestamp, condition1_id, condition2_id, conflict_type, resolution)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            conflict.get('timestamp', datetime.now().isoformat()),
            conflict.get('condition1_id'),
            conflict.get('condition2_id'),
            conflict.get('type', 'unknown'),
            conflict.get('resolution', '')
        ))
        
        conn.commit()
        conflict_id = cursor.lastrowid
        conn.close()
        
        return conflict_id
    
    def load_conflicts(self, condition_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load conflict history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if condition_id:
            cursor.execute('''
                SELECT * FROM conflicts 
                WHERE condition1_id = ? OR condition2_id = ?
            ''', (condition_id, condition_id))
        else:
            cursor.execute('SELECT * FROM conflicts')
        
        rows = cursor.fetchall()
        conn.close()
        
        conflicts = []
        for row in rows:
            conflicts.append({
                'id': row[0],
                'timestamp': row[1],
                'condition1_id': row[2],
                'condition2_id': row[3],
                'type': row[4],
                'resolution': row[5]
            })
        
        return conflicts
    
    def save_session(self, session_id: str, dialogue_history: List[Dict], 
                    memory_snapshot: Dict) -> bool:
        """Save a dialogue session with memory snapshot"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO sessions 
                (session_id, start_time, end_time, dialogue_history, memory_snapshot)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                session_id,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                json.dumps(dialogue_history),
                json.dumps(memory_snapshot)
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving session: {e}")
            return False
        finally:
            conn.close()
    
    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load a session by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'session_id': row[1],
                'start_time': row[2],
                'end_time': row[3],
                'dialogue_history': json.loads(row[4]),
                'memory_snapshot': json.loads(row[5])
            }
        return None
    
    def _row_to_condition(self, row) -> Dict[str, Any]:
        """Convert database row to condition dict"""
        return {
            'id': row[0],
            'category': row[1],
            'text': row[2],
            'source_turn': row[3],
            'confidence': row[4],
            'importance_score': row[5],
            'timestamp': row[6],
            'access_count': row[7],
            'last_accessed': row[8],
            'metadata': json.loads(row[9]) if row[9] else {}
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Total conditions
        cursor.execute('SELECT COUNT(*) FROM conditions')
        stats['total_conditions'] = cursor.fetchone()[0]
        
        # Conditions by category
        cursor.execute('''
            SELECT category, COUNT(*) FROM conditions 
            GROUP BY category
        ''')
        stats['by_category'] = dict(cursor.fetchall())
        
        # Total conflicts
        cursor.execute('SELECT COUNT(*) FROM conflicts')
        stats['total_conflicts'] = cursor.fetchone()[0]
        
        # Total sessions
        cursor.execute('SELECT COUNT(*) FROM sessions')
        stats['total_sessions'] = cursor.fetchone()[0]
        
        conn.close()
        return stats