import { useState, useEffect, useRef, useCallback } from 'react';
import { Search, X, Brain } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { formatRelativeTime } from '../utils/formatters';

const REGION_COLORS = {
  hippocampus: 'bg-blue-500/20 text-blue-300',
  temporal_lobe: 'bg-purple-500/20 text-purple-300',
  amygdala: 'bg-red-500/20 text-red-300',
  prefrontal: 'bg-amber-500/20 text-amber-300',
  basal_ganglia: 'bg-emerald-500/20 text-emerald-300',
};

export function MemorySearchModal({ isOpen, onClose, searchMemories }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const inputRef = useRef(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setResults([]);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose]);

  const handleSearch = useCallback((q) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!q.trim()) {
      setResults([]);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setIsSearching(true);
      const data = await searchMemories(q);
      setResults(data || []);
      setIsSearching(false);
    }, 300);
  }, [searchMemories]);

  const handleInputChange = (e) => {
    const val = e.target.value;
    setQuery(val);
    handleSearch(val);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-start justify-center pt-[15vh]"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.96 }}
          className="w-full max-w-xl bg-surface border border-border rounded-xl shadow-2xl overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Search input */}
          <div className="flex items-center gap-3 px-4 border-b border-border">
            <Search size={18} className="text-muted flex-shrink-0" />
            <input
              ref={inputRef}
              value={query}
              onChange={handleInputChange}
              placeholder="Search memories..."
              className="flex-1 bg-transparent py-4 text-sm text-white placeholder:text-muted focus:outline-none"
            />
            <button onClick={onClose} className="text-muted hover:text-foreground transition-colors">
              <X size={18} />
            </button>
          </div>

          {/* Results */}
          <div className="max-h-[50vh] overflow-y-auto scrollbar-thin">
            {isSearching && (
              <div className="px-4 py-6 text-center text-xs text-muted">Searching...</div>
            )}

            {!isSearching && query && results.length === 0 && (
              <div className="px-4 py-6 text-center text-xs text-muted">No memories found</div>
            )}

            {!isSearching && results.map((item, i) => (
              <div
                key={i}
                className="px-4 py-3 border-b border-border/50 last:border-0 hover:bg-surface-hover/30 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <Brain size={14} className="text-muted mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-200 line-clamp-3">
                      {item.content || item.text || JSON.stringify(item)}
                    </p>
                    <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                      {item.source_region && (
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${REGION_COLORS[item.source_region] || 'bg-white/10 text-gray-400'}`}>
                          {item.source_region}
                        </span>
                      )}
                      {item.importance != null && (
                        <span className="text-[10px] text-muted">
                          importance: {typeof item.importance === 'number' ? item.importance.toFixed(2) : item.importance}
                        </span>
                      )}
                      {item.relevance_score != null && (
                        <span className="text-[10px] text-emerald-400">
                          relevance: {typeof item.relevance_score === 'number' ? item.relevance_score.toFixed(2) : item.relevance_score}
                        </span>
                      )}
                      {item.timestamp && (
                        <span className="text-[10px] text-muted">
                          {formatRelativeTime(item.timestamp)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {!query && !isSearching && (
              <div className="px-4 py-8 text-center text-xs text-muted">
                Type to search through stored memories
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
