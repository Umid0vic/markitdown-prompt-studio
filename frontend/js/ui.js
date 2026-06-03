/**
 * UI utility functions.
 */
const UI = {
  $(sel) { return document.querySelector(sel); },
  $$(sel) { return document.querySelectorAll(sel); },

  show(el) { if (typeof el === 'string') el = this.$(el); el?.classList.remove('hidden'); },
  hide(el) { if (typeof el === 'string') el = this.$(el); el?.classList.add('hidden'); },

  toast(message, type = 'success') {
    const container = this.$('#toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  },

  openModal(title, contentHtml, { fullscreen = false } = {}) {
    this.$('#modal-title').textContent = title;
    this.$('#modal-body').innerHTML = contentHtml;
    const overlay = this.$('#modal-overlay');
    overlay.classList.toggle('fullscreen', fullscreen);
    overlay.classList.add('open');
  },

  closeModal() {
    const overlay = this.$('#modal-overlay');
    overlay.classList.remove('open');
    overlay.classList.remove('fullscreen');
  },

  // Simple markdown to HTML (basic)
  renderMarkdown(text) {
    if (!text) return '';
    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Code blocks
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    // Bold & italic
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Lists
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    // Horizontal rules
    html = html.replace(/^---$/gm, '<hr>');
    // Paragraphs
    html = html.replace(/\n\n/g, '</p><p>');
    html = '<p>' + html + '</p>';
    html = html.replace(/<p><\/p>/g, '');
    html = html.replace(/<p>(<h[123]>)/g, '$1');
    html = html.replace(/(<\/h[123]>)<\/p>/g, '$1');
    html = html.replace(/<p>(<pre>)/g, '$1');
    html = html.replace(/(<\/pre>)<\/p>/g, '$1');
    html = html.replace(/<p>(<ul>)/g, '$1');
    html = html.replace(/(<\/ul>)<\/p>/g, '$1');
    html = html.replace(/<p>(<hr>)<\/p>/g, '$1');

    return html;
  },

  // Tab switching
  initTabs(containerSel) {
    const container = typeof containerSel === 'string' ? this.$(containerSel) : containerSel;
    if (!container) return;
    const tabs = container.querySelectorAll('.tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const tabId = tab.dataset.tab;
        // Find corresponding content
        const parent = container.parentElement;
        parent.querySelectorAll(':scope > .tab-content').forEach(tc => {
          tc.classList.remove('active');
          if (tc.id === 'tab-' + tabId) tc.classList.add('active');
        });
      });
    });
  },

  // Populate select element
  populateSelect(sel, options, selectedValue = '') {
    const select = typeof sel === 'string' ? this.$(sel) : sel;
    if (!select) return;
    select.innerHTML = options.map(opt =>
      `<option value="${opt}" ${opt === selectedValue ? 'selected' : ''}>${opt}</option>`
    ).join('');
  },

  // Copy to clipboard
  async copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      this.toast('Copied to clipboard!');
    } catch {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      this.toast('Copied to clipboard!');
    }
  },

  // Download file
  downloadFile(content, filename, mimeType = 'text/markdown') {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },

  downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },

  // Format numbers
  formatNumber(n) {
    return n.toLocaleString();
  },

  // Metric HTML
  metricHtml(label, value) {
    return `<div class="metric"><div class="metric-value">${value}</div><div class="metric-label">${label}</div></div>`;
  },
};
