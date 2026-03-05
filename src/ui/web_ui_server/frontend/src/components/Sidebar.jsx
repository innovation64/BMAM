import { Plus, Search, Mic, Monitor, Settings, X, Brain, Database } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { ConversationList } from './ConversationList';
import clsx from 'clsx';

export function Sidebar({
  conversations,
  activeId,
  onNewChat,
  onSwitchConversation,
  onDeleteConversation,
  onOpenSearch,
  onOpenSettings,
  isOpen,
  onClose,
}) {
  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onClose}
        />
      )}

      <div
        className={clsx(
          'h-full flex flex-col bg-surface border-r border-border transition-transform duration-200 z-50',
          // Mobile: fixed overlay with slide-in
          'fixed md:relative',
          'w-[280px]',
          isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        )}
      >
        {/* Header */}
        <div className="px-3 pt-3 pb-2 flex items-center justify-between">
          <div className="flex items-center gap-2 text-foreground font-semibold tracking-tight px-1">
            <div className="w-6 h-6 rounded bg-emerald-600 text-white flex items-center justify-center">
              <Brain size={14} />
            </div>
            <span>Yaoguang</span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted hover:text-foreground hover:bg-surface-hover transition-colors md:hidden"
          >
            <X size={18} />
          </button>
        </div>

        {/* New Chat button */}
        <div className="px-3 py-2">
          <button
            onClick={onNewChat}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg border border-border hover:border-white/20 text-sm text-secondary hover:text-foreground hover:bg-surface-hover transition-all"
          >
            <Plus size={16} />
            <span>New Chat</span>
          </button>
        </div>

        {/* Conversation list */}
        <ConversationList
          conversations={conversations}
          activeId={activeId}
          onSwitch={onSwitchConversation}
          onDelete={onDeleteConversation}
        />

        {/* Bottom tools */}
        <div className="p-3 border-t border-border space-y-0.5">
          <div className="text-[10px] text-muted uppercase tracking-wider px-3 mb-1">Tools</div>

          <NavButton to="/voice" icon={<Mic size={16} />} label="Voice Mode" />
          <NavButton to="/monitor" icon={<Monitor size={16} />} label="Monitor" />
          <NavButton to="/memories" icon={<Database size={16} />} label="Memory Manager" />

          <button
            onClick={onOpenSearch}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-secondary hover:text-foreground hover:bg-surface-hover transition-all group"
          >
            <Search size={16} />
            <span className="flex-1 text-left">Search Memory</span>
            <kbd className="text-[10px] text-muted bg-surface-hover px-1.5 py-0.5 rounded font-mono hidden sm:inline">
              ⌘K
            </kbd>
          </button>

          <button
            onClick={onOpenSettings}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-secondary hover:text-foreground hover:bg-surface-hover transition-all group"
          >
            <Settings size={16} />
            <span>Settings</span>
          </button>
        </div>
      </div>
    </>
  );
}

function NavButton({ to, icon, label }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        clsx(
          'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-200',
          isActive
            ? 'bg-surface-hover text-foreground font-medium'
            : 'text-secondary hover:text-foreground hover:bg-surface-hover'
        )
      }
    >
      {icon}
      <span>{label}</span>
    </NavLink>
  );
}
