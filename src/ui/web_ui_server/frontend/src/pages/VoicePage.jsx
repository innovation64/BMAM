import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, Square } from 'lucide-react';
import { useSoul } from '../contexts/SoulContext';

export function VoicePage() {
    const {
        isConnected,
        messages,
        isThinking,
        thinkingStages,
        voice,
    } = useSoul();

    const {
        isRecording,
        isSpeaking,
        isSystemSpeaking,
        partialTranscript,
        startRecording,
        stopRecording,
        bargeIn,
    } = voice;

    // Derive overall state for visual feedback
    const state = isSystemSpeaking
        ? 'speaking'
        : isThinking
            ? 'thinking'
            : isSpeaking
                ? 'listening'
                : isRecording
                    ? 'ready'
                    : 'idle';

    const lastResponse = messages.filter((m) => m.type === 'system').slice(-1)[0];
    const lastThinkingStage = thinkingStages.length > 0
        ? thinkingStages[thinkingStages.length - 1]
        : null;

    const handleMicClick = () => {
        if (isSystemSpeaking) {
            // Barge-in: interrupt system speech
            bargeIn();
            return;
        }
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    };

    return (
        <div className="flex flex-col items-center justify-center h-full relative overflow-hidden">
            {/* Background atmosphere */}
            <div className="absolute inset-0 bg-gradient-to-b from-transparent to-purple-900/20 pointer-events-none" />

            {/* Connection status */}
            {!isConnected && (
                <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30 px-4 py-2 bg-red-500/80 rounded-full text-sm text-white">
                    Reconnecting...
                </div>
            )}

            {/* Avatar with VAD-driven visual feedback */}
            <div className="relative z-10 mb-16">
                <VoiceOrb state={state} />
            </div>

            {/* Status / Transcript / Response */}
            <div className="z-10 text-center space-y-4 max-w-lg w-full px-4">
                {/* Partial transcript (real-time as user speaks) */}
                <AnimatePresence mode="wait">
                    {partialTranscript && (isRecording || isSpeaking) && (
                        <motion.div
                            key="partial"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="bg-black/30 backdrop-blur-md rounded-xl p-4 text-white/90 border border-white/10"
                        >
                            <span className="text-xs text-muted mr-2">You:</span>
                            {partialTranscript}
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Thinking stage */}
                {isThinking && lastThinkingStage && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="text-sm text-muted animate-pulse"
                    >
                        {lastThinkingStage}
                    </motion.div>
                )}

                {/* Latest response */}
                <AnimatePresence>
                    {lastResponse && !isRecording && !isThinking && (
                        <motion.div
                            key={lastResponse.id}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="bg-primary/20 backdrop-blur-md rounded-xl p-4 text-primary-100 border border-primary/30 max-h-48 overflow-y-auto text-sm leading-relaxed"
                        >
                            {lastResponse.text}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Mic button */}
            <div className="absolute bottom-12 z-20">
                <button
                    onClick={handleMicClick}
                    disabled={!isConnected}
                    aria-label={
                        isSystemSpeaking ? 'Interrupt' :
                        isRecording ? 'Stop recording' : 'Start recording'
                    }
                    className={`p-6 rounded-full transition-all duration-300 shadow-xl border-2 ${
                        isSystemSpeaking
                            ? 'bg-orange-500 border-orange-400 hover:bg-orange-600'
                            : isRecording
                                ? 'bg-red-500 border-red-400 animate-pulse scale-110'
                                : 'bg-primary border-primary-400 hover:scale-105'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                    {isSystemSpeaking ? (
                        <Square size={32} className="text-white" />
                    ) : isRecording ? (
                        <MicOff size={32} className="text-white" />
                    ) : (
                        <Mic size={32} className="text-white" />
                    )}
                </button>

                {/* State label */}
                <div className="text-center mt-3 text-xs text-muted">
                    {isSystemSpeaking
                        ? 'Tap to interrupt'
                        : isRecording
                            ? isSpeaking ? 'Listening...' : 'Tap to stop'
                            : 'Tap to speak'}
                </div>
            </div>
        </div>
    );
}

/**
 * Animated orb with state-driven visual feedback.
 */
function VoiceOrb({ state }) {
    const ringColors = {
        idle: 'border-white/10',
        ready: 'border-cyan-500/30',
        listening: 'border-cyan-400/60',
        thinking: 'border-yellow-400/50',
        speaking: 'border-pink-400/60',
    };

    const glowColors = {
        idle: '',
        ready: 'shadow-[0_0_20px_rgba(0,200,255,0.15)]',
        listening: 'shadow-[0_0_50px_rgba(0,255,255,0.4)]',
        thinking: 'shadow-[0_0_40px_rgba(255,200,0,0.3)]',
        speaking: 'shadow-[0_0_50px_rgba(255,100,255,0.4)]',
    };

    const innerColors = {
        idle: 'bg-white/5',
        ready: 'bg-cyan-500/5',
        listening: 'bg-cyan-500/10',
        thinking: 'bg-yellow-500/10',
        speaking: 'bg-pink-500/10',
    };

    return (
        <div className="relative w-64 h-64 flex items-center justify-center">
            {/* Pulsing ring (VAD active) */}
            {(state === 'listening' || state === 'speaking') && (
                <motion.div
                    className={`absolute inset-0 border-2 rounded-full ${ringColors[state]}`}
                    animate={{ scale: [1, 1.15, 1], opacity: [0.4, 0.1, 0.4] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                />
            )}

            {/* Outer ring */}
            <div
                className={`w-48 h-48 rounded-full border-4 ${ringColors[state]} ${glowColors[state]} ${innerColors[state]} flex items-center justify-center transition-all duration-500`}
            >
                {/* Inner icon */}
                <div className="text-5xl">
                    {state === 'idle' && '\u{1F399}\u{FE0F}'}
                    {state === 'ready' && '\u{1F3A4}'}
                    {state === 'listening' && '\u{1F442}'}
                    {state === 'thinking' && '\u{1F9E0}'}
                    {state === 'speaking' && '\u{1F5E3}\u{FE0F}'}
                </div>
            </div>
        </div>
    );
}
