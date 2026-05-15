/**
 * Spec 218 Slice 218-3 — CalendarAsk shape renderer.
 *
 * Renders a shadcn Calendar inside a Popover trigger for date selection.
 * Returns ISO date string ("YYYY-MM-DD") on submit; backend computes
 * age int from the DoB.
 *
 * Cluster X: replaced native <input type="date"> with shadcn Calendar
 * + Popover (per components.json shadcn-primitive rule + Cluster X spec).
 * Applies 18-year-ago max constraint matching Cluster Y age-gate.
 *
 * min_date / max_date envelope fields constrain the Calendar via the
 * `disabled` prop — dates outside range are disabled.
 */

"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

import type { CalendarAsk } from "./types/envelope";

type Props = {
  envelope: CalendarAsk;
  onSubmit: (isoDate: string) => void;
};

/**
 * Compute the date 18 years ago from today for the age-gate constraint.
 * Returns a Date at midnight UTC.
 */
function eighteenYearsAgo(): Date {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 18);
  // Use end-of-day so a calendar cell at midnight on the exact 18th birthday
  // is never > maxDate — prevents wall-clock time / DST from disabling the
  // birthday itself (midnight < current time → cell > maxDate → disabled).
  d.setHours(23, 59, 59, 999);
  return d;
}

export function CalendarShape({ envelope, onSubmit }: Props) {
  const [date, setDate] = React.useState<Date | undefined>(undefined);
  const [open, setOpen] = React.useState(false);

  // Build the disabled function for the calendar.
  // Applies envelope.max_date (or 18-year minimum age gate), and
  // envelope.min_date if provided.
  const maxDate: Date = envelope.max_date
    ? new Date(envelope.max_date)
    : eighteenYearsAgo();
  const minDate: Date | undefined = envelope.min_date
    ? new Date(envelope.min_date)
    : undefined;

  const isDateDisabled = (d: Date) => {
    if (d > maxDate) return true;
    if (minDate && d < minDate) return true;
    return false;
  };

  const handleSelect = (selected: Date | undefined) => {
    setDate(selected);
    if (selected) {
      setOpen(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!date) return;
    // Convert to ISO YYYY-MM-DD using local date parts to avoid UTC offset
    // shifting the date (e.g. 2000-12-31 rendered as 2001-01-01 in UTC+14).
    const iso = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
    onSubmit(iso);
  };

  // Age gate: compute the local ISO date 18 years ago today (Fix #3 — QA iter-1).
  // Use getFullYear/getMonth/getDate (local) NOT toISOString() (UTC) to avoid
  // a ±1-day boundary shift for users in western timezones who render this page
  // before UTC midnight. A PST user exactly 18 years old today must not be
  // blocked by a stale UTC date.
  const eighteenYearsAgo = React.useMemo(() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 18);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`; // local "YYYY-MM-DD"
  }, []);

  return (
    <form
      data-testid="v2-calendar-shape"
      onSubmit={handleSubmit}
      className="flex flex-col gap-3"
    >
      <p className="text-base text-foreground">{envelope.prompt}</p>
      <div className="flex flex-col gap-2">
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button
              type="button"
              variant="outline"
              className={cn(
                "w-[240px] justify-start text-left font-normal",
                !date && "text-muted-foreground",
              )}
              aria-label={envelope.prompt}
            >
              {date ? date.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }) : "Select a date"}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="single"
              selected={date}
              onSelect={handleSelect}
              disabled={isDateDisabled}
              defaultMonth={maxDate}
              initialFocus
            />
          </PopoverContent>
        </Popover>
      </div>
      <Button type="submit" disabled={!date} className="self-start">
        Continue
      </Button>
    </form>
  );
}
