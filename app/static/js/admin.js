/* =====================================================
   ORYA Admin — admin.js
   Sidebar toggle, modals, table helpers, status badges
   ===================================================== */

'use strict';

/* ══════════════════════════════════════════════════
   SIDEBAR TOGGLE
══════════════════════════════════════════════════ */
(function initSidebar() {
  const sidebar  = document.getElementById('sidebar');
  const toggle   = document.getElementById('sidebar-toggle');
  const overlay  = document.getElementById('sidebar-overlay');

  if (!sidebar || !toggle) return;

  function openSidebar() {
    sidebar.classList.add('open');
    if (overlay) {
      overlay.classList.add('visible');
      overlay.style.display = 'block';
    }
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('visible');
    document.body.style.overflow = '';
    // hide overlay after transition
    setTimeout(() => {
      if (overlay && !overlay.classList.contains('visible')) {
        overlay.style.display = '';
      }
    }, 300);
  }

  toggle.addEventListener('click', () => {
    sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
  });

  if (overlay) {
    overlay.addEventListener('click', closeSidebar);
  }

  // Close sidebar on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && sidebar.classList.contains('open')) {
      closeSidebar();
    }
  });

  // Restore sidebar on resize to desktop
  window.addEventListener('resize', () => {
    if (window.innerWidth > 768) {
      sidebar.classList.remove('open');
      if (overlay) overlay.classList.remove('visible');
      document.body.style.overflow = '';
    }
  });
})();

/* ══════════════════════════════════════════════════
   HEADER DROPDOWNS (Notifications & User)
══════════════════════════════════════════════════ */
(function initDropdowns() {
  const dropdowns = [
    { toggle: 'notif-toggle', menu: 'notif-dropdown' },
    { toggle: 'user-menu-toggle', menu: 'user-dropdown' }
  ];

  dropdowns.forEach(d => {
    const btn = document.getElementById(d.toggle);
    const menu = document.getElementById(d.menu);
    if (!btn || !menu) return;

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      // Close others first
      dropdowns.forEach(other => {
        if (other.menu !== d.menu) {
          const otherMenu = document.getElementById(other.menu);
          if (otherMenu) otherMenu.style.display = 'none';
        }
      });
      // Toggle current
      const isOpen = menu.style.display === 'block';
      menu.style.display = isOpen ? 'none' : 'block';
    });
  });

  // Close all on outside click
  document.addEventListener('click', () => {
    dropdowns.forEach(d => {
      const menu = document.getElementById(d.menu);
      if (menu) menu.style.display = 'none';
    });
  });
})();

/* ══════════════════════════════════════════════════
   ACTIVE NAV HIGHLIGHTING (URL-based fallback)
══════════════════════════════════════════════════ */
(function highlightNav() {
  const path  = window.location.pathname;
  const items = document.querySelectorAll('.nav-item');

  items.forEach(item => {
    const href = item.getAttribute('href');
    if (!href || href === '#') return;
    // exact match or sub-path match
    if (path === href || (path.startsWith(href) && href !== '/admin/')) {
      item.classList.add('active');
    }
  });
})();

/* ══════════════════════════════════════════════════
   MODAL HELPERS
══════════════════════════════════════════════════ */

/**
 * Open a modal overlay by id.
 * @param {string} id - The id of the .modal-overlay element
 */
function openModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';

  // Close on overlay click (but not on box click)
  modal.addEventListener('click', function handler(e) {
    if (e.target === modal) {
      closeModal(id);
      modal.removeEventListener('click', handler);
    }
  });
}

/**
 * Close a modal overlay by id.
 * @param {string} id
 */
function closeModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.remove('open');
  document.body.style.overflow = '';
}

// Wire up all [data-modal-open] and [data-modal-close] buttons automatically
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-modal-open]').forEach(btn => {
    btn.addEventListener('click', () => openModal(btn.dataset.modalOpen));
  });

  document.querySelectorAll('[data-modal-close]').forEach(btn => {
    btn.addEventListener('click', () => closeModal(btn.dataset.modalClose));
  });

  // Also wire class .modal-close buttons inside modals
  document.querySelectorAll('.modal-close').forEach(btn => {
    btn.addEventListener('click', () => {
      const overlay = btn.closest('.modal-overlay');
      if (overlay) closeModal(overlay.id);
    });
  });

  // Close modal on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.open').forEach(m => {
        closeModal(m.id);
      });
    }
  });
});

