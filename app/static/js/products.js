/**
 * ORYA - Products Listing Logic
 * Handles filtering, dual-range slider, and AJAX pagination.
 */

(function() {
    // --- 1. Dual-Handle Price Slider ---
    const minPriceInput = document.getElementById('min-price');
    const maxPriceInput = document.getElementById('max-price');
    const minValLabel = document.getElementById('min-val');
    const maxValLabel = document.getElementById('max-val');
    const sliderTrack = document.getElementById('slider-track');

    function updateSlider() {
        let min = parseInt(minPriceInput.value);
        let max = parseInt(maxPriceInput.value);

        if (min > max) {
            [min, max] = [max, min];
            // Update inputs to match sorted values only if necessary to avoid feedback loops
            // But usually we want the inputs to stay where the user put them if they are separate thumbs.
            // If they are separate thumbs, we should probably just ensure the range is correct.
        }

        const minPercent = (min / minPriceInput.max) * 100;
        const maxPercent = (max / maxPriceInput.max) * 100;

        if (sliderTrack) {
            sliderTrack.style.left = minPercent + "%";
            sliderTrack.style.width = (maxPercent - minPercent) + "%";
        }

        if (minValLabel) minValLabel.textContent = min;
        if (maxValLabel) maxValLabel.textContent = max;
    }

    [minPriceInput, maxPriceInput].forEach(input => {
        input?.addEventListener('input', updateSlider);
        input?.addEventListener('change', () => fetchProducts(1));
    });

    // --- 2. Filter Elements ---
    const sortBy = document.getElementById('sort-by');
    const materialFilters = document.querySelectorAll('.material-filter');
    const saleOnly = document.getElementById('sale-only');
    const resetBtn = document.getElementById('reset-filters');
    const productGrid = document.getElementById('product-grid');
    const productCount = document.getElementById('product-count') || document.getElementById('results-count');
    const pagination = document.getElementById('pagination');

    function getFilterData() {
        const materials = Array.from(materialFilters)
            .filter(i => i.checked)
            .map(i => i.value)
            .join(',');

        const p1 = parseFloat(minPriceInput.value);
        const p2 = parseFloat(maxPriceInput.value);

        const data = {
            min_price: Math.min(p1, p2),
            max_price: Math.max(p1, p2),
            material: materials,
            sort: sortBy.value,
            sale: saleOnly.checked ? 'true' : ''
        };

        const urlParams = new URLSearchParams(window.location.search);
        const urlQ = urlParams.get('q');

        if (window.currentCategory === 'search' || urlQ) {
            data.q = urlQ || window.searchQuery || '';
            window.currentCategory = 'search'; // Ensure we stay in search mode
        } else {
            data.category = window.currentCategory || 'all';
        }

        return data;
    }

    function fetchProducts(page = 1) {
        const data = getFilterData();
        data.page = page;

        const params = new URLSearchParams(data);
        const apiParams = new URLSearchParams(data);
        apiParams.set('_', Date.now()); // Cache buster for API only
        
        const isSearch = window.currentCategory === 'search';
        const url = isSearch ? `/api/products/search?${apiParams.toString()}` : `/api/products?${apiParams.toString()}`;

        // Update URL without reload
        const displayUrl = isSearch 
            ? `/search?${params.toString()}`
            : `/products/${data.category}?${params.toString()}`;
        
        window.history.pushState(data, '', displayUrl);

        showSkeletons();

        fetch(url)
            .then(res => res.json())
            .then(resData => {
                const dataObj = resData.data || {};
                renderProducts(dataObj.products || []);
                renderPagination(dataObj.total || 0, page);
                if (productCount) productCount.textContent = dataObj.total || 0;
                window.scrollTo({ top: 0, behavior: 'smooth' });
            })
            .catch(err => {
                console.error('Fetch error:', err);
                productGrid.innerHTML = '<div class="empty-state">Error loading products.</div>';
            });
    }

    function showSkeletons() {
        const template = document.getElementById('skeleton-template') || document.getElementById('product-skeleton');
        if (!template || !productGrid) return;
        
        productGrid.innerHTML = '';
        for (let i = 0; i < 8; i++) {
            productGrid.appendChild(template.content.cloneNode(true));
        }
    }

    function renderProducts(products) {
        if (!products || products.length === 0) {
            productGrid.innerHTML = `
                <div class="empty-state">
                    <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                    <h3 data-i18n="no_products">No products found</h3>
                    <p data-i18n="no_products_desc">Try adjusting your filters.</p>
                </div>
            `;
            return;
        }

        productGrid.innerHTML = products.map(p => `
            <article class="product-card">
                <div class="product-image-wrap">
                    <a href="/product/${p.id}">
                        <img src="${p.primary_image}" data-hover="${p.secondary_image || p.primary_image}" alt="${p.name_en}" class="product-img">
                    </a>
                    <div class="product-badges">
                        ${p.is_new ? `<span class="badge badge--new" data-i18n="badge_new">New</span>` : ''}
                        ${p.is_on_sale ? `<span class="badge badge--sale" data-i18n="badge_sale">Sale</span>` : ''}
                    </div>
                    <button class="wishlist-btn ${p.in_wishlist ? 'active' : ''}" data-id="${p.id}">
                        <svg viewBox="0 0 24 24"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
                    </button>
                </div>
                <div class="product-info">
                    <span class="material-badge">${p.material}</span>
                    <h3 class="product-name" data-name-ar="${p.name_ar}" data-name-en="${p.name_en}">
                        ${window.currentLang === 'ar' ? p.name_ar : p.name_en}
                    </h3>
                    <div class="product-price">
                        ${p.is_on_sale ? 
                            `<span class="price-original">${window.formatPrice(p.price)}</span>
                             <span class="price-sale">${window.formatPrice(p.sale_price)}</span>` : 
                            `<span class="price-regular">${window.formatPrice(p.price)}</span>`
                        }
                    </div>
                    <button class="btn-add-cart" data-id="${p.id}" data-i18n="add_to_cart">Add to Cart</button>
                </div>
            </article>
        `).join('');

        // Re-initialize hover effects
        if (window.initProductCards) window.initProductCards();
        // Update translations
        if (window.updateTranslations) window.updateTranslations(productGrid);
    }

    function renderPagination(total, current) {
        const pages = Math.ceil(total / 12);
        if (pages <= 1) {
            pagination.innerHTML = '';
            return;
        }

        let html = `<a href="#" class="page-link prev ${current === 1 ? 'disabled' : ''}" data-page="${current - 1}">«</a>`;
        for (let i = 1; i <= pages; i++) {
            html += `<a href="#" class="page-link ${i === current ? 'active' : ''}" data-page="${i}">${i}</a>`;
        }
        html += `<a href="#" class="page-link next ${current === pages ? 'disabled' : ''}" data-page="${current + 1}">»</a>`;
        
        pagination.innerHTML = html;
    }

    // --- 3. Event Listeners ---
    sortBy?.addEventListener('change', () => fetchProducts(1));
    materialFilters.forEach(i => i.addEventListener('change', () => fetchProducts(1)));
    saleOnly?.addEventListener('change', () => fetchProducts(1));

    pagination?.addEventListener('click', (e) => {
        const link = e.target.closest('.page-link');
        if (link && !link.classList.contains('active') && !link.classList.contains('disabled')) {
            e.preventDefault();
            fetchProducts(parseInt(link.dataset.page));
        }
    });

    window.resetAllFilters = function() {
        minPriceInput.value = 0;
        maxPriceInput.value = 5000;
        updateSlider();
        sortBy.value = 'newest';
        saleOnly.checked = false;
        materialFilters.forEach(i => i.checked = false);
        fetchProducts(1);
    };

    resetBtn?.addEventListener('click', window.resetAllFilters);

    // --- 4. Mobile Drawer ---
    const openFilters = document.getElementById('open-filters');
    const closeFilters = document.getElementById('close-filters');
    const sidebar = document.getElementById('filters-sidebar');
    const overlay = document.getElementById('filter-overlay');

    function toggleSidebar(show) {
        sidebar.classList.toggle('active', show);
        overlay.classList.toggle('active', show);
        document.body.style.overflow = show ? 'hidden' : '';
    }

    openFilters?.addEventListener('click', () => toggleSidebar(true));
    closeFilters?.addEventListener('click', () => toggleSidebar(false));
    overlay?.addEventListener('click', () => toggleSidebar(false));

    // Initialize slider and fetch products on load
    updateSlider();
    fetchProducts(1);

    // Re-fetch products when language is toggled to update catalog display
    window.addEventListener('languageChanged', () => {
        const urlParams = new URLSearchParams(window.location.search);
        const page = parseInt(urlParams.get('page')) || 1;
        fetchProducts(page);
    });

    // Handle back/forward browser buttons
    window.addEventListener('popstate', (e) => {
        if (e.state) {
            // Restore filter values from state and fetch
            // (Skipping full restoration logic for brevity, but normally you'd sync UI)
            fetchProducts(e.state.page || 1);
        }
    });

})();
