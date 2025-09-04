"""
Data Loader for MA-CMM Framework

This module handles loading different dataset formats for experiments.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional


class DataLoader:
    """Data loader for MA-CMM experiments"""
    
    def __init__(self):
        """Initialize data loader"""
        self.logger = logging.getLogger(__name__)
    
    def load_continuing_dialogue(self, dataset_path: str, max_samples: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load continuing dialogue dataset
        
        Args:
            dataset_path: Path to dataset directory
            max_samples: Maximum number of samples to load
            
        Returns:
            List of loaded samples
        """
        
        dataset_path = Path(dataset_path)
        
        if not dataset_path.exists():
            self.logger.error(f"Dataset path does not exist: {dataset_path}")
            return []
        
        samples = []
        
        try:
            # Get all files in the directory
            files = list(dataset_path.glob("*"))
            
            # Filter for data files (.txt, .json)
            data_files = [f for f in files if f.suffix in ['.txt', '.json']]
            
            if not data_files:
                self.logger.warning(f"No data files found in {dataset_path}")
                return []
            
            # Sort files for consistent ordering
            data_files.sort()
            
            # Load samples from files
            for file_path in data_files:
                try:
                    sample = self._load_single_file(file_path)
                    if sample:
                        samples.append(sample)
                        
                        # Check max samples limit
                        if max_samples and len(samples) >= max_samples:
                            break
                            
                except Exception as e:
                    self.logger.error(f"Error loading file {file_path}: {str(e)}")
                    continue
            
            self.logger.info(f"Loaded {len(samples)} samples from {dataset_path}")
            return samples
            
        except Exception as e:
            self.logger.error(f"Error loading dataset {dataset_path}: {str(e)}")
            return []
    
    def _load_single_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load a single data file
        
        Args:
            file_path: Path to the file
            
        Returns:
            Loaded sample or None if failed
        """
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                return None
            
            # Try to parse as JSON first
            try:
                data = json.loads(content)
                
                # Add file metadata
                data['_file_path'] = str(file_path)
                data['_file_name'] = file_path.name
                
                return self._normalize_sample_format(data)
                
            except json.JSONDecodeError:
                # Try to parse as multi-session JSON (multiple JSON arrays/objects per line)
                try:
                    sessions = []
                    for line in content.split('\n'):
                        line = line.strip()
                        if line:
                            sessions.append(json.loads(line))
                    
                    if sessions:
                        # For multi-session files, use the last session
                        data = {'dialogue_sessions': sessions}
                        data['_file_path'] = str(file_path)
                        data['_file_name'] = file_path.name
                        return self._normalize_sample_format(data)
                except:
                    pass
                
                # If not JSON, treat as plain text
                return self._parse_text_format(content, file_path)
                
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {str(e)}")
            return None
    
    def _normalize_sample_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize sample format to consistent structure
        
        Args:
            data: Raw sample data
            
        Returns:
            Normalized sample
        """
        
        normalized = {
            'id': data.get('id', data.get('_file_name', 'unknown')),
            'history': [],
            'query': '',
            'reference': '',
            'conditions': [],
            'metadata': {}
        }
        
        # Handle different dataset formats
        
        # Format 1: Continuing Previous Dialogue
        if 'previous_dialogue' in data:
            normalized['history'] = data.get('previous_dialogue', [])
            test_turn = data.get('test_turn', {})
            normalized['query'] = test_turn.get('user', '')
            normalized['reference'] = test_turn.get('reference', '')
        
        # Format 2: Learning from Human Feedback
        elif 'background_dialogue' in data:
            normalized['history'] = data.get('background_dialogue', [])
            normalized['query'] = data.get('test_query', '')
            normalized['reference'] = data.get('reference_response', '')
            
            # Extract key condition if available
            if 'key_condition' in data:
                normalized['conditions'] = [{
                    'type': data.get('condition_type', 'unknown'),
                    'description': data['key_condition'],
                    'importance': 'high'
                }]
        
        # Format 3: Learning New Knowledge
        elif 'dialogue_sessions' in data:
            # Flatten dialogue sessions into history
            history = []
            for session in data.get('dialogue_sessions', []):
                history.extend(session.get('turns', []))
            normalized['history'] = history
            
            # Use first test question if available
            test_questions = data.get('test_questions', [])
            if test_questions:
                first_question = test_questions[0]
                normalized['query'] = first_question.get('question', '')
                normalized['reference'] = first_question.get('answer', '')
        
        # Format 4: Generic format
        else:
            normalized['history'] = data.get('history', data.get('dialogue_history', []))
            normalized['query'] = data.get('query', data.get('current_query', ''))
            normalized['reference'] = data.get('reference', data.get('reference_response', ''))
            normalized['conditions'] = data.get('conditions', [])
        
        # Store original data in metadata
        normalized['metadata'] = {
            'original_format': 'json',
            'source_keys': list(data.keys()),
            'file_path': data.get('_file_path', ''),
            'file_name': data.get('_file_name', '')
        }
        
        return normalized
    
    def _parse_text_format(self, content: str, file_path: Path) -> Dict[str, Any]:
        """
        Parse plain text format (fallback)
        
        Args:
            content: File content
            file_path: File path
            
        Returns:
            Parsed sample
        """
        
        # Simple text format parsing
        lines = content.split('\n')
        
        sample = {
            'id': file_path.stem,
            'history': [],
            'query': '',
            'reference': '',
            'conditions': [],
            'metadata': {
                'original_format': 'text',
                'file_path': str(file_path),
                'file_name': file_path.name,
                'line_count': len(lines)
            }
        }
        
        # Try to extract query from content
        if lines:
            # Use the first non-empty line as query
            for line in lines:
                line = line.strip()
                if line:
                    sample['query'] = line
                    break
        
        # If content looks like dialogue, try to parse it
        if 'user:' in content.lower() or 'assistant:' in content.lower():
            sample['history'] = self._parse_dialogue_text(content)
        
        return sample
    
    def _parse_dialogue_text(self, content: str) -> List[Dict[str, str]]:
        """
        Parse dialogue from text format
        
        Args:
            content: Text content
            
        Returns:
            List of dialogue turns
        """
        
        dialogue = []
        lines = content.split('\n')
        
        current_role = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for role indicators
            if line.lower().startswith('user:'):
                # Save previous turn
                if current_role and current_content:
                    dialogue.append({
                        'role': current_role,
                        'content': ' '.join(current_content)
                    })
                
                # Start new turn
                current_role = 'user'
                current_content = [line[5:].strip()]  # Remove 'user:' prefix
                
            elif line.lower().startswith('assistant:'):
                # Save previous turn
                if current_role and current_content:
                    dialogue.append({
                        'role': current_role,
                        'content': ' '.join(current_content)
                    })
                
                # Start new turn
                current_role = 'assistant'
                current_content = [line[10:].strip()]  # Remove 'assistant:' prefix
                
            else:
                # Continue current turn
                if current_content:
                    current_content.append(line)
        
        # Save final turn
        if current_role and current_content:
            dialogue.append({
                'role': current_role,
                'content': ' '.join(current_content)
            })
        
        return dialogue
    
    def load_sample_datasets(self, base_path: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load all available datasets
        
        Args:
            base_path: Base directory containing datasets
            
        Returns:
            Dictionary of dataset_name -> samples
        """
        
        if base_path is None:
            # Use parent directory of project root
            base_path = Path(__file__).parent.parent.parent
        else:
            base_path = Path(base_path)
        datasets = {}
        
        # Standard dataset directories
        dataset_dirs = [
            "continuing_previous_dialogue",
            "learning_from_human_feedback", 
            "learning_new_knowledge"
        ]
        
        for dataset_name in dataset_dirs:
            dataset_path = base_path / dataset_name
            if dataset_path.exists():
                samples = self.load_continuing_dialogue(str(dataset_path), max_samples=5)  # Limit for testing
                if samples:
                    datasets[dataset_name] = samples
                    self.logger.info(f"Loaded {len(samples)} samples from {dataset_name}")
        
        return datasets
    
    def get_sample_info(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary information about a sample
        
        Args:
            sample: Sample data
            
        Returns:
            Sample information
        """
        
        return {
            'id': sample.get('id', 'unknown'),
            'history_turns': len(sample.get('history', [])),
            'query_length': len(sample.get('query', '')),
            'reference_length': len(sample.get('reference', '')),
            'conditions_count': len(sample.get('conditions', [])),
            'format': sample.get('metadata', {}).get('original_format', 'unknown')
        }


def main():
    """Test data loader"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    loader = DataLoader()
    
    print("🔍 Testing Data Loader")
    print("=" * 30)
    
    # Test loading datasets
    datasets = loader.load_sample_datasets()
    
    for dataset_name, samples in datasets.items():
        print(f"\n📊 Dataset: {dataset_name}")
        print(f"   Samples: {len(samples)}")
        
        if samples:
            # Show first sample info
            sample_info = loader.get_sample_info(samples[0])
            print(f"   Sample info: {sample_info}")
            
            # Show sample content preview
            sample = samples[0]
            print(f"   Query: {sample.get('query', 'No query')[:60]}...")
            print(f"   History turns: {len(sample.get('history', []))}")


if __name__ == "__main__":
    main()