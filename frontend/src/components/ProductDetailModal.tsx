import React, { useState } from 'react';
import { X, ExternalLink, Ruler, ShieldCheck, Tag, Box, Info, Sparkles } from 'lucide-react';
import { CatalogProduct } from '../types';
import { RawJsonInspector } from './RawJsonInspector';

interface ProductDetailModalProps {
  product: CatalogProduct | null;
  onClose: () => void;
}

interface ShoeSizeConversion {
  usMen: string;
  usWomen: string;
  uk: string;
  eu: string;
  cm: string;
}

// Official On Running & Nordstrom Conversion Tables
const ON_SHOE_SIZES: ShoeSizeConversion[] = [
  { usMen: '3.5', usWomen: '5', uk: '2.5', eu: '35.5', cm: '22' },
  { usMen: '4', usWomen: '5.5', uk: '3', eu: '36', cm: '22.5' },
  { usMen: '4.5', usWomen: '6', uk: '3.5', eu: '36.5', cm: '23' },
  { usMen: '5', usWomen: '6.5', uk: '4', eu: '37', cm: '23.5' },
  { usMen: '5.5', usWomen: '7', uk: '4.5', eu: '37.5', cm: '24' },
  { usMen: '6', usWomen: '7.5', uk: '5', eu: '38', cm: '24.5' },
  { usMen: '6.5', usWomen: '8', uk: '5.5', eu: '38.5', cm: '25' },
  { usMen: '7', usWomen: '8.5', uk: '6', eu: '39', cm: '25.5' },
  { usMen: '7.5', usWomen: '9', uk: '6.5', eu: '40', cm: '26' },
  { usMen: '8', usWomen: '9.5', uk: '7', eu: '40.5', cm: '26.5' },
  { usMen: '8.5', usWomen: '10', uk: '7.5', eu: '41', cm: '27' },
  { usMen: '9', usWomen: '10.5', uk: '8', eu: '42', cm: '27.5' },
  { usMen: '9.5', usWomen: '11', uk: '8.5', eu: '42.5', cm: '28' },
  { usMen: '10', usWomen: '11.5', uk: '9', eu: '43', cm: '28.5' },
  { usMen: '10.5', usWomen: '12', uk: '9.5', eu: '44', cm: '29' },
  { usMen: '11', usWomen: '12.5', uk: '10', eu: '44.5', cm: '29.5' },
  { usMen: '11.5', usWomen: '13', uk: '10.5', eu: '45', cm: '30' },
  { usMen: '12', usWomen: '13.5', uk: '11', eu: '46', cm: '30.5' },
  { usMen: '12.5', usWomen: '14', uk: '11.5', eu: '47', cm: '31' },
  { usMen: '13', usWomen: '14.5', uk: '12', eu: '47.5', cm: '31.5' },
  { usMen: '13.5', usWomen: '15', uk: '12.5', eu: '48', cm: '32' },
  { usMen: '14', usWomen: '15.5', uk: '13', eu: '48.5', cm: '32.5' },
];

function deriveShoeSize(rawUs: string, rawUk: string, gender: string): ShoeSizeConversion {
  const cleanUs = rawUs.replace(/[^0-9.]/g, '');
  const cleanUk = rawUk.replace(/[^0-9.]/g, '');
  const isWomen = gender.toLowerCase().includes('women');

  // Try matching by UK first (UK is gender-neutral foot length)
  if (cleanUk) {
    const match = ON_SHOE_SIZES.find((s) => parseFloat(s.uk) === parseFloat(cleanUk));
    if (match) return match;
  }

  // Try matching by US depending on gender
  if (cleanUs) {
    const match = ON_SHOE_SIZES.find((s) =>
      isWomen
        ? parseFloat(s.usWomen) === parseFloat(cleanUs)
        : parseFloat(s.usMen) === parseFloat(cleanUs)
    );
    if (match) return match;
  }

  // Fallback if size is outside standard array
  const usNum = parseFloat(cleanUs) || 0;
  const ukNum = parseFloat(cleanUk) || (isWomen ? Math.max(0, usNum - 2) : Math.max(0, usNum - 0.5));
  const usMen = isWomen ? (usNum > 0 ? (usNum - 1.5).toString() : (ukNum + 0.5).toString()) : usNum.toString();
  const usWomen = isWomen ? usNum.toString() : (usNum > 0 ? (usNum + 1.5).toString() : (ukNum + 2).toString());
  const eu = (33 + (parseFloat(usMen) || ukNum) * 1.0).toFixed(0);
  const cm = (21 + ukNum * 0.8).toFixed(1);

  return { usMen, usWomen, uk: ukNum.toString(), eu, cm };
}

