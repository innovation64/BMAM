/**
 * Brain Network Visualization
 * Matches actual 5 brain region agents + process agents
 */
'use strict';

(function () {
    // Actual brain region agents from BMAM coordinator
    const BRAIN_REGIONS = {
        'hippocampus': {
            name: 'Hippocampus', nameZh: '海马体',
            emoji: '🧠', color: '#FF6B6B', role: 'Episodic Memory'
        },
        'temporal_lobe': {
            name: 'Temporal Lobe', nameZh: '颞叶',
            emoji: '📚', color: '#4ECDC4', role: 'Semantic + KG'
        },
        'amygdala': {
            name: 'Amygdala', nameZh: '杏仁核',
            emoji: '❤️', color: '#FDA7DF', role: 'Salience'
        },
        'prefrontal': {
            name: 'Prefrontal Cortex', nameZh: '前额叶',
            emoji: '🎯', color: '#74B9FF', role: 'Working Memory'
        },
        'basal_ganglia': {
            name: 'Basal Ganglia', nameZh: '基底神经节',
            emoji: '⚙️', color: '#FFEAA7', role: 'Procedural'
        },
        // Process agents
        'conversation': {
            name: 'Conversation', nameZh: '对话',
            emoji: '💬', color: '#DFE6E9', role: 'Dialog'
        },
        'memory_retrieval': {
            name: 'Memory Retrieval', nameZh: '记忆检索',
            emoji: '🔍', color: '#96CEB4', role: 'Retrieval'
        },
        'consolidation': {
            name: 'Consolidation', nameZh: '记忆巩固',
            emoji: '🔗', color: '#45B7D1', role: 'Consolidation'
        },
        'reasoning_validator': {
            name: 'Reasoning', nameZh: '推理验证',
            emoji: '🧩', color: '#FF6B6B', role: 'Validation'
        }
    };

    function getRegionLabel(regionId) {
        const config = BRAIN_REGIONS[regionId];
        if (!config) return regionId;
        const lang = (typeof I18N !== 'undefined') ? I18N.getLang() : 'en';
        return lang === 'zh' ? config.nameZh : config.name;
    }

    function initBrainPanel() {
        const container = document.getElementById('brain-regions');
        if (!container) return;

        container.innerHTML = '';

        Object.keys(BRAIN_REGIONS).forEach(regionId => {
            const config = BRAIN_REGIONS[regionId];
            const el = document.createElement('div');
            el.id = `region-${regionId}`;
            el.className = 'brain-region-item';
            el.style.cssText = `
                padding: 8px 12px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                border-left: 3px solid ${config.color};
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: space-between;
                opacity: 0.5;
                margin-bottom: 6px;
            `;

            el.innerHTML = `
                <span class="region-label" style="font-size: 11px; color: #ccc;">
                    ${config.emoji} <span class="region-name">${getRegionLabel(regionId)}</span>
                </span>
                <div style="width: 50px; height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; overflow: hidden;">
                    <div class="activation-bar" style="width: 0%; height: 100%; background: ${config.color}; transition: width 0.5s ease;"></div>
                </div>
            `;
            container.appendChild(el);
        });
    }

    /**
     * Build activation map from agents_involved list
     * @param {string[]} agentsInvolved - list of agent IDs from ProcessingResult
     * @returns {Object} regionId -> activation (0-1)
     */
    function buildActivationMap(agentsInvolved) {
        if (!agentsInvolved || !Array.isArray(agentsInvolved)) return {};

        const map = {};
        agentsInvolved.forEach(agentId => {
            // Normalize agent ID (some agents may use different naming)
            const normalized = agentId.toLowerCase().replace(/\s+/g, '_');

            // Try direct match first
            if (BRAIN_REGIONS[normalized]) {
                map[normalized] = 1.0;
                return;
            }

            // Partial matching for known patterns
            for (const regionId of Object.keys(BRAIN_REGIONS)) {
                if (normalized.includes(regionId) || regionId.includes(normalized)) {
                    map[regionId] = 1.0;
                    return;
                }
            }

            // Fallback: add with full activation anyway
            map[normalized] = 0.8;
        });

        return map;
    }

    function updateBrainActivity(regions, reasoningChain) {
        if (regions) {
            Object.keys(BRAIN_REGIONS).forEach(regionId => {
                const el = document.getElementById(`region-${regionId}`);
                if (!el) return;

                const activation = regions[regionId] || 0;
                const bar = el.querySelector('.activation-bar');
                if (bar) {
                    bar.style.width = `${activation * 100}%`;
                }

                if (activation > 0.5) {
                    el.style.opacity = '1';
                    el.style.background = 'rgba(255, 255, 255, 0.15)';
                    el.style.transform = 'translateX(3px)';
                } else {
                    el.style.opacity = '0.5';
                    el.style.background = 'rgba(255, 255, 255, 0.05)';
                    el.style.transform = 'translateX(0)';
                }
            });
        }

        if (reasoningChain) {
            updateReasoningChain(reasoningChain);
        }
    }

    function updateReasoningChain(chain) {
        const container = document.getElementById('reasoning-steps');
        if (!container) return;

        if (!chain || chain.length === 0) {
            const noReasoning = (typeof I18N !== 'undefined')
                ? I18N.t('right.no_reasoning')
                : 'No active reasoning...';
            container.innerHTML = `<div style="color: #888; font-style: italic;">${noReasoning}</div>`;
            return;
        }

        container.innerHTML = '';
        chain.forEach((step, index) => {
            const el = document.createElement('div');
            el.style.cssText = `
                margin-bottom: 10px;
                padding: 10px;
                background: rgba(107, 70, 193, 0.1);
                border-radius: 6px;
                border-left: 2px solid #6B46C1;
                animation: brainFadeIn 0.3s ease-in-out forwards;
                animation-delay: ${index * 0.1}s;
                opacity: 0;
            `;

            const icon = getStepIcon(step.type || step.agent || '');
            el.innerHTML = `
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <span style="font-size: 14px; margin-right: 8px;">${icon}</span>
                    <span style="font-size: 11px; color: #00D9FF; font-weight: bold;">
                        ${step.agent || step.phase || 'System'}
                    </span>
                </div>
                <div style="font-size: 11px; color: #ccc; line-height: 1.4;">
                    ${step.description || step.text || step.content || 'Processing...'}
                </div>
                ${step.confidence ? `<div style="font-size: 10px; color: #888; margin-top: 5px;">Confidence: ${(step.confidence * 100).toFixed(0)}%</div>` : ''}
            `;
            container.appendChild(el);
        });

        // Add CSS keyframes once
        if (!document.getElementById('brain-viz-styles')) {
            const style = document.createElement('style');
            style.id = 'brain-viz-styles';
            style.textContent = `
                @keyframes brainFadeIn {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `;
            document.head.appendChild(style);
        }
    }

    function refreshLabels() {
        Object.keys(BRAIN_REGIONS).forEach(regionId => {
            const el = document.getElementById(`region-${regionId}`);
            if (!el) return;
            const nameSpan = el.querySelector('.region-name');
            if (nameSpan) {
                nameSpan.textContent = getRegionLabel(regionId);
            }
        });
    }

    function getStepIcon(type) {
        const t = (type || '').toLowerCase();
        const icons = {
            'retrieval': '🔍', 'memory_retrieval': '🔍',
            'reasoning': '🧩', 'reasoning_validator': '🧩',
            'consolidation': '🔗',
            'reflection': '💭',
            'validation': '✅',
            'collaboration': '🤝',
            'hippocampus': '🧠',
            'temporal_lobe': '📚',
            'amygdala': '❤️',
            'prefrontal': '🎯',
            'basal_ganglia': '⚙️',
            'conversation': '💬',
        };
        return icons[t] || '▶️';
    }

    function simulateBrainActivity() {
        const mockRegions = {
            'hippocampus': 1.0,
            'temporal_lobe': 0.9,
            'prefrontal': 0.8,
            'amygdala': 0.6,
            'memory_retrieval': 0.7,
            'reasoning_validator': 0.5
        };
        const mockChain = [
            { agent: 'Hippocampus', type: 'retrieval', description: 'Retrieving episodic memories...', confidence: 0.95 },
            { agent: 'Temporal Lobe', type: 'retrieval', description: 'Querying knowledge graph', confidence: 0.9 },
            { agent: 'Prefrontal', type: 'reasoning', description: 'Working memory integration', confidence: 0.85 },
            { agent: 'Reasoning Validator', type: 'validation', description: 'Validating answer', confidence: 0.92 }
        ];
        updateBrainActivity(mockRegions, mockChain);
    }

    // Initialize on DOM load
    window.addEventListener('DOMContentLoaded', () => {
        initBrainPanel();
    });

    // Expose globally
    window.updateBrainActivity = updateBrainActivity;
    window.buildActivationMap = buildActivationMap;
    window.simulateBrainActivity = simulateBrainActivity;
    window.refreshBrainLabels = refreshLabels;
    window.initBrainPanel = initBrainPanel;
})();
