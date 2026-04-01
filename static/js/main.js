/* main.js – GadgetHub PH */

// ── Animate product cards on scroll ────────────────────────
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = '1';
      entry.target.style.transform = 'translateY(0)';
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.product-card').forEach((card, i) => {
  card.style.opacity = '0';
  card.style.transform = 'translateY(30px)';
  card.style.transition = `opacity 0.5s ease ${i * 0.06}s, transform 0.5s ease ${i * 0.06}s`;
  observer.observe(card);
});

// ── Add to cart ─────────────────────────────────────────────
async function addToCart(productId, btn) {
  if (!btn || btn.disabled) return;

  const original = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<i class="bi bi-hourglass-split"></i>';

  try {
    const res = await fetch('/cart/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: productId, quantity: 1 })
    });
    const data = await res.json();

    if (res.ok && data.success) {
      btn.innerHTML = '<i class="bi bi-check-lg"></i> Added!';
      btn.style.background = 'var(--accent2)';
      updateCartBadge(data.cart_count);
      setTimeout(() => {
        btn.innerHTML = original;
        btn.style.background = '';
        btn.disabled = false;
      }, 1800);
    } else if (res.status === 401) {
      window.location.href = '/login';
    } else {
      btn.innerHTML = original;
      btn.disabled = false;
      alert(data.message || 'Could not add to cart.');
    }
  } catch {
    btn.innerHTML = original;
    btn.disabled = false;
  }
}

// ── Update cart badge count in navbar ───────────────────────
function updateCartBadge(count) {
  const badge = document.querySelector('.cart-badge');
  if (badge) {
    badge.textContent = count;
    badge.style.transform = 'scale(1.4)';
    setTimeout(() => badge.style.transform = '', 300);
  }
}

// ── Auto-dismiss flash alerts ────────────────────────────────
setTimeout(() => {
  document.querySelectorAll('.alert').forEach(a => {
    a.style.transition = 'opacity 0.5s';
    a.style.opacity = '0';
    setTimeout(() => a.remove(), 500);
  });
}, 4000);