import { useState, useCallback } from 'react';
import { generateTitle } from '../utils/formatters';

const STORAGE_KEY = 'yaoguang_conversations';
const MAX_CONVERSATIONS = 100;

function loadConversations() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveConversations(convos) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(convos.slice(0, MAX_CONVERSATIONS)));
  } catch {
    // localStorage full - trim older conversations
    localStorage.setItem(STORAGE_KEY, JSON.stringify(convos.slice(0, 50)));
  }
}

export function useConversations() {
  const [conversations, setConversations] = useState(() => loadConversations());
  const [activeId, setActiveId] = useState(null);

  const persist = useCallback((convos) => {
    setConversations(convos);
    saveConversations(convos);
  }, []);

  const createConversation = useCallback(() => {
    const id = crypto.randomUUID();
    const newConvo = {
      id,
      title: 'New Conversation',
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    const updated = [newConvo, ...conversations];
    persist(updated);
    setActiveId(id);
    return id;
  }, [conversations, persist]);

  const switchConversation = useCallback((id) => {
    setActiveId(id);
  }, []);

  const deleteConversation = useCallback((id) => {
    const updated = conversations.filter((c) => c.id !== id);
    persist(updated);
    if (activeId === id) {
      setActiveId(updated.length > 0 ? updated[0].id : null);
    }
  }, [conversations, activeId, persist]);

  const updateMessages = useCallback((id, messages) => {
    const updated = conversations.map((c) => {
      if (c.id !== id) return c;
      const title = c.title === 'New Conversation' && messages.length > 0
        ? generateTitle(messages.find((m) => m.type === 'user')?.text)
        : c.title;
      return { ...c, messages, title, updatedAt: new Date().toISOString() };
    });
    persist(updated);
  }, [conversations, persist]);

  const activeConversation = conversations.find((c) => c.id === activeId) || null;

  const clearHistory = useCallback(() => {
    persist([]);
    setActiveId(null);
  }, [persist]);

  return {
    conversations,
    activeId,
    activeConversation,
    createConversation,
    switchConversation,
    deleteConversation,
    updateMessages,
    clearHistory,
  };
}
