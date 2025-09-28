# Voice Anime UI Specification for BMAM

## Overview
A Grok-Ani style voice-driven user interface featuring a 2D anime character (Yaoguang/摇光明明) integrated with the BMAM memory management framework. The UI provides real-time voice interaction, memory visualization, and interactive control capabilities.

## Design Philosophy
- **Style**: Clean, playful, and reactive anime aesthetics
- **Interaction**: Natural voice-driven conversation with visual feedback
- **Transparency**: Real-time display of memory states and reasoning
- **Engagement**: Dynamic character animations synchronized with system state

## UI Layout Specification

### Screen Layout (Normalized Coordinates 0-1)

```
┌──────────────────────────────────────────────────────┐
│                                                       │
│     Character (35%, 50%)        Memory Panel         │
│         ╭─────╮                 ┌──────────┐         │
│         │ ^ ^ │                 │ Memory 1 │ 75%, 50%│
│         │  ◡  │                 │ Memory 2 │         │
│         ╰─────╯                 │ Memory 3 │         │
│      Chat Bubble                │ Memory 4 │         │
│     ╱           ╲               │ Memory 5 │         │
│    │  Speaking... │              └──────────┘         │
│     ╲           ╱                                     │
│                                                       │
│     ≈≈≈≈≈≈≈≈≈≈≈≈                                    │
│     Voice Waveform                                    │
│                                                       │
│    [🎤 Listen] [📝 Edit] [⚙️ Settings]               │
└──────────────────────────────────────────────────────┘
```

### Component Positioning

| Component | Position (X, Y) | Size (W, H) | Notes |
|-----------|----------------|-------------|--------|
| **Character** | (0.35, 0.5) | 40% height | Center-left, animated sprite |
| **Memory Panel** | (0.75, 0.5) | (0.35, 0.8) | Right side, semi-transparent |
| **Chat Bubble** | (0.35, 0.75) | 0.3 max width | Above character, auto-hide |
| **Voice Waveform** | (0.35, 0.15) | (0.3, 0.08) | Below character, 32 bars |
| **Control Panel** | (0.5, 0.95) | Full width, 0.08 height | Bottom center |

## Character Design

### Animation States
- **IDLE**: Natural breathing, occasional blinking
- **LISTENING**: Attentive pose, head slightly tilted
- **THINKING**: Eyes looking up, thoughtful expression
- **SPEAKING**: Mouth sync animation, expressive gestures
- **HAPPY**: Bright eyes, cheerful bounce
- **CONFUSED**: Head tilt, questioning expression
- **EXCITED**: Energetic movements, sparkle effects
- **CONCERNED**: Softer expression, gentle movements

### Expression System
- **Eye Animation**:
  - Blink cycle: 3-3.5 seconds
  - Emotional eye shapes
  - Dynamic pupil tracking

- **Mouth Sync**:
  - 8Hz modulation during speech
  - Amplitude-based openness
  - Emotion-modified shapes

- **Body Language**:
  - Subtle breathing: 0.5Hz sine wave
  - Head tracking: ±10° rotation
  - Arm gestures: Context-aware positioning

## Memory Visualization Panel

