import { useQuery } from "@tanstack/react-query";
import { fetchUserQueuePosition } from "@/api/pipelines";
import { motion, AnimatePresence } from "framer-motion";
import { Clock, Users } from "lucide-react";

interface QueuePositionBannerProps {
  sourceType: 'slack' | 'document';
  className?: string;
}

export function QueuePositionBanner({ sourceType, className = "" }: QueuePositionBannerProps) {
  const { data: queueData, isLoading } = useQuery({
    queryKey: [`userQueuePosition-${sourceType}`],
    queryFn: () => fetchUserQueuePosition(sourceType),
    refetchInterval: 5000, 
    refetchOnWindowFocus: true,
  });

  // Don't show banner if user has no pending pipelines
  if (isLoading || !queueData?.has_pending || !queueData.user_position) {
    return null;
  }

  const { user_position, total_pending } = queueData;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -20, scale: 0.95 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className={`bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-400/20 rounded-lg p-4 mb-4 ${className}`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
              <Clock className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-blue-400">
                Your {sourceType === 'slack' ? 'Slack channels' : 'documents'} are in the queue
              </h3>
              <p className="text-xs text-gray-400">
                Position {user_position} of {total_pending} pending pipelines
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <Users className="w-4 h-4" />
            <span>{total_pending} total</span>
          </div>
        </div>
        
        {/* Progress bar */}
        <div className="mt-3 w-full bg-gray-800/50 rounded-full h-1.5">
          <div 
            className="bg-gradient-to-r from-blue-500 to-purple-500 h-1.5 rounded-full transition-all duration-300"
            style={{ width: `${(user_position / total_pending) * 100}%` }}
          />
        </div>
        
        <p className="text-xs text-gray-500 mt-2">
          Processing one pipeline at a time. Your request will start automatically when it's your turn.
        </p>
      </motion.div>
    </AnimatePresence>
  );
}