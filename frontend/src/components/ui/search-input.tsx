"use client";

import * as React from "react";
import { Search, X, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SearchInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange"> {
  onSearchChange?: (val: string) => void;
  debounceMs?: number;
  isLoading?: boolean;
  shortcutBadge?: string;
}

export function SearchInput({
  onSearchChange,
  debounceMs = 300,
  isLoading = false,
  shortcutBadge,
  placeholder = "Search...",
  className,
  value: controlledValue,
  defaultValue = "",
  ...props
}: SearchInputProps) {
  const [internalValue, setInternalValue] = React.useState(defaultValue as string);
  const isControlled = controlledValue !== undefined;
  const currentValue = isControlled ? (controlledValue as string) : internalValue;
  const inputRef = React.useRef<HTMLInputElement>(null);

  // Debounced search trigger
  React.useEffect(() => {
    const handler = setTimeout(() => {
      onSearchChange?.(currentValue);
    }, debounceMs);

    return () => clearTimeout(handler);
  }, [currentValue, debounceMs, onSearchChange]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!isControlled) {
      setInternalValue(e.target.value);
    }
  };

  const handleClear = () => {
    if (!isControlled) {
      setInternalValue("");
    }
    onSearchChange?.("");
    inputRef.current?.focus();
  };

  return (
    <div className={cn("relative flex items-center w-full", className)}>
      <Search className="w-4 h-4 text-slate-400 absolute left-3 pointer-events-none" />

      <input
        ref={inputRef}
        type="text"
        value={currentValue}
        onChange={handleChange}
        placeholder={placeholder}
        className="h-9 w-full rounded-md border border-input bg-background pl-9 pr-14 text-xs shadow-xs placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
        {...props}
      />

      <div className="absolute right-2.5 flex items-center gap-1.5">
        {isLoading && <Loader2 className="w-3.5 h-3.5 text-primary animate-spin" />}

        {currentValue && !isLoading && (
          <button
            type="button"
            onClick={handleClear}
            className="p-0.5 rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}

        {shortcutBadge && !currentValue && !isLoading && (
          <kbd className="px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-slate-100 border border-slate-200 rounded">
            {shortcutBadge}
          </kbd>
        )}
      </div>
    </div>
  );
}
