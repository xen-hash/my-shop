/* checkout.js – GadgetHub PH
   Handles checkout form validation, order submission, and truck animation
*/

document.addEventListener('DOMContentLoaded', () => {

  const form      = document.getElementById('checkout-form');
  const submitBtn = document.getElementById('place-order-btn');

  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const address = document.getElementById('shipping_address').value.trim();
    if (!address) {
      showError('Please enter your shipping address.');
      return;
    }

    // Show truck animation overlay
    showTruckOverlay();

    submitBtn.disabled  = true;
    submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Placing Order…';

    try {
      const res  = await fetch('/orders/checkout', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ shipping_address: address })
      });
      const data = await res.json();

      if (res.ok && data.success) {
        // Let the truck animation play for 2s before redirecting
        setTimeout(() => {
          window.location.href = `/orders/${data.order_id}`;
        }, 2200);
      } else {
        hideTruckOverlay();
        showError(data.message || 'Checkout failed. Please try again.');
        submitBtn.disabled  = false;
        submitBtn.innerHTML = '<i class="bi bi-bag-check"></i> Place Order';
      }
    } catch (err) {
      hideTruckOverlay();
      showError('Network error. Please try again.');
      submitBtn.disabled  = false;
      submitBtn.innerHTML = '<i class="bi bi-bag-check"></i> Place Order';
    }
  });

  function showError(msg) {
    let el = document.getElementById('checkout-error');
    if (!el) {
      el = document.createElement('div');
      el.id        = 'checkout-error';
      el.className = 'alert alert-danger mt-3';
      form.prepend(el);
    }
    el.textContent = msg;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function showTruckOverlay() {
    const overlay = document.getElementById('truck-overlay');
    if (overlay) {
      overlay.style.opacity   = '0';
      overlay.style.display   = 'flex';
      requestAnimationFrame(() => {
        overlay.style.transition = 'opacity 0.4s ease';
        overlay.style.opacity    = '1';
      });
    }
  }

  function hideTruckOverlay() {
    const overlay = document.getElementById('truck-overlay');
    if (overlay) {
      overlay.style.opacity = '0';
      setTimeout(() => { overlay.style.display = 'none'; }, 400);
    }
  }

});