// Optional live repository metadata. Core content and language links need no JavaScript.
(() => {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  fetch('https://api.github.com/repos/arpanjot-coding/CheatCraft', {
    credentials: 'omit',
    headers: { Accept: 'application/vnd.github+json' },
    signal: controller.signal
  }).then(response => {
    if (!response.ok) throw new Error('Repository metadata unavailable');
    return response.json();
  }).then(data => {
    const count = data.stargazers_count;
    if (!Number.isSafeInteger(count) || count < 0) return;
    const formatted = new Intl.NumberFormat(document.documentElement.lang).format(count);
    document.querySelectorAll('[data-stars]').forEach(element => {
      element.textContent = formatted;
      const link = element.closest('[data-star-label]');
      if (link) link.setAttribute('aria-label', link.dataset.starLabel + ': ' + formatted);
    });
  }).catch(() => {
    // Keep the neutral placeholder if the public API is rate-limited or unavailable.
  }).finally(() => clearTimeout(timeout));
})();