/* ══════════════════════════════════════════════════
   STATUS BADGE HELPER
══════════════════════════════════════════════════ */
const STATUS_LABELS = {
  pending:        t('status_pending') || 'Pending',
  processing:     t('status_processing') || 'Processing',
  delivered:      t('status_delivered') || 'Delivered',
  cancelled:      t('status_cancelled') || 'Cancelled',
  active:         t('status_active') || 'Active',
  inactive:       t('status_inactive') || 'Inactive',
  approved:       t('table_review_approved') || 'Approved',
  pending_review: t('pending_approval') || 'Pending Review',
};

/**
 * Build an HTML status badge string.
 * @param {string} status - e.g. 'pending', 'delivered'
 * @returns {string} HTML string
 */
function statusBadge(status) {
  const cls   = 'status-' + (status || '').replace(/_/g, '-');
  const label = STATUS_LABELS[status] || status;
  return `<span class="status-badge ${cls}">${label}</span>`;
}

/* ══════════════════════════════════════════════════
   STAR RATING RENDER
══════════════════════════════════════════════════ */
/**
 * Render a star rating as HTML.
 * @param {number} rating - 1-5
 * @returns {string} HTML
 */
function renderStars(rating) {
  let html = '<span class="stars">';
  for (let i = 1; i <= 5; i++) {
    html += i <= rating ? '★' : '<span class="star-empty">★</span>';
  }
  html += '</span>';
  return html;
}

/* ══════════════════════════════════════════════════
   TABLE CHECKBOX / BULK SELECT
══════════════════════════════════════════════════ */
/**
 * Initialise a table with bulk-select checkboxes.
 * Expects: #select-all checkbox, .row-check checkboxes, bulk-bar element.
 * @param {string} tableId
 * @param {string} bulkBarId
 */
function initBulkSelect(tableId, bulkBarId) {
  const table     = document.getElementById(tableId);
  const bulkBar   = document.getElementById(bulkBarId);
  const selectAll = table ? table.querySelector('#select-all') : null;

  if (!table || !bulkBar) return;

  function updateBulkBar() {
    const checked = table.querySelectorAll('.row-check:checked');
    bulkBar.classList.toggle('visible', checked.length > 0);
    const countEl = bulkBar.querySelector('.bulk-count');
    if (countEl) countEl.textContent = checked.length;
  }

  if (selectAll) {
    selectAll.addEventListener('change', () => {
      table.querySelectorAll('.row-check').forEach(cb => {
        cb.checked = selectAll.checked;
      });
      updateBulkBar();
    });
  }

  table.addEventListener('change', (e) => {
    if (e.target.classList.contains('row-check')) {
      updateBulkBar();
      if (selectAll) {
        const all     = table.querySelectorAll('.row-check');
        const checked = table.querySelectorAll('.row-check:checked');
        selectAll.indeterminate = checked.length > 0 && checked.length < all.length;
        selectAll.checked       = checked.length === all.length;
      }
    }
  });

  return {
    getSelected() {
      return [...table.querySelectorAll('.row-check:checked')]
        .map(cb => cb.value);
    },
    clearAll() {
      table.querySelectorAll('.row-check').forEach(cb => cb.checked = false);
      if (selectAll) { selectAll.checked = false; selectAll.indeterminate = false; }
      updateBulkBar();
    }
  };
}

/* ══════════════════════════════════════════════════
   CONFIRM DIALOG (custom, gold style)
══════════════════════════════════════════════════ */
/**
 * Show a styled confirm dialog.
 * @param {string} message
 * @param {Function} onConfirm
 * @param {string} [confirmLabel]
 * @param {boolean} [isDanger=false]
 */
function showConfirm(message, onConfirm, confirmLabel = null, isDanger = false) {
  const lbl = confirmLabel || t('confirm_action');
  // Remove existing confirm modal if any
  const existing = document.getElementById('_admin-confirm');
  if (existing) existing.remove();

  const modal = document.createElement('div');
  modal.id    = '_admin-confirm';
  modal.className = 'modal-overlay open';
  modal.innerHTML = `
    <div class="modal-box" style="max-width:400px">
      <div class="modal-header">
        <span class="modal-title" data-i18n="confirm_action">${t('confirm_action') || 'Confirm Action'}</span>
      </div>
      <p style="font-size:14px;color:rgba(44,44,44,0.7);line-height:1.6">${message}</p>
      <div class="modal-footer">
        <button class="btn btn-outline btn-sm" id="_confirm-cancel" data-i18n="cancel">${t('cancel') || 'Cancel'}</button>
        <button class="btn btn-sm ${isDanger ? 'btn-danger' : 'btn-gold'}" id="_confirm-ok">
          ${lbl}
        </button>
      </div>
    </div>`;

  document.body.appendChild(modal);
  document.body.style.overflow = 'hidden';

  document.getElementById('_confirm-cancel').onclick = () => {
    modal.remove();
    document.body.style.overflow = '';
  };

  document.getElementById('_confirm-ok').onclick = () => {
    modal.remove();
    document.body.style.overflow = '';
    onConfirm();
  };

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
      document.body.style.overflow = '';
    }
  });
}

