// 全局变量
let capacityChart = null;
let flowChart = null;
let feedbackChart = null;
let soulRadarChart = null;
let autoRefresh = true;
let refreshInterval = null;
let soulRefreshInterval = null;

// ... (existing code) ...

// 加载所有数据
async function loadAllData() {
    // ... (existing code) ...
}

// 加载灵魂状态 (独立的高频轮询)
async function loadSoulState() {
    try {
        const response = await fetch('/api/soul_state');
        const result = await response.json();

        if (result.success) {
            const state = result.data;
            updateSoulVisuals(state);
        }
    } catch (error) {
        console.error('加载灵魂状态失败:', error);
    }
}

function updateSoulVisuals(state) {
    // 1. Update Text Stats
    document.getElementById('current-emotion').textContent = state.emotion;
    document.getElementById('emotion-intensity').textContent = `Intensity: ${state.intensity.toFixed(2)}`;
    document.getElementById('dream-state').textContent = state.is_dreaming ? "Dreaming 🌌" : "Awake 👁️";
    document.getElementById('soul-status').textContent = state.emotion;

    // 2. Update Consciousness Stream
    const streamDiv = document.getElementById('consciousness-stream');
    if (state.active_thought) {
        // Only update if changed to avoid flicker
        const currentText = streamDiv.querySelector('.stream-text')?.textContent;
        if (currentText !== state.active_thought) {
            streamDiv.innerHTML = `<span class="stream-text">${state.active_thought}</span>`;
        }
    }

    // 3. Update Soul Core Animation
    const core = document.getElementById('soul-core');
    // Change color based on emotion
    let color = '#00f3ff'; // Default Cyan (Neutral)
    if (state.emotion === 'Emotional') color = '#f56565'; // Red
    if (state.emotion === 'Analytical') color = '#48bb78'; // Green
    if (state.emotion === 'Habitual') color = '#9f7aea'; // Purple
    if (state.emotion === 'Curious') color = '#ed8936'; // Orange
    if (state.is_dreaming) color = '#ecc94b'; // Yellow

    core.style.background = color;
    core.style.boxShadow = `0 0 15px ${color}`;

    // Pulse speed based on intensity
    const duration = Math.max(0.5, 2.0 - state.intensity);
    core.style.animationDuration = `${duration}s`;

    // 4. Update Radar Chart
    if (window.soulRadarChart) {
        window.soulRadarChart.data.datasets[0].data = [
            state.weights.amygdala || 0,
            state.weights.prefrontal || 0,
            state.weights.basal_ganglia || 0
        ];
        window.soulRadarChart.data.datasets[0].borderColor = color;
        window.soulRadarChart.data.datasets[0].backgroundColor = adjustColor(color, -20) + '33'; // Add transparency
        window.soulRadarChart.update();
    }
}

// ... (existing load functions) ...

