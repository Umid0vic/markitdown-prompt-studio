/**
 * Templates page logic.
 */
const TemplatesPage = {
  init() {
    UI.initTabs('#template-tabs');
    UI.$('#save-template-btn').addEventListener('click', () => this.saveTemplate());
  },

  async load() {
    await Promise.all([this.loadBuiltin(), this.loadCustom()]);
  },

  async loadBuiltin() {
    State.builtinTemplates = await API.getBuiltinTemplates();
    this.renderBuiltin();
  },

  async loadCustom() {
    State.customTemplates = await API.getCustomTemplates();
    this.renderCustom();
  },

  renderBuiltin() {
    const container = UI.$('#builtin-template-list');
    container.innerHTML = State.builtinTemplates.map(tpl => `
      <div class="card mb-4">
        <div class="card-header">
          <h3 class="card-title">${tpl.name}</h3>
          <div>${(tpl.tags || []).map(t => `<span class="tag">${t}</span>`).join(' ')}</div>
        </div>
        <p class="text-sm text-muted mb-4">${tpl.description}</p>
        <p class="text-xs text-muted mb-4">Variables: ${tpl.variables.map(v => `<code>{{${v}}}</code>`).join(', ')}</p>

        <div class="flex gap-3 flex-col" style="max-width:400px">
          ${tpl.variables.map(v => `
            <div class="input-group">
              <label class="input-label">${v}</label>
              <input class="input" id="tpl-${tpl.id}-${v}" placeholder="Enter ${v}...">
            </div>
          `).join('')}
          <div class="input-group">
            <label class="input-label">Context</label>
            <textarea class="textarea" id="tpl-${tpl.id}-context" placeholder="Paste context..." style="min-height:80px"></textarea>
          </div>
        </div>

        <div class="flex gap-3 mt-4">
          <button class="btn btn-primary" data-gen-tpl="${tpl.id}">Generate</button>
          <button class="btn" data-save-tpl="${tpl.id}">Save to Library</button>
        </div>

        <div class="hidden mt-4" id="tpl-result-${tpl.id}">
          <div class="markdown-preview" id="tpl-preview-${tpl.id}" style="max-height:300px"></div>
          <div class="flex gap-3 mt-3">
            <button class="btn btn-sm" data-copy-tpl="${tpl.id}">📋 Copy</button>
            <button class="btn btn-sm" data-dl-tpl="${tpl.id}">⬇ Download</button>
          </div>
        </div>
      </div>
    `).join('');

    // Generate handlers
    container.querySelectorAll('[data-gen-tpl]').forEach(btn => {
      btn.addEventListener('click', () => this.generateFromTemplate(btn.dataset.genTpl));
    });

    container.querySelectorAll('[data-save-tpl]').forEach(btn => {
      btn.addEventListener('click', () => this.saveFromTemplate(btn.dataset.saveTpl));
    });

    container.querySelectorAll('[data-copy-tpl]').forEach(btn => {
      btn.addEventListener('click', () => {
        const preview = UI.$(`#tpl-preview-${btn.dataset.copyTpl}`);
        UI.copyToClipboard(preview?.dataset?.content || '');
      });
    });

    container.querySelectorAll('[data-dl-tpl]').forEach(btn => {
      btn.addEventListener('click', () => {
        const tpl = State.builtinTemplates.find(t => t.id === btn.dataset.dlTpl);
        const preview = UI.$(`#tpl-preview-${btn.dataset.dlTpl}`);
        UI.downloadFile(preview?.dataset?.content || '', `${tpl?.name || 'template'}.md`);
      });
    });
  },

  generateFromTemplate(tplId) {
    const tpl = State.builtinTemplates.find(t => t.id === tplId);
    if (!tpl) return;

    let filled = tpl.template;
    tpl.variables.forEach(v => {
      const val = UI.$(`#tpl-${tplId}-${v}`)?.value || `[${v}]`;
      filled = filled.replace(new RegExp(`\\{\\{${v}\\}\\}`, 'g'), val);
    });
    const ctx = UI.$(`#tpl-${tplId}-context`)?.value || '[paste context here]';
    filled = filled.replace(/\{\{context\}\}/g, ctx);

    const preview = UI.$(`#tpl-preview-${tplId}`);
    preview.innerHTML = UI.renderMarkdown(filled);
    preview.dataset.content = filled;
    UI.show(`#tpl-result-${tplId}`);
    UI.toast('Template generated!');
  },

  async saveFromTemplate(tplId) {
    const preview = UI.$(`#tpl-preview-${tplId}`);
    const content = preview?.dataset?.content;
    if (!content) {
      UI.toast('Generate first', 'error');
      return;
    }
    const tpl = State.builtinTemplates.find(t => t.id === tplId);
    await API.savePrompt({ name: tpl?.name || 'Template', content, task: tpl?.description || '' });
    UI.toast('Saved to library!');
    App.refreshStats();
  },

  renderCustom() {
    const container = UI.$('#custom-template-list');
    if (State.customTemplates.length === 0) {
      container.innerHTML = '<p class="text-muted" style="padding:var(--space-8);text-align:center">No custom templates yet.</p>';
      return;
    }

    container.innerHTML = State.customTemplates.map(tpl => `
      <div class="card mb-4">
        <div class="card-header">
          <h3 class="card-title">${tpl.name}</h3>
          <button class="btn btn-danger btn-sm" data-del-ctpl="${tpl.id}">Delete</button>
        </div>
        <p class="text-sm text-muted mb-4">${tpl.description || ''}</p>
        <p class="text-xs text-muted">Variables: ${(tpl.variables || []).map(v => `<code>{{${v}}}</code>`).join(', ') || 'none'}</p>
      </div>
    `).join('');

    container.querySelectorAll('[data-del-ctpl]').forEach(btn => {
      btn.addEventListener('click', async () => {
        await API.deleteTemplate(btn.dataset.delCtpl);
        this.loadCustom();
        UI.toast('Template deleted');
      });
    });
  },

  async saveTemplate() {
    const name = UI.$('#tpl-name')?.value?.trim();
    const body = UI.$('#tpl-body')?.value?.trim();
    if (!name || !body) {
      UI.toast('Name and body are required', 'error');
      return;
    }

    const desc = UI.$('#tpl-desc')?.value?.trim() || '';
    const vars = (UI.$('#tpl-vars')?.value || '').split(',').map(s => s.trim()).filter(Boolean);
    const tags = (UI.$('#tpl-tags')?.value || '').split(',').map(s => s.trim()).filter(Boolean);

    await API.saveTemplate({ name, description: desc, template: body, variables: vars, tags });
    UI.toast(`Template "${name}" saved!`);
    this.loadCustom();

    // Clear form
    UI.$('#tpl-name').value = '';
    UI.$('#tpl-desc').value = '';
    UI.$('#tpl-vars').value = '';
    UI.$('#tpl-tags').value = '';
    UI.$('#tpl-body').value = '';
  },
};
