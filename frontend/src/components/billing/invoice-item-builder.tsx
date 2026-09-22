"use client";

import React from "react";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { BillingPackage, BillingService, InvoiceItemDraft, InvoiceItemType } from "@/types/billing";

function currency(amount: number): string {
  return `₹${amount.toFixed(2)}`;
}

export function newDraftItem(): InvoiceItemDraft {
  return {
    key: `item-${Math.random().toString(36).slice(2)}`,
    itemType: "SERVICE",
    serviceId: undefined,
    packageId: undefined,
    description: "",
    quantity: "1",
    unitPrice: "",
    discountAmount: "0",
    taxAmount: "0",
  };
}

const ITEM_TYPE_OPTIONS: { value: InvoiceItemType; label: string }[] = [
  { value: "SERVICE", label: "Service" },
  { value: "PACKAGE", label: "Package" },
  { value: "CUSTOM", label: "Custom" },
];

export function estimateTotals(items: InvoiceItemDraft[]) {
  let subtotal = 0;
  let discount = 0;
  let tax = 0;
  let total = 0;
  for (const item of items) {
    const quantity = Number(item.quantity || "0");
    const unitPrice = Number(item.unitPrice || "0");
    const discountAmount = Number(item.discountAmount || "0");
    const taxAmount = Number(item.taxAmount || "0");
    const gross = quantity * unitPrice;
    subtotal += gross;
    discount += discountAmount;
    tax += taxAmount;
    total += gross - discountAmount + taxAmount;
  }
  return { subtotal, discount, tax, total };
}

export function validateDraftItems(items: InvoiceItemDraft[]): string | null {
  if (items.length === 0) return "Add at least one line item.";
  for (const item of items) {
    const quantity = Number(item.quantity);
    if (!item.quantity || Number.isNaN(quantity) || quantity <= 0) return "Every item needs a quantity greater than zero.";
    if (item.itemType === "SERVICE" && !item.serviceId) return "Select a service for every service line item.";
    if (item.itemType === "PACKAGE" && !item.packageId) return "Select a package for every package line item.";
    if (item.itemType === "CUSTOM") {
      if (!item.description.trim()) return "Custom line items need a description.";
      const unitPrice = Number(item.unitPrice);
      if (item.unitPrice.trim() === "" || Number.isNaN(unitPrice) || unitPrice < 0) {
        return "Custom line items need a valid unit price.";
      }
    }
  }
  return null;
}

