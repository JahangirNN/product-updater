import React, { useState } from 'react';
import { Layers, Eye, CheckCircle2, AlertCircle, Sparkles } from 'lucide-react';
import { CatalogProduct } from '../types';

interface ProductCardProps {
  product: CatalogProduct;
  onSelect: (product: CatalogProduct) => void;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product, onSelect }) => {
  const [imgLoaded, setImgLoaded] = useState(false);
  const primaryImg = product.images && product.images.length > 0
    ? product.images[0]
    : 'https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=600&q=80';

  const isSoldOut = product.availability !== 'in_stock';
  const colorName = product.variants[0]?.title && product.variants[0]?.title !== 'Default Title'
    ? product.variants[0].title
    : product.title.includes(' - ')
      ? product.title.split(' - ').pop()
      : null;

  const rawDims = product.specifications?.['Bag Dimensions'] || product.specifications?.['Dimension'] || '';
  // Clean short dimensions for card chip
  const shortDims = rawDims.split('(')[0].trim();

  return (
    <div
      onClick={() => onSelect(product)}
      className="group relative flex flex-col bg-zinc-900/60 hover:bg-zinc-900/90 rounded-2xl border border-zinc-800/80 hover:border-amber-500/40 transition-all duration-300 overflow-hidden cursor-pointer shadow-sm hover:shadow-glow-gold active:scale-[0.99]"
    >
      {/* Image Container with Badges */}
      <div className="relative aspect-[4/5] w-full overflow-hidden bg-zinc-950">
        {!imgLoaded && (
          <div className="absolute inset-0 bg-zinc-800 animate-pulse flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-zinc-600 animate-spin" />
          </div>
        )}
        <img
          src={primaryImg}
          alt={product.title}
          loading="lazy"
          onLoad={() => setImgLoaded(true)}
          className={`h-full w-full object-cover object-center transition-transform duration-500 group-hover:scale-105 ${
            imgLoaded ? 'opacity-100' : 'opacity-0'
          } ${isSoldOut ? 'grayscale-[0.4] opacity-80' : ''}`}
        />

        {/* Top Floating Badges */}
        <div className="absolute top-2.5 left-2.5 right-2.5 flex items-center justify-between gap-1 pointer-events-none">
          {/* Subgroup / Carrying Style */}
          <span className="glass-pill text-[10px] font-semibold text-zinc-300 px-2 py-0.5 rounded-md uppercase tracking-wider">
            {product.subgroup_display}
          </span>

          {/* Stock Status Pill */}
          <span
            className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 shadow-md ${
              isSoldOut
                ? 'bg-rose-950/90 text-rose-300 border border-rose-500/30'
                : 'bg-emerald-950/90 text-emerald-300 border border-emerald-500/30'
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isSoldOut ? 'bg-rose-400' : 'bg-emerald-400 animate-pulse'
              }`}
            />
            {isSoldOut ? 'Sold Out' : 'In Stock'}
          </span>
        </div>

        {/* Bottom Floating Photos Count */}
        {product.images && product.images.length > 1 && (
          <div className="absolute bottom-2 right-2 glass-pill text-[10px] font-mono text-zinc-300 px-1.5 py-0.5 rounded-md flex items-center gap-1 pointer-events-none">
            <Layers className="w-3 h-3 text-zinc-400" />
            <span>{product.images.length}</span>
          </div>
        )}

        {/* Quick View Hover Indicator */}
        <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center pointer-events-none">
          <span className="glass-pill text-white text-xs font-semibold px-3 py-1.5 rounded-xl flex items-center gap-1.5 shadow-lg transform translate-y-2 group-hover:translate-y-0 transition-transform">
            <Eye className="w-3.5 h-3.5 text-amber-400" />
            Quick Inspect
          </span>
        </div>
      </div>

      {/* Content Body */}
      <div className="p-3 sm:p-3.5 flex flex-col flex-1 justify-between gap-2.5">
        <div>
          {/* Brand & SKU */}
          <div className="flex items-center justify-between text-[11px] text-zinc-500 font-mono mb-1">
            <span className="font-semibold text-amber-400/90">{product.vendor}</span>
            <span className="truncate max-w-[110px]">{product.source_sku}</span>
          </div>

          {/* Title */}
          <h3 className="text-xs sm:text-sm font-semibold text-zinc-100 line-clamp-2 leading-snug group-hover:text-amber-300 transition-colors">
            {product.title}
          </h3>

          {/* Color Tag if available */}
          {colorName && (
            <div className="mt-1.5 flex items-center gap-1 text-[11px] text-zinc-400">
              <span className="w-2 h-2 rounded-full bg-zinc-400/80 inline-block" />
              <span className="truncate">{colorName}</span>
            </div>
          )}
        </div>

        {/* Specification Chips */}
        <div className="flex flex-wrap items-center gap-1 text-[10px]">
          {product.material && (
            <span className="px-2 py-0.5 rounded-md bg-zinc-800/80 text-zinc-300 border border-zinc-700/40 truncate max-w-[140px]">
              {product.material}
            </span>
          )}
          {shortDims && (
            <span className="px-2 py-0.5 rounded-md bg-zinc-800/80 text-zinc-400 border border-zinc-700/40 font-mono">
              📏 {shortDims.slice(0, 18)}
            </span>
          )}
        </div>

        {/* Pricing Area (Dual Currency) */}
        <div className="pt-2 border-t border-zinc-800/60 flex items-baseline justify-between">
          <div>
            {/* Primary INR Price */}
            <div className="flex items-baseline gap-1.5">
              <span className="text-sm sm:text-base font-bold text-white tracking-tight">
                ₹{product.current_price?.toLocaleString('en-IN')}
              </span>
              {product.compare_at_price && product.compare_at_price > product.current_price && (
                <span className="text-[11px] text-zinc-500 line-through">
                  ₹{product.compare_at_price?.toLocaleString('en-IN')}
                </span>
              )}
            </div>
          </div>

          {/* Secondary Source USD Price */}
          <div className="text-[11px] font-mono text-amber-400/80 font-medium">
            ${product.source_price?.toFixed(2)} USD
          </div>
        </div>
      </div>
    </div>
  );
};
