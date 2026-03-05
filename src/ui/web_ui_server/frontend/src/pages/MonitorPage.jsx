
import { useState, useEffect } from 'react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import { Activity, Database, Cpu, Heart } from 'lucide-react';

const BRAIN_REGIONS = [
    { id: 'hippocampus', name: 'Hippocampus', type: 'episodic' },
    { id: 'temporal_lobe', name: 'Temporal Lobe', type: 'semantic' },
    { id: 'amygdala', name: 'Amygdala', type: 'emotional' },
    { id: 'prefrontal', name: 'Prefrontal', type: 'working' },
    { id: 'basal_ganglia', name: 'Basal Ganglia', type: 'procedural' },
];

function buildRegionsFromStats(statsData) {
    const total = statsData.total_memories || 0;
    const episodic = statsData.episodic_memories || 0;
    const semantic = statsData.semantic_memories || 0;
    const other = Math.max(0, total - episodic - semantic);

    return BRAIN_REGIONS.map(region => {
        let count = 0;
        const capacity = 10000;
        if (region.type === 'episodic') count = episodic;
        else if (region.type === 'semantic') count = semantic;
        else count = Math.round(other / 3);
        return { ...region, current_count: count, capacity };
    });
}

export function MonitorPage() {
    const [stats, setStats] = useState(null);
    const [healthData, setHealthData] = useState(null);
    const [history, setHistory] = useState([]);
    const [fetchError, setFetchError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [statsRes, healthRes] = await Promise.all([
                    fetch('/v1/system/stats'),
                    fetch('/v1/system/health'),
                ]);
                const statsData = await statsRes.json();
                const healthRaw = await healthRes.json();

                const regions = buildRegionsFromStats(statsData);
                const activeRegions = regions.filter(r => r.current_count > 0).length;

                setStats({
                    summary: {
                        total_memories: statsData.total_memories || 0,
                        active_regions: activeRegions,
                    },
                    regions,
                });

                setHealthData({
                    status: healthRaw.status || 'unknown',
                    health_percentage: healthRaw.health_percentage || 0,
                    features: healthRaw.features || {},
                    degraded_features: healthRaw.degraded_features || [],
                });

                setHistory(prev => {
                    const newPoint = {
                        time: new Date().toLocaleTimeString(),
                        active: activeRegions,
                        memories: statsData.total_memories || 0,
                        intensity: healthRaw.health_percentage ? healthRaw.health_percentage / 100 : 0,
                    };
                    const newHist = [...prev, newPoint];
                    return newHist.slice(-20);
                });
                setFetchError(null);
            } catch (e) {
                console.error("Monitor fetch error", e);
                setFetchError('Failed to fetch system data');
            }
        };

        const interval = setInterval(fetchData, 5000);
        fetchData();
        return () => clearInterval(interval);
    }, []);

    if (!stats || !healthData) return (
        <div className="p-10 text-center space-y-4">
            <div className="text-white/50 animate-pulse">Initializing Neural Interface...</div>
            {fetchError && <div className="text-red-400 text-sm">{fetchError}</div>}
        </div>
    );

    // Build radar data from real feature health status
    const features = healthData.features || {};
    const featureMapping = {
        'Hippocampus': ['episodic_storage', 'hippocampus'],
        'Temporal': ['semantic_memory', 'temporal_lobe', 'knowledge_graph'],
        'Amygdala': ['salience_scoring', 'amygdala'],
        'Prefrontal': ['working_memory', 'prefrontal'],
        'Basal G.': ['procedural_memory', 'basal_ganglia'],
    };
    const radarData = Object.entries(featureMapping).map(([subject, keys]) => {
        const matchedKey = keys.find(k => k in features);
        const healthy = matchedKey ? features[matchedKey] === true : null;
        return { subject, A: healthy === true ? 0.9 : healthy === false ? 0.3 : 0.5, fullMark: 1.0 };
    });

    return (
        <div className="h-full overflow-y-auto p-6 space-y-6 scrollbar-thin">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-blue-500">
                        System Monitor
                    </h1>
                    <div className="text-xs text-white/50 font-mono">Real-time Neural Telemetry</div>
                </div>
                <div className="flex gap-4">
                    <StatusBadge label="System Health" status={healthData.status.toUpperCase()} color={healthData.status === 'healthy' ? 'bg-green-500' : healthData.status === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'} />
                    <StatusBadge label="Health %" status={`${healthData.health_percentage.toFixed(0)}%`} color="bg-purple-500" />
                </div>
            </div>

            {/* Top Grid - Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <MetricCard
                    label="Total Memories"
                    value={stats.summary.total_memories.toLocaleString()}
                    icon={<Database size={16} />}
                />
                <MetricCard
                    label="Active Regions"
                    value={`${stats.summary.active_regions} / ${stats.regions.length}`}
                    icon={<Activity size={16} />}
                    color="text-green-400"
                />
                <MetricCard
                    label="Health Score"
                    value={`${healthData.health_percentage.toFixed(0)}%`}
                    icon={<Heart size={16} />}
                    color="text-red-400"
                />
                <MetricCard
                    label="Degraded Features"
                    value={healthData.degraded_features.length.toString()}
                    icon={<Cpu size={16} />}
                    color={healthData.degraded_features.length > 0 ? "text-yellow-400" : "text-blue-400"}
                />
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[300px]">
                {/* Main Activity Graph */}
                <div className="glass-panel p-4 rounded-xl flex flex-col">
                    <h3 className="text-sm font-bold text-white/70 mb-4">Neural Activity History</h3>
                    <div className="flex-1 min-h-0">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={history}>
                                <defs>
                                    <linearGradient id="colorIntensity" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8} />
                                        <stop offset="95%" stopColor="#8884d8" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                                <XAxis dataKey="time" stroke="#ffffff50" tick={{ fontSize: 10 }} interval={4} />
                                <YAxis stroke="#ffffff50" tick={{ fontSize: 10 }} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#000000dd', border: '1px solid #333', borderRadius: '8px' }}
                                    itemStyle={{ color: '#fff' }}
                                />
                                <Area type="monotone" dataKey="intensity" stroke="#8884d8" fillOpacity={1} fill="url(#colorIntensity)" />
                                <Line type="monotone" dataKey="active" stroke="#82ca9d" strokeWidth={2} dot={false} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Soul Radar & Stats */}
                <div className="glass-panel p-4 rounded-xl flex flex-col">
                    <h3 className="text-sm font-bold text-white/70 mb-4">Soul Architecture Weights</h3>
                    <div className="flex-1 min-h-0">
                        <ResponsiveContainer width="100%" height="100%">
                            <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                                <PolarGrid stroke="#ffffff20" />
                                <PolarAngleAxis dataKey="subject" tick={{ fill: '#ffffff80', fontSize: 11 }} />
                                <PolarRadiusAxis angle={30} domain={[0, 1.0]} tick={false} axisLine={false} />
                                <Radar name="Soul" dataKey="A" stroke="#8884d8" fill="#8884d8" fillOpacity={0.6} />
                            </RadarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Detailed Region List */}
            <div className="glass-panel p-4 rounded-xl">
                <h3 className="text-sm font-bold text-white/70 mb-4">Regional Memory Status</h3>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    {stats.regions.map(region => (
                        <div key={region.id} className="bg-white/5 rounded-lg p-3 border border-white/5">
                            <div className="text-xs text-white/50 uppercase mb-1">{region.name}</div>
                            <div className="text-sm font-bold">{region.current_count} <span className="text-[10px] font-normal text-white/30">/ {region.capacity}</span></div>
                            <div className="w-full bg-white/10 h-1 mt-2 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-blue-500 rounded-full"
                                    style={{ width: `${Math.min(100, Math.max(5, (region.current_count / region.capacity) * 100))}%` }}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

function MetricCard({ label, value, icon, color = "text-white", trend }) {
    return (
        <div className="glass-panel p-4 rounded-xl flex items-center justify-between">
            <div>
                <div className="text-xs text-white/50 mb-1">{label}</div>
                <div className={`text-xl font-bold font-mono ${color}`}>{value}</div>
            </div>
            <div className="text-right">
                <div className={`p-2 rounded-lg bg-white/5 ${color}`}>{icon}</div>
                {trend && <div className="text-[10px] text-green-400 mt-1">{trend}</div>}
            </div>
        </div>
    );
}

function StatusBadge({ label, status, color }) {
    return (
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10">
            <span className="text-xs text-white/50">{label}:</span>
            <span className="flex items-center gap-1.5 font-bold text-sm">
                <span className={`w-2 h-2 rounded-full ${color} animate-pulse`} />
                {status}
            </span>
        </div>
    );
}