// 初始化图表
function initCharts() {
    // ... (existing charts) ...

    // 灵魂雷达图
    const soulCtx = document.getElementById('soul-radar-chart').getContext('2d');
    window.soulRadarChart = new Chart(soulCtx, {
        type: 'radar',
        data: {
            labels: ['Amygdala (Emotion)', 'Prefrontal (Logic)', 'Basal Ganglia (Habit)'],
            datasets: [{
                label: 'Brain Activity',
                data: [0, 0, 0],
                fill: true,
                backgroundColor: 'rgba(0, 243, 255, 0.2)',
                borderColor: '#00f3ff',
                pointBackgroundColor: '#fff',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: '#00f3ff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                r: {
                    angleLines: { color: 'rgba(255, 255, 255, 0.1)' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    pointLabels: {
                        color: '#a0aec0',
                        font: { size: 12 }
                    },
                    ticks: { display: false, max: 1.0, min: 0 }
                }
            }
        }
    });
}

// 自动刷新
function startAutoRefresh() {
    // Regular stats (5s)
    refreshInterval = setInterval(() => {
        if (autoRefresh) {
            loadAllData();
        }
    }, 5000);

    // Soul State (1s) - High frequency for "live" feel
    soulRefreshInterval = setInterval(() => {
        if (autoRefresh) {
            loadSoulState();
        }
    }, 1000);
}

// ... (rest of the file) ...
const regionColors = {
    'hippocampus': '#667eea',
    'temporal_lobe': '#48bb78',
    'prefrontal': '#ed8936',
    'prefrontal_storage': '#ed8936',
    'amygdala': '#f56565',
    'basal_ganglia': '#9f7aea',
    'short_term_memory': '#4fd1c5',
    'long_term_memory': '#38b2ac',
    'memory_retrieval': '#4299e1',
    'consolidation': '#805ad5',
    'memory_distortion': '#d53f8c',
    'reflection': '#3182ce',
    'forgetting': '#718096',
    'stress_response': '#e53e3e',
    'reasoning_validator': '#dd6b20',
    'persona_memory': '#d69e2e',
    'personality': '#b794f4',
    'conversation': '#63b3ed',
    'executive_control': '#f687b3',
    'perception_encoding': '#68d391',
    'action_execution': '#f6ad55',
    'environment': '#cbd5e0'
};

// 初始化
document.addEventListener('DOMContentLoaded', function () {
    console.log('🧠 BMAM Memory Visualizer 初始化...');

    // 初始化图表
    initCharts();

    // 加载数据
    loadAllData();

    // 设置自动刷新
    startAutoRefresh();

    // 绑定事件
    document.getElementById('refresh-btn').addEventListener('click', loadAllData);
    document.getElementById('auto-refresh-btn').addEventListener('click', toggleAutoRefresh);
});

// 加载所有数据
async function loadAllData() {
    console.log('📡 加载数据...');
    updateTime();

    try {
        await Promise.all([
            loadMemoryState(),
            loadDataFlow(),
            loadPerformance(),
            loadHealth(),
            loadRecentEvents(),
            loadFeedbackStats()
        ]);
        console.log('✅ 数据加载完成');
    } catch (error) {
        console.error('❌ 数据加载失败:', error);
    }
}

// 加载记忆状态
async function loadMemoryState() {
    try {
        const response = await fetch('/api/memory_state');
        const result = await response.json();

        if (result.success) {
            const { regions, summary } = result.data;

            // 更新概览统计
            document.getElementById('total-memories').textContent = summary.total_memories.toLocaleString();
            document.getElementById('overall-usage').textContent = summary.overall_usage.toFixed(2) + '%';
            document.getElementById('active-regions').textContent = `${summary.active_regions}/${regions.length}`;

            // 更新脑区列表
            updateBrainRegions(regions);

            // 更新容量图表
            updateCapacityChart(regions);
        }
    } catch (error) {
        console.error('加载记忆状态失败:', error);
    }
}

// 更新脑区列表
function updateBrainRegions(regions) {
    const container = document.getElementById('brain-regions');
    container.innerHTML = '';

    regions.forEach(region => {
        const regionDiv = document.createElement('div');
        regionDiv.className = 'brain-region';

        const color = regionColors[region.id] || '#667eea';

        regionDiv.innerHTML = `
            <div class="region-header">
                <div class="region-name" style="color: ${color}">
                    ${region.name}
                </div>
                <div class="region-stats">
                    <span>${region.current_count.toLocaleString()} / ${region.capacity.toLocaleString()}</span>
                    <span>${region.usage_percentage.toFixed(1)}%</span>
                </div>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${region.usage_percentage}%; background: linear-gradient(90deg, ${color}, ${adjustColor(color, 20)})">
                    ${region.usage_percentage > 5 ? region.usage_percentage.toFixed(1) + '%' : ''}
                </div>
            </div>
            <div class="region-details">
                ${region.avg_importance !== null ? `
                <div class="detail-item">
                    <div class="detail-label">平均重要性</div>
                    <div class="detail-value">${region.avg_importance.toFixed(3)}</div>
                </div>` : ''}
                ${region.total_stored !== null ? `
                <div class="detail-item">
                    <div class="detail-label">累计存储</div>
                    <div class="detail-value">${region.total_stored.toLocaleString()}</div>
                </div>` : ''}
                ${region.total_evicted !== null && region.total_evicted > 0 ? `
                <div class="detail-item">
                    <div class="detail-label">已淘汰</div>
                    <div class="detail-value">${region.total_evicted.toLocaleString()}</div>
                </div>` : ''}
                ${Object.keys(region.memory_types).length > 0 ? `
                <div class="detail-item">
                    <div class="detail-label">记忆类型</div>
                    <div class="detail-value">${Object.entries(region.memory_types).map(([type, count]) => `${type}: ${count}`).join(', ')}</div>
                </div>` : ''}
            </div>
        `;

        container.appendChild(regionDiv);
    });
}

// 加载数据流
async function loadDataFlow() {
    try {
        const response = await fetch('/api/dataflow');
        const result = await response.json();

        if (result.success) {
            const { total_events, event_type_counts, flows, top_flows } = result.data;

            // 更新事件类型
            const eventTypesDiv = document.getElementById('event-types');
            if (Object.keys(event_type_counts).length > 0) {
                eventTypesDiv.innerHTML = '';
                Object.entries(event_type_counts).forEach(([type, count]) => {
                    const percentage = (count / total_events * 100).toFixed(1);
                    eventTypesDiv.innerHTML += `
                        <div class="flow-item">
                            <span class="flow-name">${type}</span>
                            <span class="flow-count">${count} (${percentage}%)</span>
                        </div>
                    `;
                });
            } else {
                eventTypesDiv.innerHTML = '<div class="empty-state">暂无数据</div>';
            }

            // 更新最活跃的流
            const topFlowsDiv = document.getElementById('top-flows');
            if (top_flows.length > 0) {
                topFlowsDiv.innerHTML = '';
                top_flows.forEach(({ flow, count }) => {
                    const percentage = (count / total_events * 100).toFixed(1);
                    topFlowsDiv.innerHTML += `
                        <div class="flow-item">
                            <span class="flow-name">${flow}</span>
                            <span class="flow-count">${count} (${percentage}%)</span>
                        </div>
                    `;
                });
            } else {
                topFlowsDiv.innerHTML = '<div class="empty-state">暂无数据</div>';
            }

            // 更新流向图
            updateFlowChart(flows);
        }
    } catch (error) {
        console.error('加载数据流失败:', error);
    }
}

// 更新流向图
function updateFlowChart(flows) {
    // Define all possible nodes based on regionColors
    const allNodes = Object.keys(regionColors).map((id, index) => ({
        name: id,
        category: index % 10, // Just to vary colors if category used for color
        symbolSize: id === 'hippocampus' || id === 'temporal_lobe' ? 60 : 40,
        itemStyle: { color: regionColors[id] }
    }));

    // Filter nodes to only those involved in flows or core regions
    const activeNodeNames = new Set(['hippocampus', 'temporal_lobe', 'prefrontal', 'amygdala', 'basal_ganglia']);
    flows.forEach(f => {
        activeNodeNames.add(f.source);
        activeNodeNames.add(f.target);
    });

    const nodes = allNodes.filter(n => activeNodeNames.has(n.name));

    const links = flows.map(flow => ({
        source: flow.source,
        target: flow.target,
        value: flow.count,
        lineStyle: {
            width: Math.max(1, flow.count / 5)
        }
    }));

    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            formatter: function (params) {
                if (params.dataType === 'edge') {
                    return `${params.data.source} → ${params.data.target}<br/>数量: ${params.data.value}`;
                }
                return params.name;
            }
        },
        series: [{
            type: 'graph',
            layout: 'force',
            data: nodes,
            links: links,
            roam: true,
            label: {
                show: true,
                position: 'right',
                formatter: '{b}',
                color: '#e2e8f0'
            },
            lineStyle: {
                color: 'source',
                curveness: 0.3
            },
            emphasis: {
                focus: 'adjacency',
                lineStyle: {
                    width: 10
                }
            },
            force: {
                repulsion: 300,
                edgeLength: 150
            }
        }]
    };

    flowChart.setOption(option);
}

