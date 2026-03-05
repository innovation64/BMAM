/**
 * Live2D Character Viewer for BMAM Voice UI
 * Supports both Cubism 2.1 and Cubism 4.0 models
 */

class Live2DViewer {
    constructor(canvasId, modelUrl) {
        this.canvas = document.getElementById(canvasId);
        this.modelUrl = modelUrl;
        this.app = null;
        this.model = null;
        this.currentExpression = 'neutral';
        this.currentMotion = 'idle';
        this.isLoaded = false;
        this.mouthParamId = null;
        this.mouthParamNotFoundLogged = false;
        this._onResizeHandler = this.handleResize.bind(this);
    }

    async init() {
        try {
            const { width, height } = this.ensureCanvasSize();
            // Initialize PIXI Application
            this.app = new PIXI.Application({
                view: this.canvas,
                width,
                height,
                backgroundColor: 0x000000,
                transparent: true,
                antialias: true,
                powerPreference: "high-performance"
            });

            // Add to global scope for debugging
            window.pixiApp = this.app;

            await this.loadModel();
            this.setupEventListeners();
            window.addEventListener('resize', this._onResizeHandler);

            console.log('Live2D viewer initialized successfully');
            this.isLoaded = true;

        } catch (error) {
            console.error('Failed to initialize Live2D viewer:', error);
            this.showFallbackCharacter();
        }
    }

    async loadModel() {
        try {
            console.log('Attempting to load model from:', this.modelUrl);

            // Check if PIXI live2d plugin is available
            if (!window.PIXI || !window.PIXI.live2d) {
                console.error('PIXI Live2D plugin not loaded');
                throw new Error('PIXI Live2D plugin not loaded');
            }

            console.log('PIXI available:', !!window.PIXI);
            console.log('PIXI.live2d available:', !!window.PIXI.live2d);

            // Load model with pixi-live2d-display
            console.log('Loading with pixi-live2d-display...');
            this.model = await PIXI.live2d.Live2DModel.from(this.modelUrl);

            if (!this.model) {
                throw new Error('Failed to load Live2D model');
            }

            this.model.anchor.set(0.5, 1);

            // Add to stage
            this.app.stage.addChild(this.model);
            this.fitModelToCanvas();
            setTimeout(() => this.fitModelToCanvas(), 0);

            // Setup interactions
            this.model.interactive = true;
            this.model.on('pointerdown', this.onModelTouch.bind(this));

            console.log('Live2D model loaded successfully');

        } catch (error) {
            console.error('Model loading failed:', error);
            throw error;
        }
    }

    ensureCanvasSize() {
        if (!this.canvas) {
            return { width: 800, height: 600 };
        }

        const container = this.canvas.parentElement;
        const width = Math.max(1, container ? container.clientWidth : this.canvas.clientWidth || 800);
        const height = Math.max(1, container ? container.clientHeight : this.canvas.clientHeight || 600);

        this.canvas.width = width;
        this.canvas.height = height;

        return { width, height };
    }

    fitModelToCanvas() {
        if (!this.model || !this.app) {
            return;
        }

        const { width, height } = this.ensureCanvasSize();
        this.app.renderer.resize(width, height);

        // Reset scale to measure bounds accurately
        this.model.scale.set(1);
        this.model.position.set(width / 2, height);

        const bounds = this.model.getBounds(false);
        const modelWidth = bounds.width || 1;
        const modelHeight = bounds.height || 1;

        const scaleX = (width * 0.65) / modelWidth;
        const scaleY = (height * 0.65) / modelHeight;
        const baseScale = Math.min(scaleX, scaleY);
        const targetScale = Math.max(0.08, Math.min(0.2, baseScale));

        this.model.scale.set(targetScale);
        this.model.position.set(width / 2, height * 1.03);

        console.log('Model fit to canvas', {
            canvasWidth: width,
            canvasHeight: height,
            modelWidth,
            modelHeight,
            targetScale
        });
    }

    resolveMouthParameterId() {
        if (this.mouthParamId) {
            return this.mouthParamId;
        }

        if (!this.model || !this.model.internalModel) {
            return null;
        }

        const coreModel = this.model.internalModel.coreModel;
        if (!coreModel || typeof coreModel.getParameterCount !== 'function') {
            return null;
        }

        const preferredIds = ['ParamMouthOpenY', 'PARAM_MOUTH_OPEN_Y', 'ParamMouthOpen', 'PARAM_MOUTH_OPEN'];
        const total = coreModel.getParameterCount();
        let looseMatch = null;

        for (let i = 0; i < total; i += 1) {
            const id = coreModel.getParameterId(i);
            if (preferredIds.includes(id)) {
                this.mouthParamId = id;
                break;
            }
            if (!looseMatch && /mouth.*open/i.test(id)) {
                looseMatch = id;
            }
        }

        if (!this.mouthParamId && looseMatch) {
            this.mouthParamId = looseMatch;
        }

        return this.mouthParamId;
    }

