/* checkout.js – GadgetHub PH
   Handles checkout form validation and order submission
*/

document.addEventListener('DOMContentLoaded', () => {

  const form        = document.getElementById('checkout-form');
  const submitBtn   = document.getElementById('place-order-btn');

  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Basic validation
    const address = document.getElementById('shipping_address').value.trim();
    if (!address) {
      showError('Please enter your shipping address.');
      return;
    }

    // Disable button & show loading
    submitBtn.disabled   = true;
    submitBtn.innerHTML  = '<i class="bi bi-hourglass-split"></i> Placing Order…';

    try {
      const res  = await fetch('/orders/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ shipping_address: address })
      });
      const data = await res.json();

      if (res.ok && data.success) {
        // Redirect to order confirmation
        window.location.href = `/orders/${data.order_id}`;
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

  function showError(msg) {
    let el = document.getElementById('checkout-error');
    if (!el) {
      el = document.createElement('div');
      el.id = 'checkout-error';
      el.className = 'alert alert-danger mt-3';
      form.prepend(el);
    }
    el.textContent = msg;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

});