// 加载性能数据
async function loadPerformance() {
    try {
        const response = await fetch('/api/performance');
        const result = await response.json();

        if (result.success) {
            const { total_calls, success_rate, avg_duration_ms, error_count, slowest_functions } = result.data;

            document.getElementById('total-calls').textContent = total_calls.toLocaleString();
            document.getElementById('success-rate').textContent = success_rate.toFixed(1) + '%';
            document.getElementById('avg-duration').textContent = avg_duration_ms.toFixed(2) + ' ms';
            document.getElementById('error-count').textContent = error_count;

            // 更新最慢函数
            const slowestDiv = document.getElementById('slowest-functions');
            if (slowest_functions && slowest_functions.length > 0) {
                slowestDiv.innerHTML = '';
                slowest_functions.slice(0, 5).forEach((func, index) => {
                    slowestDiv.innerHTML += `
                        <div class="function-item">
                            <div class="function-name">${index + 1}. ${func.function}</div>
                            <div class="function-stats">
                                <span>平均: ${func.avg_duration_ms.toFixed(2)} ms</span>
                                <span>调用: ${func.call_count} 次</span>
                                <span>错误: ${func.error_count} 次</span>
                            </div>
                        </div>
                    `;
                });
            } else {
                slowestDiv.innerHTML = '<div class="empty-state">暂无数据</div>';
            }
        }
    } catch (error) {
        console.error('加载性能数据失败:', error);
    }
}

