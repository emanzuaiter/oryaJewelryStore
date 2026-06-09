/**
 * ORYA - Product Detail Logic
 * Gallery, Zoom, Reviews, and Recently Viewed.
 */

(function() {
    // --- 1. Image Gallery & Zoom ---
    const zoomContainer = document.getElementById('zoom-container');
    const mainImage = document.getElementById('main-image');
    const thumbnails = document.querySelectorAll('.thumbnail');

    if (zoomContainer && mainImage) {
        zoomContainer.addEventListener('mousemove', (e) => {
            const { left, top, width, height } = zoomContainer.getBoundingClientRect();
            const x = ((e.clientX - left) / width) * 100;
            const y = ((e.clientY - top) / height) * 100;
            
            mainImage.style.transformOrigin = `${x}% ${y}%`;
            mainImage.style.transform = 'scale(1.8)';
        });

        zoomContainer.addEventListener('mouseleave', () => {
            mainImage.style.transform = 'scale(1)';
            mainImage.style.transformOrigin = 'center center';
        });
    }

    thumbnails.forEach(thumb => {
        thumb.addEventListener('click', () => {
            const newSrc = thumb.dataset.src;
            if (mainImage.src === newSrc) return;

            // Fade out
            mainImage.style.opacity = '0';
            
            setTimeout(() => {
                mainImage.src = newSrc;
                mainImage.style.opacity = '1';
                
                thumbnails.forEach(t => t.classList.remove('active'));
                thumb.classList.add('active');
            }, 200);
        });
    });

    // --- 2. Quantity Selector ---
    const qtyInput = document.getElementById('qty-input');
    const qtyMinus = document.getElementById('qty-minus');
    const qtyPlus = document.getElementById('qty-plus');

    function updateQtyButtons() {
        if (!qtyInput) return;
        const val = parseInt(qtyInput.value);
        const max = parseInt(qtyInput.getAttribute('max')) || 1;
        
        if (qtyMinus) qtyMinus.disabled = (val <= 1);
        if (qtyPlus) qtyPlus.disabled = (val >= max);
    }

    if (qtyInput) {
        qtyMinus?.addEventListener('click', () => {
            if (qtyInput.value > 1) {
                qtyInput.value--;
                updateQtyButtons();
            }
        });

        qtyPlus?.addEventListener('click', () => {
            const max = parseInt(qtyInput.getAttribute('max')) || 99;
            if (qtyInput.value < max) {
                qtyInput.value++;
                updateQtyButtons();
            }
        });

        qtyInput.addEventListener('change', () => {
            const max = parseInt(qtyInput.getAttribute('max')) || 99;
            let val = parseInt(qtyInput.value);
            if (isNaN(val) || val < 1) val = 1;
            if (val > max) val = max;
            qtyInput.value = val;
            updateQtyButtons();
        });

        updateQtyButtons();
    }

    // --- 3. Accordion ---
    const careAccordion = document.getElementById('care-accordion');
    if (careAccordion) {
        careAccordion.querySelector('.accordion-header').addEventListener('click', () => {
            careAccordion.classList.toggle('active');
        });
    }

    // --- 4. Review Interactions ---
    const showReviewBtn = document.getElementById('btn-show-review-form');
    const reviewForm = document.getElementById('review-form-container');
    const cancelReview = document.getElementById('cancel-review');
    const starSelector = document.getElementById('star-selector');
    const stars = starSelector?.querySelectorAll('svg');
    const reviewText = document.getElementById('review-text');
    let selectedRating = 0;

    showReviewBtn?.addEventListener('click', () => {
        reviewForm.style.display = 'block';
        showReviewBtn.style.display = 'none';
    });

    cancelReview?.addEventListener('click', () => {
        reviewForm.style.display = 'none';
        showReviewBtn.style.display = 'block';
    });

    stars?.forEach(star => {
        star.addEventListener('click', () => {
            selectedRating = parseInt(star.dataset.rating);
            updateStars(selectedRating);
        });

        star.addEventListener('mouseenter', () => {
            updateStars(parseInt(star.dataset.rating));
        });

        star.addEventListener('mouseleave', () => {
            updateStars(selectedRating);
        });
    });

    function updateStars(rating) {
        stars?.forEach((s, idx) => {
            s.classList.toggle('active', idx < rating);
        });
    }

    const submitReview = document.getElementById('submit-review');

    submitReview?.addEventListener('click', () => {
        const comment = reviewText.value.trim();
        if (selectedRating === 0) {
            window.showToast('Please select a rating', 'error');
            return;
        }
        if (comment.length < 20) {
            window.showToast('Review must be at least 20 characters', 'error');
            return;
        }

        fetch(`/api/products/${window.productId}/reviews`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rating: selectedRating, comment: comment })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                window.showToast(window.t('review_submitted'), 'success');
                reviewForm.style.display = 'none';
                showReviewBtn.style.display = 'block';
                reviewText.value = '';
                selectedRating = 0;
                updateStars(0);
                // Optionally reload reviews list here
            } else {
                window.showToast(data.message || 'Error submitting review', 'error');
            }
        });
    });

    // --- 5. Recently Viewed ---
    const rvSection = document.getElementById('recently-viewed-section');
    const rvContainer = document.getElementById('recently-viewed-container');

    function trackView() {
        fetch('/api/recently-viewed', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: window.productId })
        });
    }

    function fetchRecentlyViewed() {
        fetch('/api/recently-viewed')
            .then(res => res.json())
            .then(data => {
                if (data.products && data.products.length > 0) {
                    const filtered = data.products.filter(p => p.id != window.productId).slice(0, 6);
                    if (filtered.length > 0) {
                        renderRV(filtered);
                    } else {
                        rvSection.style.display = 'none';
                    }
                } else {
                    rvSection.style.display = 'none';
                }
            });
    }

    function renderRV(products) {
        rvContainer.innerHTML = products.map(p => `
            <article class="product-card">
                <div class="product-image-wrap">
                    <a href="/product/${p.id}">
                        <img src="${p.primary_image}" alt="${p.name_en}" class="product-img">
                    </a>
                </div>
                <div class="product-info">
                    <h3 class="product-name" data-name-ar="${p.name_ar}" data-name-en="${p.name_en}">
                        ${window.currentLang === 'ar' ? p.name_ar : p.name_en}
                    </h3>
                    <div class="product-price">
                        <span class="price-regular">${p.price.toFixed(3)} JOD</span>
                    </div>
                </div>
            </article>
        `).join('');
        
        if (window.updateTranslations) window.updateTranslations(rvContainer);
    }

    // Initialize
    if (window.productId) {
        trackView();
        fetchRecentlyViewed();
    }

    // Sync Translations & Names
    function updateDetailPage() {
        if (window.updateTranslations) window.updateTranslations();
        
        // Sync Names
        const nameElements = document.querySelectorAll('[data-name-ar]');
        nameElements.forEach(el => {
            const lang = window.currentLang;
            el.textContent = lang === 'ar' ? el.dataset.nameAr : el.dataset.nameEn;
        });
    }

    document.addEventListener('DOMContentLoaded', updateDetailPage);
    window.addEventListener('languageChanged', updateDetailPage);

    // Add to Cart
    const addCartBtn = document.getElementById('add-to-cart-btn');
    addCartBtn?.addEventListener('click', () => {
        const qtyInput = document.getElementById('qty-input');
        const qty = qtyInput ? parseInt(qtyInput.value) : 1;
        if (window.addToCart) {
            window.addToCart(window.productId, qty);
        }
    });
    
    // Wishlist Toggle is handled globally by main.js
})();
