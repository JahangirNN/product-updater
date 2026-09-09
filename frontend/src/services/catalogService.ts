import { CatalogProduct, CatalogMeta, FilterState } from '../types';

let cachedCatalog: CatalogProduct[] | null = null;
let cachedMeta: CatalogMeta | null = null;

export async function fetchCatalogData(): Promise<{ products: CatalogProduct[]; meta: CatalogMeta }> {
  if (cachedCatalog && cachedMeta) {
    return { products: cachedCatalog, meta: cachedMeta };
  }

  try {
    // Relative path works both in dev server and on GitHub Pages subpaths
    const [catResp, metaResp] = await Promise.all([
      fetch('./data/catalog.json'),
      fetch('./data/meta.json')
    ]);

    if (!catResp.ok) {
      throw new Error(`Failed to load catalog.json: ${catResp.status}`);
    }

    const products: CatalogProduct[] = await catResp.json();
    const meta: CatalogMeta = metaResp.ok
      ? await metaResp.json()
      : {
          total_products: products.length,
          in_stock: products.filter(p => p.availability === 'in_stock').length,
          out_of_stock: products.filter(p => p.availability !== 'in_stock').length,
          stores: Array.from(new Set(products.map(p => p.store_display))),
          groups: Array.from(new Set(products.map(p => p.group_display))),
          subgroups: Array.from(new Set(products.map(p => p.subgroup_display))),
          price_range_inr: {
            min: Math.min(...products.map(p => p.current_price || 0)),
            max: Math.max(...products.map(p => p.current_price || 0))
          },
          last_updated: new Date().toISOString()
        };

    cachedCatalog = products;
    cachedMeta = meta;

    return { products, meta };
  } catch (err) {
    console.error('Failed to load catalog data:', err);
    throw err;
  }
}

export function filterAndSortProducts(
  products: CatalogProduct[],
  filters: FilterState
): CatalogProduct[] {
  let result = [...products];

  // 1. Store Filter (Level 1)
  if (filters.selectedStore && filters.selectedStore !== 'All Stores') {
    result = result.filter(p => p.store_display === filters.selectedStore);
  }

  // 2. Group Filter (Level 2)
  if (filters.selectedGroup && filters.selectedGroup !== 'All Groups') {
    result = result.filter(p => p.group_display === filters.selectedGroup);
  }

  // 3. Subgroup Filter (Level 3)
  if (filters.selectedSubgroup && filters.selectedSubgroup !== 'All') {
    result = result.filter(p => p.subgroup_display === filters.selectedSubgroup);
  }

  // 4. Stock Filter
  if (filters.stockFilter === 'in_stock') {
    result = result.filter(p => p.availability === 'in_stock');
  } else if (filters.stockFilter === 'out_of_stock') {
    result = result.filter(p => p.availability !== 'in_stock');
  }

  // 5. Search Query (Title, SKU, Handle, Material, Color)
  if (filters.searchQuery.trim()) {
    const q = filters.searchQuery.toLowerCase().trim();
    result = result.filter(p => {
      const titleMatch = p.title.toLowerCase().includes(q);
      const skuMatch = p.source_sku.toLowerCase().includes(q);
      const handleMatch = p.handle.toLowerCase().includes(q);
      const materialMatch = (p.material || '').toLowerCase().includes(q);
      const colorMatch = (p.variants[0]?.title || '').toLowerCase().includes(q);
      return titleMatch || skuMatch || handleMatch || materialMatch || colorMatch;
    });
  }

  // 6. Sorting
  if (filters.sortBy === 'price_asc') {
    result.sort((a, b) => (a.current_price || 0) - (b.current_price || 0));
  } else if (filters.sortBy === 'price_desc') {
    result.sort((a, b) => (b.current_price || 0) - (a.current_price || 0));
  } else if (filters.sortBy === 'newest') {
    result.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  } else {
    // Default: 'popular' (in stock first, then original catalog order)
    result.sort((a, b) => {
      const aStock = a.availability === 'in_stock' ? 0 : 1;
      const bStock = b.availability === 'in_stock' ? 0 : 1;
      return aStock - bStock;
    });
  }

  return result;
}
