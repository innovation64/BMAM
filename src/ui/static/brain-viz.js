/**
 * Brain Network Visualization
 * 脑区激活和推理链可视化
 */

'use strict';

(function() {
    // Brain regions configuration
    const BRAIN_REGIONS = {
        'reasoning_validator': { name: 'Reasoning Validator', emoji: '🧩', color: '#FF6B6B' },
        'reflection': { name: 'Reflection', emoji: '💭', color: '#4ECDC4' },
        'consolidation': { name: 'Consolidation', emoji: '🔗', color: '#45B7D1' },
        'memory_retrieval': { name: 'Memory Retrieval', emoji: '🔍', color: '#96CEB4' },
        'perception_encoding': { name: 'Perception', emoji: '👁️', color: '#FFEAA7' },
        'conversation': { name: 'Conversation', emoji: '💬', color: '#DFE6E9' },
        'executive_control': { name: 'Executive Control', emoji: '🎯', color: '#74B9FF' },
        'short_term_memory': { name: 'Working Memory', emoji: '⚡', color: '#FDA7DF' }
    };

    function initBrainPanel() {
        const brainRegionsDiv = document.getElementById('brain-regions');
        if (!brainRegionsDiv) return;

        // Initialize brain region displays
        Object.keys(BRAIN_REGIONS).forEach(regionId => {
            const config = BRAIN_REGIONS[regionId];
            const regionEl = document.createElement('div');
            regionEl.id = `region-${regionId}`;
            regionEl.style.cssText = `
                padding: 8px 12px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                border-left: 3px solid ${config.color};
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: space-between;
                opacity: 0.5;
            `;

            regionEl.innerHTML = `
                <span style="font-size: 11px; color: #ccc;">
                    ${config.emoji} ${config.name}
                </span>
                <div style="width: 50px; height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; overflow: hidden;">
                    <div class="activation-bar" style="width: 0%; height: 100%; background: ${config.color}; transition: width 0.5s ease;"></div>
                </div>
            `;

            brainRegionsDiv.appendChild(regionEl);
        });
    }

    function updateBrainActivity(regions, reasoningChain) {
        // Update brain region activations
        if (regions) {
            Object.keys(BRAIN_REGIONS).forEach(regionId => {
                const regionEl = document.getElementById(`region-${regionId}`);
                if (!regionEl) return;

                const activation = regions[regionId] || 0;
                const activationBar = regionEl.querySelector('.activation-bar');

                if (activationBar) {
                    activationBar.style.width = `${activation * 100}%`;
                }

                // Highlight active regions
                if (activation > 0.5) {
                    regionEl.style.opacity = '1';
                    regionEl.style.background = `rgba(255, 255, 255, 0.15)`;
                    regionEl.style.transform = 'translateX(3px)';
                } else {
                    regionEl.style.opacity = '0.5';
                    regionEl.style.background = 'rgba(255, 255, 255, 0.05)';
                    regionEl.style.transform = 'translateX(0)';
                }
            });
        }

        // Update reasoning chain
        if (reasoningChain) {
            updateReasoningChain(reasoningChain);
        }
    }

    function updateReasoningChain(chain) {
        const reasoningStepsDiv = document.getElementById('reasoning-steps');
        if (!reasoningStepsDiv) return;

        if (!chain || chain.length === 0) {
            reasoningStepsDiv.innerHTML = '<div style="color: #888; font-style: italic;">No active reasoning...</div>';
            return;
        }

        reasoningStepsDiv.innerHTML = '';

        chain.forEach((step, index) => {
            const stepEl = document.createElement('div');
            stepEl.style.cssText = `
                margin-bottom: 10px;
                padding: 10px;
                background: rgba(107, 70, 193, 0.1);
                border-radius: 6px;
                border-left: 2px solid #6B46C1;
                animation: fadeIn 0.3s ease-in-out;
                animation-delay: ${index * 0.1}s;
                opacity: 0;
                animation-fill-mode: forwards;
            `;

            const stepIcon = getStepIcon(step.type);

            stepEl.innerHTML = `
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <span style="font-size: 14px; margin-right: 8px;">${stepIcon}</span>
                    <span style="font-size: 11px; color: #00D9FF; font-weight: bold;">${step.agent || 'System'}</span>
                </div>
                <div style="font-size: 11px; color: #ccc; line-height: 1.4;">
                    ${step.description || step.text || 'Processing...'}
                </div>
                ${step.confidence ? `<div style="font-size: 10px; color: #888; margin-top: 5px;">Confidence: ${(step.confidence * 100).toFixed(0)}%</div>` : ''}
            `;

            reasoningStepsDiv.appendChild(stepEl);
        });

        // Add CSS animation
        if (!document.getElementById('brain-viz-styles')) {
            const style = document.createElement('style');
            style.id = 'brain-viz-styles';
            style.textContent = `
                @keyframes fadeIn {
                    from {
                        opacity: 0;
                        transform: translateY(-10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }

    function getStepIcon(type) {
        const icons = {
            'retrieval': '🔍',
            'reasoning': '🧩',
            'consolidation': '🔗',
            'reflection': '💭',
            'validation': '✅',
            'collaboration': '🤝'
        };
        return icons[type] || '▶️';
    }

    // Mock data for testing (will be replaced by real WebSocket data)
    function simulateBrainActivity() {
        const mockRegions = {
            'perception_encoding': 1.0,
            'memory_retrieval': 0.9,
            'reasoning_validator': 0.8,
            'reflection': 0.7,
            'consolidation': 0.6,
            'conversation': 0.5
        };

        const mockChain = [
            { agent: 'Perception', type: 'retrieval', description: 'Processing query: "What is Caroline interested in?"', confidence: 1.0 },
            { agent: 'Memory Retrieval', type: 'retrieval', description: 'Retrieved 20 relevant memories from FAISS', confidence: 0.95 },
            { agent: 'Reasoning Validator', type: 'reasoning', description: 'Detected question type: multi_hop', confidence: 0.9 },
            { agent: 'Reflection Agent', type: 'reflection', description: 'Pattern-based reasoning: identifying interests from behaviors', confidence: 0.85 },
            { agent: 'Reflection', type: 'collaboration', description: 'Inferred: LGBTQ advocacy, adoption services', confidence: 0.90 },
            { agent: 'Reasoning Validator', type: 'validation', description: 'Validated and synthesized final answer', confidence: 0.95 }
        ];

        updateBrainActivity(mockRegions, mockChain);
    }

    // Initialize on page load
    window.addEventListener('DOMContentLoaded', () => {
        initBrainPanel();

        // Simulate brain activity for demo (remove in production)
        // setTimeout(simulateBrainActivity, 2000);
    });

    // Expose globally
    window.updateBrainActivity = updateBrainActivity;
    window.simulateBrainActivity = simulateBrainActivity;
})();
