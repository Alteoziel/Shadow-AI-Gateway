"use client";

import { useCallback, useMemo, useState } from "react";

type Props = {
  value: string;
  onChange: (next: string) => void;
  onRun: () => void;
  onReset: () => void;
  running?: boolean;
  label?: string;
};

/**
 * Lightweight mini editor: monospace textarea + line gutter + tab-to-indent.
 * Intentionally not Monaco — keeps the quiz bundle small on Vercel.
 */
export function MiniCodeEditor({
  value,
  onChange,
  onRun,
  onReset,
  running,
  label = "Your solution",
}: Props) {
  const lines = useMemo(() => value.split("\n").length, [value]);
  const gutter = useMemo(
    () =>
      Array.from({ length: Math.max(lines, 1) }, (_, i) => i + 1).join("\n"),
    [lines]
  );

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Tab") {
        e.preventDefault();
        const el = e.currentTarget;
        const start = el.selectionStart;
        const end = el.selectionEnd;
        const next = value.slice(0, start) + "  " + value.slice(end);
        onChange(next);
        requestAnimationFrame(() => {
          el.selectionStart = el.selectionEnd = start + 2;
        });
      }
    },
    [onChange, value]
  );

  return (
    <div className="overflow-hidden rounded-lg border border-white/15 bg-black/40">
      <div className="flex items-center justify-between border-b border-white/10 px-3 py-2 text-xs text-mist">
        <span>{label} · JavaScript</span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onReset}
            className="rounded px-2 py-1 hover:bg-white/10 hover:text-white"
          >
            Reset
          </button>
          <button
            type="button"
            onClick={onRun}
            disabled={running}
            className="rounded bg-signal/20 px-2 py-1 font-semibold text-signal hover:bg-signal/30 disabled:opacity-50"
          >
            {running ? "Running…" : "Run tests"}
          </button>
        </div>
      </div>
      <div className="flex max-h-72 min-h-[160px] overflow-auto font-mono text-xs leading-5">
        <pre
          aria-hidden
          className="select-none border-r border-white/10 bg-black/30 px-2 py-3 text-right text-white/30"
        >
          {gutter}
        </pre>
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          spellCheck={false}
          className="min-h-[160px] w-full flex-1 resize-y bg-transparent px-3 py-3 text-signal outline-none"
          aria-label={label}
        />
      </div>
    </div>
  );
}
