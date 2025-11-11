# MBTI Personality Package - Quick Reference
# MBTI人格包 - 快速参考

## Import Examples
## 导入示例

```python
# Basic import (backward compatible)
from src.agents.core.mbti_personality import MBTIPersonalityAgent, MBTIType

# Create an agent
agent = MBTIPersonalityAgent(mbti_type=MBTIType.INTJ)

# Import specific components
from src.agents.core.mbti_personality import (
    MBTIType,
    CognitiveFunctionType,
    MBTIProfile,
    MBTIPersonalityFactory
)

# Create a profile directly
profile = MBTIPersonalityFactory.create_profile(MBTIType.ENFP)
```

## File Locations
## 文件位置

```
/Users/liyang/Desktop/testversion/BMAM/src/agents/core/mbti_personality/
├── Core Modules
│   ├── __init__.py                  (49 lines)
│   ├── types.py                     (59 lines)
│   ├── profile.py                   (64 lines)
│   └── factory.py                   (49 lines)
├── Profile Data
│   ├── profiles_nt.py              (116 lines) - INTJ, ENTP
│   ├── profiles_nf.py              (116 lines) - ENFP, INFJ
│   ├── profiles_sp.py               (63 lines) - ISTP
│   └── profiles_sj.py               (63 lines) - ESFJ
└── Mixins
    ├── core.py                     (121 lines)
    ├── system_prompt.py             (61 lines)
    ├── cognitive.py                (139 lines)
    ├── response.py                 (139 lines)
    ├── prompt_builder.py            (72 lines)
    ├── interaction.py              (114 lines)
    ├── analysis.py                  (91 lines)
    └── personality_management.py   (102 lines)
```

## Available MBTI Types
## 可用的MBTI类型

Currently Implemented (6):
- MBTIType.INTJ - The Architect (建筑师)
- MBTIType.ENTP - The Debater (辩论家)
- MBTIType.ENFP - The Campaigner (竞选者)
- MBTIType.INFJ - The Advocate (提倡者)
- MBTIType.ISTP - The Virtuoso (鉴赏家)
- MBTIType.ESFJ - The Consul (执政官)

All Defined (16):
- INTJ, INTP, ENTJ, ENTP (NT - Analysts)
- INFJ, INFP, ENFJ, ENFP (NF - Diplomats)
- ISTJ, ISFJ, ESTJ, ESFJ (SJ - Sentinels)
- ISTP, ISFP, ESTP, ESFP (SP - Explorers)

## Key Methods
## 关键方法

```python
# Initialize agent
agent = MBTIPersonalityAgent(
    mbti_type=MBTIType.INTJ,
    client=openai_client,
    llm_service=llm_service,
    persona_memory_agent=memory_agent,
    name="My Assistant"
)

# Generate response
response = await agent.process_message(AgentMessage(
    content={
        'action': 'generate_response',
        'user_input': 'Hello!',
        'context': {},
        'memories': []
    }
))

# Switch personality
result = await agent.process_message(AgentMessage(
    content={
        'action': 'switch_personality',
        'new_type': 'ENFP'
    }
))

# Get personality info
info = await agent.process_message(AgentMessage(
    content={'action': 'get_personality_info'}
))

# Analyze interactions
analysis = await agent.process_message(AgentMessage(
    content={'action': 'analyze_interaction'}
))

# Adjust communication style
adjusted = await agent.process_message(AgentMessage(
    content={
        'action': 'adjust_communication',
        'adjustments': {
            'directness': 0.8,
            'emotional_expression': 0.6
        }
    }
))
```

## Module Responsibilities
## 模块职责

| Module | Purpose | Key Classes/Functions |
|--------|---------|----------------------|
| types.py | Type definitions | MBTIType, CognitiveFunctionType |
| profile.py | Data structure | MBTIProfile |
| factory.py | Profile creation | MBTIPersonalityFactory |
| profiles_*.py | Profile data | Profile constants |
| core.py | Main agent | MBTIPersonalityCore |
| system_prompt.py | Prompt building | SystemPromptMixin |
| cognitive.py | Analysis | CognitiveFunctionMixin |
| response.py | Response gen | ResponseGenerationMixin |
| prompt_builder.py | Prompt construction | PromptBuilderMixin |
| interaction.py | Tracking | InteractionTrackingMixin |
| analysis.py | Pattern analysis | InteractionAnalysisMixin |
| personality_management.py | Switching | PersonalityManagementMixin |

## Testing
## 测试

```bash
# Test import
python3 -c "from src.agents.core.mbti_personality import MBTIPersonalityAgent, MBTIType; print('OK')"

# Check line counts
wc -l src/agents/core/mbti_personality/*.py

# Check for bare excepts
grep "except:" src/agents/core/mbti_personality/*.py

# List all files
ls -lh src/agents/core/mbti_personality/
```

## Adding New Personality Types
## 添加新的人格类型

1. Create profile constant in appropriate profiles_*.py file
2. Add to factory.py profiles dictionary
3. Test import and creation

Example:
```python
# In profiles_nt.py
INTP_PROFILE = MBTIProfile(
    mbti_type=MBTIType.INTP,
    title="The Thinker",
    # ... rest of profile
)

# In factory.py
profiles = {
    MBTIType.INTJ: INTJ_PROFILE,
    MBTIType.INTP: INTP_PROFILE,  # Add here
    # ... other profiles
}
```

## Documentation Files
## 文档文件

- MBTI_PERSONALITY_SPLIT_SUMMARY.md - Detailed summary
- MBTI_ARCHITECTURE_DIAGRAM.txt - Visual architecture
- MBTI_QUICK_REFERENCE.md - This file

Location: /Users/liyang/Desktop/testversion/BMAM/
