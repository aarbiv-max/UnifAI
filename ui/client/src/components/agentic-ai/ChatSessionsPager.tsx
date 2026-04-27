import React from "react";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { CHAT_SESSIONS_PAGE_SIZE } from "@/hooks/use-chat-sessions-pagination";

type ChatSessionsPagerProps = {
  total: number;
  currentPage: number;
  maxPageIndex: number;
  onPrev: () => void;
  onNext: () => void;
  disabled?: boolean;
};

export default function ChatSessionsPager({
  total,
  currentPage,
  maxPageIndex,
  onPrev,
  onNext,
  disabled,
}: ChatSessionsPagerProps) {
  if (total <= CHAT_SESSIONS_PAGE_SIZE) {
    return null;
  }

  const start = currentPage * CHAT_SESSIONS_PAGE_SIZE + 1;
  const end = Math.min(total, (currentPage + 1) * CHAT_SESSIONS_PAGE_SIZE);

  return (
    <div className="flex items-center justify-between gap-2 px-3 py-2 border-t border-gray-800 bg-background-card/80 flex-shrink-0">
      <span className="text-xs text-gray-500 truncate">
        {start}–{end} of {total}
      </span>
      <div className="flex items-center gap-1 flex-shrink-0">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          onClick={onPrev}
          disabled={disabled || currentPage <= 0}
          title="Previous page"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="text-xs text-gray-400 tabular-nums min-w-[3rem] text-center">
          {currentPage + 1}/{maxPageIndex + 1}
        </span>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          onClick={onNext}
          disabled={disabled || currentPage >= maxPageIndex}
          title="Next page"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
