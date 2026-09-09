import React from 'react';
import { Search, X, Sparkles, RefreshCw } from 'lucide-react';
import { CatalogMeta } from '../types';

interface HeaderProps {
  meta: CatalogMeta | null;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  filteredCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  meta,
  searchQuery,
  onSearchChange,
  filteredCount,
}) => {
  return (
    <header className="sticky top-0 z-40 glass-panel border-b border-zinc-800/80 px-4 py-3 sm:px-6">
      <div className="max-w-7xl mx-auto flex flex-col gap-3">
        {/* Top Row: Brand & Status Pill */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-amber-600 to-amber-400 flex items-center justify-center shadow-glow-gold">
              <Sparkles className="w-5 h-5 text-zinc-950 stroke-[2.2]" />
            </div>
            <div>
              <h1 className="text-base sm:text-lg font-bold tracking-tight text-white flex items-center gap-2 font-serif">
                JW PEI Catalog
                <span className="text-[10px] font-sans font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  Data Viewer
                </span>
              </h1>
              <p className="text-[11px] text-zinc-400 hidden sm:block">
                Automated dropship product ingestion & live data audit
              </p>
            </div>
          </div>

          {/* Live Status Indicators */}
          {meta && (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-glow-emerald" />
                <span>{meta.in_stock} In Stock</span>
              </div>
              {meta.out_of_stock > 0 && (
                <div className="hidden xs:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-medium">
                  <span>{meta.out_of_stock} Sold Out</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Bottom Row: Search Bar & Count */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search title, SKU, color, or material..."
              className="w-full bg-zinc-900/90 text-white placeholder-zinc-500 text-sm rounded-xl pl-9 pr-9 py-2 border border-zinc-700/60 focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400/30 transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => onSearchChange('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white p-0.5"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="text-xs font-medium text-zinc-400 px-3 py-2 rounded-xl bg-zinc-900/60 border border-zinc-800 whitespace-nowrap">
            <span className="text-amber-400 font-semibold">{filteredCount}</span> products
          </div>
        </div>
      </div>
    </header>
  );
};