// 加载健康报告
async function loadHealth() {
    try {
        const response = await fetch('/api/health');
        const result = await response.json();

        if (result.success) {
            const { health_score } = result.data;

            const healthScoreEl = document.getElementById('health-score');
            const healthIconEl = document.getElementById('health-icon');

            healthScoreEl.textContent = health_score;

            // 设置颜色和图标
            const healthConfig = {
                'EXCELLENT': { color: '#48bb78', icon: '💚' },
                'GOOD': { color: '#ed8936', icon: '💛' },
                'WARNING': { color: '#f56565', icon: '🧡' },
                'CRITICAL': { color: '#c53030', icon: '❤️' }
            };

            const config = healthConfig[health_score] || healthConfig['GOOD'];
            healthScoreEl.style.color = config.color;
            healthIconEl.textContent = config.icon;
        }
    } catch (error) {
        console.error('加载健康报告失败:', error);
    }
}

// 加载最近事件
async function loadRecentEvents() {
    try {
        const response = await fetch('/api/recent_events');
        const result = await response.json();

        if (result.success) {
            const events = result.data;
            const eventsListDiv = document.getElementById('events-list');

            if (events.length > 0) {
                eventsListDiv.innerHTML = '';
                events.reverse().forEach(event => {
                    const eventDiv = document.createElement('div');
                    eventDiv.className = 'event-item';

                    const time = new Date(event.timestamp).toLocaleString('zh-CN');
                    const flow = event.target_region
                        ? `${event.source_region} → ${event.target_region}`
                        : event.source_region;

                    eventDiv.innerHTML = `
                        <div class="event-info">
                            <div class="event-type">${getEventTypeEmoji(event.event_type)} ${event.event_type}</div>
                            <div class="event-details">${flow}</div>
                        </div>
                        <div class="event-time">${time}</div>
                    `;

                    eventsListDiv.appendChild(eventDiv);
                });
            } else {
                eventsListDiv.innerHTML = '<div class="empty-state">暂无事件</div>';
            }
        }
    } catch (error) {
        console.error('加载最近事件失败:', error);
    }
}

// 加载反馈统计
async function loadFeedbackStats() {
    try {
        const response = await fetch('/api/feedback_stats');
        const result = await response.json();

        if (result.success) {
            const { stats, summary } = result.data;

            // 更新列表
            const listDiv = document.getElementById('feedback-list');
            if (stats.length > 0) {
                listDiv.innerHTML = '';
                // Show latest first
                [...stats].reverse().forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'event-item';
                    const time = new Date(item.timestamp).toLocaleString('zh-CN');
                    const effectiveness = (item.effectiveness * 100).toFixed(0);
                    const color = effectiveness > 80 ? '#48bb78' : (effectiveness > 50 ? '#ed8936' : '#f56565');

                    div.innerHTML = `
                        <div class="event-info">
                            <div class="event-type">🎯 Effectiveness: <span style="color:${color}">${effectiveness}%</span></div>
                            <div class="event-details">Facts: ${item.facts_extracted} | Triples: ${item.triples_extracted}</div>
                        </div>
                        <div class="event-time">${time}</div>
                    `;
                    listDiv.appendChild(div);
                });
            } else {
                listDiv.innerHTML = '<div class="empty-state">暂无反馈数据</div>';
            }

            // 更新图表
            updateFeedbackChart(stats);
        }
    } catch (error) {
        console.error('加载反馈统计失败:', error);
    }
}

// 初始化图表
function initCharts() {
    // 容量图表
    const capacityCtx = document.getElementById('capacity-chart').getContext('2d');
    capacityChart = new Chart(capacityCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: '当前记忆数',
                data: [],
                backgroundColor: Object.values(regionColors),
                borderColor: Object.values(regionColors),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#a0aec0'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#a0aec0'
                    }
                }
            }
        }
    });

    // 反馈图表
    const feedbackCtx = document.getElementById('feedback-chart').getContext('2d');
    window.feedbackChart = new Chart(feedbackCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Effectiveness',
                data: [],
                borderColor: '#00f3ff',
                backgroundColor: 'rgba(0, 243, 255, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 1.0,
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: '#a0aec0' }
                },
                x: {
                    grid: { display: false },
                    ticks: { display: false } // Hide timestamps to avoid clutter
                }
            }
        }
    });

    // 流向图 (ECharts)
    flowChart = echarts.init(document.getElementById('flow-chart'));
}

