/**
 * MK7 Real-time Stock Deduction & AJAX Cart Handler
 */
(function () {
  // Ensure toast container exists
  function getToastContainer() {
    let container = document.querySelector('.mk7-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'mk7-toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  function showToast(message, isWarning = false) {
    const container = getToastContainer();
    const toast = document.createElement('div');
    toast.className = 'mk7-toast' + (isWarning ? ' mk7-toast-warning' : '');
    toast.innerHTML = `
      <span class="mk7-toast-icon">${isWarning ? '!' : '✓'}</span>
      <span>${message}</span>
    `;
    container.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => {
      toast.classList.add('show');
    });

    // Auto-remove after 3 seconds
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 320);
    }, 3000);
  }

  // Update UI stock numbers and buttons across the current page
  function updateProductStockUI(productId, remainingStock) {
    // 1. Update stock badge labels
    const stockHolders = document.querySelectorAll(`[data-product-id="${productId}"]`);
    stockHolders.forEach((holder) => {
      const countEl = holder.querySelector('.stock-count');
      const pillEl = holder.classList.contains('stock-pill') ? holder : holder.querySelector('.stock-pill');

      if (countEl) {
        countEl.textContent = remainingStock;
        countEl.classList.remove('pulse');
        void countEl.offsetWidth; // trigger reflow for css animation
        countEl.classList.add('pulse');
      }

      if (pillEl) {
        pillEl.classList.remove('stock-in', 'stock-low', 'stock-out');
        if (remainingStock > 10) {
          pillEl.classList.add('stock-in');
          pillEl.innerHTML = `<span class="stock-count pulse">${remainingStock}</span> in stock`;
        } else if (remainingStock > 0) {
          pillEl.classList.add('stock-low');
          pillEl.innerHTML = `Only <span class="stock-count pulse">${remainingStock}</span> left`;
        } else {
          pillEl.classList.add('stock-out');
          pillEl.innerHTML = `Out of stock`;
        }
      }
    });

    // 2. Disable buttons if out of stock
    if (remainingStock <= 0) {
      const addButtons = document.querySelectorAll(`.btn-add-ajax[data-product-id="${productId}"]`);
      addButtons.forEach((btn) => {
        btn.disabled = true;
        btn.classList.add('disabled');
        if (btn.id === 'detailAddBagBtn') {
          btn.innerHTML = '<i class="bi bi-x-circle me-2"></i> Out of Stock';
        } else {
          btn.textContent = '✕';
          btn.title = 'Sold Out';
        }
      });
    }
  }

  // Update navbar bag counter with bounce effect
  function updateNavCartCount(count) {
    const cartBadge = document.querySelector('.cart-badge');
    if (cartBadge) {
      cartBadge.setAttribute('data-count', count);
      cartBadge.style.transform = 'scale(1.22)';
      setTimeout(() => {
        cartBadge.style.transform = '';
      }, 200);
    }
  }

  // Add click listener
  document.addEventListener('DOMContentLoaded', function () {
    document.addEventListener('click', function (e) {
      const btn = e.target.closest('.btn-add-ajax');
      if (!btn) return;

      e.preventDefault();
      e.stopPropagation();

      const productId = btn.getAttribute('data-product-id');
      if (!productId || btn.disabled) return;

      // Temporary button feedback
      const originalHtml = btn.innerHTML;
      btn.style.pointerEvents = 'none';

      // Get CSRF token if available in DOM or window
      const csrfMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfInput = document.querySelector('input[name="csrf_token"]');
      const csrfToken = (window.CSRF_TOKEN) || (csrfMeta ? csrfMeta.getAttribute('content') : '') || (csrfInput ? csrfInput.value : '');

      const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      };
      if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken;
      }

      fetch('/cart/add-ajax', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ product_id: parseInt(productId) }),
      })
        .then((response) => {
          return response.json().then(
            (data) => ({ status: response.status, body: data }),
            () => ({ status: response.status, body: { success: false, message: 'Server returned error ' + response.status } })
          );
        })
        .then(({ status, body }) => {
          if (status === 200 && body.success) {
            updateProductStockUI(productId, body.remaining_stock);
            updateNavCartCount(body.cart_count);
            showToast(`${body.title ? `"${body.title}" added` : 'Added to Bag'} · ${body.remaining_stock} remaining`);
          } else {
            showToast(body.message || 'Cannot add item to bag.', true);
            if (body.remaining_stock !== undefined) {
              updateProductStockUI(productId, body.remaining_stock);
            }
          }
        })
        .catch((err) => {
          showToast('Network error adding to bag. Please try again.', true);
        })
        .finally(() => {
          btn.style.pointerEvents = '';
        });
    });
  });
})();
