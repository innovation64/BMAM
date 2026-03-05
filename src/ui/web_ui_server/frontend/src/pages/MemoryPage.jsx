import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Plus, Trash2, Edit3, X, ChevronLeft, ChevronRight, LayoutGrid, List, Brain } from 'lucide-react';

const MEMORY_TYPES = ['all', 'episodic', 'semantic', 'procedural', 'working'];
const BRAIN_REGIONS = ['all', 'hippocampus', 'temporal_lobe', 'amygdala', 'prefrontal', 'basal_ganglia'];

export function MemoryPage() {
    const [memories, setMemories] = useState([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize] = useState(20);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState(null);
    const [typeFilter, setTypeFilter] = useState('all');
    const [regionFilter, setRegionFilter] = useState('all');
    const [viewMode, setViewMode] = useState('card');
    const [editingMemory, setEditingMemory] = useState(null);
    const [showAddModal, setShowAddModal] = useState(false);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(null);
    const [error, setError] = useState(null);

    // Reset to page 1 when filters change
    useEffect(() => { setPage(1); }, [typeFilter, regionFilter]);

    const fetchMemories = useCallback(async () => {
        setLoading(true);
        try {
            const resp = await fetch(`/v1/memories/?page=${page}&page_size=${pageSize}`);
            const data = await resp.json();
            let items = data.memories || [];
            // Client-side filtering
            if (typeFilter !== 'all') {
                items = items.filter(m => m.memory_type === typeFilter);
            }
            if (regionFilter !== 'all') {
                items = items.filter(m => m.brain_region === regionFilter);
            }
            setMemories(items);
            setTotal(data.total || 0);
        } catch (e) {
            console.error('Failed to fetch memories:', e);
            setError('Failed to load memories');
        }
        setLoading(false);
    }, [page, pageSize, typeFilter, regionFilter]);

    useEffect(() => {
        if (!searchResults) {
            fetchMemories();
        }
    }, [fetchMemories, searchResults]);

    const handleSearch = async () => {
        if (!searchQuery.trim()) {
            setSearchResults(null);
            return;
        }
        setLoading(true);
        try {
            const resp = await fetch('/v1/memories/search/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: searchQuery, limit: 50 }),
            });
            const data = await resp.json();
            setSearchResults(data.results || []);
        } catch (e) {
            console.error('Search failed:', e);
            setError('Search failed');
        }
        setLoading(false);
    };

    const handleClearSearch = () => {
        setSearchQuery('');
        setSearchResults(null);
    };

    const handleDelete = async (id) => {
        try {
            const resp = await fetch(`/v1/memories/${id}`, { method: 'DELETE' });
            if (!resp.ok) throw new Error('Delete failed');
            setShowDeleteConfirm(null);
            setError(null);
            if (searchResults) {
                setSearchResults(searchResults.filter(m => m.id !== id));
            } else {
                fetchMemories();
            }
        } catch (e) {
            console.error('Delete failed:', e);
            setError('Failed to delete memory');
        }
    };

    const handleUpdate = async (id, updates) => {
        try {
            const resp = await fetch(`/v1/memories/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates),
            });
            if (!resp.ok) throw new Error('Update failed');
            setEditingMemory(null);
            setError(null);
            fetchMemories();
        } catch (e) {
            console.error('Update failed:', e);
            setError('Failed to update memory');
        }
    };

    const handleAdd = async (content, memoryType, importance) => {
        try {
            const resp = await fetch('/v1/memories/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content, memory_type: memoryType, importance }),
            });
            if (!resp.ok) throw new Error('Add failed');
            setShowAddModal(false);
            setError(null);
            fetchMemories();
        } catch (e) {
            console.error('Add failed:', e);
            setError('Failed to add memory');
        }
    };

    const displayItems = searchResults || memories;
    const totalPages = searchResults ? 1 : Math.ceil(total / pageSize);

    return (
        <div className="h-full overflow-y-auto p-6 space-y-6 scrollbar-thin">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-blue-500">
                        Memory Manager
                    </h1>
                    <div className="text-xs text-white/50 font-mono">{total} memories stored</div>
                </div>
                <button
                    onClick={() => setShowAddModal(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-primary rounded-lg text-sm font-medium hover:bg-primary/80 transition-colors"
                >
                    <Plus size={16} /> Add Memory
                </button>
            </div>

            {/* Search + Filters */}
            <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1 flex gap-2">
                    <div className="flex-1 relative">
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                            placeholder="Search memories..."
                            className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 pl-10 text-sm text-foreground placeholder:text-muted focus:outline-none focus:border-primary/50"
                        />
                        <Search size={16} className="absolute left-3 top-3 text-muted" />
                    </div>
                    {searchResults && (
                        <button onClick={handleClearSearch} className="px-3 py-2 text-sm text-muted hover:text-foreground bg-surface border border-border rounded-lg">
                            Clear
                        </button>
                    )}
                </div>

                <div className="flex gap-2">
                    <select
                        value={typeFilter}
                        onChange={(e) => setTypeFilter(e.target.value)}
                        className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground"
                    >
                        {MEMORY_TYPES.map(t => (
                            <option key={t} value={t}>{t === 'all' ? 'All Types' : t}</option>
                        ))}
                    </select>
                    <select
                        value={regionFilter}
                        onChange={(e) => setRegionFilter(e.target.value)}
                        className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground"
                    >
                        {BRAIN_REGIONS.map(r => (
                            <option key={r} value={r}>{r === 'all' ? 'All Regions' : r.replace('_', ' ')}</option>
                        ))}
                    </select>
                    <div className="flex rounded-lg border border-border overflow-hidden">
                        <button
                            onClick={() => setViewMode('card')}
                            className={`p-2 ${viewMode === 'card' ? 'bg-primary/20 text-primary' : 'bg-surface text-muted hover:text-foreground'}`}
                        >
                            <LayoutGrid size={16} />
                        </button>
                        <button
                            onClick={() => setViewMode('list')}
                            className={`p-2 ${viewMode === 'list' ? 'bg-primary/20 text-primary' : 'bg-surface text-muted hover:text-foreground'}`}
                        >
                            <List size={16} />
                        </button>
                    </div>
                </div>
            </div>

            {/* Error Banner */}
            {error && (
                <div className="flex items-center justify-between bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2 text-sm text-red-400">
                    <span>{error}</span>
                    <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 ml-4">
                        <X size={14} />
                    </button>
                </div>
            )}

            {/* Content */}
            {loading ? (
                <div className="text-center py-20 text-white/50 animate-pulse">Loading memories...</div>
            ) : displayItems.length === 0 ? (
                <div className="text-center py-20 text-white/30">
                    {searchResults ? 'No results found.' : 'No memories stored yet.'}
                </div>
            ) : viewMode === 'card' ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {displayItems.map(m => (
                        <MemoryCard
                            key={m.id}
                            memory={m}
                            onEdit={() => setEditingMemory(m)}
                            onDelete={() => setShowDeleteConfirm(m.id)}
                        />
                    ))}
                </div>
            ) : (
                <div className="space-y-2">
                    {displayItems.map(m => (
                        <MemoryRow
                            key={m.id}
                            memory={m}
                            onEdit={() => setEditingMemory(m)}
                            onDelete={() => setShowDeleteConfirm(m.id)}
                        />
                    ))}
                </div>
            )}

            {/* Pagination */}
            {!searchResults && totalPages > 1 && (
                <div className="flex items-center justify-center gap-4 pt-4">
                    <button
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                        className="p-2 rounded-lg bg-surface border border-border text-muted hover:text-foreground disabled:opacity-30"
                    >
                        <ChevronLeft size={16} />
                    </button>
                    <span className="text-sm text-secondary">
                        Page {page} of {totalPages}
                    </span>
                    <button
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                        className="p-2 rounded-lg bg-surface border border-border text-muted hover:text-foreground disabled:opacity-30"
                    >
                        <ChevronRight size={16} />
                    </button>
                </div>
            )}

            {/* Edit Modal */}
            <AnimatePresence>
                {editingMemory && (
                    <EditModal
                        memory={editingMemory}
                        onSave={(updates) => handleUpdate(editingMemory.id, updates)}
                        onClose={() => setEditingMemory(null)}
                    />
                )}
            </AnimatePresence>

            {/* Add Modal */}
            <AnimatePresence>
                {showAddModal && (
                    <AddModal
                        onSave={handleAdd}
                        onClose={() => setShowAddModal(false)}
                    />
                )}
            </AnimatePresence>

            {/* Delete Confirm */}
            <AnimatePresence>
                {showDeleteConfirm && (
                    <DeleteConfirmModal
                        onConfirm={() => handleDelete(showDeleteConfirm)}
                        onCancel={() => setShowDeleteConfirm(null)}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}

function MemoryCard({ memory, onEdit, onDelete }) {
    const regionColor = {
        hippocampus: 'border-blue-500/30',
        temporal_lobe: 'border-green-500/30',
        amygdala: 'border-red-500/30',
        prefrontal: 'border-yellow-500/30',
        basal_ganglia: 'border-purple-500/30',
    }[memory.brain_region] || 'border-white/10';

    return (
        <div className={`bg-white/5 rounded-xl p-4 border ${regionColor} hover:bg-white/8 transition-colors group`}>
            <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                    <Brain size={12} className="text-primary/50" />
                    <span className="text-[10px] uppercase text-muted font-mono">{memory.brain_region?.replace('_', ' ')}</span>
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onClick={onEdit} className="p-1 text-muted hover:text-foreground"><Edit3 size={12} /></button>
                    <button onClick={onDelete} className="p-1 text-muted hover:text-red-400"><Trash2 size={12} /></button>
                </div>
            </div>
            <p className="text-sm text-foreground/80 line-clamp-3 mb-3">{memory.content}</p>
            <div className="flex items-center justify-between text-[10px] text-muted">
                <span className="px-1.5 py-0.5 rounded bg-white/5">{memory.memory_type}</span>
                <span>{memory.timestamp ? new Date(memory.timestamp).toLocaleDateString() : ''}</span>
            </div>
            {memory.score != null && (
                <div className="mt-2 text-[10px] text-primary/60">Score: {memory.score.toFixed(3)}</div>
            )}
        </div>
    );
}

function MemoryRow({ memory, onEdit, onDelete }) {
    return (
        <div className="flex items-center gap-4 bg-white/5 rounded-lg p-3 border border-white/5 hover:bg-white/8 transition-colors group">
            <div className="w-24 text-[10px] text-muted uppercase font-mono">{memory.brain_region?.replace('_', ' ')}</div>
            <div className="w-20 text-[10px] text-muted"><span className="px-1.5 py-0.5 rounded bg-white/5">{memory.memory_type}</span></div>
            <div className="flex-1 text-sm text-foreground/80 truncate">{memory.content}</div>
            <div className="text-[10px] text-muted w-24">{memory.timestamp ? new Date(memory.timestamp).toLocaleDateString() : ''}</div>
            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={onEdit} className="p-1 text-muted hover:text-foreground"><Edit3 size={14} /></button>
                <button onClick={onDelete} className="p-1 text-muted hover:text-red-400"><Trash2 size={14} /></button>
            </div>
        </div>
    );
}

function EditModal({ memory, onSave, onClose }) {
    const [content, setContent] = useState(memory.content || '');
    const [importance, setImportance] = useState(memory.importance || 0.5);

    return (
        <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center"
            onClick={onClose}
        >
            <motion.div
                initial={{ scale: 0.96 }} animate={{ scale: 1 }} exit={{ scale: 0.96 }}
                className="w-full max-w-lg bg-surface border border-border rounded-xl p-6 space-y-4"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-foreground">Edit Memory</h3>
                    <button onClick={onClose} className="text-muted hover:text-foreground"><X size={18} /></button>
                </div>
                <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    rows={5}
                    className="w-full bg-black/20 border border-border rounded-lg p-3 text-sm text-foreground resize-none focus:outline-none focus:border-primary/50"
                />
                <div className="flex items-center gap-3">
                    <label className="text-xs text-muted">Importance:</label>
                    <input
                        type="range" min="0" max="1" step="0.1"
                        value={importance}
                        onChange={(e) => setImportance(parseFloat(e.target.value))}
                        className="flex-1"
                    />
                    <span className="text-xs text-foreground w-8">{importance.toFixed(1)}</span>
                </div>
                <div className="flex justify-end gap-2">
                    <button onClick={onClose} className="px-4 py-2 text-sm text-muted hover:text-foreground border border-border rounded-lg">Cancel</button>
                    <button onClick={() => onSave({ content, importance })} className="px-4 py-2 text-sm bg-primary rounded-lg hover:bg-primary/80">Save</button>
                </div>
            </motion.div>
        </motion.div>
    );
}

function AddModal({ onSave, onClose }) {
    const [content, setContent] = useState('');
    const [memoryType, setMemoryType] = useState('episodic');
    const [importance, setImportance] = useState(0.5);

    return (
        <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center"
            onClick={onClose}
        >
            <motion.div
                initial={{ scale: 0.96 }} animate={{ scale: 1 }} exit={{ scale: 0.96 }}
                className="w-full max-w-lg bg-surface border border-border rounded-xl p-6 space-y-4"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-foreground">Add Memory</h3>
                    <button onClick={onClose} className="text-muted hover:text-foreground"><X size={18} /></button>
                </div>
                <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    rows={5}
                    placeholder="Enter memory content..."
                    className="w-full bg-black/20 border border-border rounded-lg p-3 text-sm text-foreground resize-none focus:outline-none focus:border-primary/50 placeholder:text-muted"
                />
                <div className="flex gap-4">
                    <div className="flex-1">
                        <label className="text-xs text-muted block mb-1">Type</label>
                        <select
                            value={memoryType}
                            onChange={(e) => setMemoryType(e.target.value)}
                            className="w-full bg-black/20 border border-border rounded-lg px-3 py-2 text-sm text-foreground"
                        >
                            <option value="episodic">Episodic</option>
                            <option value="semantic">Semantic</option>
                            <option value="procedural">Procedural</option>
                            <option value="working">Working</option>
                        </select>
                    </div>
                    <div className="flex-1">
                        <label className="text-xs text-muted block mb-1">Importance: {importance.toFixed(1)}</label>
                        <input
                            type="range" min="0" max="1" step="0.1"
                            value={importance}
                            onChange={(e) => setImportance(parseFloat(e.target.value))}
                            className="w-full mt-2"
                        />
                    </div>
                </div>
                <div className="flex justify-end gap-2">
                    <button onClick={onClose} className="px-4 py-2 text-sm text-muted hover:text-foreground border border-border rounded-lg">Cancel</button>
                    <button
                        onClick={() => content.trim() && onSave(content, memoryType, importance)}
                        disabled={!content.trim()}
                        className="px-4 py-2 text-sm bg-primary rounded-lg hover:bg-primary/80 disabled:opacity-30"
                    >
                        Add
                    </button>
                </div>
            </motion.div>
        </motion.div>
    );
}

function DeleteConfirmModal({ onConfirm, onCancel }) {
    return (
        <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center"
            onClick={onCancel}
        >
            <motion.div
                initial={{ scale: 0.96 }} animate={{ scale: 1 }} exit={{ scale: 0.96 }}
                className="w-full max-w-sm bg-surface border border-border rounded-xl p-6 space-y-4"
                onClick={(e) => e.stopPropagation()}
            >
                <h3 className="text-sm font-semibold text-foreground">Delete Memory?</h3>
                <p className="text-sm text-secondary">This action cannot be undone. The memory will be permanently removed.</p>
                <div className="flex justify-end gap-2">
                    <button onClick={onCancel} className="px-4 py-2 text-sm text-muted hover:text-foreground border border-border rounded-lg">Cancel</button>
                    <button onClick={onConfirm} className="px-4 py-2 text-sm bg-red-500 text-white rounded-lg hover:bg-red-600">Delete</button>
                </div>
            </motion.div>
        </motion.div>
    );
}
