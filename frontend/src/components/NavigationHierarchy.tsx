import React from 'react';
import { Layers, ArrowUpDown, SlidersHorizontal, Check } from 'lucide-react';
import { FilterState } from '../types';

interface NavigationHierarchyProps {
  stores: string[];
  departmentCounts: { All: number; Women: number; Men: number };
  groups: string[];
  subgroups: string[];
  subgroupCounts: Record<string, number>;
  filters: FilterState;
  onFilterChange: (newFilters: Partial<FilterState>) => void;
}

export const NavigationHierarchy: React.FC<NavigationHierarchyProps> = ({
  stores,
  departmentCounts,
  groups,
  subgroups,
  subgroupCounts,
  filters,
  onFilterChange,
}) => {
  return (
    <nav className="border-b border-zinc-800/60 bg-zinc-950/40 px-4 py-3 sm:px-6">
      <div className="max-w-7xl mx-auto flex flex-col gap-3">
        {/* Tier 1: Store & Department Switcher */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-850/80 pb-2.5">
          <div className="flex items-center gap-1.5 text-xs text-zinc-400 font-medium overflow-x-auto py-1">
            <span className="flex items-center gap-1 text-zinc-500 uppercase tracking-wider text-[10px] font-semibold mr-1">
              <Layers className="w-3.5 h-3.5 text-amber-500" />
              Store:
            </span>
            {['All Stores', ...stores].map((s) => (
              <button
                key={s}
                onClick={() => onFilterChange({ selectedStore: s })}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  filters.selectedStore === s
                    ? 'bg-amber-500 text-zinc-950 shadow-glow-gold'
                    : 'bg-zinc-900 text-zinc-300 hover:text-white hover:bg-zinc-800'
                }`}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Department / Gender Switcher */}
          <div className="flex items-center gap-1 bg-zinc-900/90 p-1 rounded-xl border border-zinc-800">
            <span className="text-zinc-500 uppercase tracking-wider text-[10px] font-bold px-2">
              Department:
            </span>
            {(['All', 'Women', 'Men'] as const).map((dept) => {
              const count = departmentCounts[dept];
              const isSelected = filters.selectedDepartment === dept;
              return (
                <button
                  key={dept}
                  onClick={() => onFilterChange({ selectedDepartment: dept })}
                  className={`px-3 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                    isSelected
                      ? dept === 'Women'
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow-sm'
                        : dept === 'Men'
                        ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-sm'
                        : 'bg-zinc-200 text-zinc-950'
                      : 'text-zinc-400 hover:text-white hover:bg-zinc-800/80'
                  }`}
                >
                  <span>{dept === 'All' ? 'All' : dept === 'Women' ? "Women's" : "Men's"}</span>
                  <span
                    className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${
                      isSelected
                        ? dept === 'Women'
                          ? 'bg-rose-500/40 text-rose-100'
                          : dept === 'Men'
                          ? 'bg-sky-500/40 text-sky-100'
                          : 'bg-zinc-400 text-zinc-950'
                        : 'bg-zinc-800 text-zinc-400'
                    }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Tier 2: Categories (Filtered by Department) */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-xs text-zinc-400 font-medium overflow-x-auto py-1">
            <span className="text-zinc-500 uppercase tracking-wider text-[10px] font-semibold mr-1">
              Category:
            </span>
            {groups.map((g) => (
              <button
                key={g}
                onClick={() => onFilterChange({ selectedGroup: g })}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                  filters.selectedGroup === g
                    ? 'bg-zinc-200 text-zinc-950'
                    : 'bg-zinc-900 text-zinc-300 hover:text-white hover:bg-zinc-800'
                }`}
              >
                {g}
              </button>
            ))}
          </div>

          {/* Quick Stock & Sort Dropdowns */}
          <div className="flex items-center gap-2 text-xs">
            {/* Stock Filter Pills */}
            <div className="flex items-center p-0.5 rounded-lg bg-zinc-900 border border-zinc-800">
              <button
                onClick={() => onFilterChange({ stockFilter: 'all' })}
                className={`px-2 py-1 rounded-md text-[11px] font-medium transition-all ${
                  filters.stockFilter === 'all'
                    ? 'bg-zinc-800 text-white'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                All
              </button>
              <button
                onClick={() => onFilterChange({ stockFilter: 'in_stock' })}
                className={`px-2 py-1 rounded-md text-[11px] font-medium transition-all ${
                  filters.stockFilter === 'in_stock'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    : 'text-zinc-400 hover:text-emerald-400'
                }`}
              >
                In Stock
              </button>
              <button
                onClick={() => onFilterChange({ stockFilter: 'out_of_stock' })}
                className={`px-2 py-1 rounded-md text-[11px] font-medium transition-all ${
                  filters.stockFilter === 'out_of_stock'
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                    : 'text-zinc-400 hover:text-rose-400'
                }`}
              >
                Sold Out
              </button>
            </div>

            {/* Sort Select */}
            <div className="relative">
              <select
                value={filters.sortBy}
                onChange={(e) => onFilterChange({ sortBy: e.target.value as any })}
                className="bg-zinc-900 text-zinc-300 text-xs rounded-lg px-2.5 py-1.5 border border-zinc-800 focus:outline-none focus:border-amber-400 appearance-none pr-7 cursor-pointer"
              >
                <option value="popular">Best Selling</option>
                <option value="price_asc">Price: Low to High</option>
                <option value="price_desc">Price: High to Low</option>
                <option value="newest">Newest Added</option>
              </select>
              <ArrowUpDown className="w-3 h-3 text-zinc-400 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Tier 3: Subgroup Pills (Carrying Style / Silhouette) */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 pt-0.5 no-scrollbar">
          <button
            onClick={() => onFilterChange({ selectedSubgroup: 'All' })}
            className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all flex items-center gap-1.5 ${
              filters.selectedSubgroup === 'All'
                ? 'bg-amber-400/10 text-amber-300 border border-amber-400/40 shadow-glow-gold'
                : 'bg-zinc-900 text-zinc-400 hover:text-zinc-200 border border-zinc-800 hover:border-zinc-700'
            }`}
          >
            <span>All Subcategories</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-zinc-800 text-zinc-400 font-mono">
              {Object.values(subgroupCounts).reduce((a, b) => a + b, 0)}
            </span>
          </button>

          {subgroups.map((sub) => {
            const count = subgroupCounts[sub] || 0;
            const isActive = filters.selectedSubgroup === sub;
            return (
              <button
                key={sub}
                onClick={() => onFilterChange({ selectedSubgroup: sub })}
                className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all flex items-center gap-1.5 ${
                  isActive
                    ? 'bg-amber-400/10 text-amber-300 border border-amber-400/40 shadow-glow-gold'
                    : 'bg-zinc-900 text-zinc-400 hover:text-zinc-200 border border-zinc-800 hover:border-zinc-700'
                }`}
              >
                <span>{sub}</span>
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                  isActive ? 'bg-amber-500/20 text-amber-300' : 'bg-zinc-800 text-zinc-400'
                }`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </nav>
  );
};
