/**
 * Live2D Character Viewer using GitHub repo's live2dv3.js
 * Compatible with BMAM Voice UI
 */

class Live2DViewerV3 {
    constructor(canvasId, modelName = 'ANIYA') {
        this.canvasId = canvasId;
        this.canvas = document.getElementById(canvasId);
        this.modelName = modelName;
        this.viewer = null;
        this.isLoaded = false;
        this.currentExpression = 'neutral';
        this.currentMotion = 'idle';
    }

    async init() {
        try {
            console.log('Initializing Live2D viewer with model:', this.modelName);

            // Check if L2dViewer is available
            if (typeof L2dViewer === 'undefined') {
                throw new Error('L2dViewer not loaded from live2dv3.js');
            }

            // Initialize L2dViewer
            this.viewer = new L2dViewer({
                el: this.canvas,
                modelHomePath: '/static/models/',
                model: 'aniya/ANIYA',  // Use our ANIYA model
                autoMotion: true,
                _finishedLoadModel: () => {
                    console.log('Live2D model loaded successfully');
                    this.adjustModelScale();
                    this.isLoaded = true;
                    this.setupEventHandlers();
                    this.hideCharacterFallback();
                }
            });

            // Wait for model to load
            await this.waitForModelLoad();

            console.log('Live2D viewer initialized successfully');

        } catch (error) {
            console.error('Failed to initialize Live2D viewer:', error);
            this.showCharacterFallback();
            throw error;
        }
    }

    async waitForModelLoad() {
        return new Promise((resolve, reject) => {
            let attempts = 0;
            const maxAttempts = 100; // 10 seconds timeout

            const checkLoaded = () => {
                attempts++;
                if (this.isLoaded) {
                    resolve();
                } else if (attempts >= maxAttempts) {
                    reject(new Error('Timeout waiting for model to load'));
                } else {
                    setTimeout(checkLoaded, 100);
                }
            };

            checkLoaded();
        });
    }

    adjustModelScale() {
        if (!this.viewer) return;

        try {
            // Get the model and canvas dimensions
            const canvas = this.canvas;
            const canvasWidth = canvas.width || 800;
            const canvasHeight = canvas.height || 600;

            console.log('Canvas dimensions:', canvasWidth, 'x', canvasHeight);

            // Scale the model to fit properly in the canvas
            // ANIYA models are typically quite large, so we need significant scaling down
            const scale = Math.min(canvasWidth / 2000, canvasHeight / 2000); // Adjust divider as needed
            const adjustedScale = Math.max(0.15, Math.min(0.4, scale)); // Clamp between 0.15 and 0.4

            console.log('Calculated scale:', adjustedScale);

            // Apply scaling and positioning
            if (this.viewer.app && this.viewer.app.stage && this.viewer.app.stage.children.length > 0) {
                const model = this.viewer.app.stage.children[0];

                if (model) {
                    // Scale the model
                    model.scale.set(adjustedScale);

                    // Center the model
                    model.x = canvasWidth / 2;
                    model.y = canvasHeight * 0.85; // Position slightly towards bottom

                    console.log('Model scaled and positioned:', {
                        scale: adjustedScale,
                        x: model.x,
                        y: model.y
                    });
                }
            } else {
                // Fallback: try to access model through viewer properties
                console.log('Trying alternative model access...');
                // We might need to implement this based on live2dv3.js internal structure
            }

        } catch (error) {
            console.error('Failed to adjust model scale:', error);
        }
    }

    setupEventHandlers() {
        if (!this.canvas) return;

        this.canvas.addEventListener('click', (event) => {
            this.onModelTouch(event);
        });
    }

    onModelTouch(event) {
        console.log('Model touched');
        this.setExpression('joy');
        this.playRandomMotion();

        // Reset after delay
        setTimeout(() => {
            this.setExpression('neutral');
        }, 2000);
    }

    setExpression(emotion) {
        if (!this.isLoaded || !this.viewer) return;

        this.currentExpression = emotion;

        // Live2DV3 API doesn't have direct expression control
        // Instead, we can trigger motions that represent emotions
        const emotionMotions = {
            'neutral': 'Idle',
            'joy': 'TapBody',
            'surprise': 'TapHead',
            'thinking': 'Idle',
            'concern': 'Idle'
        };

        const motionName = emotionMotions[emotion] || 'Idle';
        console.log('Setting emotion:', emotion, 'with motion:', motionName);
    }

    playMotion(motionName) {
        if (!this.isLoaded || !this.viewer) return;

        try {
            // Get available motions
            const motions = this.viewer.getMotions();

            // Find motion by name (case insensitive)
            for (let [key, value] of motions) {
                if (key.toLowerCase().includes(motionName.toLowerCase())) {
                    this.viewer.startMotion(key);
                    console.log('Playing motion:', key);
                    return;
                }
            }

            console.log('Motion not found:', motionName);
        } catch (error) {
            console.log('Motion play failed:', error);
        }
    }

    playRandomMotion() {
        if (!this.isLoaded || !this.viewer) return;

        try {
            const motions = this.viewer.getMotions();
            const motionKeys = Array.from(motions.keys());

            if (motionKeys.length > 0) {
                const randomKey = motionKeys[Math.floor(Math.random() * motionKeys.length)];
                this.viewer.startMotion(randomKey);
                console.log('Playing random motion:', randomKey);
            }
        } catch (error) {
            console.log('Random motion play failed:', error);
        }
    }

    setState(state) {
        const stateMap = {
            'idle': { expression: 'neutral', motion: 'Idle' },
            'listening': { expression: 'surprise', motion: 'TapHead' },
            'thinking': { expression: 'thinking', motion: 'Idle' },
            'speaking': { expression: 'joy', motion: 'TapBody' },
            'happy': { expression: 'joy', motion: 'TapBody' },
            'confused': { expression: 'thinking', motion: 'Idle' },
            'excited': { expression: 'joy', motion: 'TapBody' },
            'concerned': { expression: 'concern', motion: 'Idle' }
        };

        const config = stateMap[state] || stateMap['idle'];
        this.setExpression(config.expression);
        this.playMotion(config.motion);
    }

    startSpeaking() {
        this.playMotion('TapBody');
        this.setExpression('joy');
    }

    stopSpeaking() {
        this.setExpression('neutral');
        this.playMotion('Idle');
    }

    hideCharacterFallback() {
        const fallbackEl = document.getElementById('character');
        if (fallbackEl) {
            fallbackEl.style.display = 'none';
            console.log('CSS fallback character hidden');
        }
    }

    showCharacterFallback() {
        const fallbackEl = document.getElementById('character');
        if (fallbackEl) {
            fallbackEl.style.display = 'block';
            console.log('CSS fallback character shown');
        }
    }

    destroy() {
        // Clean up resources
        if (this.viewer) {
            // L2dViewer doesn't have explicit destroy method
            this.viewer = null;
        }
        this.isLoaded = false;
    }
}

// Global instance
let live2dViewer = null;

// Initialize Live2D viewer
async function initLive2DViewer() {
    try {
        console.log('Starting Live2D initialization...');

        live2dViewer = new Live2DViewerV3('live2d-canvas', 'ANIYA');
        await live2dViewer.init();

        console.log('Live2D viewer initialization completed');
        return live2dViewer;

    } catch (error) {
        console.error('Live2D initialization failed:', error);

        // Show fallback character
        live2dViewer = new Live2DViewerV3('live2d-canvas');
        live2dViewer.showCharacterFallback();

        return live2dViewer;
    }
}

// Export for use in main app
window.Live2DViewerV3 = Live2DViewerV3;
window.initLive2DViewer = initLive2DViewer;