### Display Features
- **Maximum Visible**: 5 memories simultaneously
- **Scrollable**: Smooth scrolling for additional memories
- **Importance Indicator**: Color-coded bars
  - High (>0.7): Pink (#FF6B9D)
  - Medium (0.4-0.7): Yellow (#FFC93D)
  - Low (<0.4): Cyan (#00D9FF)

### Memory Card Structure
```
┌─────────────────────────┐
│ ▌ Importance: 85%       │
├─────────────────────────┤
│ Content text displayed  │
│ here with word wrap...  │
├─────────────────────────┤
│ Tags: emotion, context  │
└─────────────────────────┘
```

### Interactive Controls
- **Select**: Click to highlight memory
- **Edit**: Double-click to modify content
- **Importance Adjust**: Slider control
- **Save**: Auto-save with visual confirmation

## Voice Interface

### Audio Configuration
- **Sample Rate**: 16kHz
- **Channels**: Mono
- **Chunk Size**: 1024 bytes
- **Silence Threshold**: 500 RMS
- **End Detection**: 1.5s silence

### Voice Activity Visualization
- **Waveform Bars**: 32 vertical bars
- **Update Rate**: 30 FPS
- **Color Gradient**: Cyan to Purple
- **Amplitude Mapping**: Real-time audio levels

### Speech Processing
- **STT Language**: Chinese (zh-CN) primary, English secondary
- **TTS Voice**: Youthful, energetic female voice
- **Emotion Modulation**:
  - Normal: 1.0x speed
  - Excited: 1.2x speed
  - Concerned: 0.9x speed

## Color Palette

| Element | Color | Hex Code | Usage |
|---------|-------|----------|--------|
| **Primary** | Purple | #6B46C1 | Main accent, buttons |
| **Secondary** | Pink | #FF6B9D | Highlights, importance |
| **Accent** | Cyan | #00D9FF | Info, low importance |
| **Background** | Dark Blue | #1A1A2E | Main background |
| **Panel** | Semi-transparent | rgba(30,30,50,0.85) | Memory panel |
| **Text** | White | #FFFFFF | Primary text |

## Animation Specifications

### Timing Functions
- **Character Transitions**: 300ms ease
- **Panel Fade**: 2000ms ease-in-out
- **Bubble Appearance**: 3000ms fade
- **Waveform Smoothing**: 150ms linear

### Frame Rates
- **Character Animation**: 30 FPS
- **Waveform Update**: 30 FPS
- **Memory Panel Refresh**: 2 FPS
- **WebSocket Updates**: 30 Hz

## WebSocket Communication

### Message Types

#### Client → Server
```json
{
  "type": "start_listening" | "stop_listening" | "text_input",
  "text": "optional text content"
}
```

#### Server → Client
```json
{
  "type": "animation_update",
  "character": {
    "state": "idle",
    "emotion": "neutral",
    "eye_openness": 1.0,
    "mouth_openness": 0.0
  },
  "waveform": [0.1, 0.2, ...],
  "chat_bubble": {
    "visible": true,
    "text": "Response text",
    "alpha": 1.0
  }
}
```

## Control Commands

### Voice Commands
| Command | Trigger Phrase | Action |
|---------|---------------|--------|
| Edit Memory | "编辑记忆" | Open memory editor |
| Show Memory | "显示记忆" | Display memory panel |
| Clear Memory | "清除记忆" | Clear selected memory |
| Save State | "保存状态" | Save current session |
| Switch Mode | "切换模式" | Toggle UI mode |

## Performance Targets

- **Response Latency**: <500ms for voice detection
- **Processing Time**: <2s for BMAM response
- **Animation FPS**: Stable 30 FPS
- **Memory Usage**: <200MB client-side
- **WebSocket Latency**: <50ms local, <200ms remote

## Accessibility Features

- **Keyboard Navigation**: Tab through controls
- **Screen Reader**: ARIA labels for all elements
- **High Contrast Mode**: Alternative color scheme
- **Font Scaling**: Responsive text sizing
- **Voice Feedback**: Audio confirmations

## Implementation Files

1. **`voice_anime_ui.py`**: Core UI controller and animation system
2. **`voice_interface.py`**: Audio processing and speech engines
3. **`web_ui_server.py`**: WebSocket server and API endpoints
4. **`static/index.html`**: Web client interface

## Integration Points

### BMAM Coordinator
- Process user input through `coordinator.process_user_input()`
- Retrieve memories via `result.memories_retrieved`
- Access personality context from `PersonalityAgent`
- Monitor system status with `coordinator.get_system_status()`

### Memory System
- Display conditions from `MemoryCondition` dataclass
- Edit importance and content fields
- Trigger consolidation on changes
- Reflect updates in real-time

## Future Enhancements

1. **Multi-language Support**: Extend beyond Chinese/English
2. **Custom Character Skins**: User-selectable anime characters
3. **Advanced Animations**: Particle effects, transitions
4. **Mobile Responsive**: Touch-optimized interface
5. **Voice Cloning**: Personalized TTS voices
6. **Gesture Recognition**: Camera-based input
7. **Memory Graphs**: Visual relationship mapping
8. **Emotion Analytics**: Mood tracking dashboard