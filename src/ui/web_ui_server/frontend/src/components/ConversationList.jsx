import { Trash2, MessageSquare } from 'lucide-react';
import clsx from 'clsx';
import { formatRelativeTime } from '../utils/formatters';

export function ConversationList({ conversations, activeId, onSwitch, onDelete }) {
  if (conversations.length === 0) {
    return (
      <div className="px-3 py-8 text-center text-xs text-muted">
        No conversations yet
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin space-y-0.5 px-1">
      {conversations.map((convo) => (
        <button
          key={convo.id}
          onClick={() => onSwitch(convo.id)}
          className={clsx(
            'w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 group text-left',
            convo.id === activeId
              ? 'bg-surface-hover text-foreground'
              : 'text-secondary hover:text-foreground hover:bg-surface-hover/50'
          )}
        >
          <MessageSquare size={14} className="flex-shrink-0 text-muted" />
          <div className="flex-1 min-w-0">
            <div className="truncate text-[13px]">{convo.title}</div>
            <div className="text-[10px] text-muted truncate">
              {formatRelativeTime(convo.updatedAt)}
            </div>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(convo.id);
            }}
            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 hover:text-red-400 transition-all flex-shrink-0"
            title="Delete conversation"
          >
            <Trash2 size={13} />
          </button>
        </button>
      ))}
    </div>
  );
}
