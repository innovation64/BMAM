# MBTI Personality System Documentation

## Overview
The MBTI (Myers-Briggs Type Indicator) Personality System provides an advanced personality framework based on the 16 MBTI personality types. This system allows users to interact with AI agents that exhibit distinct personality characteristics, communication styles, and behavioral patterns based on psychological type theory.

## Features

### 🎭 16 MBTI Personality Types
- **Analysts (NT)**: INTJ, INTP, ENTJ, ENTP
- **Diplomats (NF)**: INFJ, INFP, ENFJ, ENFP
- **Sentinels (SJ)**: ISTJ, ISFJ, ESTJ, ESFJ
- **Explorers (SP)**: ISTP, ISFP, ESTP, ESFP

### 🧠 Cognitive Function Implementation
Each personality type is implemented with its authentic cognitive function stack:
- **Dominant Function**: Primary way of processing information
- **Auxiliary Function**: Supporting and balancing function
- **Tertiary Function**: Developing function that adds complexity
- **Inferior Function**: Least developed, emerges under stress

### 🔄 Dynamic Personality Switching
- Switch between any of the 16 personality types in real-time
- Maintain conversation continuity across personality switches
- Track personality usage statistics and preferences

### ⚙️ Advanced Configuration
- Adjust communication style parameters (formality, directness, emotion)
- Override specific personality traits
- Set adaptive vs. fixed personality modes
- Configure automatic personality recommendations

## Architecture

```
MBTIPersonalitySystem/
├── Core Components
│   ├── MBTIPersonalityAgent          # Individual personality implementation
│   ├── MBTIPersonalityFactory        # Creates personality profiles
│   ├── MBTIConfigurationManager      # Manages settings and persistence
│   └── MBTIIntegratedPersonalityAgent # Main integration layer
├── Configuration
│   ├── PersonalityProfile            # MBTI type definitions
│   ├── CognitiveFunctionType         # Function type definitions
│   └── MBTIConfiguration            # System configuration
└── Integration
    ├── Personality switching
    ├── Memory integration
    └── Session management
```

## Usage

### Basic Setup

```python
from agents.core.mbti_integration import create_mbti_personality_system

# Create MBTI personality system
system = create_mbti_personality_system(
    initial_personality="INTJ",
    name="My AI Assistant"
)

# Switch personality
await system.process_message(AgentMessage(
    content={
        'action': 'mbti_switch_personality',
        'personality_type': 'ENFP'
    }
))

# Generate personality-specific response
response = await system.process_message(AgentMessage(
    content={
        'action': 'generate_personality_response',
        'user_input': 'How should I approach this problem?'
    }
))
```

### Available Actions

#### Personality Management
- `mbti_switch_personality`: Switch to a different personality type
- `mbti_get_info`: Get comprehensive system information
- `mbti_get_menu`: Get interactive personality selection menu

#### Analysis and Comparison
- `mbti_compare_types`: Compare two personality types
- `mbti_recommend`: Get personality recommendations based on input
- `mbti_get_stats`: View session statistics and usage patterns

#### Configuration
- `mbti_configure`: Update system settings
- `mbti_reset`: Reset system to defaults

### Personality Examples

#### INTJ - The Architect
```
Characteristics:
- Strategic and analytical thinking
- Direct, efficient communication
- Focus on long-term planning
- Independent problem-solving approach

Communication Style:
- High directness (90%)
- Logic-focused (95%)
- Minimal emotional expression (30%)
- Big-picture oriented (95%)
```

#### ENFP - The Campaigner
```
Characteristics:
- Enthusiastic and creative
- Warm, expressive communication
- Focus on possibilities and people
- Flexible, spontaneous approach

Communication Style:
- Moderate directness (60%)
- Balanced logic/emotion (40%/90%)
- High emotional expression (90%)
- Big-picture oriented (85%)
```

## Configuration Options

### Personality Settings
```python
{
    "current_personality": "INTJ",
    "personality_mode": "fixed",  # fixed, adaptive, contextual, user_choice
    "allow_personality_switching": True,
    "remember_personality_choice": True,
    "auto_detect_preference": False
}
```

### Communication Adjustments
```python
{
    "formality_adjustment": 0.0,      # -1.0 to +1.0
    "directness_adjustment": 0.0,     # -1.0 to +1.0
    "emotion_expression_adjustment": 0.0  # -1.0 to +1.0
}
```

### Advanced Settings
```python
{
    "personality_adaptation_threshold": 10,
    "consistency_enforcement": 0.8,
    "cognitive_function_emphasis": {
        "dominant": 0.4,
        "auxiliary": 0.3,
        "tertiary": 0.2,
        "inferior": 0.1
    }
}
```

## Personality Type Details

### Analysts (NT) - Rational Types

**INTJ - The Architect**
- Dominant: Ni (Introverted Intuition)
- Auxiliary: Te (Extraverted Thinking)
- Communication: Strategic, direct, long-term focused
- Strengths: Strategic thinking, independence, determination

**INTP - The Thinker**
- Dominant: Ti (Introverted Thinking)
- Auxiliary: Ne (Extraverted Intuition)
- Communication: Analytical, precise, concept-focused
- Strengths: Logical analysis, theoretical thinking, objectivity

**ENTJ - The Commander**
- Dominant: Te (Extraverted Thinking)
- Auxiliary: Ni (Introverted Intuition)
- Communication: Direct, organized, goal-oriented
- Strengths: Leadership, organization, efficiency

