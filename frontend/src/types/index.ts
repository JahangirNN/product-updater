export interface VariantOptionValue {
  option_name: string;
  name: string;
}

export interface ProductVariant {
  id?: number | string;
  sku: string;
  title: string;
  price: string;
  compare_at_price?: string | null;
  source_price: number;
  source_compare_at_price?: number | null;
  currency: string;
  source_currency: string;
  in_stock: boolean;
  image_url?: string | null;
  option_values?: VariantOptionValue[];
}

export interface ProductOption {
  name: string;
  values: { name: string }[];
}

export interface CatalogProduct {
  id: string;
  source_store: string;
  source_url: string;
  handle: string;
  title: string;
  vendor: string;
  product_type: string;
  source_sku: string;
  source_price: number;
  source_compare_at_price?: number | null;
  current_price: number;
  compare_at_price?: number | null;
  currency: string;
  source_currency: string;
  forex_rate_used?: number;
  availability: 'in_stock' | 'out_of_stock';
  status: 'ACTIVE' | 'DRAFT';
  material?: string;
  specifications: Record<string, string>;
  descriptionHtml: string;
  images: string[];
  variants: ProductVariant[];
  product_options: ProductOption[];
  tags: string[];
  groups: string[];
  store_display: string;
  group_display: string;
  subgroup_display: string;
  created_at: string;
  updated_at: string;
  validation_warnings?: string[];
}

export interface CatalogMeta {
  total_products: number;
  in_stock: number;
  out_of_stock: number;
  stores: string[];
  groups: string[];
  subgroups: string[];
  price_range_inr: {
    min: number;
    max: number;
  };
  last_updated: string;
  generated_by?: string;
}

export interface FilterState {
  selectedStore: string;
  selectedGroup: string;
  selectedSubgroup: string;
  searchQuery: string;
  stockFilter: 'all' | 'in_stock' | 'out_of_stock';
  sortBy: 'popular' | 'price_asc' | 'price_desc' | 'newest';
}
