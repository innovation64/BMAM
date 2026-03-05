import { useEffect, useRef, useState, useCallback } from 'react';
import { Send, Mic, MicOff } from 'lucide-react';
import { AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { MessageBubble } from './MessageBubble';
import { ThinkingIndicator } from './ThinkingIndicator';
import { WelcomeScreen } from './WelcomeScreen';

export function ChatInterface({ messages, onSendMessage, isThinking, isConnected, thinkingStages, thinkingElapsed, silentSeconds, voice }) {
    const [input, setInput] = useState('');
    const endRef = useRef(null);
    const textareaRef = useRef(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isThinking]);

    const resizeTextarea = useCallback(() => {
        const el = textareaRef.current;
        if (!el) return;
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 200) + 'px';
    }, []);

    useEffect(() => {
        resizeTextarea();
    }, [input, resizeTextarea]);

    const handleSubmit = () => {
        if (!input.trim() || isThinking) return;
        onSendMessage(input);
        setInput('');
        // Reset textarea height
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const handleSuggestion = (text) => {
        onSendMessage(text);
    };

    // Voice input: when recording, show partial transcript in textarea
    useEffect(() => {
        if (voice?.isRecording && voice?.partialTranscript) {
            setInput(voice.partialTranscript);
        }
    }, [voice?.partialTranscript, voice?.isRecording]);

    if (messages.length === 0 && !isThinking) {
        return (
            <div className="flex flex-col h-full overflow-hidden relative">
                <WelcomeScreen onSend={handleSuggestion} />

                {/* Input Area */}
                <InputArea
                    input={input}
                    setInput={setInput}
                    textareaRef={textareaRef}
                    isThinking={isThinking}
                    onKeyDown={handleKeyDown}
                    onSubmit={handleSubmit}
                    voice={voice}
                />
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full overflow-hidden relative">
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto w-full scrollbar-thin">
                <div className="max-w-3xl mx-auto py-8 px-4 space-y-6">
                    <AnimatePresence initial={false}>
                        {messages.map((msg) => (
                            <MessageBubble key={msg.id} message={msg} />
                        ))}
                    </AnimatePresence>

                    {isThinking && (
                        <ThinkingIndicator
                          stages={thinkingStages}
                          elapsed={thinkingElapsed}
                          silentSeconds={silentSeconds}
                          isConnected={isConnected}
                        />
                    )}

                    <div ref={endRef} className="h-4" />
                </div>
            </div>

            {/* Input Area */}
            <InputArea
                input={input}
                setInput={setInput}
                textareaRef={textareaRef}
                isThinking={isThinking}
                onKeyDown={handleKeyDown}
                onSubmit={handleSubmit}
                voice={voice}
            />
        </div>
    );
}

function InputArea({ input, setInput, textareaRef, isThinking, onKeyDown, onSubmit, voice }) {
    const handleMicClick = () => {
        if (!voice) return;
        if (voice.isRecording) {
            voice.stopRecording();
        } else {
            voice.startRecording();
        }
    };

    return (
        <div className="w-full pb-6 pt-2 px-4 bg-gradient-to-t from-background via-background to-transparent z-10">
            <div className="max-w-3xl mx-auto">
                <div className="relative bg-surface border border-white/10 rounded-xl shadow-lg focus-within:border-white/20 focus-within:shadow-xl transition-all overflow-hidden">
                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={onKeyDown}
                        placeholder={voice?.isRecording ? 'Listening...' : 'Send a message...'}
                        rows={1}
                        className="w-full bg-transparent border-none py-3 pl-4 pr-20 text-sm text-white placeholder:text-muted focus:ring-0 focus:outline-none resize-none max-h-[200px] scrollbar-thin"
                    />
                    <div className="absolute right-2 bottom-2 flex items-center gap-1">
                        {/* Mic button */}
                        {voice && (
                            <button
                                type="button"
                                onClick={handleMicClick}
                                className={clsx(
                                    'p-1.5 rounded-md transition-all duration-200',
                                    voice.isRecording
                                        ? 'bg-red-500 text-white animate-pulse'
                                        : 'bg-transparent text-muted hover:text-white'
                                )}
                                title={voice.isRecording ? 'Stop voice input' : 'Voice input'}
                            >
                                {voice.isRecording ? <MicOff size={14} /> : <Mic size={14} />}
                            </button>
                        )}
                        {/* Send button */}
                        <button
                            type="button"
                            onClick={onSubmit}
                            disabled={!input.trim() || isThinking}
                            className={clsx(
                                'p-1.5 rounded-md transition-all duration-200',
                                input.trim() && !isThinking
                                    ? 'bg-emerald-500 text-white hover:bg-emerald-600'
                                    : 'bg-transparent text-muted cursor-not-allowed'
                            )}
                        >
                            <Send size={14} />
                        </button>
                    </div>
                </div>
                <div className="text-center text-[10px] text-muted mt-2">
                    Yaoguang can make mistakes. Consider checking important information.
                </div>
            </div>
        </div>
    );
}
