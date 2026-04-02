/* checkout.js – GadgetHub PH
   Handles checkout form validation, order submission,
   and a spectacular success animation (confetti + truck)
*/

document.addEventListener('DOMContentLoaded', () => {

  const form      = document.getElementById('checkout-form');
  const submitBtn = document.getElementById('place-order-btn');

  if (!form) return;

  // ── Magnetic button effect ────────────────────────────────
  submitBtn.addEventListener('mousemove', (e) => {
    const rect = submitBtn.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top  - rect.height / 2;
    submitBtn.style.transform = `translate(${x * 0.12}px, ${y * 0.12}px) scale(1.04)`;
  });
  submitBtn.addEventListener('mouseleave', () => {
    submitBtn.style.transform = '';
  });

  // ── Form submit ───────────────────────────────────────────
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const address = document.getElementById('shipping_address').value.trim();
    if (!address) {
      showError('Please enter your shipping address.');
      shakeField('shipping_address');
      return;
    }

    submitBtn.disabled  = true;
    submitBtn.innerHTML = '<span class="spinner-dots"><span></span><span></span><span></span></span> Processing…';

    try {
      const res  = await fetch('/orders/checkout', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ shipping_address: address })
      });
      const data = await res.json();

      if (res.ok && data.success) {
        showSuccessOverlay();
        setTimeout(() => {
          window.location.href = `/orders/${data.order_id}`;
        }, 3200);
      } else {
        showError(data.message || 'Checkout failed. Please try again.');
        submitBtn.disabled  = false;
        submitBtn.innerHTML = '<i class="bi bi-bag-check"></i> Place Order';
      }
    } catch (err) {
      showError('Network error. Please try again.');
      submitBtn.disabled  = false;
      submitBtn.innerHTML = '<i class="bi bi-bag-check"></i> Place Order';
    }
  });

  // ── Error helpers ─────────────────────────────────────────
  function showError(msg) {
    let el = document.getElementById('checkout-error');
    if (!el) {
      el = document.createElement('div');
      el.id        = 'checkout-error';
      el.className = 'alert alert-danger mt-3';
      form.prepend(el);
    }
    el.textContent = msg;
    el.style.animation = 'none';
    void el.offsetWidth;
    el.style.animation = 'shakeX 0.4s ease';
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function shakeField(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.animation = 'none';
    void el.offsetWidth;
    el.style.animation = 'shakeX 0.4s ease';
    el.addEventListener('animationend', () => el.style.animation = '', { once: true });
  }

  // ── Success overlay ───────────────────────────────────────
  function showSuccessOverlay() {
    const overlay = document.getElementById('success-overlay');
    if (!overlay) return;

    overlay.style.display = 'flex';
    requestAnimationFrame(() => {
      overlay.style.opacity = '1';
    });

    // Launch confetti
    launchConfetti();

    // Animate truck across screen
    const truck = overlay.querySelector('.checkout-truck');
    if (truck) {
      setTimeout(() => {
        truck.style.transform   = 'translateX(110vw)';
        truck.style.transition  = 'transform 2.2s cubic-bezier(0.25,0.46,0.45,0.94)';
      }, 400);
    }

    // Animate checkmark
    const check = overlay.querySelector('.success-checkmark');
    if (check) {
      setTimeout(() => check.classList.add('pop'), 200);
    }
  }

  // ── Confetti ──────────────────────────────────────────────
  function launchConfetti() {
    const canvas = document.getElementById('confetti-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;

    const colors  = ['#7c5cfc','#ff4d6d','#00d4aa','#ffc107','#fff'];
    const pieces  = Array.from({ length: 120 }, () => ({
      x:     Math.random() * canvas.width,
      y:     -20,
      w:     Math.random() * 10 + 5,
      h:     Math.random() * 14 + 6,
      color: colors[Math.floor(Math.random() * colors.length)],
      rot:   Math.random() * 360,
      rotV:  (Math.random() - 0.5) * 6,
      vy:    Math.random() * 4 + 2,
      vx:    (Math.random() - 0.5) * 3,
      alpha: 1,
    }));

    let frame;
    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      let alive = 0;
      for (const p of pieces) {
        p.y   += p.vy;
        p.x   += p.vx;
        p.rot += p.rotV;
        if (p.y > canvas.height * 0.7) p.alpha = Math.max(0, p.alpha - 0.025);
        if (p.alpha <= 0) continue;
        alive++;
        ctx.save();
        ctx.globalAlpha = p.alpha;
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot * Math.PI / 180);
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
        ctx.restore();
      }
      if (alive > 0) frame = requestAnimationFrame(draw);
    }
    draw();
    setTimeout(() => cancelAnimationFrame(frame), 3500);
  }

});