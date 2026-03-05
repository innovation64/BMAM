import { useState, useEffect, useRef, useCallback } from 'react';
import { useVoiceStream } from './useVoiceStream';

export function useSoulConnection() {
    const [isConnected, setIsConnected] = useState(false);
    const [messages, setMessages] = useState([]);
    const [brainRegions, setBrainRegions] = useState({});
    const [reasoningChain, setReasoningChain] = useState([]);
    const [retrievedMemories, setRetrievedMemories] = useState([]);
    const [stats, setStats] = useState({ totalMemories: 0, activeRegions: 0 });
    const [isThinking, setIsThinking] = useState(false);
    const [thinkingStages, setThinkingStages] = useState([]);
    const [thinkingElapsed, setThinkingElapsed] = useState(0);
    // Seconds since last brain_status or any server message while thinking
    const [silentSeconds, setSilentSeconds] = useState(0);
    const [voiceAvailable, setVoiceAvailable] = useState(false);

    const ws = useRef(null);
    const reconnectAttempts = useRef(0);
    const reconnectTimer = useRef(null);
    const brainRegionTimer = useRef(null);
    const thinkingTimerRef = useRef(null);
    const thinkingStartRef = useRef(null);
    const lastActivityRef = useRef(null);
    const MAX_RECONNECT = 5;
    const MAX_THINKING_STAGES = 50;

    // Voice streaming hook — shares the same WebSocket
    const voice = useVoiceStream(ws);

    const connect = useCallback(() => {
        // Close previous connection if any
        if (ws.current) {
            try { ws.current.close(); } catch (_) { /* ignore */ }
            ws.current = null;
        }
        // Clear any pending reconnect timer
        if (reconnectTimer.current) {
            clearTimeout(reconnectTimer.current);
            reconnectTimer.current = null;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws`;

        console.log('Connecting to:', wsUrl);
        ws.current = new WebSocket(wsUrl);

        // Use binaryType = 'arraybuffer' for TTS audio chunks
        ws.current.binaryType = 'arraybuffer';

        ws.current.onopen = () => {
            console.log('Connected');
            setIsConnected(true);
            reconnectAttempts.current = 0;
            fetchStats();
        };

        ws.current.onclose = () => {
            console.log('Disconnected');
            const wasThinking = isThinking;
            setIsConnected(false);
            setIsThinking(false);
            // If disconnected while waiting for a response, show network error
            if (wasThinking) {
                addMessage({
                    id: Date.now(),
                    type: 'system',
                    text: 'Network disconnected while waiting for response. Reconnecting...',
                    timestamp: new Date(),
                    isError: true,
                });
            }
            if (reconnectAttempts.current < MAX_RECONNECT) {
                reconnectAttempts.current++;
                reconnectTimer.current = setTimeout(connect, 2000 * reconnectAttempts.current);
            }
        };

        ws.current.onerror = (err) => {
            console.error('WS Error:', err);
        };

        ws.current.onmessage = (event) => {
            // Binary frame → TTS audio
            if (event.data instanceof ArrayBuffer) {
                voice.handleBinaryMessage(event.data);
                return;
            }

            // Text frame → JSON
            try {
                const data = JSON.parse(event.data);
                handleMessage(data);
            } catch (e) {
                console.error('Parse error:', e);
            }
        };
    }, []);

    const handleMessage = (data) => {
        // Voice protocol messages
        if (data.type && data.type.startsWith('voice_')) {
            voice.handleVoiceMessage(data);
            return;
        }

        switch (data.type) {
            case 'connected':
                setVoiceAvailable(!!data.voice_available);
                break;
            case 'response':
                setIsThinking(false);
                setThinkingStages([]);
                addMessage({
                    id: Date.now(),
                    type: 'system',
                    text: data.text,
                    timestamp: new Date(),
                    processingTime: data.full_result?.processing_time
                });
                if (data.full_result) {
                    updateVisualization(data.full_result);
                }
                fetchStats();
                break;
            case 'brain_status':
                lastActivityRef.current = Date.now();
                setThinkingStages(prev => {
                    const stage = data.stage || data.message || data.status;
                    if (!stage) return prev;
                    const next = [...prev, stage];
                    // Cap to prevent unbounded growth
                    return next.length > MAX_THINKING_STAGES
                        ? next.slice(-MAX_THINKING_STAGES)
                        : next;
                });
                break;
            case 'memory_search_result':
                break;
            case 'error':
                setIsThinking(false);
                setThinkingStages([]);
                addMessage({
                    id: Date.now(),
                    type: 'system',
                    text: `Error: ${data.message}`,
                    timestamp: new Date(),
                    isError: true
                });
                break;
            default:
                break;
        }
    };

    const updateVisualization = (result) => {
        if (result.memories_retrieved) {
            setRetrievedMemories(result.memories_retrieved);
        }

        if (result.agents_involved) {
            const newRegions = {};
            result.agents_involved.forEach(agent => {
                const key = normalizeAgentName(agent);
                newRegions[key] = 1.0;
            });
            setBrainRegions(newRegions);
            // Clear previous timer before setting a new one
            if (brainRegionTimer.current) {
                clearTimeout(brainRegionTimer.current);
            }
            brainRegionTimer.current = setTimeout(() => setBrainRegions({}), 3000);
        }

        if (result.reasoning_steps) {
            setReasoningChain(result.reasoning_steps);
        }
    };

    const normalizeAgentName = (name) => {
        const n = name.toLowerCase();
        if (n.includes('hippocampus')) return 'hippocampus';
        if (n.includes('temporal')) return 'temporal_lobe';
        if (n.includes('amygdala')) return 'amygdala';
        if (n.includes('prefrontal')) return 'prefrontal';
        if (n.includes('basal')) return 'basal_ganglia';
        return 'cortex';
    };

    // Elapsed timer: ticks every second while isThinking is true
    // Also tracks silentSeconds = time since last brain_status message
    useEffect(() => {
        if (isThinking) {
            const now = Date.now();
            thinkingStartRef.current = now;
            lastActivityRef.current = now;
            setThinkingElapsed(0);
            setSilentSeconds(0);
            thinkingTimerRef.current = setInterval(() => {
                const now2 = Date.now();
                setThinkingElapsed(Math.floor((now2 - thinkingStartRef.current) / 1000));
                setSilentSeconds(Math.floor((now2 - lastActivityRef.current) / 1000));
            }, 1000);
        } else {
            if (thinkingTimerRef.current) {
                clearInterval(thinkingTimerRef.current);
                thinkingTimerRef.current = null;
            }
            setThinkingElapsed(0);
            setSilentSeconds(0);
        }
        return () => {
            if (thinkingTimerRef.current) clearInterval(thinkingTimerRef.current);
        };
    }, [isThinking]);

    const sendMessage = (text) => {
        if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
            addMessage({
                id: Date.now(),
                type: 'system',
                text: 'Connection lost. Attempting to reconnect...',
                timestamp: new Date(),
                isError: true,
            });
            connect();
            return;
        }

        setIsThinking(true);
        setThinkingStages([]);

        addMessage({
            id: Date.now(),
            type: 'user',
            text: text,
            timestamp: new Date()
        });

        ws.current.send(JSON.stringify({ type: 'text_input', text }));
    };

    const addMessage = (msg) => {
        setMessages(prev => [...prev, msg]);
    };

    const clearMessages = () => {
        setMessages([]);
        setIsThinking(false);
        setThinkingStages([]);
    };

    const fetchStats = async () => {
        try {
            const resp = await fetch('/v1/system/stats');
            const data = await resp.json();
            const total = data.total_memories || 0;
            const episodic = data.episodic_memories || 0;
            const semantic = data.semantic_memories || 0;
            let active = 0;
            if (episodic > 0) active++;
            if (semantic > 0) active++;
            if (total - episodic - semantic > 0) active++;
            setStats({ totalMemories: total, activeRegions: Math.max(active, total > 0 ? 1 : 0) });
        } catch (e) {
            console.warn("Failed to fetch stats", e);
        }
    };

    useEffect(() => {
        connect();
        return () => {
            if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
            if (brainRegionTimer.current) clearTimeout(brainRegionTimer.current);
            if (ws.current) ws.current.close();
        };
    }, [connect]);

    const searchMemories = async (query) => {
        try {
            const resp = await fetch('/v1/memories/search/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, limit: 10 })
            });
            const json = await resp.json();
            return json.results || [];
        } catch (e) {
            console.error("Search failed", e);
            return [];
        }
    };

    return {
        isConnected,
        messages,
        setMessages,
        sendMessage,
        clearMessages,
        brainRegions,
        reasoningChain,
        retrievedMemories,
        stats,
        searchMemories,
        isThinking,
        thinkingStages,
        thinkingElapsed,
        silentSeconds,
        voiceAvailable,
        voice,
    };
}
