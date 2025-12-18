import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { FaFire } from "react-icons/fa";
import GlassPanel from "@/components/ui/GlassPanel";
import { PaginationControls } from "./PaginationControls";

type TimeRange = 'today' | '7days' | '30days' | 'all';

interface ActiveTodayTableProps {
  users: Array<{
    user_id: string;
    runs_today?: number;
    recent_runs?: number;
    total_runs?: number;
    status_breakdown?: {
      COMPLETED?: number;
      FAILED?: number;
    };
  }>;
  page: number;
  setPage: (updater: (page: number) => number) => void;
  itemsPerPage: number;
  timeRange?: TimeRange;
}

export function ActiveTodayTable({ users, page, setPage, itemsPerPage, timeRange = 'today' }: ActiveTodayTableProps) {
  const getTitle = () => {
    switch (timeRange) {
      case 'today':
        return 'Active Today';
      case '7days':
        return 'Active (Last 7 Days)';
      case '30days':
        return 'Active (Last 30 Days)';
      case 'all':
        return 'Active (All Time)';
      default:
        return 'Active Today';
    }
  };

  const getRunsField = (user: any) => {
    switch (timeRange) {
      case 'today':
        return user.runs_today || 0;
      case '7days':
      case '30days':
        return user.recent_runs || 0;
      case 'all':
        return user.total_runs || 0;
      default:
        return user.runs_today || 0;
    }
  };

  const getEmptyMessage = () => {
    switch (timeRange) {
      case 'today':
        return 'No active users today';
      case '7days':
        return 'No active users in the last 7 days';
      case '30days':
        return 'No active users in the last 30 days';
      case 'all':
        return 'No active users';
      default:
        return 'No active users';
    }
  };

  return (
    <GlassPanel>
      <Card className="shadow-card border-gray-800 h-full flex flex-col bg-transparent border-0">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-heading flex items-center gap-2">
            <FaFire className="text-warning" />
            {getTitle()}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User ID</TableHead>
                  <TableHead className="text-right">Runs</TableHead>
                  <TableHead className="text-right">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.length > 0 ? (
                  users.slice(page * itemsPerPage, (page + 1) * itemsPerPage).map((user, idx) => (
                    <TableRow key={idx} className="hover:bg-muted/50">
                      <TableCell className="font-medium text-sm truncate max-w-[200px]">
                        {user.user_id}
                      </TableCell>
                      <TableCell className="text-right text-sm">{getRunsField(user)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex gap-1 justify-end">
                          {user.status_breakdown?.COMPLETED && user.status_breakdown.COMPLETED > 0 && (
                            <Badge variant="outline" className="border-success text-success text-xs">
                              ✓ {user.status_breakdown.COMPLETED}
                            </Badge>
                          )}
                          {user.status_breakdown?.FAILED && user.status_breakdown.FAILED > 0 && (
                            <Badge variant="outline" className="border-error text-error text-xs">
                              ✗ {user.status_breakdown.FAILED}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center py-6 text-gray-400">
                      {getEmptyMessage()}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
          {users.length > itemsPerPage && (
            <PaginationControls 
              currentPage={page}
              totalItems={users.length}
              itemsPerPage={itemsPerPage}
              onPageChange={setPage}
            />
          )}
        </CardContent>
      </Card>
    </GlassPanel>
  );
}

