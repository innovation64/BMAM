/**
 * useVoiceStream — React hook for streaming voice interaction over WebSocket.
 *
 * Handles:
 *   - Microphone capture via AudioWorklet (PCM 16kHz mono)
 *   - Binary WebSocket frames for audio upload
 *   - Voice protocol messages (VAD, partial, transcript, TTS)
 *   - TTS audio playback via Web Audio API
 *   - Barge-in (interrupt system speech)
 */

import { useState, useRef, useCallback, useEffect } from 'react';

export function useVoiceStream(wsRef) {
    const [isRecording, setIsRecording] = useState(false);
    const [isSpeaking, setIsSpeaking] = useState(false);        // VAD: user is speaking
    const [isSystemSpeaking, setIsSystemSpeaking] = useState(false); // TTS playback active
    const [partialTranscript, setPartialTranscript] = useState('');
    const [voiceReady, setVoiceReady] = useState(false);

    const audioContextRef = useRef(null);
    const workletNodeRef = useRef(null);
    const mediaStreamRef = useRef(null);

    // TTS playback
    const playbackContextRef = useRef(null);
    const audioQueueRef = useRef([]);
    const isPlayingRef = useRef(false);
    const nextPlayTimeRef = useRef(0);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            stopRecording();
            if (playbackContextRef.current) {
                playbackContextRef.current.close();
            }
        };
    }, []);

    /**
     * Start recording: getUserMedia → AudioContext (16kHz) → AudioWorklet → WS binary
     */
    const startRecording = useCallback(async () => {
        const ws = wsRef?.current;
        if (!ws || ws.readyState !== WebSocket.OPEN) return;

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 16000,
                },
            });
            mediaStreamRef.current = stream;

            const audioCtx = new AudioContext({ sampleRate: 16000 });
            audioContextRef.current = audioCtx;

            // Load AudioWorklet processor
            await audioCtx.audioWorklet.addModule('/audio-worklet-processor.js');

            const source = audioCtx.createMediaStreamSource(stream);
            const worklet = new AudioWorkletNode(audioCtx, 'pcm-capture-processor');
            workletNodeRef.current = worklet;

            // Forward PCM chunks as binary WebSocket frames
            worklet.port.onmessage = (e) => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send(e.data); // ArrayBuffer → binary frame
                }
            };

            source.connect(worklet);
            // Don't connect worklet to destination — we don't want to hear our own mic

            // Tell server we're starting voice
            ws.send(JSON.stringify({
                type: 'voice_start',
                language: 'auto',
            }));

            setIsRecording(true);
            setPartialTranscript('');
            setVoiceReady(true);
        } catch (err) {
            console.error('Failed to start recording:', err);
        }
    }, [wsRef]);

    /**
     * Stop recording and request final transcription.
     */
    const stopRecording = useCallback(() => {
        if (workletNodeRef.current) {
            workletNodeRef.current.disconnect();
            workletNodeRef.current = null;
        }
        if (audioContextRef.current) {
            audioContextRef.current.close();
            audioContextRef.current = null;
        }
        if (mediaStreamRef.current) {
            mediaStreamRef.current.getTracks().forEach((t) => t.stop());
            mediaStreamRef.current = null;
        }

        const ws = wsRef?.current;
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'voice_stop' }));
        }

        setIsRecording(false);
        setIsSpeaking(false);
    }, [wsRef]);

    /**
     * Barge-in: stop TTS playback and resume recording.
     */
    const bargeIn = useCallback(() => {
        // Stop playback
        if (playbackContextRef.current) {
            playbackContextRef.current.close();
            playbackContextRef.current = null;
        }
        audioQueueRef.current = [];
        isPlayingRef.current = false;
        setIsSystemSpeaking(false);

        // Tell server to cancel TTS
        const ws = wsRef?.current;
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'voice_barge_in' }));
        }
    }, [wsRef]);

    /**
     * Handle incoming voice protocol messages (called from useSoulConnection).
     */
    const handleVoiceMessage = useCallback((data) => {
        switch (data.type) {
            case 'voice_vad':
                setIsSpeaking(!!data.speaking);
                break;
            case 'voice_partial':
                setPartialTranscript(data.text || '');
                break;
            case 'voice_transcript':
                setPartialTranscript(data.text || '');
                break;
            case 'voice_tts_start':
                setIsSystemSpeaking(true);
                // Prepare playback context
                if (!playbackContextRef.current ||
                    playbackContextRef.current.state === 'closed') {
                    playbackContextRef.current = new AudioContext();
                }
                audioQueueRef.current = [];
                nextPlayTimeRef.current = 0;
                break;
            case 'voice_tts_end':
                // Don't immediately set false — wait for audio queue to drain
                setTimeout(() => setIsSystemSpeaking(false), 500);
                break;
            default:
                break;
        }
    }, []);

    /**
     * Handle incoming binary frame (TTS audio from server).
     * Decodes MP3 chunks and queues for seamless playback.
     */
    const handleBinaryMessage = useCallback(async (arrayBuffer) => {
        const ctx = playbackContextRef.current;
        if (!ctx || ctx.state === 'closed') return;

        try {
            const audioBuffer = await ctx.decodeAudioData(arrayBuffer.slice(0));
            const source = ctx.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(ctx.destination);

            const now = ctx.currentTime;
            const startTime = Math.max(now, nextPlayTimeRef.current);
            source.start(startTime);
            nextPlayTimeRef.current = startTime + audioBuffer.duration;
        } catch (err) {
            // MP3 fragments may fail to decode individually — this is expected
            // for chunked streaming. Accumulate and retry.
            audioQueueRef.current.push(new Uint8Array(arrayBuffer));
            tryDecodeAccumulated(ctx);
        }
    }, []);

    /**
     * Try to decode accumulated audio chunks as a single blob.
     */
    const tryDecodeAccumulated = async (ctx) => {
        if (audioQueueRef.current.length < 2) return;

        const totalLen = audioQueueRef.current.reduce((s, a) => s + a.length, 0);
        const merged = new Uint8Array(totalLen);
        let offset = 0;
        for (const chunk of audioQueueRef.current) {
            merged.set(chunk, offset);
            offset += chunk.length;
        }

        try {
            const audioBuffer = await ctx.decodeAudioData(merged.buffer.slice(0));
            audioQueueRef.current = [];

            const source = ctx.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(ctx.destination);

            const now = ctx.currentTime;
            const startTime = Math.max(now, nextPlayTimeRef.current);
            source.start(startTime);
            nextPlayTimeRef.current = startTime + audioBuffer.duration;
        } catch {
            // Still can't decode — wait for more data
        }
    };

    return {
        isRecording,
        isSpeaking,
        isSystemSpeaking,
        partialTranscript,
        voiceReady,
        startRecording,
        stopRecording,
        bargeIn,
        handleVoiceMessage,
        handleBinaryMessage,
    };
}