**ENTP - The Debater**
- Dominant: Ne (Extraverted Intuition)
- Auxiliary: Ti (Introverted Thinking)
- Communication: Innovative, challenging, idea-focused
- Strengths: Innovation, quick thinking, debate skills

### Diplomats (NF) - Idealist Types

**INFJ - The Advocate**
- Dominant: Ni (Introverted Intuition)
- Auxiliary: Fe (Extraverted Feeling)
- Communication: Insightful, empathetic, meaning-focused
- Strengths: Insight, empathy, vision

**INFP - The Mediator**
- Dominant: Fi (Introverted Feeling)
- Auxiliary: Ne (Extraverted Intuition)
- Communication: Authentic, value-driven, personal
- Strengths: Authenticity, idealism, individual focus

**ENFJ - The Protagonist**
- Dominant: Fe (Extraverted Feeling)
- Auxiliary: Ni (Introverted Intuition)
- Communication: Inspiring, supportive, people-focused
- Strengths: Leadership, empathy, communication

**ENFP - The Campaigner**
- Dominant: Ne (Extraverted Intuition)
- Auxiliary: Fi (Introverted Feeling)
- Communication: Enthusiastic, creative, possibility-focused
- Strengths: Enthusiasm, creativity, inspiration

### Sentinels (SJ) - Guardian Types

**ISTJ - The Logistician**
- Dominant: Si (Introverted Sensing)
- Auxiliary: Te (Extraverted Thinking)
- Communication: Methodical, detailed, fact-based
- Strengths: Reliability, organization, tradition

**ISFJ - The Defender**
- Dominant: Si (Introverted Sensing)
- Auxiliary: Fe (Extraverted Feeling)
- Communication: Supportive, detailed, service-oriented
- Strengths: Supportiveness, reliability, care

**ESTJ - The Executive**
- Dominant: Te (Extraverted Thinking)
- Auxiliary: Si (Introverted Sensing)
- Communication: Direct, organized, results-oriented
- Strengths: Organization, leadership, efficiency

**ESFJ - The Consul**
- Dominant: Fe (Extraverted Feeling)
- Auxiliary: Si (Introverted Sensing)
- Communication: Warm, supportive, harmony-focused
- Strengths: Supportiveness, organization, harmony

### Explorers (SP) - Artisan Types

**ISTP - The Virtuoso**
- Dominant: Ti (Introverted Thinking)
- Auxiliary: Se (Extraverted Sensing)
- Communication: Practical, direct, action-focused
- Strengths: Practicality, adaptability, problem-solving

**ISFP - The Adventurer**
- Dominant: Fi (Introverted Feeling)
- Auxiliary: Se (Extraverted Sensing)
- Communication: Gentle, authentic, present-focused
- Strengths: Authenticity, flexibility, aesthetics

**ESTP - The Entrepreneur**
- Dominant: Se (Extraverted Sensing)
- Auxiliary: Ti (Introverted Thinking)
- Communication: Energetic, direct, immediate-focused
- Strengths: Adaptability, practicality, energy

**ESFP - The Entertainer**
- Dominant: Se (Extraverted Sensing)
- Auxiliary: Fi (Introverted Feeling)
- Communication: Warm, spontaneous, people-focused
- Strengths: Enthusiasm, spontaneity, people skills

## Integration with Existing Systems

### Memory Integration
The MBTI system integrates with persona memory to:
- Store personality preferences and choices
- Track personality-specific interactions
- Maintain consistency across sessions

### LLM Service Integration
- Uses existing LLM service interface
- Maintains compatibility with different LLM providers
- Provides fallback mechanisms

### Configuration Persistence
- JSON-based configuration storage
- Session-aware settings management
- Cross-session learning capabilities

## Best Practices

### Personality Selection
1. Consider user interaction style and preferences
2. Use personality recommendations for new users
3. Allow users to experiment with different types
4. Track usage patterns for optimization

### Configuration Management
1. Start with default settings
2. Adjust based on user feedback
3. Maintain personality authenticity
4. Monitor consistency scores

### System Integration
1. Initialize system early in application startup
2. Handle graceful degradation to fallback systems
3. Monitor system health and performance
4. Provide clear user feedback on personality switches

## Troubleshooting

### Common Issues

**Personality switching fails**
- Check if personality type is valid (16 valid types)
- Verify configuration allows switching
- Ensure system is properly initialized

**Inconsistent personality behavior**
- Check consistency enforcement settings
- Review custom trait overrides
- Monitor cognitive function usage

**Configuration not persisting**
- Verify config file path permissions
- Check JSON format validity
- Ensure proper file system access

### System Health Monitoring
```python
# Check system health
health = system.get_system_health()
print(f"Status: {health['overall_status']}")
print(f"Errors: {health['errors']}")
```

## Advanced Usage

### Custom Personality Profiles
While the system provides 16 standard MBTI types, advanced users can:
- Modify trait distributions
- Adjust communication style parameters
- Create custom cognitive function emphasis
- Override specific behavioral patterns

### Adaptive Personality Systems
Configure the system for automatic adaptation:
- Enable auto-detection of user preferences
- Set adaptation thresholds
- Configure contextual switching
- Implement learning-based adjustments

### Multi-User Support
For multi-user scenarios:
- Maintain separate configuration files
- Track per-user personality preferences
- Implement user-specific memory isolation
- Provide user-specific personality recommendations

## Future Enhancements

- Additional personality frameworks (Big Five, Enneagram)
- Machine learning-based personality detection
- Voice and speech pattern analysis
- Cross-cultural personality adaptations
- Advanced cognitive function modeling

---

For more information and examples, see the demo script at `examples/mbti_personality_demo.py`.