/* ══════════════════════════════════════════════════
   TOAST NOTIFICATIONS
══════════════════════════════════════════════════ */
let _toastContainer = null;

function getToastContainer() {
  if (!_toastContainer) {
    _toastContainer = document.createElement('div');
    _toastContainer.id = '_toast-container';
    const isRtl = (window.currentLang === 'ar');
    Object.assign(_toastContainer.style, {
      position: 'fixed',
      bottom: '24px',
      [isRtl ? 'left' : 'right']: '24px',
      zIndex: '9999',
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
      pointerEvents: 'none',
    });
    document.body.appendChild(_toastContainer);
  }
  return _toastContainer;
}

/**
 * Show a toast message.
 * @param {string} message
 * @param {'success'|'error'|'warning'|'info'} [type='info']
 * @param {number} [duration=3500]
 */
function showToast(message, type = 'info', duration = 3500) {
  const container = getToastContainer();
  const toast = document.createElement('div');
  const colors = {
    success: { bg: '#D1FAE5', color: '#065F46', border: '#A7F3D0' },
    error:   { bg: '#FEE2E2', color: '#991B1B', border: '#FECACA' },
    warning: { bg: '#FEF3C7', color: '#92400E', border: '#FDE68A' },
    info:    { bg: '#DBEAFE', color: '#1E40AF', border: '#BFDBFE' },
  };
  const c = colors[type] || colors.info;

  Object.assign(toast.style, {
    background: c.bg,
    color: c.color,
    border: `1px solid ${c.border}`,
    borderRadius: '8px',
    padding: '12px 18px',
    fontSize: '14px',
    fontWeight: '600',
    fontFamily: 'inherit',
    boxShadow: '0 4px 16px rgba(0,0,0,0.1)',
    pointerEvents: 'all',
    opacity: '0',
    transform: 'translateY(10px)',
    transition: 'opacity 0.25s ease, transform 0.25s ease',
    direction: window.currentLang === 'ar' ? 'rtl' : 'ltr',
    maxWidth: '320px',
  });

  toast.textContent = message;
  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
  });

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/* ══════════════════════════════════════════════════
   GENERIC FETCH WRAPPER (JSON API calls)
══════════════════════════════════════════════════ */
/**
 * Wrapper around fetch for admin API calls.
 * @param {string} url
 * @param {object} [options={}]
 * @returns {Promise<object>}
 */
async function adminFetch(url, options = {}) {
  const defaults = {
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    credentials: 'same-origin',
  };
  const config = { ...defaults, ...options };
  if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
    config.body = JSON.stringify(config.body);
  }
  if (config.body instanceof FormData) {
    delete config.headers['Content-Type'];
  }

  const res = await fetch(url, config);
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data.message || data.error || `HTTP ${res.status}`);
  }
  return data;
}

/* ══════════════════════════════════════════════════
   TOGGLE VISIBILITY (products, coupons, announcements)
══════════════════════════════════════════════════ */
/**
 * Toggle a boolean field on a resource and update the button state.
 * @param {string} url - PUT endpoint
 * @param {object} body - body payload e.g. {is_visible: true}
 * @param {HTMLElement} btn - the toggle button element
 */
async function toggleResource(url, body, btn) {
  try {
    await adminFetch(url, { method: 'PUT', body });
    Admin.showToast(t('update_success') || 'Updated', 'success');
    location.reload();
  } catch (err) {
    Admin.showToast(err.message || t('error_occurred'), 'error');
  }
}

/* ══════════════════════════════════════════════════
   EXPORT: attach to window so inline scripts can use
══════════════════════════════════════════════════ */
/**
 * Sync language toggle with the shared i18n system
 * @param {string} lang 
 */
function setAdminLanguage(lang) {
  if (window.toggleLang) {
    window.toggleLang();
  } else {
    fetch('/api/set-language', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lang })
    }).then(() => location.reload());
  }
}
window.setAdminLanguage = setAdminLanguage;

// Update UI when language changes
window.addEventListener('languageChanged', (e) => {
  const lang = e.detail.lang;
  const btn = document.querySelector('.lang-toggle-btn');
  if (btn) {
    btn.textContent = (lang === 'ar') ? 'English' : 'العربية';
    btn.setAttribute('onclick', `setAdminLanguage('${lang === 'ar' ? 'en' : 'ar'}')`);
  }
});

window.Admin = {
  openModal,
  closeModal,
  showConfirm,
  showToast,
  adminFetch,
  statusBadge,
  renderStars,
  initBulkSelect,
  toggleResource,
  setAdminLanguage,
};
