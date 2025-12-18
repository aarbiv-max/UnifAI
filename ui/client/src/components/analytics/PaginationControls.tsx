import { Button } from "@/components/ui/button";

interface PaginationControlsProps {
  currentPage: number;
  totalItems: number;
  itemsPerPage: number;
  onPageChange: (updater: (page: number) => number) => void;
}

export function PaginationControls({ currentPage, totalItems, itemsPerPage, onPageChange }: PaginationControlsProps) {
  return (
    <div className="flex justify-between items-center mt-4 px-2">
      <span className="text-sm text-gray-400">
        Showing {currentPage * itemsPerPage + 1}-{Math.min((currentPage + 1) * itemsPerPage, totalItems)} of {totalItems}
      </span>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange((p: number) => Math.max(0, p - 1))}
          disabled={currentPage === 0}
          className="border-gray-700"
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange((p: number) => p + 1)}
          disabled={(currentPage + 1) * itemsPerPage >= totalItems}
          className="border-gray-700"
        >
          Next
        </Button>
      </div>
    </div>
  );
}

