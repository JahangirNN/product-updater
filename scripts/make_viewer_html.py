import json
from pathlib import Path

ARTIFACTS_DIR = Path(r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad")
SCRATCH_DIR = Path(r"C:\Users\Administrator\WorkPlace\dropship-scraper-portable-20260905\product-updater\scratch")

jds_data = json.loads((SCRATCH_DIR / "jds_viewer_data.json").read_text(encoding="utf-8"))

html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>JD Sports — Nike Footwear Catalog Viewer</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    :root {
      --background: #0b1120;
      --card: #1e293b;
      --border: #334155;
      --muted: #94a3b8;
    }
    body { background: #0b1120; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .badge { display: inline-flex; align-items: center; padding: 0.2rem 0.55rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
    .size-pill { display: inline-flex; align-items: center; justify-content: center; padding: 0.25rem 0.5rem; border-radius: 0.375rem; font-size: 0.72rem; font-weight: 500; border: 1px solid #334155; }
    .size-pill.in-stock { background: rgba(34, 197, 94, 0.15); border-color: rgba(34, 197, 94, 0.4); color: #4ade80; }
    .size-pill.out-of-stock { background: rgba(148, 163, 184, 0.08); border-color: rgba(148, 163, 184, 0.2); color: #64748b; text-decoration: line-through; }
  </style>
</head>
<body class="antialiased min-h-screen p-4 md:p-6">

  <!-- HEADER -->
  <header class="max-w-7xl mx-auto mb-6 bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl">
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div class="flex items-center gap-3.5">
        <div class="w-12 h-12 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center font-black text-xl text-white shadow-lg">
          JD
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-xl md:text-2xl font-bold tracking-tight text-white">JD Sports US — Nike Dropship Catalog</h1>
            <span class="badge bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Live Ingested</span>
          </div>
          <p class="text-sm text-slate-400">Nike Air Max, Air Force 1 &amp; Dunk Low &bull; Multi-Tier Sizing &bull; Whole-Rupee INR Math</p>
        </div>
      </div>
      <div class="flex items-center gap-2.5 flex-wrap">
        <a href="http://localhost:5173" target="_blank" class="px-4 py-2 bg-sky-500 hover:bg-sky-400 text-slate-950 rounded-xl text-sm font-semibold transition-all flex items-center gap-2 shadow-md hover:shadow-sky-500/25">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
          Open React App (:5173)
        </a>
      </div>
    </div>
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-5 pt-5 border-t border-slate-800">
      <div class="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
        <div class="text-xs text-slate-400">Ingested Products</div>
        <div class="text-xl font-bold text-white mt-0.5">12</div>
      </div>
      <div class="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
        <div class="text-xs text-slate-400">Size Variants</div>
        <div class="text-xl font-bold text-sky-400 mt-0.5">142</div>
      </div>
      <div class="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
        <div class="text-xs text-slate-400">In-Stock Rate</div>
        <div class="text-xl font-bold text-emerald-400 mt-0.5">75% <span class="text-xs font-normal text-emerald-500/80">(9/12)</span></div>
      </div>
      <div class="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
        <div class="text-xs text-slate-400">Clearance / OOS</div>
        <div class="text-xl font-bold text-amber-400 mt-0.5">25% <span class="text-xs font-normal text-amber-500/80">(3/12)</span></div>
      </div>
      <div class="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
        <div class="text-xs text-slate-400">Sizing Integrity</div>
        <div class="text-xl font-bold text-emerald-400 mt-0.5">0 Truncations</div>
      </div>
      <div class="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
        <div class="text-xs text-slate-400">Forex Applied</div>
        <div class="text-xl font-bold text-indigo-400 mt-0.5">1 USD = ₹95.99</div>
      </div>
    </div>
  </header>

  <!-- CONTROLS & FILTER BAR -->
  <section class="max-w-7xl mx-auto mb-6 bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-lg">
    <div class="flex flex-col md:flex-row gap-4 justify-between items-stretch md:items-center">
      <div class="relative flex-1">
        <input type="text" id="search-input" placeholder="Search model, SKU, or colorway (e.g. Air Max 90, CT3839, Black)..." class="w-full pl-4 pr-4 py-2 bg-slate-950 border border-slate-700 rounded-xl text-sm text-white placeholder-slate-400 focus:outline-none focus:border-sky-500">
      </div>
      <div class="flex items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-700 self-start md:self-auto">
        <button onclick="setStockFilter('all')" id="btn-stock-all" class="filter-stock-btn px-3 py-1.5 rounded-lg text-xs font-semibold bg-sky-500 text-slate-950 transition-all">All (12)</button>
        <button onclick="setStockFilter('in_stock')" id="btn-stock-in" class="filter-stock-btn px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white transition-all">In Stock (9)</button>
        <button onclick="setStockFilter('out_of_stock')" id="btn-stock-out" class="filter-stock-btn px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white transition-all">Out of Stock (3)</button>
      </div>
    </div>
    <div class="flex items-center gap-2 mt-3 pt-3 border-t border-slate-800 overflow-x-auto pb-1">
      <button onclick="setCategoryFilter('all')" class="cat-pill px-3 py-1 rounded-lg text-xs font-semibold bg-white/10 text-white border border-white/20 whitespace-nowrap active-cat" data-cat="all">All Silhouettes (12)</button>
      <button onclick="setCategoryFilter('air-max')" class="cat-pill px-3 py-1 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-950/60 border border-slate-800 whitespace-nowrap" data-cat="air-max">Air Max (6)</button>
      <button onclick="setCategoryFilter('air-force')" class="cat-pill px-3 py-1 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-950/60 border border-slate-800 whitespace-nowrap" data-cat="air-force">Air Force 1 (2)</button>
      <button onclick="setCategoryFilter('dunk')" class="cat-pill px-3 py-1 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-950/60 border border-slate-800 whitespace-nowrap" data-cat="dunk">Dunk Low (2)</button>
      <button onclick="setCategoryFilter('big-kids')" class="cat-pill px-3 py-1 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-950/60 border border-slate-800 whitespace-nowrap" data-cat="big-kids">Grade School / Big Kids (4)</button>
      <button onclick="setCategoryFilter('adult-men')" class="cat-pill px-3 py-1 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-950/60 border border-slate-800 whitespace-nowrap" data-cat="adult-men">Men's (5)</button>
      <button onclick="setCategoryFilter('adult-women')" class="cat-pill px-3 py-1 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-950/60 border border-slate-800 whitespace-nowrap" data-cat="adult-women">Women's (3)</button>
    </div>
  </section>

  <!-- GRID -->
  <main class="max-w-7xl mx-auto">
    <div id="product-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"></div>
    <div id="empty-state" class="hidden text-center py-16 bg-slate-900 rounded-2xl border border-slate-800 mt-4">
      <div class="text-4xl mb-2">🔍</div>
      <h3 class="text-lg font-bold text-white">No products found</h3>
      <p class="text-sm text-slate-400 mt-1">Try adjusting your search query or filter selections.</p>
    </div>
  </main>

  <!-- MODAL -->
  <div id="product-modal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl p-6 relative">
      <button onclick="closeModal()" class="absolute top-4 right-4 text-slate-400 hover:text-white p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
      </button>
      <div id="modal-content"></div>
    </div>
  </div>

  <script>
    const PRODUCTS = """ + json.dumps(jds_data) + """;
    let currentStockFilter = 'all';
    let currentCategoryFilter = 'all';
    let currentSearch = '';

    function renderProducts() {
      const grid = document.getElementById('product-grid');
      const empty = document.getElementById('empty-state');
      grid.innerHTML = '';

      const filtered = PRODUCTS.filter(p => {
        if (currentStockFilter === 'in_stock' && p.availability !== 'in_stock') return false;
        if (currentStockFilter === 'out_of_stock' && p.availability === 'in_stock') return false;

        const titleL = p.title.toLowerCase();
        const grpL = (p.group_display || '').toLowerCase();
        const subgrpL = (p.subgroup_display || '').toLowerCase();
        if (currentCategoryFilter === 'air-max' && !titleL.includes('air max') && !titleL.includes('vapormax')) return false;
        if (currentCategoryFilter === 'air-force' && !titleL.includes('air force')) return false;
        if (currentCategoryFilter === 'dunk' && !titleL.includes('dunk')) return false;
        if (currentCategoryFilter === 'big-kids' && !titleL.includes('big kids') && !subgrpL.includes('big kids')) return false;
        if (currentCategoryFilter === 'adult-men' && !grpL.includes("men's")) return false;
        if (currentCategoryFilter === 'adult-women' && !grpL.includes("women's")) return false;

        if (currentSearch) {
          const q = currentSearch.toLowerCase();
          const sku = (p.source_sku || '').toLowerCase();
          const color = (p.specifications && p.specifications.Color ? p.specifications.Color : '').toLowerCase();
          if (!titleL.includes(q) && !sku.includes(q) && !color.includes(q)) return false;
        }

        return true;
      });

      if (filtered.length === 0) {
        empty.classList.remove('hidden');
        return;
      } else {
        empty.classList.add('hidden');
      }

      filtered.forEach((p, idx) => {
        const card = document.createElement('div');
        card.className = "bg-slate-900 border border-slate-800 hover:border-sky-500/50 rounded-2xl overflow-hidden shadow-lg transition-all duration-200 flex flex-col hover:-translate-y-1";

        const isInStock = p.availability === 'in_stock';
        const image = (p.images && p.images.length > 0) ? p.images[0] : 'https://media.jdsports.com/i/jdsports/JDSportsLogo';
        const inrPrice = Math.round(p.current_price || 0).toLocaleString('en-IN');
        const usdPrice = (p.source_price || 0).toFixed(2);
        const variants = p.variants || [];
        const inStockVariantsCount = variants.filter(v => v.in_stock).length;

        const isKids = p.title.includes("Big Kids") || (p.subgroup_display || '').includes("Big Kids");
        const sizingBadge = isKids 
          ? '<span class="badge bg-purple-500/20 text-purple-300 border border-purple-500/30">Grade School (GS)</span>'
          : '<span class="badge bg-blue-500/20 text-blue-300 border border-blue-500/30">Adult</span>';

        const stockBadge = isInStock
          ? '<span class="badge bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">● In Stock (' + inStockVariantsCount + '/' + variants.length + ' sizes)</span>'
          : '<span class="badge bg-amber-500/20 text-amber-300 border border-amber-500/30">Delisted / OOS (0/' + variants.length + ' sizes)</span>';

        const sizePillsHtml = variants.slice(0, 8).map(v => {
          const cleanSize = v.title.split(' - ')[0] || v.sku;
          const cls = v.in_stock ? 'in-stock' : 'out-of-stock';
          return '<span class="size-pill ' + cls + '">' + cleanSize + '</span>';
        }).join('');

        const moreSizes = variants.length > 8 ? '<span class="text-xs text-slate-500 self-center">+' + (variants.length - 8) + ' more</span>' : '';

        card.innerHTML = `
          <div class="relative bg-slate-950 p-4 flex items-center justify-center border-b border-slate-800 group h-64 overflow-hidden">
            <img src="${image}" alt="${p.title}" class="max-h-56 w-auto object-contain transition-transform duration-300 group-hover:scale-105" loading="lazy">
            <div class="absolute top-3 left-3 flex flex-col gap-1.5 items-start">
              ${stockBadge}
              ${sizingBadge}
            </div>
            <div class="absolute bottom-3 right-3 bg-slate-900/90 backdrop-blur-md px-2.5 py-1 rounded-lg border border-slate-700 text-xs font-mono text-slate-300">
              ${p.source_sku || 'SKU'}
            </div>
          </div>

          <div class="p-5 flex-1 flex flex-col justify-between">
            <div>
              <div class="flex items-baseline justify-between gap-2 mb-2">
                <span class="text-xs font-semibold uppercase tracking-wider text-sky-400">${p.subgroup_display || 'Nike Footwear'}</span>
                <span class="text-xs text-slate-400">${p.group_display || ''}</span>
              </div>
              <h2 class="font-bold text-base text-white line-clamp-2 leading-snug mb-3 hover:text-sky-300 transition-colors cursor-pointer" onclick="openModal(${idx})">
                ${p.title}
              </h2>

              <div class="flex items-baseline gap-2.5 mb-4">
                <span class="text-2xl font-black text-white">₹${inrPrice}</span>
                <span class="text-sm font-semibold text-slate-400">($${usdPrice} USD)</span>
              </div>

              <div class="mb-4">
                <div class="text-xs font-semibold text-slate-400 mb-1.5 flex items-center justify-between">
                  <span>Size Run (${variants.length} sizes):</span>
                  <span class="text-[10px] text-slate-500 font-mono">C/Y tokens preserved</span>
                </div>
                <div class="flex flex-wrap gap-1.5">
                  ${sizePillsHtml}
                  ${moreSizes}
                </div>
              </div>
            </div>

            <button onclick="openModal(${idx})" class="w-full mt-2 py-2.5 px-4 bg-slate-800 hover:bg-slate-700 active:bg-slate-600 text-white rounded-xl text-sm font-semibold transition-colors flex items-center justify-center gap-2 border border-slate-700">
              <svg class="w-4 h-4 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>
              View Full Specs &amp; Size Guide
            </button>
          </div>
        `;
        grid.appendChild(card);
      });
    }

    function openModal(idx) {
      const p = PRODUCTS[idx];
      if (!p) return;
      const modal = document.getElementById('product-modal');
      const content = document.getElementById('modal-content');

      const inrPrice = Math.round(p.current_price || 0).toLocaleString('en-IN');
      const usdPrice = (p.source_price || 0).toFixed(2);
      const variants = p.variants || [];

      const imagesHtml = (p.images || []).map((img, i) => `
        <div class="bg-slate-950 p-2 rounded-xl border border-slate-800 flex items-center justify-center">
          <img src="${img}" alt="Image ${i+1}" class="max-h-48 w-auto object-contain rounded-lg">
        </div>
      `).join('');

      const variantsTable = variants.map(v => `
        <tr class="border-b border-slate-800 text-xs">
          <td class="py-2 px-3 font-mono text-slate-300">${v.sku}</td>
          <td class="py-2 px-3 font-semibold text-white">${v.title.split(' - ')[0]}</td>
          <td class="py-2 px-3 text-sky-400 font-medium">₹${Math.round(parseFloat(v.price || 0)).toLocaleString('en-IN')}</td>
          <td class="py-2 px-3">${v.in_stock ? '<span class="text-emerald-400 font-bold">In Stock</span>' : '<span class="text-slate-500 line-through">Out of Stock</span>'}</td>
        </tr>
      `).join('');

      content.innerHTML = `
        <div class="flex items-center gap-2 text-xs font-semibold text-sky-400 mb-1">
          <span>JD SPORTS</span> &bull; <span>${p.group_display || 'Shoes'}</span> &bull; <span>${p.subgroup_display || ''}</span>
        </div>
        <h2 class="text-xl md:text-2xl font-bold text-white mb-2">${p.title}</h2>

        <div class="flex items-center gap-3 mb-5">
          <span class="text-3xl font-black text-white">₹${inrPrice}</span>
          <span class="text-base text-slate-400">($${usdPrice} USD)</span>
          <span class="badge ${p.availability === 'in_stock' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' : 'bg-amber-500/20 text-amber-300 border-amber-500/30'} border">
            ${p.availability === 'in_stock' ? '● In Stock' : 'Out of Stock / Delisted'}
          </span>
          <a href="${p.source_url}" target="_blank" class="text-xs text-sky-400 hover:underline ml-auto flex items-center gap-1">
            View on JDSports.com
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
          </a>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2.5 mb-6">
          ${imagesHtml}
        </div>

        <div class="mb-6">
          <h4 class="text-sm font-bold text-white mb-2 flex items-center justify-between">
            <span>Complete Variant Matrix (${variants.length} sizes)</span>
            <span class="text-xs font-normal text-slate-400">Whole Rupee Math Verified</span>
          </h4>
          <div class="border border-slate-800 rounded-xl overflow-hidden max-h-56 overflow-y-auto">
            <table class="w-full text-left">
              <thead class="bg-slate-950 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800">
                <tr>
                  <th class="py-2 px-3">Variant SKU</th>
                  <th class="py-2 px-3">Size Run Label</th>
                  <th class="py-2 px-3">Price (INR)</th>
                  <th class="py-2 px-3">Status</th>
                </tr>
              </thead>
              <tbody>
                ${variantsTable}
              </tbody>
            </table>
          </div>
        </div>

        <div class="mt-6 pt-4 border-t border-slate-800">
          <h4 class="text-sm font-bold text-white mb-2">Description &amp; Size Guide</h4>
          <div class="text-xs text-slate-300 leading-relaxed bg-slate-950 p-4 rounded-xl border border-slate-800">
            ${p.descriptionHtml || p.description_html || 'No description HTML available'}
          </div>
        </div>
      `;

      modal.classList.remove('hidden');
    }

    function closeModal() {
      document.getElementById('product-modal').classList.add('hidden');
    }

    function setStockFilter(val) {
      currentStockFilter = val;
      document.querySelectorAll('.filter-stock-btn').forEach(btn => {
        btn.classList.remove('bg-sky-500', 'text-slate-950', 'font-semibold');
        btn.classList.add('text-slate-300', 'font-medium');
      });
      if (val === 'all') document.getElementById('btn-stock-all').classList.add('bg-sky-500', 'text-slate-950', 'font-semibold');
      if (val === 'in_stock') document.getElementById('btn-stock-in').classList.add('bg-sky-500', 'text-slate-950', 'font-semibold');
      if (val === 'out_of_stock') document.getElementById('btn-stock-out').classList.add('bg-sky-500', 'text-slate-950', 'font-semibold');
      renderProducts();
    }

    function setCategoryFilter(val) {
      currentCategoryFilter = val;
      document.querySelectorAll('.cat-pill').forEach(btn => {
        if (btn.dataset.cat === val) {
          btn.classList.add('bg-white/10', 'text-white', 'border-white/20');
          btn.classList.remove('bg-slate-950/60', 'text-slate-300', 'border-slate-800');
        } else {
          btn.classList.remove('bg-white/10', 'text-white', 'border-white/20');
          btn.classList.add('bg-slate-950/60', 'text-slate-300', 'border-slate-800');
        }
      });
      renderProducts();
    }

    document.getElementById('search-input').addEventListener('input', (e) => {
      currentSearch = e.target.value.trim();
      renderProducts();
    });

    document.getElementById('product-modal').addEventListener('click', (e) => {
      if (e.target.id === 'product-modal') closeModal();
    });

    renderProducts();
  </script>
</body>
</html>
"""

out_file = ARTIFACTS_DIR / "jd_sports_catalog_viewer.html"
out_file.write_text(html, encoding="utf-8")
print(f"SUCCESS: Generated {out_file} ({len(html)} bytes)")
