/* cart.js – GadgetHub PH
   Handles cart quantity updates and item removal via fetch API
*/

// ── Update item quantity ─────────────────────────────────────
async function updateQty(cartItemId, delta) {
  const qtyEl = document.getElementById(`qty-${cartItemId}`);
  const current = parseInt(qtyEl.textContent);
  const newQty  = current + delta;

  if (newQty < 1) {
    removeItem(cartItemId);
    return;
  }

  try {
    const res  = await fetch('/cart/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cart_item_id: cartItemId, quantity: newQty })
    });
    const data = await res.json();

    if (res.ok && data.success) {
      qtyEl.textContent = newQty;
      // Update subtotal for this row
      const subtotalEl = document.getElementById(`subtotal-${cartItemId}`);
      if (subtotalEl) subtotalEl.textContent = `₱${data.subtotal.toFixed(2)}`;
      // Update totals
      refreshTotals(data.cart_total, data.cart_count);
    }
  } catch (err) {
    console.error('Update qty error:', err);
  }
}

// ── Remove item ──────────────────────────────────────────────
async function removeItem(cartItemId) {
  const row = document.getElementById(`cart-item-${cartItemId}`);
  if (row) {
    row.style.transition = 'opacity 0.3s, transform 0.3s';
    row.style.opacity    = '0';
    row.style.transform  = 'translateX(-20px)';
  }

  try {
    const res  = await fetch('/cart/remove', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cart_item_id: cartItemId })
    });
    const data = await res.json();

    if (res.ok && data.success) {
      setTimeout(() => {
        if (row) row.remove();
        refreshTotals(data.cart_total, data.cart_count);
        if (data.cart_count === 0) showEmptyCart();
      }, 300);
    }
  } catch (err) {
    console.error('Remove item error:', err);
    if (row) { row.style.opacity = '1'; row.style.transform = ''; }
  }
}

// ── Refresh totals in sidebar ────────────────────────────────
function refreshTotals(total, count) {
  const totalEl = document.getElementById('cart-total');
  const countEl = document.getElementById('cart-count');
  const badgeEl = document.querySelector('.cart-badge');

  if (totalEl) totalEl.textContent = `₱${parseFloat(total).toFixed(2)}`;
  if (countEl) countEl.textContent = count;
  if (badgeEl) badgeEl.textContent = count;
}

// ── Show empty cart state ─────────────────────────────────────
function showEmptyCart() {
  const container = document.getElementById('cart-items-container');
  if (container) {
    container.innerHTML = `
      <div class="empty-cart">
        <div class="empty-cart-icon">🛒</div>
        <h3>Your cart is empty</h3>
        <p>Looks like you haven't added anything yet.</p>
        <a href="/" class="btn-primary-custom mt-3">
          <i class="bi bi-grid-fill"></i> Start Shopping
        </a>
      </div>`;
  }
  // Hide checkout button and summary
  const checkoutBtn = document.getElementById('checkout-btn');
  if (checkoutBtn) checkoutBtn.style.display = 'none';
}