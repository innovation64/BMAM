import { motion } from 'framer-motion';

const REGIONS = [
    { id: 'prefrontal', label: 'Prefrontal Cortex', x: 50, y: 15, color: '#60a5fa' }, // Blue
    { id: 'hippocampus', label: 'Hippocampus', x: 50, y: 50, color: '#f472b6' },   // Pink
    { id: 'temporal_lobe', label: 'Temporal Lobe', x: 20, y: 40, color: '#4ade80' }, // Green
    { id: 'amygdala', label: 'Amygdala', x: 70, y: 60, color: '#f87171' },        // Red
    { id: 'basal_ganglia', label: 'Basal Ganglia', x: 50, y: 80, color: '#fbbf24' } // Yellow
];

// Connections (simple schematic)
const LINKS = [
    ['prefrontal', 'hippocampus'],
    ['prefrontal', 'basal_ganglia'],
    ['hippocampus', 'temporal_lobe'],
    ['hippocampus', 'amygdala'],
    ['amygdala', 'basal_ganglia']
];

export function BrainRegionMap({ activeRegions }) {
    return (
        <div className="relative w-full h-[400px] bg-black/20 rounded-xl overflow-hidden backdrop-blur-sm border border-white/5">
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-20">
                {/* Background Grid or Decor */}
                <div className="w-[300px] h-[300px] border border-white/10 rounded-full" />
                <div className="absolute w-[200px] h-[200px] border border-white/10 rounded-full" />
            </div>

            {/* Links */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none">
                {LINKS.map(([startName, endName], i) => {
                    const start = REGIONS.find(r => r.id === startName);
                    const end = REGIONS.find(r => r.id === endName);
                    const isActive = activeRegions[startName] && activeRegions[endName];
                    return (
                        <motion.line
                            key={i}
                            x1={`${start.x}%`}
                            y1={`${start.y}%`}
                            x2={`${end.x}%`}
                            y2={`${end.y}%`}
                            stroke={isActive ? start.color : "rgba(255,255,255,0.1)"}
                            strokeWidth={isActive ? 2 : 1}
                            initial={{ pathLength: 0 }}
                            animate={{ pathLength: 1, opacity: isActive ? 1 : 0.2 }}
                            transition={{ duration: 1 }}
                        />
                    );
                })}
            </svg>

            {/* Nodes */}
            {REGIONS.map(region => {
                const isActive = !!activeRegions[region.id];
                return (
                    <div
                        key={region.id}
                        className="absolute transform -translate-x-1/2 -translate-y-1/2 flex flex-col items-center group cursor-pointer"
                        style={{ left: `${region.x}%`, top: `${region.y}%` }}
                    >
                        <motion.div
                            className={`w-12 h-12 rounded-full flex items-center justify-center border-2 shadow-[0_0_15px_rgba(0,0,0,0.5)] transition-colors duration-300 relative z-10`}
                            style={{
                                backgroundColor: isActive ? region.color : 'rgba(255,255,255,0.05)',
                                borderColor: isActive ? '#fff' : 'rgba(255,255,255,0.2)'
                            }}
                            animate={{
                                scale: isActive ? [1, 1.2, 1] : 1,
                                boxShadow: isActive ? `0 0 30px ${region.color}` : '0 0 0 rgba(0,0,0,0)'
                            }}
                            transition={{ repeat: isActive ? Infinity : 0, duration: 2 }}
                        >
                            <span className="text-xl">{getEmoji(region.id)}</span>
                        </motion.div>

                        <motion.span
                            className="mt-2 text-xs font-bold uppercase tracking-wider text-center"
                            style={{ color: isActive ? region.color : 'rgba(255,255,255,0.4)' }}
                        >
                            {region.label}
                        </motion.span>
                    </div>
                );
            })}

            {/* Legend / Status */}
            <div className="absolute bottom-4 right-4 text-xs text-muted">
                System Status: <span className="text-secondary">ACTIVE</span>
            </div>
        </div>
    );
}

function getEmoji(id) {
    const emojis = {
        prefrontal: '🎯',
        hippocampus: '🧠',
        temporal_lobe: '📚',
        amygdala: '❤️',
        basal_ganglia: '⚙️'
    };
    return emojis[id] || '•';
}
