import { useState, useEffect, useRef } from 'react';
import { X, Download, Upload, Trash2, Wifi, WifiOff } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export function SettingsModal({ isOpen, onClose, stats, isConnected, onClearHistory }) {
  const [status, setStatus] = useState(null);
  const dismissTimer = useRef(null);

  // Auto-dismiss status messages after 4 seconds
  useEffect(() => {
    if (status && status.type !== 'info') {
      clearTimeout(dismissTimer.current);
      dismissTimer.current = setTimeout(() => setStatus(null), 4000);
    }
    return () => clearTimeout(dismissTimer.current);
  }, [status]);

  const handleExport = async () => {
    try {
      setStatus({ type: 'info', text: 'Exporting memories...' });
      const archiveName = `ui_export_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}`;
      const resp = await fetch('/v1/archives/export/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ archive_name: archiveName }),
      });
      if (!resp.ok) throw new Error('Export failed');
      const data = await resp.json();
      if (data.success) {
        const path = data.details?.archive_path || data.details?.path || '';
        setStatus({ type: 'success', text: `Memory exported: ${path || 'success'}` });
      } else {
        throw new Error(data.message || 'Export failed');
      }
    } catch (e) {
      setStatus({ type: 'error', text: `Export failed: ${e.message}` });
    }
  };

  const handleImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setStatus({ type: 'info', text: 'Importing memories...' });
      const formData = new FormData();
      formData.append('file', file);
      const resp = await fetch('/v1/archives/upload/', {
        method: 'POST',
        body: formData,
      });
      if (!resp.ok) throw new Error('Import failed');
      const data = await resp.json();
      if (data.success) {
        setStatus({ type: 'success', text: 'Memory imported successfully' });
      } else {
        throw new Error(data.message || 'Import failed');
      }
    } catch (err) {
      setStatus({ type: 'error', text: `Import failed: ${err.message}` });
    }
    e.target.value = '';
  };

  const handleClearHistory = () => {
    onClearHistory();
    setStatus({ type: 'success', text: 'Conversation history cleared' });
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.96 }}
          className="w-full max-w-md bg-surface border border-border rounded-xl shadow-2xl overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <h2 className="text-sm font-semibold text-foreground">Settings</h2>
            <button onClick={onClose} className="text-muted hover:text-foreground transition-colors">
              <X size={18} />
            </button>
          </div>

          <div className="p-5 space-y-5">
            {/* System Info */}
            <div className="space-y-3">
              <h3 className="text-xs font-medium text-muted uppercase tracking-wider">System</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-secondary">Connection</span>
                  <span className="flex items-center gap-1.5">
                    {isConnected
                      ? <><Wifi size={14} className="text-emerald-400" /> <span className="text-emerald-400">Connected</span></>
                      : <><WifiOff size={14} className="text-red-400" /> <span className="text-red-400">Disconnected</span></>
                    }
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-secondary">Memory Count</span>
                  <span className="text-foreground">{stats?.totalMemories || 0}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-secondary">Active Regions</span>
                  <span className="text-foreground">{stats?.activeRegions || 0}</span>
                </div>
              </div>
            </div>

            {/* Memory Management */}
            <div className="space-y-3">
              <h3 className="text-xs font-medium text-muted uppercase tracking-wider">Memory</h3>
              <div className="space-y-2">
                <button
                  onClick={handleExport}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-secondary hover:text-foreground hover:bg-surface-hover border border-border hover:border-white/20 transition-all"
                >
                  <Download size={16} />
                  <span>Export Memory</span>
                </button>
                <label className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-secondary hover:text-foreground hover:bg-surface-hover border border-border hover:border-white/20 transition-all cursor-pointer">
                  <Upload size={16} />
                  <span>Import Memory</span>
                  <input type="file" accept=".tar.gz,.bma.tar.gz" onChange={handleImport} className="hidden" />
                </label>
              </div>
            </div>

            {/* Danger Zone */}
            <div className="space-y-3">
              <h3 className="text-xs font-medium text-muted uppercase tracking-wider">Data</h3>
              <button
                onClick={handleClearHistory}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 border border-red-500/20 hover:border-red-500/40 transition-all"
              >
                <Trash2 size={16} />
                <span>Clear Conversation History</span>
              </button>
            </div>

            {/* Status feedback */}
            {status && (
              <div className={`text-xs px-3 py-2 rounded-lg ${
                status.type === 'success' ? 'bg-emerald-500/10 text-emerald-400' :
                status.type === 'error' ? 'bg-red-500/10 text-red-400' :
                'bg-blue-500/10 text-blue-400'
              }`}>
                {status.text}
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