    setMouthOpen(amount) {
        if (!this.model || !this.model.internalModel) {
            return;
        }

        const coreModel = this.model.internalModel.coreModel;
        if (!coreModel || typeof coreModel.setParameterValueById !== 'function') {
            return;
        }

        const paramId = this.resolveMouthParameterId();
        if (!paramId) {
            if (!this.mouthParamNotFoundLogged) {
                console.log('Live2D mouth parameter not found; skipping mouth sync.');
                this.mouthParamNotFoundLogged = true;
            }
            return;
        }

        const normalized = Math.max(0, Math.min(1, amount * 3));

        try {
            coreModel.setParameterValueById(paramId, normalized);
        } catch (error) {
            console.log('Mouth parameter update failed:', error);
        }
    }

    handleResize() {
        this.fitModelToCanvas();
    }

    async loadWithCubismSDK() {
        // Direct Cubism SDK implementation
        // This would require more complex setup
        console.log('Direct Cubism SDK loading not implemented yet');
        throw new Error('Direct SDK loading not available');
    }

    showFallbackCharacter() {
        // Initialize PIXI app if not already done
        if (!this.app) {
            const { width, height } = this.ensureCanvasSize();
            this.app = new PIXI.Application({
                view: this.canvas,
                width,
                height,
                backgroundColor: 0x000000,
                transparent: true,
                antialias: true,
                powerPreference: "high-performance"
            });
        }

        const { width, height } = this.ensureCanvasSize();
        this.app.renderer.resize(width, height);

        // Clear existing content
        this.app.stage.removeChildren();

        // Create a simple animated character using PIXI graphics
        const character = new PIXI.Container();

        // Body
        const body = new PIXI.Graphics();
        body.beginFill(0xFFE4E6);
        body.lineStyle(3, 0xFF6B9D);
        body.drawRoundedRect(-60, -140, 120, 180, 40);
        body.endFill();

        // Head
        const head = new PIXI.Graphics();
        head.beginFill(0xFFE4E6);
        head.lineStyle(3, 0xFF6B9D);
        head.drawCircle(0, -200, 60);
        head.endFill();

        // Eyes
        const leftEye = new PIXI.Graphics();
        leftEye.beginFill(0x1A1A2E);
        leftEye.drawCircle(-20, -210, 10);
        leftEye.endFill();

        const rightEye = new PIXI.Graphics();
        rightEye.beginFill(0x1A1A2E);
        rightEye.drawCircle(20, -210, 10);
        rightEye.endFill();

        // Mouth
        const mouth = new PIXI.Graphics();
        mouth.lineStyle(3, 0xFF6B9D);
        mouth.arc(0, -190, 15, 0, Math.PI);

        // Hair
        const hair = new PIXI.Graphics();
        hair.beginFill(0x6B46C1);
        hair.drawRoundedRect(-70, -260, 140, 80, 50);
        hair.endFill();

        // Assemble character
        character.addChild(hair);
        character.addChild(body);
        character.addChild(head);
        character.addChild(leftEye);
        character.addChild(rightEye);
        character.addChild(mouth);

        // Position character
        character.x = this.app.screen.width / 2;
        character.y = this.app.screen.height * 0.8;

        // Add to stage
        this.app.stage.addChild(character);

        // Store reference
        this.model = character;
        this.isLoaded = true;

        // Add breathing animation
        this.startBreathingAnimation();

        console.log('Fallback character created');
    }

    startBreathingAnimation() {
        if (!this.model) return;

        let time = 0;
        const animate = () => {
            time += 0.016; // 60 FPS

            if (this.model && this.model.scale) {
                const breath = 1 + Math.sin(time * 2) * 0.02;
                this.model.scale.set(this.model.scale.x, breath * Math.abs(this.model.scale.y));
            }

            requestAnimationFrame(animate);
        };

        animate();
    }

    setupEventListeners() {
        if (!this.model) return;

        this.model.interactive = true;
        this.model.buttonMode = true;

        this.model.on('pointerdown', this.onModelTouch.bind(this));
        this.model.on('pointerover', () => {
            this.canvas.style.cursor = 'pointer';
        });
        this.model.on('pointerout', () => {
            this.canvas.style.cursor = 'default';
        });
    }

    onModelTouch(event) {
        console.log('Model touched');
        this.setExpression('joy');
        this.playMotion('TapBody');

        // Reset after a delay
        setTimeout(() => {
            this.setExpression('neutral');
        }, 2000);
    }

