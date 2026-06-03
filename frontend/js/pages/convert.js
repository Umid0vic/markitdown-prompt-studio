/**
 * Convert page logic — upload, convert, build prompt.
 */
const ConvertPage = {
  files: [],

  init() {
    const zone = UI.$('#upload-zone');
    const fileInput = UI.$('#file-input');

    // Click to upload
    zone.addEventListener('click', () => fileInput.click());

    // Drag and drop
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', e => {
      e.preventDefault();
      zone.classList.remove('dragover');
      this.addFiles(Array.from(e.dataTransfer.files));
    });

    // File input change
    fileInput.addEventListener('change', () => {
      this.addFiles(Array.from(fileInput.files));
      fileInput.value = '';
    });

    // Convert button
    UI.$('#convert-btn').addEventListener('click', () => this.convert());

    // Result tabs
    UI.initTabs('#result-tabs');
    UI.initTabs('#prompt-tabs');

    // Copy / Download buttons
    UI.$('#copy-md-btn').addEventListener('click', () => {
      UI.copyToClipboard(State.markdownContent);
    });
    UI.$('#download-md-btn').addEventListener('click', () => {
      const name = State.conversionResults[0]?.output_filename || 'converted.md';
      UI.downloadFile(State.markdownContent, name);
    });

    // Generate prompt
    UI.$('#generate-btn').addEventListener('click', () => this.generatePrompt());

    // Prompt actions
    UI.$('#copy-prompt-btn').addEventListener('click', () => {
      UI.copyToClipboard(State.generatedPrompt);
    });
    UI.$('#download-prompt-btn').addEventListener('click', () => {
      UI.downloadFile(State.generatedPrompt, 'prompt.md');
    });
    UI.$('#save-prompt-btn').addEventListener('click', () => this.saveToLibrary());

    // Editor sync
    UI.$('#markdown-editor').addEventListener('input', e => {
      State.markdownContent = e.target.value;
    });

    // Context panel collapse toggle
    UI.$('#context-toggle').addEventListener('click', () => {
      const body = UI.$('#context-panel-body');
      const btn = UI.$('#context-collapse-btn');
      body.classList.toggle('collapsed');
      btn.classList.toggle('collapsed');
    });
  },

  addFiles(newFiles) {
    const valid = newFiles.filter(f => {
      const ext = '.' + f.name.split('.').pop().toLowerCase();
      return ['.pdf', '.docx', '.pptx', '.xlsx', '.xls'].includes(ext);
    });
    if (valid.length === 0) {
      UI.toast('Unsupported file type', 'error');
      return;
    }
    this.files = [...this.files, ...valid];
    this.renderFileList();
    UI.show('#convert-btn');
  },

  removeFile(index) {
    this.files.splice(index, 1);
    this.renderFileList();
    if (this.files.length === 0) UI.hide('#convert-btn');
  },

  renderFileList() {
    const container = UI.$('#file-list');
    container.innerHTML = this.files.map((f, i) => `
      <div class="file-item">
        <span class="icon">📄</span>
        <span class="name">${f.name}</span>
        <span class="size">${this.formatSize(f.size)}</span>
        <button class="btn btn-ghost btn-sm remove-btn" data-index="${i}">✕</button>
      </div>
    `).join('');

    container.querySelectorAll('.remove-btn').forEach(btn => {
      btn.addEventListener('click', () => this.removeFile(parseInt(btn.dataset.index)));
    });
  },

  formatSize(bytes) {
    if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    if (bytes >= 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return bytes + ' B';
  },

  async convert() {
    if (this.files.length === 0) return;

    const btn = UI.$('#convert-btn');
    btn.textContent = 'Converting...';
    btn.disabled = true;

    try {
      const data = await API.convertFiles(this.files);
      State.conversionResults = data.results;

      const successful = data.results.filter(r => r.status !== 'error');
      if (successful.length === 0) {
        UI.toast('No files converted successfully', 'error');
        return;
      }

      // Use first result for now (combine for batch later)
      State.markdownContent = successful.map(r => r.markdown).join('\n\n---\n\n');

      // Show results
      const totalTokens = successful.reduce((acc, r) => acc + r.token_count, 0);
      const totalChars = successful.reduce((acc, r) => acc + r.char_count, 0);

      UI.$('#result-metrics').innerHTML =
        `<span>${UI.formatNumber(totalTokens)} tokens</span> · <span>${UI.formatNumber(totalChars)} chars</span> · <span>${successful.length} file(s)</span>`;

      UI.$('#markdown-preview').innerHTML = UI.renderMarkdown(State.markdownContent);
      UI.$('#markdown-editor').value = State.markdownContent;

      UI.show('#post-convert');

      // Collapse upload zone to compact mode
      UI.$('#upload-zone').classList.add('compact');

      UI.toast(`Converted ${successful.length} file(s)`);
    } catch (err) {
      UI.toast(err.message, 'error');
    } finally {
      btn.textContent = '⚡ Convert Files';
      btn.disabled = false;
    }
  },

  async generatePrompt() {
    const task = UI.$('#task-input').value.trim();
    if (!task) {
      UI.toast('Enter a task description', 'error');
      return;
    }

    const btn = UI.$('#generate-btn');
    btn.textContent = 'Generating...';
    btn.disabled = true;

    try {
      const data = await API.generatePrompt({
        prompt_type: UI.$('#prompt-type').value,
        role: UI.$('#agent-role').value,
        task: task,
        output_format: UI.$('#output-format').value,
        markdown_content: State.markdownContent,
        filename: State.conversionResults[0]?.filename || 'document',
      });

      State.generatedPrompt = data.prompt;
      State.promptTokens = data.tokens;

      // Metrics
      UI.$('#prompt-metrics').innerHTML =
        UI.metricHtml('Tokens', UI.formatNumber(data.tokens)) +
        UI.metricHtml('Characters', UI.formatNumber(data.chars));

      // Token budget
      if (State.tokenBudget > 0) {
        const pct = Math.min(data.tokens / State.tokenBudget, 1);
        UI.$('#budget-label').textContent = `${UI.formatNumber(data.tokens)} / ${UI.formatNumber(State.tokenBudget)}`;
        const fill = UI.$('#budget-fill');
        fill.style.width = (pct * 100) + '%';
        fill.className = 'progress-fill' + (pct >= 1 ? ' danger' : pct >= 0.8 ? ' warning' : '');
        UI.show('#token-budget-bar');
      } else {
        UI.hide('#token-budget-bar');
      }

      // Render
      UI.$('#prompt-preview').innerHTML = UI.renderMarkdown(data.prompt);
      UI.$('#prompt-editor').value = data.prompt;

      UI.show('#generated-prompt');

      if (data.warning) UI.toast(data.warning, 'error');
      else UI.toast('Prompt generated!');
    } catch (err) {
      UI.toast(err.message, 'error');
    } finally {
      btn.textContent = 'Generate Prompt';
      btn.disabled = false;
    }
  },

  async saveToLibrary() {
    const prompt = UI.$('#prompt-editor').value || State.generatedPrompt;
    const task = UI.$('#task-input').value;
    const defaultName = State.conversionResults[0]?.filename?.replace(/\.[^.]+$/, '') || 'prompt';

    // Ensure folders are loaded
    if (!State.folders.length) {
      try { State.folders = await API.getFolders(); } catch {}
    }

    // Show save modal with name + folder choice
    const folderOptions = (State.folders || []).map(f =>
      `<option value="${f.id}">${f.name}</option>`
    ).join('');

    UI.openModal('Save to Library', `
      <div class="input-group mb-4">
        <label class="input-label">Name</label>
        <input class="input" id="save-name-input" value="${defaultName}">
      </div>
      <div class="input-group mb-4">
        <label class="input-label">Folder</label>
        <select class="select" id="save-folder-select">
          <option value="">No folder</option>
          ${folderOptions}
        </select>
      </div>
      <button class="btn btn-primary" id="save-confirm-btn">Save</button>
    `);

    UI.$('#save-confirm-btn')?.addEventListener('click', async () => {
      const name = UI.$('#save-name-input')?.value?.trim() || defaultName;
      const folderId = UI.$('#save-folder-select')?.value || null;
      try {
        await API.savePrompt({
          name,
          content: prompt,
          task,
          folder_id: folderId,
          tags: [],
          metadata: { type: UI.$('#prompt-type').value, role: UI.$('#agent-role').value },
        });
        UI.closeModal();
        UI.toast('Saved to library!');
        App.refreshStats();
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    });
  },
};
