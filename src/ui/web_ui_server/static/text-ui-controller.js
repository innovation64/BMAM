/**
 * Pro Text UI Controller for BMAM
 * Handles dashboard logic, memory management, and visualization
 */

document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const messagesContainer = document.getElementById('chat-history');
    const inputEl = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const exportBtn = document.getElementById('export-btn');
    const importBtn = document.getElementById('import-btn');
    const fileInput = document.getElementById('file-input');
    const memoryCountEl = document.getElementById('memory-count');
    const reasoningTraceEl = document.getElementById('reasoning-trace');
    const connectionStatus = document.getElementById('connection-status');

    let ws = null;
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 5;

    // --- WebSocket Logic ---

    function initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('Connected to BMAM Server');
            reconnectAttempts = 0;
            connectionStatus.style.color = 'var(--primary-cyan)';
            connectionStatus.textContent = '● Connected';
            updateStats(); // Fetch initial stats
        };

        ws.onclose = () => {
            console.log('Disconnected');
            connectionStatus.style.color = 'var(--secondary-pink)';
            connectionStatus.textContent = '● Disconnected';

            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                reconnectAttempts++;
                setTimeout(initWebSocket, 2000 * reconnectAttempts);
            }
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleMessage(data);
            } catch (e) {
                console.error('Error parsing message:', e);
            }
        };
    }

    function handleMessage(data) {
        switch (data.type) {
            case 'response':
                // Handle full result if available
                if (data.full_result) {
                    visualizeReasoning(data.full_result);
                }
                addMessage(data.text, 'system');
                updateStats(); // Refresh stats after interaction
                break;
            case 'connected':
                break;
            default:
                console.log('Received:', data);
        }
    }

    // --- UI Functions ---

    function addMessage(text, type) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${type}`;

        const contentDiv = document.createElement('div');
        contentDiv.textContent = text;

        const timeDiv = document.createElement('div');
        timeDiv.style.fontSize = '0.7rem';
        timeDiv.style.opacity = '0.5';
        timeDiv.style.marginTop = '5px';
        timeDiv.style.textAlign = 'right';
        timeDiv.textContent = new Date().toLocaleTimeString();

        msgDiv.appendChild(contentDiv);
        msgDiv.appendChild(timeDiv);

        messagesContainer.appendChild(msgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function visualizeReasoning(result) {
        reasoningTraceEl.innerHTML = ''; // Clear previous trace

        // Extract trace from result (adjust based on actual result structure)
        // Assuming result has 'trace', 'steps', or similar
        const steps = result.steps || result.trace || [];

        if (steps.length === 0) {
            reasoningTraceEl.innerHTML = '<div style="opacity:0.5">No detailed trace available.</div>';
            return;
        }

        steps.forEach((step, index) => {
            const item = document.createElement('div');
            item.className = 'trace-item';
            item.style.animationDelay = `${index * 0.1}s`;

            const header = document.createElement('div');
            header.className = 'trace-header';
            header.textContent = step.agent || step.phase || `Step ${index + 1}`;

            const content = document.createElement('div');
            content.className = 'trace-content';
            content.textContent = step.content || step.description || JSON.stringify(step);

            item.appendChild(header);
            item.appendChild(content);
            reasoningTraceEl.appendChild(item);
        });
    }

    function sendMessage() {
        const text = inputEl.value.trim();
        if (!text) return;

        if (!ws || ws.readyState !== WebSocket.OPEN) {
            addMessage('Error: Not connected to server', 'system');
            return;
        }

        addMessage(text, 'user');
        ws.send(JSON.stringify({
            type: 'text_input',
            text: text
        }));

        inputEl.value = '';

        // Clear previous reasoning trace to show new activity starting
        reasoningTraceEl.innerHTML = '<div style="opacity:0.5">Thinking...</div>';
    }

    // --- Memory Management ---

    async function updateStats() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            if (data.ui_state && data.ui_state.memory_count !== undefined) {
                memoryCountEl.textContent = data.ui_state.memory_count;
            }
        } catch (e) {
            console.error('Failed to fetch stats:', e);
        }
    }

    async function exportMemories() {
        try {
            exportBtn.textContent = '⏳ Exporting...';
            const response = await fetch('/api/memory/export');

            if (response.ok) {
                // 服务器返回 .bma.tar.gz 文件
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `bmam_soul_${new Date().toISOString().slice(0, 10)}.bma.tar.gz`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                exportBtn.textContent = '✅ Exported';
            } else {
                const data = await response.json();
                alert('Export failed: ' + (data.error || 'Unknown error'));
                exportBtn.textContent = '❌ Failed';
            }
        } catch (e) {
            console.error('Export error:', e);
            exportBtn.textContent = '❌ Error';
        }

        setTimeout(() => exportBtn.textContent = '⬇️ Export Soul', 2000);
    }

    async function importMemories(file) {
        if (!file) return;

        // 验证文件格式
        if (!file.name.endsWith('.bma.tar.gz') && !file.name.endsWith('.tar.gz')) {
            alert('Please select a .bma.tar.gz archive file');
            return;
        }

        try {
            importBtn.textContent = '⏳ Importing...';

            // 使用 FormData 上传文件
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/api/memory/import', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                alert(result.message);
                importBtn.textContent = '✅ Imported';
                updateStats();
            } else {
                alert('Import failed: ' + result.error);
                importBtn.textContent = '❌ Failed';
            }
        } catch (e) {
            console.error('Import error:', e);
            alert('Invalid file format');
            importBtn.textContent = '❌ Error';
        }

        setTimeout(() => importBtn.textContent = '⬆️ Import JSON', 2000);
        fileInput.value = ''; // Reset input
    }

    // --- Event Listeners ---

    sendBtn.addEventListener('click', sendMessage);
    inputEl.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    exportBtn.addEventListener('click', exportMemories);

    importBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            importMemories(e.target.files[0]);
        }
    });

    // Start
    initWebSocket();
});
