import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import GlassPanel from "@/components/ui/GlassPanel";
import { PaginationControls } from "./PaginationControls";

interface AllUsersTableProps {
  users: Array<{
    user_id: string;
    total_runs: number;
    unique_blueprints: number;
  }>;
  page: number;
  setPage: (updater: (page: number) => number) => void;
  itemsPerPage: number;
}

export function AllUsersTable({ users, page, setPage, itemsPerPage }: AllUsersTableProps) {
  return (
    <GlassPanel>
      <Card className="shadow-card border-gray-800 h-full flex flex-col bg-transparent border-0">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-heading">User Activity Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User ID</TableHead>
                  <TableHead className="text-right">Runs</TableHead>
                  <TableHead className="text-right">Blueprints</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.slice(page * itemsPerPage, (page + 1) * itemsPerPage).map((user, idx) => (
                  <TableRow key={idx} className="hover:bg-muted/50">
                    <TableCell className="font-medium text-sm truncate max-w-[200px]">
                      {user.user_id}
                    </TableCell>
                    <TableCell className="text-right text-sm">{user.total_runs}</TableCell>
                    <TableCell className="text-right text-sm">{user.unique_blueprints}</TableCell>
                  </TableRow>
                ))}
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

