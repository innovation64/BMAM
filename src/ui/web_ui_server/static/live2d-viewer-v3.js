/**
 * Live2D Character Viewer using live2dv3.js
 * Compatible with BMAM Voice UI
 */

class Live2DViewerV3 {
    constructor(containerId, modelName = 'ANIYA') {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.modelName = modelName;
        this.viewer = null;
        this.isLoaded = false;
        this.currentExpression = 'neutral';
        this.currentMotion = 'idle';
    }

    async init() {
        try {
            console.log('Initializing Live2D viewer with model:', this.modelName);

            // Check if L2dViewer is available (from live2dv3.js)
            if (typeof L2dViewer === 'undefined') {
                console.error('L2dViewer not loaded. Check if live2dv3.js is included.');
                throw new Error('L2dViewer not loaded from live2dv3.js');
            }
            console.log('L2dViewer found');

            // Ensure container exists and has dimensions
            if (!this.container) {
                throw new Error('Container element not found: ' + this.containerId);
            }

            // Get container dimensions - ensure minimum size
            let width = this.container.offsetWidth || this.container.clientWidth || 800;
            let height = this.container.offsetHeight || this.container.clientHeight || 600;

            // Ensure minimum dimensions
            if (width < 100) width = 800;
            if (height < 100) height = 600;

            console.log('Container dimensions:', width, 'x', height);

            // Create L2dViewer - it expects a DIV and creates canvas internally
            console.log('Creating L2dViewer with model path: /static/models/' + this.modelName + '/' + this.modelName + '.model3.json');

            const self = this;
            this.viewer = new L2dViewer({
                el: this.container,
                modelHomePath: '/static/models/',
                model: this.modelName,
                width: width,
                height: height,
                autoMotion: true,
                _finishedLoadModel: function() {
                    console.log('Live2D model loaded successfully via callback');
                    self.isLoaded = true;
                    self.hideCharacterFallback();
                    self.setupEventHandlers();
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
            const maxAttempts = 300; // 30 seconds timeout

            const checkLoaded = () => {
                attempts++;
                if (this.isLoaded) {
                    console.log(`Live2D model loaded after ${attempts * 100}ms`);
                    resolve();
                } else if (attempts >= maxAttempts) {
                    reject(new Error('Timeout waiting for model to load (30s)'));
                } else {
                    setTimeout(checkLoaded, 100);
                }
            };

            checkLoaded();
        });
    }

    setupEventHandlers() {
        // L2dViewer creates its own canvas - find it
        const canvas = this.container.querySelector('canvas');
        if (!canvas) {
            console.warn('Canvas not found in container');
            return;
        }

        canvas.addEventListener('click', (event) => {
            this.onModelTouch(event);
        });
        console.log('Event handlers setup complete');
    }

    onModelTouch(event) {
        console.log('Model touched');
        this.playRandomMotion();
        setTimeout(() => {
            this.setExpression('neutral');
        }, 2000);
    }

    setExpression(emotion) {
        if (!this.isLoaded || !this.viewer) return;
        this.currentExpression = emotion;
        console.log('Setting emotion:', emotion);
    }

    playMotion(motionName) {
        if (!this.isLoaded || !this.viewer) return;

        try {
            if (typeof this.viewer.getMotions === 'function') {
                const motions = this.viewer.getMotions();
                for (let [key, value] of motions) {
                    if (key.toLowerCase().includes(motionName.toLowerCase())) {
                        this.viewer.startMotion(key);
                        console.log('Playing motion:', key);
                        return;
                    }
                }
            }
            console.log('Motion not found or getMotions not available:', motionName);
        } catch (error) {
            console.log('Motion play failed:', error);
        }
    }

    playRandomMotion() {
        if (!this.isLoaded || !this.viewer) return;

        try {
            if (typeof this.viewer.getMotions === 'function') {
                const motions = this.viewer.getMotions();
                const motionKeys = Array.from(motions.keys());

                if (motionKeys.length > 0) {
                    const randomKey = motionKeys[Math.floor(Math.random() * motionKeys.length)];
                    this.viewer.startMotion(randomKey);
                    console.log('Playing random motion:', randomKey);
                }
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
        if (this.viewer) {
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

        // Wait a bit for container to have proper dimensions
        await new Promise(resolve => setTimeout(resolve, 500));

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
