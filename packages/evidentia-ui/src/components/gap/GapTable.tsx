import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { SEVERITY_RANK, severityBadge } from "@/lib/severity";
import type { ControlGap } from "@/types/api";

/**
 * Sortable + filterable gap table powered by TanStack Table.
 *
 * Scales comfortably to 1000 rows without virtualization. Larger
 * reports should add TanStack Virtual (queued for v0.4.2 alongside
 * the Risk Generate page's virtual stream list).
 */
export function GapTable({ gaps }: { gaps: ControlGap[] }) {
  const [filter, setFilter] = useState("");
  const [sorting, setSorting] = useState<SortingState>([
    { id: "priority_score", desc: true },
  ]);

  const columns = useMemo<ColumnDef<ControlGap>[]>(
    () => [
      {
        accessorKey: "framework",
        header: "Framework",
        cell: ({ getValue }) => (
          <code className="rounded bg-muted px-1 py-0.5 text-xs">
            {String(getValue())}
          </code>
        ),
      },
      {
        accessorKey: "control_id",
        header: "Control",
        cell: ({ getValue }) => (
          <span className="font-mono text-xs">{String(getValue())}</span>
        ),
      },
      {
        accessorKey: "control_title",
        header: "Title",
        cell: ({ getValue }) => (
          <span className="line-clamp-1 text-sm">{String(getValue())}</span>
        ),
      },
      {
        accessorKey: "gap_severity",
        header: "Severity",
        sortingFn: (a, b, id) =>
          SEVERITY_RANK[
            a.getValue(id) as keyof typeof SEVERITY_RANK
          ] -
          SEVERITY_RANK[b.getValue(id) as keyof typeof SEVERITY_RANK],
        cell: ({ row }) => (
          <Badge variant={severityBadge(row.original.gap_severity)}>
            {row.original.gap_severity}
          </Badge>
        ),
      },
      {
        accessorKey: "implementation_effort",
        header: "Effort",
        cell: ({ row }) => (
          <Badge variant="outline" className="capitalize">
            {row.original.implementation_effort.replace(/_/g, " ")}
          </Badge>
        ),
      },
      {
        accessorKey: "priority_score",
        header: "Priority",
        cell: ({ row }) => (
          <span className="font-mono text-xs">
            {row.original.priority_score.toFixed(2)}
          </span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => (
          <span
            className={cn(
              "capitalize text-xs",
              row.original.status === "open"
                ? "text-destructive"
                : "text-muted-foreground",
            )}
          >
            {row.original.status.replace(/_/g, " ")}
          </span>
        ),
      },
    ],
    [],
  );

  const table = useReactTable({
    data: gaps,
    columns,
    state: { sorting, globalFilter: filter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    globalFilterFn: (row, _columnId, value) => {
      const q = String(value).toLowerCase();
      return (
        row.original.control_id.toLowerCase().includes(q) ||
        row.original.control_title.toLowerCase().includes(q) ||
        row.original.framework.toLowerCase().includes(q)
      );
    },
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-4">
        <Input
          type="search"
          placeholder="Filter by control ID, title, or framework..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="max-w-sm"
          aria-label="Filter gaps"
        />
        <span className="text-xs text-muted-foreground">
          {table.getFilteredRowModel().rows.length} of {gaps.length} rows
        </span>
      </div>
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    scope="col"
                    className={cn(
                      "px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground",
                      header.column.getCanSort() && "cursor-pointer select-none",
                    )}
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    {flexRender(
                      header.column.columnDef.header,
                      header.getContext(),
                    )}
                    {{
                      asc: " ▲",
                      desc: " ▼",
                    }[header.column.getIsSorted() as string] ?? null}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y">
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="hover:bg-accent/30">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-3 py-2">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
            {table.getRowModel().rows.length === 0 && (
              <tr>
                <td
                  colSpan={columns.length}
                  className="p-4 text-center text-sm text-muted-foreground"
                >
                  No gaps match the current filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
