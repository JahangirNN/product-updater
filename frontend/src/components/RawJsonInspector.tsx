import React, { useState } from 'react';
import { Code2, Copy, Check, ChevronDown, ChevronRight } from 'lucide-react';

interface RawJsonInspectorProps {
  data: any;
  title?: string;
}

export const RawJsonInspector: React.FC<RawJsonInspectorProps> = ({ data, title = "Raw Canonical JSON" }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const jsonString = JSON.stringify(data, null, 2);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/80 overflow-hidden">
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between px-3.5 py-2.5 bg-zinc-900/90 hover:bg-zinc-900 cursor-pointer transition-colors"
      >
        <div className="flex items-center gap-2 text-xs font-mono font-medium text-amber-400">
          <Code2 className="w-4 h-4 text-amber-400" />
          <span>{title}</span>
          <span className="text-[10px] text-zinc-500 font-sans">
            ({Math.round(jsonString.length / 1024 * 10) / 10} KB)
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            title="Copy JSON to clipboard"
            className="flex items-center gap-1 text-[11px] font-mono px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-emerald-400" />
                <span className="text-emerald-400">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3 text-zinc-400" />
                <span>Copy</span>
              </>
            )}
          </button>
          {isOpen ? (
            <ChevronDown className="w-4 h-4 text-zinc-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-zinc-400" />
          )}
        </div>
      </div>

      {isOpen && (
        <div className="p-3 bg-zinc-950 overflow-x-auto max-h-96 text-[11px] font-mono leading-relaxed border-t border-zinc-800">
          <pre className="text-emerald-400/90 selection:bg-emerald-950 selection:text-emerald-200">
            {jsonString}
          </pre>
        </div>
      )}
    </div>
  );
};
