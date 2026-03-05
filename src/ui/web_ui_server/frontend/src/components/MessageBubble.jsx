import { useState } from 'react';
import { User, Brain, Copy, Check } from 'lucide-react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import clsx from 'clsx';

export function MessageBubble({ message }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.type === 'user';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        'flex gap-4 group',
        isUser ? 'flex-row-reverse' : ''
      )}
    >
      {/* Avatar */}
      <div
        className={clsx(
          'w-8 h-8 rounded-sm flex items-center justify-center flex-shrink-0 mt-1',
          isUser
            ? 'bg-foreground text-background'
            : message.isError
              ? 'bg-red-500 text-white'
              : 'bg-emerald-600 text-white'
        )}
      >
        {isUser ? <User size={16} /> : <Brain size={16} />}
      </div>

      {/* Content */}
      <div
        className={clsx(
          'flex-1 max-w-[85%] relative',
          isUser ? 'text-right' : 'text-left'
        )}
      >
        {/* Name label */}
        <div className="font-semibold text-xs text-secondary mb-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {isUser ? 'You' : 'Yaoguang'}
        </div>

        {/* Message body */}
        <div
          className={clsx(
            message.isError && 'text-red-400',
          )}
        >
          {isUser ? (
            <div className="prose prose-invert prose-sm max-w-none text-gray-200 text-sm leading-7">
              {message.text}
            </div>
          ) : (
            <div className="prose-chat max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
              >
                {message.text}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Copy button (AI messages only) */}
        {!isUser && !message.isError && (
          <button
            onClick={handleCopy}
            className="absolute -bottom-6 left-0 opacity-0 group-hover:opacity-100 transition-opacity text-muted hover:text-foreground p-1 rounded"
            title="Copy message"
          >
            {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
          </button>
        )}

        {/* Processing time on hover */}
        {message.processingTime && (
          <div className="mt-2 text-[10px] text-muted opacity-0 group-hover:opacity-50 transition-opacity">
            Processed in {(message.processingTime * 1000).toFixed(0)}ms
          </div>
        )}
      </div>
    </motion.div>
  );
}
