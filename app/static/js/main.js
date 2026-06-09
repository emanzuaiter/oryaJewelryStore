/**
 * ORYA Luxury Jewelry - Main JavaScript
 * Handles common UI interactions: Navbar, Drawer, Search, and Toast.
 */

(function() {

    // --- 1. Announcement Banner ---
    const banner = document.getElementById('announcement-banner');
    const dismissBtn = document.getElementById('dismiss-announce');

    if (banner && dismissBtn) {
        // Check if already dismissed in this session
        if (sessionStorage.getItem('orya_banner_dismissed')) {
            banner.classList.add('hidden');
        }

        dismissBtn.addEventListener('click', () => {
            banner.classList.add('hidden');
            sessionStorage.setItem('orya_banner_dismissed', 'true');
        });
    }

    // --- 1. Navbar Search Expansion & Live Search ---
    const searchToggle = document.getElementById('search-toggle');
    const searchWrapper = document.getElementById('search-input-wrapper');
    const searchInput = document.getElementById('nav-search-input');
    const searchDropdown = document.getElementById('search-dropdown');
    let searchTimeout;

    if (searchToggle && searchWrapper) {
        searchToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            searchWrapper.classList.toggle('expanded');
            if (searchWrapper.classList.contains('expanded') && searchInput) {
                searchInput.focus();
            }
        });
    }

    if (searchInput && searchDropdown) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            clearTimeout(searchTimeout);
            
            if (query.length < 2) {
                searchDropdown.classList.remove('visible');
                return;
            }

            searchTimeout = setTimeout(() => {
                fetch(`/api/products/search?q=${encodeURIComponent(query)}`)
                    .then(res => res.json())
                    .then(resData => {
                        const products = (resData.data && resData.data.products) || [];
                        renderSearchResults(products);
                    })
                    .catch(err => console.error('Search error:', err));
            }, 300);
        });
    }

    // --- 2. Global Navbar Scroll Logic (Hide on Scroll Down, Show on Scroll Up) ---
    const navbar = document.querySelector('.navbar');
    let lastScrollY = window.scrollY;

    if (navbar) {
        window.addEventListener('scroll', () => {
            const currentScrollY = window.scrollY;
            
            // Initial state: visible at top
            if (currentScrollY < 50) {
                navbar.classList.remove('navbar-hidden');
            } else if (currentScrollY > lastScrollY && currentScrollY > 150) {
                // Scrolling down: hide
                navbar.classList.add('navbar-hidden');
            } else if (currentScrollY < lastScrollY) {
                // Scrolling up: show
                navbar.classList.remove('navbar-hidden');
            }
            lastScrollY = currentScrollY;
        }, { passive: true });
    }

    // Close search on click outside
    document.addEventListener('click', (e) => {
        if (searchWrapper && searchToggle && !searchWrapper.contains(e.target) && !searchToggle.contains(e.target)) {
            if (searchWrapper) searchWrapper.classList.remove('expanded');
            if (searchDropdown) searchDropdown.classList.remove('visible');
        }
    });

    function renderSearchResults(results) {
        if (!searchDropdown) return;
        
        if (results.length === 0) {
            searchDropdown.innerHTML = '<div style="padding:15px; text-align:center; font-size:14px;">No results found</div>';
        } else {
            let html = results.slice(0, 5).map(item => {
                const name = window.currentLang === 'ar' ? item.name_ar : item.name_en;
                return `
                <a href="/product/${item.id}" style="display:flex; align-items:center; gap:15px; padding:10px 15px; text-decoration:none; color:inherit; border-bottom:1px solid var(--beige-light);">
                    <img src="${item.primary_image}" alt="${name}" style="width:40px; height:40px; object-fit:cover; border-radius:4px;">
                    <div>
                        <div style="font-size:14px; font-weight:500;">${name}</div>
                        <div style="font-size:12px; color:var(--gold);">${window.formatPrice(item.price)}</div>
                    </div>
                </a>
            `}).join('');

            html += `<a href="/search?q=${encodeURIComponent(searchInput.value)}&t=${Date.now()}" style="display:block; padding:10px; text-align:center; font-size:12px; color:var(--gold); font-weight:600;">View All</a>`;
            searchDropdown.innerHTML = html;
        }
        searchDropdown.classList.add('visible');
    }

    // Handle Enter key for search
    searchInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && searchInput.value.trim().length >= 2) {
            window.location.href = `/search?q=${encodeURIComponent(searchInput.value)}&t=${Date.now()}`;
        }
    });

    // --- 3. Cart Drawer Toggle ---
    const cartToggle = document.getElementById('cart-toggle');
    const closeCart = document.getElementById('close-cart');
    const cartDrawer = document.getElementById('cart-drawer');
    const overlay = document.getElementById('drawer-overlay');

    function toggleCart(show = true) {
        if (show) {
            cartDrawer.classList.add('active');
            overlay.classList.add('active');
            document.body.style.overflow = 'hidden';
        } else {
            cartDrawer.classList.remove('active');
            overlay.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    cartToggle?.addEventListener('click', () => toggleCart(true));
    closeCart?.addEventListener('click', () => toggleCart(false));
    overlay?.addEventListener('click', () => toggleCart(false));

    // Expose toggle function globally for cart.js to use (e.g. open cart after adding item)
    window.toggleCartDrawer = toggleCart;

    // --- 4. Mobile Menu ---
    const hamburger = document.getElementById('hamburger');
    const mobileMenu = document.getElementById('mobile-menu');

    hamburger?.addEventListener('click', () => {
        mobileMenu.classList.toggle('active');
        // Simple hamburger animation
        const spans = hamburger.querySelectorAll('span');
        if (mobileMenu.classList.contains('active')) {
            spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
            spans[1].style.opacity = '0';
            spans[2].style.transform = 'rotate(-45deg) translate(7px, -7px)';
        } else {
            spans[0].style.transform = '';
            spans[1].style.opacity = '1';
            spans[2].style.transform = '';
        }
    });

    // --- Account Dropdown Toggle (Mobile) ---
    const accountDropdown = document.getElementById('account-dropdown');
    accountDropdown?.addEventListener('click', (e) => {
        if (window.innerWidth <= 768) {
            e.stopPropagation();
            accountDropdown.classList.toggle('active');
        }
    });

    document.addEventListener('click', () => {
        accountDropdown?.classList.remove('active');
    });

    // --- 5. Toast Notifications ---
    const toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container';
    document.body.appendChild(toastContainer);

    window.showToast = function(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let icon = '';
        if (type === 'success') icon = '✓';
        if (type === 'error') icon = '✕';
        if (type === 'info') icon = 'ℹ';

        toast.innerHTML = `
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-weight:bold;">${icon}</span>
                <span>${message}</span>
            </div>
            <button style="background:none; border:none; color:#fff; cursor:pointer; margin-left:15px; min-width:unset; min-height:unset;">✕</button>
        `;

        toastContainer.appendChild(toast);

        // Dismiss on button click
        toast.querySelector('button').addEventListener('click', () => {
            dismissToast(toast);
        });

        // Auto dismiss after 3s
        setTimeout(() => {
            dismissToast(toast);
        }, 3000);
    };

    function dismissToast(toast) {
        toast.classList.add('fade-out');
        setTimeout(() => {
            toast.remove();
        }, 500);
    }


    // --- 6. Product Card Interactions ---
    function initProductCards() {
        const cards = document.querySelectorAll('.product-card');
        cards.forEach(card => {
            const img = card.querySelector('.product-img');
            if (img && img.dataset.hover) {
                const originalSrc = img.src;
                const hoverSrc = img.dataset.hover;
                
                card.addEventListener('mouseenter', () => img.src = hoverSrc);
                card.addEventListener('mouseleave', () => img.src = originalSrc);
            }
            
            // Sync names initially
            updateProductNames(card);
        });
    }

    function updateProductNames(root = document) {
        const names = root.querySelectorAll('.product-name');
        const lang = window.currentLang;
        names.forEach(el => {
            const name = lang === 'ar' ? el.dataset.nameAr : el.dataset.nameEn;
            if (name) el.textContent = name;
        });
    }

    // --- 7. Category Scroll Navigation ---
    function initCategoryScroll() {
        const scroll = document.querySelector('.categories-scroll');
        const prev = document.querySelector('.scroll-btn.prev');
        const next = document.querySelector('.scroll-btn.next');

        if (scroll && prev && next) {
            prev.addEventListener('click', () => scroll.scrollBy({ left: -300, behavior: 'smooth' }));
            next.addEventListener('click', () => scroll.scrollBy({ left: 300, behavior: 'smooth' }));
        }
    }

    // --- 15. Scroll Reveal Observer ---
    function initScrollReveal() {
        const reveals = document.querySelectorAll('.reveal');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                }
            });
        }, { threshold: 0.1 });

        reveals.forEach(el => observer.observe(el));
    }

    // --- 16. Category Tab Filtering ---
    

    // Initialize all components
    document.addEventListener('DOMContentLoaded', () => {
        initProductCards();
        initCategoryScroll();
        initScrollReveal();
        
    });

    // Listen for language changes to update product names
    window.addEventListener('languageChanged', () => {
        updateProductNames();
    });

    // --- 8. Global Action Listeners ---
    document.addEventListener('click', (e) => {
        // Wishlist Toggle
        const wishlistBtn = e.target.closest('.wishlist-btn');
        if (wishlistBtn) {
            const productId = wishlistBtn.dataset.id;
            if (typeof window.wishlistToggle === 'function') {
                window.wishlistToggle(productId, wishlistBtn);
            } else {
                console.warn('wishlistToggle function not found.');
                // Fallback UI toggle
                wishlistBtn.classList.toggle('active');
                window.showToast('Product added to wishlist', 'success');
            }
        }

        // Add to Cart
        const addCartBtn = e.target.closest('.btn-add-cart');
        if (addCartBtn && addCartBtn.id !== 'add-to-cart-btn') {
            const productId = addCartBtn.dataset.id;
            if (typeof window.addToCart === 'function') {
                window.addToCart(productId, 1);
            } else {
                console.warn('addToCart function not found. Ensure cart.js is loaded.');
                window.showToast('Adding to cart...', 'info');
            }
        }

        // Quick View
        const quickViewBtn = e.target.closest('.quick-view-btn');
        if (quickViewBtn) {
            const productId = quickViewBtn.dataset.id;
            openQuickView(productId);
        }
    });

    const qvModal = document.getElementById('quick-view-modal');
    const qvBody = document.getElementById('quick-view-body');
    const qvClose = document.getElementById('close-quick-view');

    function openQuickView(id) {
        if (!qvModal || !qvBody) return;
        
        qvBody.innerHTML = '<div class="loading-spinner" style="margin: 50px auto; grid-column: span 2;"></div>';
        qvModal.classList.add('active');
        document.body.style.overflow = 'hidden';

        fetch(`/api/products/${id}`)
            .then(res => res.json())
            .then(data => {
                const product = data.data;
                const lang = window.currentLang;
                const name = lang === 'ar' ? product.name_ar : product.name_en;
                const desc = lang === 'ar' ? product.description_ar : product.description_en;
                
                qvBody.innerHTML = `
                    <div class="quick-view-image">
                        <img src="${product.primary_image}" alt="${name}">
                    </div>
                    <div class="quick-view-details">
                        <h2>${name}</h2>
                        <div class="quick-view-price">${window.formatPrice(product.price)}</div>
                        <div class="quick-view-desc">${desc || ''}</div>
                        <button class="btn-primary-new btn-add-cart" data-id="${product.id}" style="width: 100%;">
                            ${window.t('add_to_cart')}
                        </button>
                        <a href="/product/${product.id}" style="display:block; text-align:center; margin-top:15px; color:var(--text-muted); font-size:14px; text-decoration:underline;">
                            View Full Details
                        </a>
                    </div>
                `;
            })
            .catch(err => {
                qvBody.innerHTML = '<p style="text-align:center; grid-column: span 2;">Error loading product details.</p>';
                console.error(err);
            });
    }

    qvClose?.addEventListener('click', () => {
        qvModal.classList.remove('active');
        document.body.style.overflow = '';
    });

    window.addEventListener('click', (e) => {
        if (e.target === qvModal) {
            qvModal.classList.remove('active');
            document.body.style.overflow = '';
        }
    });

    // --- 9. Password Visibility Toggle ---
    document.addEventListener('click', (e) => {
        const toggle = e.target.closest('.password-toggle');
        if (toggle) {
            const input = toggle.parentElement.querySelector('input');
            const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
            input.setAttribute('type', type);
            // Toggle eye icon if using a font icon or SVG
            toggle.textContent = type === 'password' ? '👁️' : '🙈';
        }
    });

    // --- 10. Password Strength Meter ---
    const passwordInput = document.getElementById('register-password');
    const strengthBar = document.getElementById('strength-bar');
    if (passwordInput && strengthBar) {
        passwordInput.addEventListener('input', (e) => {
            const val = e.target.value;
            let strength = 0;
            if (val.length >= 8) strength++;
            if (/[A-Z]/.test(val)) strength++;
            if (/[0-9]/.test(val)) strength++;
            if (/[^A-Za-z0-9]/.test(val)) strength++;

            strengthBar.className = 'strength-bar';
            if (strength === 1) strengthBar.classList.add('weak');
            if (strength === 2) strengthBar.classList.add('fair');
            if (strength === 3) strengthBar.classList.add('good');
            if (strength === 4) strengthBar.classList.add('strong');
        });
    }

    // --- 11. Account Tabs ---
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    function switchTab(tabId) {
        tabBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });
        tabContents.forEach(content => {
            content.classList.toggle('active', content.id === tabId);
        });
        window.location.hash = tabId;
    }

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    if (window.location.hash) {
        switchTab(window.location.hash.substring(1));
    }

    // --- 12. Order Row Expansion ---
    document.addEventListener('click', (e) => {
        const row = e.target.closest('.order-row-expandable');
        if (row) {
            const orderId = row.dataset.id;
            const drawer = document.getElementById(`order-details-${orderId}`);
            if (drawer) {
                drawer.classList.toggle('active');
            }
        }
    });

    // --- 13. Wishlist Toggle ---
    window.wishlistToggle = async function(productId, btn) {
        try {
            const response = await fetch('/api/wishlist/toggle', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ product_id: productId })
            });

            if (response.redirected && response.url.includes('/login')) {
                window.location.href = response.url;
                return;
            }
            if (response.status === 401) {
                window.location.href = '/login?next=' + window.location.pathname;
                return;
            }

            const contentType = response.headers.get("content-type");
            if (!contentType || contentType.indexOf("application/json") === -1) {
                if (response.url.includes('/login')) {
                    window.location.href = response.url;
                    return;
                }
                throw new Error("Invalid response");
            }

            const result = await response.json();
            
            if (result.success) {
                const isLiked = result.data.wishlisted;
                btn.classList.toggle('active', isLiked);
                
                const heartSvg = btn.querySelector('svg');
                if (heartSvg) {
                    heartSvg.setAttribute('fill', isLiked ? 'currentColor' : 'none');
                }

                const msg = isLiked 
                    ? (window.currentLang === 'ar' ? 'تمت الإضافة للمفضلة' : 'Added to wishlist')
                    : (window.currentLang === 'ar' ? 'تمت الإزالة من المفضلة' : 'Removed from wishlist');
                
                window.showToast(msg, 'success');
            } else {
                window.showToast(result.message || 'Something went wrong', 'error');
            }
        } catch (err) {
            console.error('Wishlist error:', err);
            window.showToast('Something went wrong', 'error');
        }
    };

    // --- 14. Wishlist Remove & Share ---
    window.removeWishlistItem = function(productId, btn) {
        const card = btn.closest('.wishlist-item') || btn.closest('.product-card');
        
        fetch(`/api/wishlist/${productId}`, { method: 'DELETE' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.9)';
                    setTimeout(() => {
                        card.remove();
                        if (document.querySelectorAll('.product-grid .product-card').length === 0) {
                            location.reload(); // Show empty state
                        }
                    }, 300);
                    window.showToast('Removed from wishlist', 'info');
                }
            })
            .catch(err => {
                console.error('Wishlist removal error:', err);
                window.showToast('Error removing item', 'error');
            });
    };

    window.shareWishlist = function() {
        fetch('/api/wishlist/share-token')
            .then(res => res.json())
            .then(data => {
                const url = `${window.location.origin}/wishlist/share/${data.token}`;
                navigator.clipboard.writeText(url).then(() => {
                    window.showToast(window.t('copied'), 'success');
                });
            });
    };

    // --- 14. Navbar Live Search (Keyboard Nav) ---
    const results = document.getElementById('search-dropdown');
    let currentIndex = -1;

    searchInput?.addEventListener('keydown', (e) => {
        const items = results?.querySelectorAll('a');
        if (!items || items.length === 0) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            currentIndex = (currentIndex + 1) % items.length;
            updateSelection(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            currentIndex = (currentIndex - 1 + items.length) % items.length;
            updateSelection(items);
        } else if (e.key === 'Enter' && currentIndex > -1) {
            e.preventDefault();
            items[currentIndex].click();
        } else if (e.key === 'Escape') {
            searchDropdown.classList.remove('visible');
        }
    });

    function updateSelection(items) {
        items.forEach((item, idx) => {
            item.style.backgroundColor = (idx === currentIndex) ? 'var(--beige-light)' : '';
        });
    }

    // Initialize all components
    document.addEventListener('DOMContentLoaded', () => {
        initProductCards();
        initCategoryScroll();
        initScrollReveal();
        
    });


    // --- Homepage Category Tabs ---
    const tabItems = document.querySelectorAll('.tab-item');
    tabItems.forEach(tab => {
        tab.addEventListener('click', function() {
            const category = this.getAttribute('data-category');
            if (category) {
                window.location.href = '/products/' + category;
            }
        });
    });

})();