export function InvoiceItemBuilder({
  items,
  onChange,
  services,
  packages,
}: {
  items: InvoiceItemDraft[];
  onChange: (items: InvoiceItemDraft[]) => void;
  services: BillingService[];
  packages: BillingPackage[];
}) {
  const updateItem = (key: string, patch: Partial<InvoiceItemDraft>) => {
    onChange(items.map((item) => (item.key === key ? { ...item, ...patch } : item)));
  };

  const handleItemTypeChange = (key: string, itemType: InvoiceItemType) => {
    updateItem(key, { itemType, serviceId: undefined, packageId: undefined, description: "", unitPrice: "" });
  };

  const handleServiceChange = (key: string, serviceId: string) => {
    const service = services.find((s) => s.id === serviceId);
    updateItem(key, { serviceId, description: service?.name ?? "", unitPrice: service ? String(service.price) : "" });
  };

  const handlePackageChange = (key: string, packageId: string) => {
    const pkg = packages.find((p) => p.id === packageId);
    updateItem(key, { packageId, description: pkg?.name ?? "", unitPrice: pkg ? String(pkg.price) : "" });
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold text-slate-700">Line Items</span>
        <Button type="button" variant="outline" size="sm" className="gap-1.5 text-xs" onClick={() => onChange([...items, newDraftItem()])}>
          <Plus className="w-3.5 h-3.5" />
          Add Item
        </Button>
      </div>

      <div className="space-y-3">
        {items.map((item, index) => (
          <div key={item.key} className="rounded-md border border-slate-200 p-3 space-y-2.5 bg-slate-50/40">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-500">Item {index + 1}</span>
              {items.length > 1 && (
                <button
                  type="button"
                  onClick={() => onChange(items.filter((i) => i.key !== item.key))}
                  className="text-slate-400 hover:text-destructive"
                  title="Remove item"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <div>
                <label className="text-[10px] font-semibold text-slate-600 block mb-1">Type</label>
                <Select
                  options={ITEM_TYPE_OPTIONS}
                  value={item.itemType}
                  onChange={(value) => handleItemTypeChange(item.key, value as InvoiceItemType)}
                />
              </div>

              {item.itemType === "SERVICE" && (
                <div>
                  <label className="text-[10px] font-semibold text-slate-600 block mb-1">Service</label>
                  <Select
                    options={services.map((s) => ({ value: s.id, label: `${s.name} (${currency(s.price)})` }))}
                    value={item.serviceId ?? ""}
                    onChange={(value) => handleServiceChange(item.key, value)}
                    placeholder="Select a service"
                  />
                </div>
              )}
              {item.itemType === "PACKAGE" && (
                <div>
                  <label className="text-[10px] font-semibold text-slate-600 block mb-1">Package</label>
                  <Select
                    options={packages.map((p) => ({ value: p.id, label: `${p.name} (${currency(p.price)})` }))}
                    value={item.packageId ?? ""}
                    onChange={(value) => handlePackageChange(item.key, value)}
                    placeholder="Select a package"
                  />
                </div>
              )}
              {item.itemType === "CUSTOM" && (
                <div>
                  <label className="text-[10px] font-semibold text-slate-600 block mb-1">Description</label>
                  <Input
                    value={item.description}
                    onChange={(e) => updateItem(item.key, { description: e.target.value })}
                    placeholder="e.g. Ambulance charges"
                    className="text-xs"
                  />
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <div>
                <label className="text-[10px] font-semibold text-slate-600 block mb-1">Quantity</label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={item.quantity}
                  onChange={(e) => updateItem(item.key, { quantity: e.target.value })}
                  className="text-xs"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-600 block mb-1">Unit Price</label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={item.unitPrice}
                  onChange={(e) => updateItem(item.key, { unitPrice: e.target.value })}
                  disabled={item.itemType !== "CUSTOM"}
                  className="text-xs"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-600 block mb-1">Discount</label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={item.discountAmount}
                  onChange={(e) => updateItem(item.key, { discountAmount: e.target.value })}
                  className="text-xs"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-600 block mb-1">Tax</label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={item.taxAmount}
                  onChange={(e) => updateItem(item.key, { taxAmount: e.target.value })}
                  className="text-xs"
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function EstimatedTotals({ items }: { items: InvoiceItemDraft[] }) {
  const estimate = estimateTotals(items);
  return (
    <div>
      <label className="text-[11px] font-semibold text-slate-700 block mb-2">Estimated Totals</label>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
        <div>
          <span className="text-[10px] text-slate-500 block">Subtotal</span>
          <span className="font-semibold text-slate-900">{currency(estimate.subtotal)}</span>
        </div>
        <div>
          <span className="text-[10px] text-slate-500 block">Discount</span>
          <span className="font-semibold text-slate-900">-{currency(estimate.discount)}</span>
        </div>
        <div>
          <span className="text-[10px] text-slate-500 block">Tax</span>
          <span className="font-semibold text-slate-900">+{currency(estimate.tax)}</span>
        </div>
        <div>
          <span className="text-[10px] text-slate-500 block">Total (estimated)</span>
          <span className="font-bold text-slate-900">{currency(estimate.total)}</span>
        </div>
      </div>
      <p className="text-[10px] text-slate-400 mt-1.5">
        This is a client-side estimate. The invoice total is calculated and rounded by the server.
      </p>
    </div>
  );
}
