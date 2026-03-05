import { motion } from 'framer-motion';
import { Brain, WifiOff, Clock } from 'lucide-react';

/**
 * ThinkingIndicator — shows processing status with clear distinction between:
 *   1. Normal inference (brain_status updates arriving) → elapsed timer
 *   2. Network disconnected (WebSocket closed) → red network error
 *   3. Stale connection (connected but no activity for too long) → orange warning
 */
export function ThinkingIndicator({ stages = [], elapsed = 0, silentSeconds = 0, isConnected = true }) {
  const latestStage = stages.length > 0 ? stages[stages.length - 1] : null;

  // Determine status category
  const isNetworkDown = !isConnected;
  // Connected but no brain_status for >30s = possibly stale
  const isStale = isConnected && silentSeconds > 30;
  // Active inference: connected and recent activity
  const isActiveInference = isConnected && silentSeconds <= 30;

  const formatTime = (s) => {
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return `${m}m${rem > 0 ? ` ${rem}s` : ''}`;
  };

  return (
    <div className="flex gap-4">
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-sm flex items-center justify-center flex-shrink-0 mt-1 ${
        isNetworkDown ? 'bg-red-600' : isStale ? 'bg-orange-500' : 'bg-emerald-600'
      } text-white`}>
        {isNetworkDown ? <WifiOff size={16} /> : <Brain size={16} />}
      </div>

      {/* Content */}
      <div className="flex-1 text-sm py-2 space-y-1.5">
        {/* Row 1: dots + stage + timer */}
        <div className="flex items-center gap-3">
          {/* Bouncing dots (only when actively processing) */}
          {!isNetworkDown && (
            <div className="flex items-center gap-1">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className={`w-2 h-2 rounded-full ${isStale ? 'bg-orange-400' : 'bg-emerald-400'}`}
                  animate={{ y: [0, -6, 0] }}
                  transition={{
                    duration: 0.6,
                    repeat: Infinity,
                    delay: i * 0.15,
                    ease: 'easeInOut',
                  }}
                />
              ))}
            </div>
          )}

          {/* Stage text */}
          {latestStage && !isNetworkDown && (
            <motion.span
              key={latestStage}
              initial={{ opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
              className="text-xs text-muted truncate max-w-[280px]"
            >
              {latestStage}
            </motion.span>
          )}

          {/* Elapsed time (always show after 3s) */}
          {elapsed >= 3 && (
            <span className="text-xs text-muted/60 ml-auto tabular-nums flex items-center gap-1">
              <Clock size={10} />
              {formatTime(elapsed)}
            </span>
          )}
        </div>

        {/* Row 2: Status hint based on category */}
        {isNetworkDown && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-xs text-red-400 flex items-center gap-1.5"
          >
            <WifiOff size={12} />
            Network disconnected. Reconnecting...
          </motion.div>
        )}

        {isStale && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-xs text-orange-400"
          >
            {silentSeconds >= 60
              ? 'No response for over a minute. Network may be unstable.'
              : `No server activity for ${formatTime(silentSeconds)}. Waiting...`}
          </motion.div>
        )}

        {isActiveInference && elapsed >= 10 && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-xs text-muted/50"
          >
            Processing — brain agents are working on your request
          </motion.div>
        )}
      </div>
    </div>
  );
}
