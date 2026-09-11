import React, { useState, useEffect, useMemo } from 'react';
import { CatalogProduct, CatalogMeta, FilterState } from './types';
import { fetchCatalogData, filterAndSortProducts } from './services/catalogService';
import { Header } from './components/Header';
import { NavigationHierarchy } from './components/NavigationHierarchy';
import { ProductCard } from './components/ProductCard';
import { ProductDetailModal } from './components/ProductDetailModal';
import { Sparkles, AlertCircle, RefreshCw } from 'lucide-react';

export const App: React.FC = () => {
  const [products, setProducts] = useState<CatalogProduct[]>([]);
  const [meta, setMeta] = useState<CatalogMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedProduct, setSelectedProduct] = useState<CatalogProduct | null>(null);

  const [filters, setFilters] = useState<FilterState>({
    selectedStore: 'All Stores',
    selectedDepartment: 'All',
    selectedGroup: 'All Groups',
    selectedSubgroup: 'All',
    searchQuery: '',
    stockFilter: 'all',
    sortBy: 'popular',
  });

  // Load catalog data once
  useEffect(() => {
    fetchCatalogData()
      .then(({ products, meta }) => {
        setProducts(products);
        setMeta(meta);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load catalog');
        setLoading(false);
      });
  }, []);

  const handleFilterChange = (newFilters: Partial<FilterState>) => {
    setFilters((prev) => {
      const next = { ...prev, ...newFilters };
      // When switching store or department, reset group if incompatible
      if (newFilters.selectedStore && newFilters.selectedStore !== prev.selectedStore) {
        next.selectedGroup = 'All Groups';
        next.selectedSubgroup = 'All';
      }
      if (newFilters.selectedDepartment && newFilters.selectedDepartment !== prev.selectedDepartment) {
        next.selectedGroup = 'All Groups';
        next.selectedSubgroup = 'All';
      }
      return next;
    });
  };

  // Compute subgroup counts based on current store & group
  const subgroupCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    const relevant = products.filter(
      (p) =>
        (!filters.selectedStore || filters.selectedStore === 'All Stores' || p.store_display === filters.selectedStore) &&
        (!filters.selectedGroup || filters.selectedGroup === 'All Groups' || p.group_display === filters.selectedGroup)
    );
    for (const p of relevant) {
      const sg = p.subgroup_display || 'Other';
      counts[sg] = (counts[sg] || 0) + 1;
    }
    return counts;
  }, [products, filters.selectedStore, filters.selectedGroup]);

  // Filtered and sorted products
  const filteredProducts = useMemo(() => {
    return filterAndSortProducts(products, filters);
  }, [products, filters]);

  const stores = useMemo(() => {
    return meta?.stores || [];
  }, [meta]);

  const departmentCounts = useMemo(() => {
    const storeProds = products.filter(
      (p) => !filters.selectedStore || filters.selectedStore === 'All Stores' || p.store_display === filters.selectedStore
    );
    let women = 0;
    let men = 0;
    for (const p of storeProds) {
      const g = (p.gender || p.specifications?.['Gender'] || '').toLowerCase();
      const gd = (p.group_display || '').toLowerCase();
      if (g === 'men' || gd.includes("men's")) {
        men++;
      } else {
        women++;
      }
    }
    return {
      All: storeProds.length,
      Women: women,
      Men: men,
    };
  }, [products, filters.selectedStore]);

  const groups = useMemo(() => {
    let storeProducts = products;
    if (filters.selectedStore && filters.selectedStore !== 'All Stores') {
      storeProducts = storeProducts.filter((p) => p.store_display === filters.selectedStore);
    }
    if (filters.selectedDepartment && filters.selectedDepartment !== 'All') {
      if (filters.selectedDepartment === 'Men') {
        storeProducts = storeProducts.filter(
          (p) =>
            (p.gender && p.gender.toLowerCase() === 'men') ||
            p.group_display.toLowerCase().includes("men's") ||
            (p.specifications?.['Gender'] && p.specifications['Gender'].toLowerCase() === 'men')
        );
      } else {
        storeProducts = storeProducts.filter(
          (p) =>
            (p.gender && p.gender.toLowerCase() === 'women') ||
            p.group_display.toLowerCase().includes("women's") ||
            (p.specifications?.['Gender'] && p.specifications['Gender'].toLowerCase() === 'women') ||
            p.store_display === 'JW PEI'
        );
      }
    }
    const storeGroups = Array.from(new Set(storeProducts.map((p) => p.group_display))).sort();
    return ['All Groups', ...storeGroups];
  }, [products, filters.selectedStore, filters.selectedDepartment]);

  const subgroups = useMemo(() => {
    return (meta?.subgroups || []).filter((sub) => (subgroupCounts[sub] || 0) > 0);
  }, [meta, subgroupCounts]);

  return (
    <div className="min-h-screen flex flex-col bg-luxury-bg text-zinc-100">
      {/* Top Header */}
      <Header
        meta={meta}
        searchQuery={filters.searchQuery}
        onSearchChange={(q) => handleFilterChange({ searchQuery: q })}
        filteredCount={filteredProducts.length}
      />

      {/* Hierarchical Navigation (Store -> Department -> Group -> Subgroup) */}
      <NavigationHierarchy
        stores={stores}
        departmentCounts={departmentCounts}
        groups={groups}
        subgroups={subgroups}
        subgroupCounts={subgroupCounts}
        filters={filters}
        onFilterChange={handleFilterChange}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-5 sm:px-6">
        {/* Section Heading Banner */}
        <div className="mb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-lg sm:text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <span>{filters.selectedSubgroup === 'All' ? `All ${filters.selectedGroup}` : filters.selectedSubgroup}</span>
              <span className="text-xs font-mono font-normal text-zinc-500">
                ({filteredProducts.length} items)
              </span>
            </h2>
            <p className="text-xs text-zinc-400">
              Showing verified catalog products for{' '}
              <strong>{filters.selectedStore}</strong> &bull;{' '}
              <strong>{filters.selectedGroup}</strong>
            </p>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="py-24 flex flex-col items-center justify-center text-center">
            <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mb-4 shadow-glow-gold">
              <RefreshCw className="w-6 h-6 text-amber-400 animate-spin" />
            </div>
            <p className="text-sm font-medium text-zinc-300">Loading catalog database...</p>
            <p className="text-xs text-zinc-500 mt-1">Reading static JSON bundle</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="my-10 p-6 rounded-2xl bg-rose-950/40 border border-rose-800/60 text-center max-w-md mx-auto">
            <AlertCircle className="w-8 h-8 text-rose-400 mx-auto mb-2" />
            <h3 className="text-sm font-bold text-white">Unable to Load Catalog Data</h3>
            <p className="text-xs text-rose-300/80 mt-1">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold"
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty Search State */}
        {!loading && !error && filteredProducts.length === 0 && (
          <div className="py-20 text-center max-w-sm mx-auto">
            <div className="w-12 h-12 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mx-auto mb-3">
              <Sparkles className="w-5 h-5 text-zinc-500" />
            </div>
            <h3 className="text-sm font-semibold text-zinc-200">No matching products found</h3>
            <p className="text-xs text-zinc-500 mt-1">
              Try adjusting your search terms, clearing the subcategory filter, or resetting stock filters.
            </p>
            <button
              onClick={() =>
                setFilters({
                  selectedStore: 'All Stores',
                  selectedDepartment: 'All',
                  selectedGroup: 'All Groups',
                  selectedSubgroup: 'All',
                  searchQuery: '',
                  stockFilter: 'all',
                  sortBy: 'popular',
                })
              }
              className="mt-4 px-3.5 py-1.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-xs font-medium text-zinc-200"
            >
              Reset Filters
            </button>
          </div>
        )}

        {/* Mobile-First Responsive Product Grid */}
        {!loading && !error && filteredProducts.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
            {filteredProducts.map((prod) => (
              <ProductCard
                key={prod.id}
                product={prod}
                onSelect={(p) => setSelectedProduct(p)}
              />
            ))}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-900 bg-zinc-950/80 px-4 py-6 mt-12 text-center text-xs text-zinc-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <p>
            Dropship Product Scraper &amp; Catalog Viewer &bull; Internal Data Showcase
          </p>
          {meta && (
            <p className="font-mono text-[11px] text-zinc-600">
              Last Sync: {new Date(meta.last_updated).toLocaleString()}
            </p>
          )}
        </div>
      </footer>

      {/* Product Detail Slide-Up Modal */}
      <ProductDetailModal
        product={selectedProduct}
        onClose={() => setSelectedProduct(null)}
      />
    </div>
  );
};

export default App;