    setExpression(emotion) {
        if (!this.isLoaded) return;

        this.currentExpression = emotion;

        if (this.model && this.model.internalModel) {
            // For Live2D models
            const expressionMap = {
                'neutral': 0,
                'joy': 1,
                'surprise': 2,
                'thinking': 3,
                'concern': 4
            };

            const expressionIndex = expressionMap[emotion] || 0;

            const motionManager = this.model.internalModel.motionManager;

            if (motionManager) {
                try {
                    if (typeof motionManager.setExpression === 'function') {
                        motionManager.setExpression(expressionIndex);
                    } else if (motionManager.expressionManager &&
                        typeof motionManager.expressionManager.setExpression === 'function') {
                        motionManager.expressionManager.setExpression(expressionIndex);
                    } else {
                        console.log('Expression manager not available on current model; skipping expression change.');
                    }
                } catch (error) {
                    console.log('Expression change failed:', error);
                }
            }
        }

        console.log('Expression set to:', emotion);
    }

    playMotion(motionGroup, motionIndex = 0) {
        if (!this.isLoaded || !this.model) return;

        this.currentMotion = motionGroup;

        if (this.model.internalModel && this.model.internalModel.motionManager) {
            try {
                this.model.internalModel.motionManager.startMotion(motionGroup, motionIndex, 3);
            } catch (error) {
                console.log('Motion play failed:', error);
            }
        }

        console.log('Motion played:', motionGroup);
    }

    setState(state) {
        const stateMap = {
            'idle': { expression: 'neutral', motion: 'Idle' },
            'listening': { expression: 'surprise', motion: 'Idle' },
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

    destroy() {
        window.removeEventListener('resize', this._onResizeHandler);
        if (this.app) {
            this.app.destroy(true);
        }
    }
}

// Model URLs - you can replace these with other free models
const MODEL_URLS = {
    // Free Live2D sample models
    'mao': 'https://cdn.jsdelivr.net/gh/Live2D/CubismWebSamples@develop/Samples/Resources/Mao/',
    'haru': 'https://cdn.jsdelivr.net/gh/Live2D/CubismWebSamples@develop/Samples/Resources/Haru/',
    'mark': 'https://cdn.jsdelivr.net/gh/Live2D/CubismWebSamples@develop/Samples/Resources/Mark/',

    // ANIYA model from jianchengwang/live2d_models GitHub repository
    'aniya': '/static/models/aniya/',

    // Community models (backup)
    'hiyori': '/static/models/hiyori/',
    'koharu': '/static/models/koharu/'
};

// Global instance
let live2dViewer = null;

// Initialize Live2D viewer
async function initLive2DViewer() {
    try {
        // Try different models until one works
        const models = ['aniya'];

        for (const modelName of models) {
            try {
                console.log(`Trying to load model: ${modelName}`);

                const modelUrl = MODEL_URLS[modelName];
                live2dViewer = new Live2DViewer('live2d-canvas', modelUrl + 'ANIYA.model3.json');

                await live2dViewer.init();

                // Show canvas and hide fallback character
                const canvasEl = document.getElementById('live2d-canvas');
                const fallbackEl = document.getElementById('character');
                console.log('Canvas element:', canvasEl);
                console.log('Fallback element:', fallbackEl);

                if (canvasEl) {
                    canvasEl.style.display = 'block';
                    console.log('Canvas display set to block');
                }
                if (fallbackEl) {
                    fallbackEl.style.display = 'none';
                    console.log('Fallback character hidden');
                }

                console.log(`Successfully loaded model: ${modelName}`);
                return live2dViewer;

            } catch (error) {
                console.error(`Failed to load model ${modelName}:`, error);
                console.error('Error details:', error.message, error.stack);
                continue;
            }
        }

        // If all models fail, show CSS fallback character
        console.log('All Live2D models failed, showing CSS fallback character');
        const fallbackEl = document.getElementById('character');
        const canvasEl = document.getElementById('live2d-canvas');
        console.log('Showing fallback - Canvas element:', canvasEl);
        console.log('Showing fallback - Fallback element:', fallbackEl);

        if (canvasEl) {
            canvasEl.style.display = 'none';
            console.log('Canvas hidden for fallback');
        }
        if (fallbackEl) {
            fallbackEl.style.display = 'block';
            console.log('CSS fallback character shown');
        }

        // Create minimal Live2DViewer instance for compatibility
        live2dViewer = new Live2DViewer('live2d-canvas', '');
        live2dViewer.isLoaded = false; // Mark as not loaded

        return live2dViewer;

    } catch (error) {
        console.error('Live2D initialization failed completely:', error);
        return null;
    }
}

// Export for use in main app
window.Live2DViewer = Live2DViewer;
window.initLive2DViewer = initLive2DViewer;
