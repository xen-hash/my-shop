/* main.js – GadgetHub PH
   Enhanced with: ripple clicks, magnetic hover, stagger reveal,
   cart badge bounce, and smooth page transitions.
*/

// ── Page entrance transition ─────────────────────────────────
document.body.style.opacity = '0';
document.body.style.transition = 'opacity 0.35s ease';
window.addEventListener('load', () => {
  document.body.style.opacity = '1';
});

// Smooth exit on nav links
document.querySelectorAll('a[href]').forEach(link => {
  const href = link.getAttribute('href');
  if (!href || href.startsWith('#') || href.startsWith('javascript') ||
      link.target === '_blank') return;
  link.addEventListener('click', (e) => {
    const dest = link.href;
    if (dest && dest !== window.location.href) {
      e.preventDefault();
      document.body.style.opacity = '0';
      setTimeout(() => window.location.href = dest, 280);
    }
  });
});

// ── Stagger-reveal product cards on scroll ──────────────────
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity    = '1';
      entry.target.style.transform  = 'translateY(0) scale(1)';
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.08 });

document.querySelectorAll('.product-card').forEach((card, i) => {
  card.style.opacity    = '0';
  card.style.transform  = 'translateY(32px) scale(0.97)';
  card.style.transition = `opacity 0.5s ease ${i * 0.07}s,
                           transform 0.5s cubic-bezier(0.34,1.2,0.64,1) ${i * 0.07}s`;
  observer.observe(card);
});

// ── Magnetic tilt on product cards ──────────────────────────
document.querySelectorAll('.product-card').forEach(card => {
  card.addEventListener('mousemove', (e) => {
    const rect = card.getBoundingClientRect();
    const cx   = rect.left + rect.width  / 2;
    const cy   = rect.top  + rect.height / 2;
    const dx   = (e.clientX - cx) / (rect.width  / 2);
    const dy   = (e.clientY - cy) / (rect.height / 2);
    card.style.transform  = `
      perspective(600px)
      rotateX(${-dy * 5}deg)
      rotateY(${dx * 5}deg)
      translateY(-6px)
      scale(1.02)
    `;
    card.style.transition = 'transform 0.1s ease, box-shadow 0.1s ease';
    card.style.boxShadow  = `
      ${dx * -8}px ${dy * -8}px 30px rgba(124,92,252,0.18)
    `;
  });

  card.addEventListener('mouseleave', () => {
    card.style.transition = 'transform 0.4s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.4s ease';
    card.style.transform  = '';
    card.style.boxShadow  = '';
  });
});

// ── Ripple effect on "Add to Cart" buttons ──────────────────
function createRipple(btn, e) {
  const rect = btn.getBoundingClientRect();
  const x = e ? e.clientX - rect.left : rect.width  / 2;
  const y = e ? e.clientY - rect.top  : rect.height / 2;
  const ripple = document.createElement('span');
  const size   = Math.max(rect.width, rect.height) * 2;
  Object.assign(ripple.style, {
    position:     'absolute',
    width:        `${size}px`,
    height:       `${size}px`,
    left:         `${x - size / 2}px`,
    top:          `${y - size / 2}px`,
    background:   'rgba(255,255,255,0.25)',
    borderRadius: '50%',
    transform:    'scale(0)',
    animation:    'rippleAnim 0.55s linear',
    pointerEvents:'none',
  });
  btn.style.position = 'relative';
  btn.style.overflow = 'hidden';
  btn.appendChild(ripple);
  ripple.addEventListener('animationend', () => ripple.remove());
}

if (!document.getElementById('ripple-style')) {
  const s = document.createElement('style');
  s.id = 'ripple-style';
  s.textContent = `
    @keyframes rippleAnim {
      to { transform: scale(1); opacity: 0; }
    }
  `;
  document.head.appendChild(s);
}

// ── Add to cart ─────────────────────────────────────────────
async function addToCart(productId, btn, event) {
  if (!btn || btn.disabled) return;

  createRipple(btn, event);

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
      btn.style.transform  = 'scale(1.06)';
      updateCartBadge(data.cart_count);
      setTimeout(() => {
        btn.innerHTML        = original;
        btn.style.background = '';
        btn.style.transform  = '';
        btn.disabled         = false;
      }, 1800);
    } else if (res.status === 401) {
      window.location.href = '/login';
    } else {
      btn.innerHTML = original;
      btn.disabled  = false;
      alert(data.message || 'Could not add to cart.');
    }
  } catch {
    btn.innerHTML = original;
    btn.disabled  = false;
  }
}

// ── Update cart badge in navbar ──────────────────────────────
function updateCartBadge(count) {
  const badge = document.querySelector('.cart-badge');
  if (!badge) return;
  badge.textContent = count;
  badge.style.transition = 'transform 0.25s cubic-bezier(0.34,1.56,0.64,1)';
  badge.style.transform  = 'scale(1.6)';
  setTimeout(() => badge.style.transform = 'scale(1)', 300);
}

// ── Auto-dismiss flash alerts ────────────────────────────────
setTimeout(() => {
  document.querySelectorAll('.alert').forEach(a => {
    a.style.transition = 'opacity 0.5s, transform 0.5s';
    a.style.opacity    = '0';
    a.style.transform  = 'translateY(-10px)';
    setTimeout(() => a.remove(), 500);
  });
}, 4000);