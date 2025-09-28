# Live2D Integration Guide for BMAM Voice UI

## Overview
This guide explains how to integrate professional 2D anime character models (like Hatsune Miku) using Live2D Cubism SDK or similar technologies.

## Current Character vs Live2D Comparison

### Current CSS-Based Character ✅
- **Pros**:
  - Works immediately without additional dependencies
  - Lightweight and fast
  - Customizable expressions and animations
  - Cross-platform compatibility
- **Cons**:
  - Limited visual quality compared to professional models
  - Basic animation capabilities

### Live2D Integration 🚀
- **Pros**:
  - Professional-quality anime character models
  - Smooth, fluid animations
  - Realistic breathing, blinking, expressions
  - Industry-standard for VTuber applications
- **Cons**:
  - Requires Live2D Cubism SDK license
  - Additional dependencies and setup complexity
  - Model files can be large (50-200MB)

## Live2D Integration Options

### Option 1: Live2D Cubism SDK (Recommended)
```bash
# Install Live2D SDK for Web
npm install @live2d/cubismsdkforweb

# Or use CDN
<script src="https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js"></script>
```

### Option 2: PixiJS Live2D Plugin
```bash
npm install pixi-live2d-display
```

### Option 3: Kalidokit (Open Source Alternative)
```bash
npm install kalidokit
```

## Available Character Models

### Free/Open Source Models
1. **Hiyori Momose** (Sample model from Live2D)
   - File: `Hiyori/Hiyori.model3.json`
   - License: Free for personal use
   - Size: ~80MB

2. **Rice** (Community model)
   - Available on Booth.pm
   - License: Creative Commons

### Premium Models
1. **Hatsune Miku** (Official models)
   - Available through Crypton Future Media
   - License: Commercial license required

2. **Custom VTuber Models**
   - Commission from artists on Fiverr, Booth.pm
   - Price range: $200-2000

## Implementation Steps

### Step 1: Download Live2D Model
```bash
# Create models directory
mkdir -p src/ui/static/models/

# Download sample model (Hiyori)
# https://www.live2d.com/en/download/sample-data/
```

### Step 2: Update HTML Structure
```html
<div id="character-container">
    <canvas id="live2d-canvas" width="800" height="600"></canvas>
    <div class="character-overlay">
        <div class="emotion-particles"></div>
        <div class="character-nametag">摇光明明 (Yaoguang)</div>
    </div>
</div>
```

### Step 3: Live2D Controller
```javascript
class Live2DCharacterController {
    constructor() {
        this.app = null;
        this.model = null;
        this.currentExpression = 'neutral';
        this.currentMotion = 'idle';
    }

    async init() {
        // Initialize PIXI application
        this.app = new PIXI.Application({
            view: document.getElementById('live2d-canvas'),
            autoStart: true,
            resizeTo: window
        });

        // Load Live2D model
        this.model = await PIXI.live2d.Live2DModel.from('/static/models/hiyori/hiyori.model3.json');

        // Add to stage
        this.app.stage.addChild(this.model);

        // Set up interactions
        this.setupInteractions();
    }

    setExpression(emotion) {
        const expressionMap = {
            'joy': 'f02',
            'surprise': 'f03',
            'thinking': 'f01',
            'concern': 'f04',
            'neutral': 'f01'
        };

        const expression = expressionMap[emotion] || 'f01';
        this.model.expression(expression);
    }

    setMotion(state) {
        const motionMap = {
            'idle': 'idle_00',
            'listening': 'tap_body',
            'speaking': 'pinch_in',
            'thinking': 'shake',
            'happy': 'flick_head'
        };

        const motion = motionMap[state] || 'idle_00';
        this.model.motion(motion);
    }

    startSpeaking() {
        // Enable lip sync
        this.model.internalModel.motionManager.startRandomMotion('TapBody', 3);
    }

    stopSpeaking() {
        this.model.internalModel.motionManager.stopAllMotions();
    }
}
```

### Step 4: Integration with BMAM
```javascript
// Update character animation function
function updateCharacter(character) {
    if (live2dController) {
        live2dController.setExpression(character.emotion);
        live2dController.setMotion(character.state);

        if (character.state === 'speaking') {
            live2dController.startSpeaking();
        } else {
            live2dController.stopSpeaking();
        }
    }
}
```

