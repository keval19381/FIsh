// ── Auto-dismiss flash messages ──────────────────────────────────────────
document.querySelectorAll('.flash-msg').forEach(el => {
  el.addEventListener('click', () => el.remove());
  setTimeout(() => el.remove(), 4000);
});

// ── Hamburger menu ────────────────────────────────────────────────────────
const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('nav-links');
if (hamburger && navLinks) {
  hamburger.addEventListener('click', () => {
    navLinks.classList.toggle('open');
  });
}

// ── Loading overlay on form submit ────────────────────────────────────────
const overlay = document.getElementById('loading-overlay');
document.querySelectorAll('form.with-loading').forEach(form => {
  form.addEventListener('submit', function(e) {
    const btn = form.querySelector('button[type="submit"]');
    if (btn) {
      btn.disabled = true;
      btn.classList.add('btn-loading');
    }
    if (overlay) overlay.classList.add('active');
  });
});

// ── Auto-calculate total price ────────────────────────────────────────────
const qtyInput = document.getElementById('quantity');
const pricePerKg = document.getElementById('price-per-kg');
const totalDisplay = document.getElementById('total-display');

if (qtyInput && pricePerKg && totalDisplay) {
  const price = parseFloat(pricePerKg.dataset.price || 0);
  const calcTotal = () => {
    const qty = parseFloat(qtyInput.value) || 0;
    const total = (price * qty).toFixed(2);
    totalDisplay.textContent = '₹' + total;
    totalDisplay.style.color = qty > 0 ? 'var(--primary)' : 'var(--text-muted)';
  };
  qtyInput.addEventListener('input', calcTotal);
  calcTotal();
}

// ── Update cart count ────────────────────────────────────────────────────
function updateCartCount() {
  fetch('/cart/count')
    .then(response => response.json())
    .then(data => {
      const cartCount = document.getElementById('cart-count');
      if (cartCount) {
        cartCount.textContent = data.count;
        cartCount.style.display = data.count > 0 ? 'inline' : 'none';
      }
    })
    .catch(error => console.error('Error updating cart count:', error));
}

// Update cart count on page load
document.addEventListener('DOMContentLoaded', updateCartCount);
const searchInput = document.getElementById('fish-search');
const fishCards = document.querySelectorAll('.fish-card');

if (searchInput && fishCards.length) {
  searchInput.addEventListener('input', function() {
    const q = this.value.trim().toLowerCase();
    let visible = 0;
    fishCards.forEach(card => {
      const name = card.dataset.name || '';
      const show = !q || name.toLowerCase().includes(q);
      card.style.display = show ? '' : 'none';
      if (show) visible++;
    });
    const noResults = document.getElementById('no-results');
    if (noResults) noResults.style.display = visible === 0 ? '' : 'none';
  });
}

// ── Role selector on register page ───────────────────────────────────────
document.querySelectorAll('.role-option').forEach(opt => {
  opt.addEventListener('click', () => {
    document.querySelectorAll('.role-option').forEach(o => o.classList.remove('selected'));
    opt.classList.add('selected');
    const radio = opt.querySelector('input[type="radio"]');
    if (radio) radio.checked = true;
  });
  const radio = opt.querySelector('input[type="radio"]');
  if (radio && radio.checked) opt.classList.add('selected');
});

// ── Image preview on file input ───────────────────────────────────────────
const imgInput = document.getElementById('fish-image-input');
const imgPreview = document.getElementById('fish-image-preview');
if (imgInput && imgPreview) {
  imgInput.addEventListener('change', function() {
    if (this.files && this.files[0]) {
      const reader = new FileReader();
      reader.onload = e => {
        imgPreview.src = e.target.result;
        imgPreview.style.display = 'block';
      };
      reader.readAsDataURL(this.files[0]);
    }
  });
}

// ── Confirm delete ────────────────────────────────────────────────────────
document.querySelectorAll('.confirm-delete').forEach(form => {
  form.addEventListener('submit', function(e) {
    const name = this.dataset.name || 'this item';
    if (!confirm(`Remove ${name}? This cannot be undone.`)) {
      e.preventDefault();
    }
  });
});
