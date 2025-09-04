"""Ensure API keys are properly loaded"""
import os
from pathlib import Path

def ensure_openai_api():
    """Load OpenAI API key from .env file"""
    # Try multiple locations for .env file
    possible_paths = [
        Path('.env'),
        Path(__file__).parent.parent / '.env',
        Path.cwd() / '.env'
    ]
    
    for env_path in possible_paths:
        if env_path.exists():
            print(f"Loading environment from: {env_path}")
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key == 'OPENAI_API_KEY' and value and value != 'your-openai-key-here':
                            os.environ[key] = value
                            print(f"✅ Loaded OPENAI_API_KEY: {value[:10]}...{value[-4:]}")
                            return True
    
    # Check if already in environment
    existing_key = os.getenv('OPENAI_API_KEY')
    if existing_key and existing_key != 'your-openai-key-here':
        print(f"✅ OPENAI_API_KEY already in environment: {existing_key[:10]}...{existing_key[-4:]}")
        return True
    
    print("❌ No valid OPENAI_API_KEY found")
    return False

if __name__ == "__main__":
    ensure_openai_api()