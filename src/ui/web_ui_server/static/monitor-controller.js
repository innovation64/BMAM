/**
 * Monitor UI Controller
 * Handles real-time data updates for the system monitor
 */

class MonitorController {
    constructor() {
        this.ws = null;
        this.charts = {};
        this.maxDataPoints = 50;
        this.updateInterval = null;
    }

    init() {
        console.log('Initializing Monitor Controller...');
        this.initCharts();
        this.connectWebSocket();
        this.startMockDataSimulation(); // Fallback if no real data
    }

    connectWebSocket() {
        this.ws = new WebSocket('ws://localhost:8080/ws');

        this.ws.onopen = () => {
            console.log('✅ Monitor connected to server');
            this.addLog('System', 'Connected to BrainService', 'info');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleDataUpdate(data);
        };

        this.ws.onclose = () => {
            console.log('❌ Monitor disconnected');
            this.addLog('System', 'Connection lost. Reconnecting...', 'warn');
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    }

    initCharts() {
        // Activity Chart
        const ctx = document.getElementById('activity-chart').getContext('2d');
        this.charts.activity = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array(20).fill(''),
                datasets: [{
                    label: 'Memory Access',
                    data: Array(20).fill(0),
                    borderColor: '#7d5fff',
                    backgroundColor: 'rgba(125, 95, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Reasoning Load',
                    data: Array(20).fill(0),
                    borderColor: '#00e6ff',
                    backgroundColor: 'rgba(0, 230, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                plugins: {
                    legend: {
                        labels: { color: '#a0a0b0' }
                    }
                },
                scales: {
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#a0a0b0' },
                        beginAtZero: true,
                        min: 0,
                        max: 100,
                        suggestedMax: 100
                    },
                    x: {
                        grid: { display: false },
                        ticks: { display: false }
                    }
                }
            }
        });
    }

    handleDataUpdate(data) {
        // Update stats
        if (data.stats) {
            this.updateStat('active-agents', data.stats.active_agents);
            this.updateStat('memory-count', data.stats.memory_count);
            this.updateStat('system-load', data.stats.system_load + '%');
        }

        // Update charts
        if (data.metrics) {
            this.updateChart(this.charts.activity, [
                data.metrics.memory_access,
                data.metrics.reasoning_load
            ]);
        }

        // Add logs
        if (data.log) {
            this.addLog(data.log.source, data.log.message, data.log.level);
        }
    }

    updateStat(id, value) {
        const el = document.getElementById(id);
        if (el && value !== undefined) {
            el.textContent = value;
        }
    }

    updateChart(chart, newValues) {
        if (!chart) return;

        // Shift old data
        chart.data.datasets.forEach((dataset, i) => {
            const val = newValues[i] !== undefined ? newValues[i] : 0;
            dataset.data.push(val);
            if (dataset.data.length > 20) {
                dataset.data.shift();
            }
        });

        chart.update();
    }

    addLog(source, message, level = 'info') {
        const container = document.getElementById('log-stream');
        if (!container) return;

        const entry = document.createElement('div');
        entry.className = 'log-entry';

        const time = new Date().toLocaleTimeString('en-GB');
        const colorClass = level === 'error' ? 'log-error' : (level === 'warn' ? 'log-warn' : 'log-info');

        entry.innerHTML = `<span class="log-time">[${time}]</span> <span class="${colorClass}">${source}: ${message}</span>`;

        container.insertBefore(entry, container.firstChild);

        // Limit logs
        if (container.children.length > 50) {
            container.removeChild(container.lastChild);
        }
    }

    // Simulate data if backend isn't sending enough
    startMockDataSimulation() {
        setInterval(() => {
            const memoryLoad = 20 + Math.random() * 30;
            const reasoningLoad = 10 + Math.random() * 40;

            this.updateChart(this.charts.activity, [memoryLoad, reasoningLoad]);

            // Random logs
            if (Math.random() > 0.7) {
                const sources = ['Hippocampus', 'Amygdala', 'Prefrontal', 'Thalamus'];
                const actions = ['Consolidating memory', 'Processing emotion', 'Planning response', 'Routing signal'];
                const source = sources[Math.floor(Math.random() * sources.length)];
                const action = actions[Math.floor(Math.random() * actions.length)];
                this.addLog(source, action, 'info');
            }
        }, 1000);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.monitor = new MonitorController();
    window.monitor.init();
});