// 更新反馈图表
function updateFeedbackChart(stats) {
    if (!window.feedbackChart) return;

    const labels = stats.map(s => new Date(s.timestamp).toLocaleTimeString());
    const data = stats.map(s => s.effectiveness);

    window.feedbackChart.data.labels = labels;
    window.feedbackChart.data.datasets[0].data = data;
    window.feedbackChart.update();
}

// 更新容量图表
function updateCapacityChart(regions) {
    const labels = regions.map(r => r.name_cn || r.name.split()[0]);
    const data = regions.map(r => r.current_count);
    const colors = regions.map(r => regionColors[r.id] || '#667eea');

    capacityChart.data.labels = labels;
    capacityChart.data.datasets[0].data = data;
    capacityChart.data.datasets[0].backgroundColor = colors;
    capacityChart.data.datasets[0].borderColor = colors;
    capacityChart.update();
}

// 更新流向图
function updateFlowChart(flows) {
    const nodes = [
        { name: 'hippocampus', category: 0, symbolSize: 60 },
        { name: 'temporal_lobe', category: 1, symbolSize: 60 },
        { name: 'prefrontal', category: 2, symbolSize: 50 },
        { name: 'amygdala', category: 3, symbolSize: 50 },
        { name: 'basal_ganglia', category: 4, symbolSize: 50 },
    ];

    const links = flows.map(flow => ({
        source: flow.source,
        target: flow.target,
        value: flow.count,
        lineStyle: {
            width: Math.max(1, flow.count / 5)
        }
    }));

    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            formatter: function (params) {
                if (params.dataType === 'edge') {
                    return `${params.data.source} → ${params.data.target}<br/>数量: ${params.data.value}`;
                }
                return params.name;
            }
        },
        series: [{
            type: 'graph',
            layout: 'force',
            data: nodes,
            links: links,
            categories: [
                { name: 'Hippocampus', itemStyle: { color: regionColors.hippocampus } },
                { name: 'Temporal Lobe', itemStyle: { color: regionColors.temporal_lobe } },
                { name: 'Prefrontal', itemStyle: { color: regionColors.prefrontal } },
                { name: 'Amygdala', itemStyle: { color: regionColors.amygdala } },
                { name: 'Basal Ganglia', itemStyle: { color: regionColors.basal_ganglia } }
            ],
            roam: true,
            label: {
                show: true,
                position: 'right',
                formatter: '{b}',
                color: '#e2e8f0'
            },
            lineStyle: {
                color: 'source',
                curveness: 0.3
            },
            emphasis: {
                focus: 'adjacency',
                lineStyle: {
                    width: 10
                }
            },
            force: {
                repulsion: 200,
                edgeLength: 150
            }
        }]
    };

    flowChart.setOption(option);
}

// 更新时间
function updateTime() {
    const now = new Date().toLocaleString('zh-CN');
    document.getElementById('update-time').textContent = `最后更新: ${now}`;
}

// 自动刷新


function toggleAutoRefresh() {
    autoRefresh = !autoRefresh;
    const btn = document.getElementById('auto-refresh-btn');

    if (autoRefresh) {
        btn.textContent = '⏸️ 暂停自动刷新';
        btn.className = 'btn btn-secondary';
    } else {
        btn.textContent = '▶️ 开启自动刷新';
        btn.className = 'btn btn-primary';
    }
}

// 工具函数
function adjustColor(color, percent) {
    const num = parseInt(color.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = (num >> 16) + amt;
    const G = (num >> 8 & 0x00FF) + amt;
    const B = (num & 0x0000FF) + amt;
    return '#' + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
        (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
        (B < 255 ? B < 1 ? 0 : B : 255))
        .toString(16).slice(1);
}

function getEventTypeEmoji(type) {
    const emojis = {
        'consolidation': '🔄',
        'emotion_tagging': '💭',
        'retrieval': '🔍',
        'storage': '💾'
    };
    return emojis[type] || '📌';
}
