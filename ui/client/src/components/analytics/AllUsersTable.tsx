import React from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AnalyticCard } from "./AnalyticCard";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";

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
  const totalPages = Math.ceil(users.length / itemsPerPage);
  const startItem = page * itemsPerPage + 1;
  const endItem = Math.min((page + 1) * itemsPerPage, users.length);

  return (
    <AnalyticCard title="User Activity Summary">
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
            <div className="flex justify-between items-center mt-4 px-2">
              <span className="text-sm text-gray-400">
                Showing {startItem}-{endItem} of {users.length}
              </span>
              <Pagination>
                <PaginationContent>
                  <PaginationItem>
                    <PaginationPrevious
                      href="#"
                      onClick={(e: React.MouseEvent<HTMLAnchorElement>) => {
                        e.preventDefault();
                        setPage((p: number) => Math.max(0, p - 1));
                      }}
                      className={page === 0 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                    />
                  </PaginationItem>
                  <PaginationItem>
                    <PaginationNext
                      href="#"
                      onClick={(e: React.MouseEvent<HTMLAnchorElement>) => {
                        e.preventDefault();
                        setPage((p: number) => p + 1);
                      }}
                      className={page >= totalPages - 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                    />
                  </PaginationItem>
                </PaginationContent>
              </Pagination>
            </div>
          )}
    </AnalyticCard>
  );
}

