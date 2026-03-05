import { Brain, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

const suggestions = [
  'What do you remember about me?',
  'Tell me about your memory architecture',
  'What conversations have we had before?',
  'How does your brain work?',
];

export function WelcomeScreen({ onSend }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="text-center space-y-6 max-w-lg"
      >
        {/* Brain icon */}
        <div className="flex justify-center">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Brain size={32} className="text-white" />
          </div>
        </div>

        {/* Title */}
        <div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">Yaoguang</h1>
          <p className="text-sm text-muted mt-1">Brain-inspired memory for lasting conversations</p>
        </div>

        {/* Suggestion chips */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-8">
          {suggestions.map((text) => (
            <button
              key={text}
              onClick={() => onSend(text)}
              className="text-left px-4 py-3 rounded-xl border border-border hover:border-white/20 bg-surface/50 hover:bg-surface text-sm text-secondary hover:text-foreground transition-all group"
            >
              <div className="flex items-start gap-2">
                <Sparkles size={14} className="mt-0.5 text-muted group-hover:text-emerald-400 transition-colors flex-shrink-0" />
                <span>{text}</span>
              </div>
            </button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
