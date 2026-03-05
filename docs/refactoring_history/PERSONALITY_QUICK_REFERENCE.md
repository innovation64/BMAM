# Personality Module Quick Reference

## 🚀 Quick Start

### Import Everything
```python
from src.agents.core.personality import (
    EmotionDetector, EmotionManager,
    TraitManager, PersonalityContextBuilder,
    StyleGenerator, ResponseProcessor,
    LearningEngine, PreferenceTracker,
    PersonalityProfile, EmotionalState
)
```

---

## 📦 Module Cheatsheet

### 1. Emotion Detection
```python
detector = EmotionDetector()
context = detector.detect_emotional_context("我很开心！")
# → {'main_emotion': 'positive', 'intensity': 0.8}
```

### 2. Emotion Management
```python
manager = EmotionManager()
manager.adjust_emotional_state(context)
style = manager.get_emotion_style_adjustments()
# → {'tone': '轻松愉快', 'expressions': [...], ...}
```

### 3. Trait Management
```python
profile = PersonalityProfile()
trait_mgr = TraitManager(profile)
summary = trait_mgr.get_personality_summary()
# → "摇光明明 - 平静(0.5) | 主要特质: ..."
```

### 4. Context Building
```python
builder = PersonalityContextBuilder()
context = builder.build_personality_context(
    user_input="你好",
    memories=[], persona_memories=[],
    profile=profile, current_emotion="平静",
    emotion_intensity=0.5, style_adjustments={},
    learned_preferences={}
)
```

### 5. Response Processing
```python
processor = ResponseProcessor()
final = processor.post_process_response(
    "作为AI，我很高兴", {}, ""
)
# → "，我很高兴" (AI removed)
```

### 6. Preference Tracking
```python
tracker = PreferenceTracker()
tracker.update_style_preferences(persona_memories, memories)
prefs = tracker.get_style_preferences_dict()
# → {'formality': 0.4, 'emoji': False, ...}
```

### 7. Learning
```python
engine = LearningEngine()
prefs = engine.extract_preferences("我喜欢喝咖啡")
# → {'喜欢': '喝咖啡'}
```

---

## 🔄 Complete Workflow

```python
# 1. Detect emotion
emotion_ctx = detector.detect_emotional_context(user_input)

# 2. Adjust AI emotion
manager.adjust_emotional_state(emotion_ctx)

# 3. Build context
personality_ctx = builder.build_personality_context(
    user_input, memories, persona_memories, profile,
    manager.current_emotion.value, manager.emotion_intensity,
    manager.get_emotion_style_adjustments(),
    engine.get_learned_preferences()
)

# 4. Generate response
response = await generator.generate_natural_response(
    user_input, personality_ctx, emotion_ctx
)

# 5. Post-process
final = processor.post_process_response(response, personality_ctx)

# 6. Track
tracker.record_interaction(user_input, final, emotion_ctx)

# 7. Learn
await engine.learn_from_interaction(user_input, final)
```

---

## 📊 File Locations

```
personality/
├── models.py                         # Data models
├── emotion/
│   ├── emotion_detector.py          # Emotion detection
│   └── emotion_manager.py           # Emotion state
├── traits/
│   ├── trait_manager.py             # Trait management
│   └── personality_builder.py       # Context building
├── style/
│   ├── style_generator.py           # Response generation
│   └── response_processor.py        # Post-processing
└── adaptation/
    ├── learning_engine.py           # Learning
    └── preference_tracker.py        # Preference tracking
```

---

## 🎯 Common Tasks

### Update Personality
```python
trait_mgr.update_personality({
    'traits': {'温暖': 0.95},
    'current_emotion': '愉快'
})
```

### Get Emotion History
```python
history = manager.get_recent_emotions(count=5)
```

### Manual Style Preferences
```python
tracker.set_formality(0.7)  # More formal
tracker.set_emoji(True)
tracker.set_brevity('concise')
```

### Extract User Preferences
```python
prefs = engine.extract_preferences("我喜欢早上喝绿茶")
# → {'喜欢': '早上喝绿茶', '时间偏好': '早上'}
```

---

## 🐛 Troubleshooting

### Import Error
```python
# Make sure you're in the right directory
import sys
sys.path.append('/path/to/BMAM')
```

### Missing LLM Service
```python
# StyleGenerator requires llm_service
from src.agents.core.llm_service import create_llm_service
llm_service = create_llm_service(agent)
generator = StyleGenerator(llm_service)
```

---

## 📚 Documentation

- [Complete Report](./PERSONALITY_REFACTORING_COMPLETE.md)
- [Architecture](./PERSONALITY_MODULE_ARCHITECTURE.md)
- [File Manifest](./PERSONALITY_FILES_MANIFEST.md)
- [Implementation Summary](./PERSONALITY_IMPLEMENTATION_SUMMARY.md)

---

**Version**: v2.0.0  
**Last Updated**: 2025-11-10
