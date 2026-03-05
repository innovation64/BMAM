import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { BrainRegionMap } from './components/BrainRegionMap';
import { ChatInterface } from './components/ChatInterface';
import { MemorySearchModal } from './components/MemorySearchModal';
import { SettingsModal } from './components/SettingsModal';
import { VoicePage } from './pages/VoicePage';
import { MonitorPage } from './pages/MonitorPage';
import { MemoryPage } from './pages/MemoryPage';
import { SoulProvider, useSoul } from './contexts/SoulContext';
import { useConversations } from './hooks/useConversations';
import { motion, AnimatePresence } from 'framer-motion';
import { useState, useEffect, useCallback, useRef } from 'react';
import { Activity, ChevronRight, Menu } from 'lucide-react';

function AppContent() {
  const soul = useSoul();
  const convos = useConversations();
  const navigate = useNavigate();

  const [showInspector, setShowInspector] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Debounced sync: messages -> active conversation in localStorage
  const syncTimer = useRef(null);
  useEffect(() => {
    if (convos.activeId && soul.messages.length > 0) {
      clearTimeout(syncTimer.current);
      syncTimer.current = setTimeout(() => {
        convos.updateMessages(convos.activeId, soul.messages);
      }, 300);
    }
    return () => clearTimeout(syncTimer.current);
  }, [soul.messages]);

  // When switching conversations, load messages and navigate to chat
  const handleSwitchConversation = useCallback((id) => {
    convos.switchConversation(id);
    const convo = convos.conversations.find((c) => c.id === id);
    if (convo) {
      soul.setMessages(convo.messages || []);
    }
    setSidebarOpen(false);
    navigate('/');
  }, [convos, soul, navigate]);

  // New chat: create conversation and clear messages
  const handleNewChat = useCallback(() => {
    convos.createConversation();
    soul.clearMessages();
    setSidebarOpen(false);
    navigate('/');
  }, [convos, soul, navigate]);

  // On send: ensure there's an active conversation
  const handleSendMessage = useCallback((text) => {
    if (!convos.activeId) {
      convos.createConversation();
    }
    soul.sendMessage(text);
  }, [convos, soul]);

  // Cmd+K keyboard shortcut
  useEffect(() => {
    const handleKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, []);

  return (
    <div className="flex w-screen h-screen bg-background text-foreground overflow-hidden font-sans selection:bg-white/10">

      {/* Mobile hamburger */}
      <button
        onClick={() => setSidebarOpen(true)}
        className="fixed top-3 left-3 z-30 p-2 rounded-lg bg-surface/80 border border-border text-muted hover:text-foreground transition-colors md:hidden"
      >
        <Menu size={18} />
      </button>

      {/* Sidebar */}
      <Sidebar
        conversations={convos.conversations}
        activeId={convos.activeId}
        onNewChat={handleNewChat}
        onSwitchConversation={handleSwitchConversation}
        onDeleteConversation={convos.deleteConversation}
        onOpenSearch={() => setSearchOpen(true)}
        onOpenSettings={() => setSettingsOpen(true)}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col relative h-full min-w-0 transition-all duration-300">
        <Routes>
          <Route path="/" element={
            <div className="flex h-full w-full">
              {/* Central Chat */}
              <div className="flex-1 flex flex-col h-full max-w-4xl mx-auto w-full relative">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-accent/20 to-transparent z-20 pointer-events-none" />

                <ChatInterface
                  messages={soul.messages}
                  onSendMessage={handleSendMessage}
                  isThinking={soul.isThinking}
                  isConnected={soul.isConnected}
                  thinkingStages={soul.thinkingStages}
                  thinkingElapsed={soul.thinkingElapsed}
                  silentSeconds={soul.silentSeconds}
                  voice={soul.voice}
                />
              </div>

              {/* Inspector Drawer (opt-in) */}
              <AnimatePresence mode="wait">
                {showInspector && (
                  <motion.div
                    initial={{ width: 0, opacity: 0 }}
                    animate={{ width: 320, opacity: 1 }}
                    exit={{ width: 0, opacity: 0 }}
                    className="h-full border-l border-border bg-surface/30 backdrop-blur-sm flex flex-col overflow-hidden hidden md:flex"
                  >
                    <div className="p-4 border-b border-border flex items-center justify-between">
                      <span className="text-xs font-medium text-secondary tracking-wider uppercase">Neural Inspector</span>
                      <button onClick={() => setShowInspector(false)} className="text-muted hover:text-foreground transition-colors">
                        <ChevronRight size={16} />
                      </button>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin">
                      <div className="space-y-2">
                        <div className="text-[10px] text-muted font-mono uppercase">Activity Map</div>
                        <div className="h-48 rounded-lg overflow-hidden border border-border/50 bg-black/20 relative">
                          <BrainRegionMap activeRegions={soul.brainRegions} />
                        </div>
                      </div>

                      <div className="space-y-2">
                        <div className="text-[10px] text-muted font-mono uppercase">Reasoning Stream</div>
                        <div className="space-y-3">
                          {soul.reasoningChain.slice(-5).map((step, i) => (
                            <div key={i} className="text-xs space-y-1 group">
                              <div className="flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-accent/50 group-hover:bg-accent transition-colors" />
                                <span className="font-medium text-secondary">{step.agent}</span>
                              </div>
                              <p className="text-muted pl-3.5 border-l border-border group-hover:border-accent/30 transition-colors leading-relaxed">
                                {step.description || step.text}
                              </p>
                            </div>
                          ))}
                          {soul.reasoningChain.length === 0 && (
                            <div className="text-xs text-muted/50 italic py-4 text-center">System awaiting input...</div>
                          )}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Toggle Button for Inspector */}
              {!showInspector && (
                <button
                  onClick={() => setShowInspector(true)}
                  className="absolute top-4 right-4 p-2 text-muted hover:text-foreground transition-colors bg-surface/50 rounded-lg border border-border hover:bg-surface hidden md:block"
                >
                  <Activity size={18} />
                </button>
              )}
            </div>
          } />

          <Route path="/voice" element={<VoicePage />} />
          <Route path="/monitor" element={<MonitorPage />} />
          <Route path="/memories" element={<MemoryPage />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </div>

      {/* Modals */}
      <MemorySearchModal
        isOpen={searchOpen}
        onClose={() => setSearchOpen(false)}
        searchMemories={soul.searchMemories}
      />
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        stats={soul.stats}
        isConnected={soul.isConnected}
        onClearHistory={convos.clearHistory}
      />
    </div>
  );
}

function App() {
  return (
    <Router>
      <SoulProvider>
        <AppContent />
      </SoulProvider>
    </Router>
  );
}

export default App;