export const ProductDetailModal: React.FC<ProductDetailModalProps> = ({ product, onClose }) => {
  if (!product) return null;

  const [activeImageIndex, setActiveImageIndex] = useState(0);
  const images = product.images && product.images.length > 0
    ? product.images
    : ['https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=800&q=80'];

  const isSoldOut = product.availability !== 'in_stock';
  const specs = product.specifications || {};

  const grp = product.group_display?.toLowerCase() || '';
  const pt = product.product_type?.toLowerCase() || '';
  const store = product.source_store?.toLowerCase() || '';

  const isShoe = 
    store === 'nordstrom' || 
    grp === 'shoes' || 
    grp.includes('shoe') || 
    grp.includes('sneaker') || 
    grp.includes('sandal') || 
    grp.includes('flat') || 
    grp.includes('boot') ||
    ['shoes', 'sneakers', 'sandals', 'flats', 'boots'].includes(pt);

  const isBelt = grp.includes('belt') || pt === 'belts';

  const dimensions = specs['Bag Dimensions'] || specs['Dimension'] || specs['Dimensions'] || 'N/A';
  const handleDrop = specs['Handle Drop'] || specs['HandleDrop'] || 'N/A';
  const strapDrop = specs['Shoulder Strap Drop'] || 'N/A';
  const hardware = specs['Hardware'] || specs['Hardware Finish'] || 'N/A';
  const lining = specs['Lining Material'] || specs['Lining'] || 'N/A';
  const capacity = specs['Capacity'] || 'N/A';
  const carryingStyle = specs['Carrying Style'] || specs['Carrying Method'] || product.subgroup_display;

  // Shoe / Belt specific specs
  const gender = product.gender || specs['Gender'] || 'Unisex';
  const midsoleDrop = specs['Midsole Drop'] || '8mm';
  const cushioning = specs['Cushioning'] || 'CloudTec cushioning';
  const shoeMaterial = product.material || specs['Material'] || 'Textile and synthetic upper';

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/80 backdrop-blur-md transition-opacity animate-in fade-in"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-2xl bg-zinc-950 border border-zinc-800 rounded-t-3xl sm:rounded-3xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden animate-in slide-in-from-bottom sm:zoom-in-95 duration-200"
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-zinc-800/80 bg-zinc-900/60 sticky top-0 z-10">
          <div className="flex items-center gap-2 truncate pr-4">
            <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
              {product.source_sku}
            </span>
            <span className="text-xs text-zinc-400 font-medium truncate">
              {product.store_display} &bull; {product.group_display}
            </span>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-full text-zinc-400 hover:text-white bg-zinc-800/60 hover:bg-zinc-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="overflow-y-auto p-4 sm:p-6 space-y-6">
          {/* Main Gallery Carousel */}
          <div className="space-y-2">
            <div className="relative aspect-[4/3] w-full rounded-2xl overflow-hidden bg-zinc-900 border border-zinc-800">
              <img
                src={images[activeImageIndex]}
                alt={product.title}
                className="w-full h-full object-contain object-center"
              />

              {/* Status Badge */}
              <div className="absolute top-3 left-3">
                <span
                  className={`text-xs font-bold px-2.5 py-1 rounded-full flex items-center gap-1.5 shadow-md ${
                    isSoldOut
                      ? 'bg-rose-950/90 text-rose-300 border border-rose-500/30'
                      : 'bg-emerald-950/90 text-emerald-300 border border-emerald-500/30'
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      isSoldOut ? 'bg-rose-400' : 'bg-emerald-400 animate-pulse'
                    }`}
                  />
                  {isSoldOut ? 'Out of Stock' : 'In Stock'}
                </span>
              </div>
            </div>

            {/* Thumbnail Strip */}
            {images.length > 1 && (
              <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
                {images.map((img, i) => (
                  <button
                    key={i}
                    onClick={() => setActiveImageIndex(i)}
                    className={`relative w-14 h-14 rounded-xl overflow-hidden border-2 transition-all flex-shrink-0 ${
                      activeImageIndex === i
                        ? 'border-amber-400 scale-105 shadow-glow-gold'
                        : 'border-zinc-800 opacity-60 hover:opacity-100'
                    }`}
                  >
                    <img src={img} alt="" className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Title, Brand & Pricing Banner */}
          <div className="space-y-2 pb-4 border-b border-zinc-800/80">
            <div className="flex items-center justify-between text-xs text-amber-400 font-mono">
              <span>{product.vendor}</span>
              <span>Status: <strong className="text-white">{product.status}</strong></span>
            </div>

            <h2 className="text-base sm:text-xl font-bold text-white leading-snug">
              {product.title}
            </h2>

            {/* Dual Currency Display */}
            <div className="pt-2 flex flex-wrap items-baseline justify-between gap-3 bg-zinc-900/60 p-3.5 rounded-2xl border border-zinc-800">
              <div>
                <div className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold">
                  Shopify Storefront Price (INR)
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-xl sm:text-2xl font-extrabold text-white">
                    ₹{product.current_price?.toLocaleString('en-IN')}
                  </span>
                  {product.compare_at_price && product.compare_at_price > product.current_price && (
                    <span className="text-sm text-zinc-500 line-through">
                      ₹{product.compare_at_price?.toLocaleString('en-IN')}
                    </span>
                  )}
                </div>
              </div>

              <div className="text-right">
                <div className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold">
                  Original Source Price
                </div>
                <div className="text-base font-mono font-bold text-amber-400">
                  ${product.source_price?.toFixed(2)} USD
                </div>
                {product.forex_rate_used && (
                  <div className="text-[10px] text-zinc-500 font-mono">
                    Rate: 1 USD ≈ ₹{product.forex_rate_used.toFixed(2)}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Interactive Size & Measurement Guide Table */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-bold text-zinc-200">
              <Ruler className="w-4 h-4 text-amber-400" />
              <span>
                {isShoe 
                  ? `Footwear Size & Conversion Matrix (${gender})` 
                  : isBelt 
                  ? `Belt Size & Measurement Guide (${gender})` 
                  : 'Size & Measurement Guide'}
              </span>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 overflow-hidden">
              {isShoe ? (
                <div className="max-h-64 overflow-y-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-zinc-800/80 text-zinc-400 font-semibold sticky top-0">
                      <tr>
                        <th className="px-3 py-2">US Size</th>
                        <th className="px-3 py-2">UK Size</th>
                        <th className="px-3 py-2">EU Size</th>
                        <th className="px-3 py-2">Color / Variant</th>
                        <th className="px-3 py-2">Price</th>
                        <th className="px-3 py-2 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/60 font-mono">
                      {product.variants.map((v: any, i: number) => {
                        let us = v.size_us || '';
                        let uk = v.size_uk || '';
                        let eu = v.size_eu || '';
                        let color = '';

                        if (v.title) {
                          const m = v.title.match(/US\s*([\d.]+)(?:\s*\/\s*UK\s*([\d.]+))?(?:\s*-\s*(.*))?/i);
                          if (m) {
                            us = us || m[1];
                            uk = uk || m[2];
                            color = color || m[3];
                          } else {
                            const conv = deriveShoeSize(v.title, '', gender);
                            us = us || (gender.toLowerCase().includes('women') ? conv.usWomen : conv.usMen);
                            uk = uk || conv.uk;
                            eu = eu || conv.eu;
                          }
                          if (!color && v.title.includes(' - ')) {
                            color = v.title.split(' - ').pop() || '';
                          }
                        }

                        return (
                          <tr key={i} className="hover:bg-zinc-800/30">
                            <td className="px-3 py-2 font-bold text-white">{us ? `US ${us}` : '-'}</td>
                            <td className="px-3 py-2 font-semibold text-amber-400">{uk ? `UK ${uk}` : '-'}</td>
                            <td className="px-3 py-2 text-zinc-300">{eu ? `EU ${eu}` : '-'}</td>
                            <td className="px-3 py-2 text-zinc-400 font-sans truncate max-w-[120px]">{color || 'Standard'}</td>
                            <td className="px-3 py-2 text-zinc-200 whitespace-nowrap">₹{parseFloat(v.price || '0').toLocaleString('en-IN')}</td>
                            <td className="px-3 py-2 text-right whitespace-nowrap">
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${v.in_stock ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'}`}>
                                {v.in_stock ? 'In Stock' : 'Sold Out'}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : isBelt ? (
                <div className="max-h-64 overflow-y-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-zinc-800/80 text-zinc-400 font-semibold sticky top-0">
                      <tr>
                        <th className="px-3 py-2">Size</th>
                        <th className="px-3 py-2">Waist Measurement</th>
                        <th className="px-3 py-2">Color</th>
                        <th className="px-3 py-2">Price</th>
                        <th className="px-3 py-2 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/60 font-mono">
                      {product.variants.map((v: any, i: number) => {
                        const title = v.title || '';
                        let size = v.size || '';
                        let waist = '';
                        let color = '';
                        const match = title.match(/^([SMLX]+)\s*(?:\(([^)]+)\))?(?:\s*-\s*(.*))?/i);
                        if (match) {
                          size = size || match[1];
                          waist = match[2] || '';
                          color = match[3] || '';
                        }
                        if (!waist) {
                          if (size === 'S') waist = '32"';
                          else if (size === 'M') waist = '34"';
                          else if (size === 'L') waist = '36"';
                          else if (size === 'XL') waist = '38"';
                        }
                        return (
                          <tr key={i} className="hover:bg-zinc-800/30">
                            <td className="px-3 py-2 font-bold text-white">{size || title}</td>
                            <td className="px-3 py-2 text-amber-300 font-medium">{waist ? `Fits waist ${waist}` : '-'}</td>
                            <td className="px-3 py-2 text-zinc-400 font-sans">{color || 'Standard'}</td>
                            <td className="px-3 py-2 text-zinc-200 whitespace-nowrap">₹{parseFloat(v.price || '0').toLocaleString('en-IN')}</td>
                            <td className="px-3 py-2 text-right whitespace-nowrap">
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${v.in_stock ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'}`}>
                                {v.in_stock ? 'In Stock' : 'Sold Out'}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <table className="w-full text-xs text-left">
                  <tbody>
                    <tr className="border-b border-zinc-800/60">
                      <td className="px-4 py-2.5 font-semibold text-zinc-400 w-2/5">Dimensions</td>
                      <td className="px-4 py-2.5 font-mono text-zinc-100">{dimensions}</td>
                    </tr>
                    <tr className="border-b border-zinc-800/60">
                      <td className="px-4 py-2.5 font-semibold text-zinc-400">Handle Drop</td>
                      <td className="px-4 py-2.5 font-mono text-zinc-100">{handleDrop}</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-2.5 font-semibold text-zinc-400">Shoulder Strap Drop</td>
                      <td className="px-4 py-2.5 font-mono text-zinc-100">{strapDrop}</td>
                    </tr>
                  </tbody>
                </table>
              )}
            </div>
          </div>

          {/* Specifications Breakdown */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-bold text-zinc-200">
              <Box className="w-4 h-4 text-amber-400" />
              <span>Product Specifications</span>
            </div>

            {isShoe ? (
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
                  <span className="text-zinc-500 block text-[10px] uppercase font-semibold">Gender</span>
                  <span className="text-zinc-200 font-medium">{gender}</span>
                </div>
                <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
                  <span className="text-zinc-500 block text-[10px] uppercase font-semibold">Category / Silhouette</span>
                  <span className="text-zinc-200 font-medium">{product.subgroup_display || product.group_display}</span>
                </div>
                <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 col-span-2">
                  <span className="text-zinc-500 block text-[10px] uppercase font-semibold">Material</span>
                  <span className="text-zinc-200 font-medium">{product.material || shoeMaterial}</span>
                </div>
                {specs['DetailsBullets'] && Array.isArray(specs['DetailsBullets']) && (specs['DetailsBullets'] as any).length > 0 && (
                  <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 col-span-2">
                    <span className="text-zinc-500 block text-[10px] uppercase font-semibold mb-1">Highlights</span>
                    <ul className="list-disc pl-4 space-y-0.5 text-zinc-300">
                      {(specs['DetailsBullets'] as any).slice(0, 4).map((b: string, idx: number) => (
                        <li key={idx}>{b}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : isBelt ? (
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
                  <span className="text-zinc-500 block text-[10px] uppercase font-semibold">Gender</span>
                  <span className="text-zinc-200 font-medium">{gender}</span>
                </div>
                <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
                  <span className="text-zinc-500 block text-[10px] uppercase font-semibold">Style</span>
                  <span className="text-zinc-200 font-medium">{product.subgroup_display}</span>
                </div>
                <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 col-span-2">
                  <span className="text-zinc-500 block text-[10px] uppercase font-semibold">Material</span>
                  <span className="text-zinc-200 font-medium">{product.material || '100% Leather'}</span>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
                  <span className="text-zinc-500 block text-[10px] uppercase font-semibold">Material</span>
                  <span className="text-zinc-200 font-medium">{product.material || 'Vegan Leather'}</span>
                </div>
                <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
                  <span className="text-zinc-500 block text-[10px] uppercase font-semibold">Lining</span>
                  <span className="text-zinc-200 font-medium">{lining}</span>
                </div>
                <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
                  <span className="text-zinc-500 block text-[10px] uppercase font-semibold">Hardware</span>
                  <span className="text-zinc-200 font-medium">{hardware}</span>
                </div>
                <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
                  <span className="text-zinc-500 block text-[10px] uppercase font-semibold">Carrying Style</span>
                  <span className="text-zinc-200 font-medium">{carryingStyle}</span>
                </div>
                <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 col-span-2">
                  <span className="text-zinc-500 block text-[10px] uppercase font-semibold">Capacity</span>
                  <span className="text-zinc-200 font-medium">{capacity}</span>
                </div>
              </div>
            )}
          </div>

          {/* Official Retailer Description & Size Guide Accordion */}
          {product.descriptionHtml && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-bold text-zinc-200">
                <Info className="w-4 h-4 text-amber-400" />
                <span>Retailer Description & Specifications</span>
              </div>
              <div 
                className="p-4 rounded-2xl border border-zinc-800 bg-zinc-900/40 text-xs text-zinc-300 leading-relaxed max-h-60 overflow-y-auto [&_.size-guide-accordion]:border-zinc-800 [&_.size-guide-accordion]:bg-zinc-900/70 [&_.size-guide-accordion_table]:border-zinc-700 [&_.size-guide-accordion_td]:border-zinc-800 [&_.size-guide-accordion_th]:border-zinc-800 [&_.size-guide-accordion_th]:bg-zinc-800"
                dangerouslySetInnerHTML={{ __html: product.descriptionHtml }}
              />
            </div>
          )}

          {/* Supplier Link Action */}
          <div className="pt-2">
            <a
              href={product.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-100 text-xs font-semibold transition-all shadow-sm"
            >
              <span>View on Retailer Website ({product.vendor})</span>
              <ExternalLink className="w-3.5 h-3.5 text-zinc-400" />
            </a>
          </div>

          {/* Collapsible Raw JSON Inspector */}
          <RawJsonInspector data={product} title="Raw Database Record (Canonical JSON)" />
        </div>
      </div>
    </div>
  );
};
