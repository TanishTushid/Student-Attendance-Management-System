/* EduFlow — Main JavaScript */

// ── Attendance radio label toggle ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {

  // Make att-radio-label visually toggle on click
  document.querySelectorAll('.att-radio-label input[type="radio"]').forEach(radio => {
    radio.addEventListener('change', function() {
      const group = this.closest('.att-radio-group');
      group.querySelectorAll('.att-radio-label').forEach(lbl => {
        lbl.classList.remove('checked');
      });
      this.closest('.att-radio-label').classList.add('checked');
    });
    // Initialize checked state
    if (radio.checked) {
      radio.closest('.att-radio-label').classList.add('checked');
    }
  });

  // ── Animate stat cards on load ────────────────────────────────────────
  document.querySelectorAll('.stat-card').forEach((card, i) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(16px)';
    setTimeout(() => {
      card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, 60 * i);
  });

  // ── Animate progress bars ─────────────────────────────────────────────
  document.querySelectorAll('.progress-fill').forEach(bar => {
    const targetWidth = bar.style.width;
    bar.style.width = '0%';
    setTimeout(() => {
      bar.style.width = targetWidth;
    }, 200);
  });

  // ── Confirmation dialogs ──────────────────────────────────────────────
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', function(e) {
      if (!confirm(this.dataset.confirm)) e.preventDefault();
    });
  });
});
