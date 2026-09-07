"use client";

import * as React from "react";
import { ChevronDown, Check } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps {
  options: SelectOption[];
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  error?: string;
  id?: string;
}

export function Select({
  options,
  value: controlledValue,
  defaultValue = "",
  onChange,
  placeholder = "Select an option...",
  disabled = false,
  className,
  error,
  id,
}: SelectProps) {
  const [uncontrolledValue, setUncontrolledValue] = React.useState(defaultValue);
  const [isOpen, setIsOpen] = React.useState(false);
  const isControlled = controlledValue !== undefined;
  const activeValue = isControlled ? controlledValue : uncontrolledValue;
  const selectRef = React.useRef<HTMLDivElement>(null);

  const selectedOption = options.find((opt) => opt.value === activeValue);

  const handleSelect = (val: string) => {
    if (!isControlled) {
      setUncontrolledValue(val);
    }
    onChange?.(val);
    setIsOpen(false);
  };

  // Close on outside click
  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (selectRef.current && !selectRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className={cn("relative w-full", className)} ref={selectRef}>
      <button
        type="button"
        id={id}
        disabled={disabled}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        className={cn(
          "flex h-9 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs transition-colors placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer",
          error && "border-destructive focus:ring-destructive",
          isOpen && "ring-1 ring-primary border-primary"
        )}
      >
        <span className={cn("truncate", !selectedOption && "text-slate-400")}>
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown
          className={cn(
            "w-4 h-4 text-slate-400 transition-transform duration-200 shrink-0 ml-2",
            isOpen && "transform rotate-180"
          )}
        />
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md border border-slate-200 bg-white py-1 text-sm shadow-lg focus:outline-none animate-in fade-in-0 zoom-in-95">
          {options.length === 0 ? (
            <div className="px-3 py-2 text-xs text-slate-400">No options available</div>
          ) : (
            options.map((option) => {
              const isSelected = option.value === activeValue;
              return (
                <div
                  key={option.value}
                  onClick={() => !option.disabled && handleSelect(option.value)}
                  className={cn(
                    "relative flex cursor-pointer select-none items-center justify-between px-3 py-2 text-xs transition-colors",
                    option.disabled
                      ? "opacity-50 cursor-not-allowed"
                      : "hover:bg-slate-100/80",
                    isSelected && "bg-teal-50 text-primary font-semibold"
                  )}
                >
                  <span className="truncate">{option.label}</span>
                  {isSelected && <Check className="w-4 h-4 text-primary shrink-0 ml-2" />}
                </div>
              );
            })
          )}
        </div>
      )}

      {error && <p className="mt-1 text-[11px] text-destructive">{error}</p>}
    </div>
  );
}
