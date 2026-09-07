"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalItems?: number;
  pageSize?: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  pageSizeOptions?: number[];
  className?: string;
}

export function Pagination({
  currentPage,
  totalPages,
  totalItems,
  pageSize = 10,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 25, 50, 100],
  className,
}: PaginationProps) {
  const canGoPrevious = currentPage > 1;
  const canGoNext = currentPage < totalPages;

  return (
    <div
      className={cn(
        "flex flex-col sm:flex-row items-center justify-between gap-4 py-3 px-2 text-xs text-slate-600 border-t border-slate-100",
        className
      )}
    >
      {/* Left: Total counts & page size selector */}
      <div className="flex items-center gap-3">
        {totalItems !== undefined && (
          <span>
            Total <span className="font-semibold text-slate-900">{totalItems}</span> records
          </span>
        )}

        {onPageSizeChange && (
          <div className="flex items-center gap-1.5">
            <span>Show</span>
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              className="h-7 rounded border border-slate-200 bg-white px-2 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {pageSizeOptions.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
            <span>per page</span>
          </div>
        )}
      </div>

      {/* Right: Page navigation buttons */}
      <div className="flex items-center gap-2">
        <span className="text-slate-500 mr-2">
          Page <span className="font-semibold text-slate-900">{currentPage}</span> of{" "}
          <span className="font-semibold text-slate-900">{Math.max(1, totalPages)}</span>
        </span>

        <Button
          variant="outline"
          size="icon"
          className="h-7 w-7"
          disabled={!canGoPrevious}
          onClick={() => onPageChange(1)}
          title="First Page"
        >
          <ChevronsLeft className="h-3.5 w-3.5" />
        </Button>

        <Button
          variant="outline"
          size="icon"
          className="h-7 w-7"
          disabled={!canGoPrevious}
          onClick={() => onPageChange(currentPage - 1)}
          title="Previous Page"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
        </Button>

        <Button
          variant="outline"
          size="icon"
          className="h-7 w-7"
          disabled={!canGoNext}
          onClick={() => onPageChange(currentPage + 1)}
          title="Next Page"
        >
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>

        <Button
          variant="outline"
          size="icon"
          className="h-7 w-7"
          disabled={!canGoNext}
          onClick={() => onPageChange(totalPages)}
          title="Last Page"
        >
          <ChevronsRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