## Model Configuration

### Model Directory Structure
```
src/ui/static/models/
├── hiyori/
│   ├── hiyori.model3.json
│   ├── hiyori.moc3
│   ├── textures/
│   │   ├── texture_00.png
│   │   └── texture_01.png
│   ├── motions/
│   │   ├── idle_00.motion3.json
│   │   ├── tap_body.motion3.json
│   │   └── ...
│   └── expressions/
│       ├── f01.exp3.json
│       ├── f02.exp3.json
│       └── ...
```

### Model Parameters
```json
{
    "name": "Yaoguang",
    "model": "hiyori.model3.json",
    "expressions": {
        "neutral": "f01",
        "happy": "f02",
        "surprised": "f03",
        "concerned": "f04"
    },
    "motions": {
        "idle": ["idle_00", "idle_01"],
        "listening": ["tap_body"],
        "speaking": ["pinch_in", "pinch_out"],
        "thinking": ["shake"]
    },
    "physics": {
        "hair": true,
        "clothing": true
    }
}
```

## Voice Sync Features

### Lip Sync Implementation
```javascript
class LipSyncController {
    constructor(live2dModel) {
        this.model = live2dModel;
        this.audioContext = new AudioContext();
        this.analyzer = this.audioContext.createAnalyser();
    }

    startLipSync(audioStream) {
        const source = this.audioContext.createMediaStreamSource(audioStream);
        source.connect(this.analyzer);

        const updateLipSync = () => {
            const dataArray = new Uint8Array(this.analyzer.frequencyBinCount);
            this.analyzer.getByteFrequencyData(dataArray);

            // Calculate mouth openness based on audio amplitude
            const amplitude = dataArray.reduce((sum, value) => sum + value) / dataArray.length;
            const mouthOpenness = Math.min(amplitude / 50, 1.0);

            // Update model mouth parameter
            this.model.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', mouthOpenness);

            requestAnimationFrame(updateLipSync);
        };

        updateLipSync();
    }
}
```

## Memory Visualization Enhancement

### Interactive Memory Bubbles
```javascript
class Live2DMemoryVisualization {
    constructor(live2dController) {
        this.character = live2dController;
        this.memoryBubbles = [];
    }

    showMemoryReaction(memories) {
        // Character reacts based on memory importance
        const avgImportance = memories.reduce((sum, mem) => sum + mem.importance, 0) / memories.length;

        if (avgImportance > 0.8) {
            this.character.setExpression('surprise');
            this.character.setMotion('flick_head');
        } else if (avgImportance > 0.5) {
            this.character.setExpression('joy');
        } else {
            this.character.setExpression('thinking');
        }

        // Create floating memory bubbles around character
        this.createMemoryBubbles(memories);
    }

    createMemoryBubbles(memories) {
        memories.forEach((memory, index) => {
            const bubble = new MemoryBubble(memory, index);
            this.memoryBubbles.push(bubble);
        });
    }
}
```

## Performance Considerations

### Optimization Settings
```javascript
const live2dConfig = {
    // Model quality settings
    quality: 'high', // 'low', 'medium', 'high'

    // Performance settings
    fps: 60,
    enablePhysics: true,
    enableBreathing: true,

    // Memory management
    textureSize: 1024, // Reduce for lower-end devices
    modelCache: true
};
```

## Installation Command

For quick Live2D integration:

```bash
# Create Live2D version
mkdir -p src/ui/static/js/live2d
cd src/ui/static/js/live2d

# Download Live2D Cubism Core
wget https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js

# Install PIXI Live2D plugin
npm install pixi-live2d-display

# Download sample model
wget https://www.live2d.com/en/download/sample-data/
```

## Next Steps

1. **Choose Model**: Select Hiyori (free) or Miku (licensed)
2. **Update Dependencies**: Add Live2D SDK to requirements
3. **Implement Controller**: Replace CSS character with Live2D
4. **Test Integration**: Verify animations work with BMAM
5. **Optimize Performance**: Adjust settings for smooth operation

The current CSS-based character provides immediate functionality, while Live2D integration offers professional-grade anime character experience for production deployments.