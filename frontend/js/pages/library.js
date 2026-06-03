/**
 * Library page logic — folders, search, CRUD.
 */
const LibraryPage = {
  activeFolder: null,
  searchQuery: '',
  filterTag: '',
  favoritesOnly: false,

  init() {
    UI.$('#lib-search').addEventListener('input', e => {
      this.searchQuery = e.target.value;
      this.loadPrompts();
    });

    UI.$('#lib-tag-filter').addEventListener('change', e => {
      this.filterTag = e.target.value;
      this.loadPrompts();
    });

    UI.$('#lib-fav-toggle').addEventListener('click', () => {
      this.favoritesOnly = !this.favoritesOnly;
      UI.$('#lib-fav-toggle').textContent = this.favoritesOnly ? '★ Favorites' : '☆ Favorites';
      UI.$('#lib-fav-toggle').classList.toggle('btn-primary', this.favoritesOnly);
      this.loadPrompts();
    });

    UI.$('#lib-new-folder-btn').addEventListener('click', () => this.showNewFolderModal());
    UI.$('#lib-import-btn').addEventListener('click', () => UI.$('#import-input').click());
    UI.$('#lib-export-btn').addEventListener('click', () => this.exportLibrary());

    UI.$('#import-input').addEventListener('change', async e => {
      const file = e.target.files[0];
      if (file) {
        await API.importPrompt(file, this.activeFolder);
        UI.toast(`Imported: ${file.name}`);
        this.loadPrompts();
        App.refreshStats();
      }
      e.target.value = '';
    });

    // Folder "All" click
    UI.$('.folder-item[data-folder=""]').addEventListener('click', () => {
      this.activeFolder = null;
      this.renderFolderActive();
      this.loadPrompts();
    });
  },

  async load() {
    await Promise.all([this.loadFolders(), this.loadPrompts(), this.loadTags()]);
  },

  async loadFolders() {
    State.folders = await API.getFolders();
    this.renderFolders();
  },

  async loadPrompts() {
    const params = {};
    if (this.activeFolder) params.folder_id = this.activeFolder;
    if (this.filterTag) params.tag = this.filterTag;
    if (this.searchQuery) params.search = this.searchQuery;
    if (this.favoritesOnly) params.favorites_only = true;

    State.prompts = await API.getPrompts(params);
    this.renderPrompts();
  },

  async loadTags() {
    const tags = await API.getTags();
    const select = UI.$('#lib-tag-filter');
    select.innerHTML = '<option value="">All Tags</option>' +
      tags.map(t => `<option value="${t}">${t}</option>`).join('');
  },

  renderFolders() {
    const container = UI.$('#library-folders');
    container.innerHTML = State.folders.map(f => `
      <div class="folder-item ${f.id === this.activeFolder ? 'active' : ''}" data-folder="${f.id}">
        📁 ${f.name}
        <button class="btn btn-ghost btn-sm" data-delete-folder="${f.id}" style="margin-left:auto;opacity:0.5;font-size:0.7rem">✕</button>
      </div>
    `).join('');

    container.querySelectorAll('.folder-item').forEach(el => {
      el.addEventListener('click', e => {
        if (e.target.dataset.deleteFolder) return;
        this.activeFolder = el.dataset.folder || null;
        this.renderFolderActive();
        this.loadPrompts();
      });
    });

    container.querySelectorAll('[data-delete-folder]').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.stopPropagation();
        await API.deleteFolder(btn.dataset.deleteFolder);
        this.loadFolders();
        App.refreshStats();
      });
    });

    // Also render sidebar folders
    const sidebarFolders = UI.$('#sidebar-folders');
    sidebarFolders.innerHTML = State.folders.map(f =>
      `<button class="nav-item" data-page="library" data-folder-shortcut="${f.id}">
        <span class="icon">📁</span> ${f.name}
      </button>`
    ).join('');

    sidebarFolders.querySelectorAll('[data-folder-shortcut]').forEach(btn => {
      btn.addEventListener('click', () => {
        this.activeFolder = btn.dataset.folderShortcut;
        State.setPage('library');
        this.renderFolderActive();
        this.loadPrompts();
      });
    });
  },

  renderFolderActive() {
    UI.$$('.folder-item').forEach(el => {
      el.classList.toggle('active', (el.dataset.folder || null) === this.activeFolder);
    });
  },

  renderPrompts() {
    const container = UI.$('#library-prompts');
    const empty = UI.$('#library-empty');

    if (State.prompts.length === 0) {
      container.innerHTML = '';
      UI.show(empty);
      return;
    }

    UI.hide(empty);
    container.innerHTML = State.prompts.map(p => `
      <div class="prompt-item" data-id="${p.id}">
        <span class="favorite ${p.favorite ? 'active' : ''}" data-fav="${p.id}">${p.favorite ? '★' : '☆'}</span>
        <div class="info">
          <div class="title">${p.name}</div>
          <div class="subtitle">${p.task || ''}</div>
          <div class="mt-2">${(p.tags || []).map(t => `<span class="tag">${t}</span>`).join(' ')}</div>
        </div>
        <div class="actions">
          <button class="btn btn-sm" data-open="${p.id}">Open</button>
          <button class="btn btn-sm" data-move="${p.id}">📁 Move</button>
          <button class="btn btn-sm" data-copy="${p.id}">📋</button>
          <button class="btn btn-danger btn-sm" data-del="${p.id}">🗑</button>
        </div>
      </div>
    `).join('');

    // Event listeners
    container.querySelectorAll('[data-fav]').forEach(el => {
      el.addEventListener('click', async e => {
        e.stopPropagation();
        await API.toggleFavorite(el.dataset.fav);
        this.loadPrompts();
      });
    });

    container.querySelectorAll('[data-open]').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        this.openPrompt(btn.dataset.open);
      });
    });

    container.querySelectorAll('[data-copy]').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.stopPropagation();
        const res = await API.getPromptContent(btn.dataset.copy);
        UI.copyToClipboard(res.content);
      });
    });

    container.querySelectorAll('[data-move]').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        this.showMoveModal(btn.dataset.move);
      });
    });

    container.querySelectorAll('[data-del]').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.stopPropagation();
        await API.deletePrompt(btn.dataset.del);
        this.loadPrompts();
        App.refreshStats();
        UI.toast('Prompt deleted');
      });
    });
  },

  async openPrompt(id) {
    const res = await API.getPromptContent(id);
    const prompt = State.prompts.find(p => p.id === id);

    UI.openModal(prompt?.name || 'Prompt', `
      <div class="mb-4">
        ${(prompt?.tags || []).map(t => `<span class="tag">${t}</span>`).join(' ')}
      </div>
      <div class="markdown-preview">${UI.renderMarkdown(res.content)}</div>
      <div class="flex gap-3 mt-5">
        <button class="btn btn-primary" id="modal-copy-btn">📋 Copy</button>
        <button class="btn" id="modal-dl-btn">⬇ Download</button>
      </div>
    `, { fullscreen: true });

    UI.$('#modal-copy-btn')?.addEventListener('click', () => UI.copyToClipboard(res.content));
    UI.$('#modal-dl-btn')?.addEventListener('click', () => UI.downloadFile(res.content, (prompt?.name || 'prompt') + '.md'));
  },

  showMoveModal(promptId) {
    const folderOptions = [
      `<div class="folder-item" data-move-to="" style="margin-bottom:var(--space-2)">📂 No Folder (root)</div>`,
      ...State.folders.map(f =>
        `<div class="folder-item" data-move-to="${f.id}" style="margin-bottom:var(--space-2)">📁 ${f.name}</div>`
      )
    ].join('');

    UI.openModal('Move to Folder', `
      <div id="move-folder-list">${folderOptions}</div>
    `);

    UI.$$('#move-folder-list .folder-item').forEach(el => {
      el.addEventListener('click', async () => {
        const folderId = el.dataset.moveTo || null;
        await API.movePrompt(promptId, folderId);
        UI.closeModal();
        this.loadPrompts();
        UI.toast('Prompt moved');
      });
    });
  },

  showNewFolderModal() {
    UI.openModal('New Folder', `
      <div class="input-group mb-4">
        <label class="input-label">Folder name</label>
        <input class="input" id="new-folder-input" placeholder="My Folder">
      </div>
      <button class="btn btn-primary" id="create-folder-confirm">Create</button>
    `);

    UI.$('#create-folder-confirm')?.addEventListener('click', async () => {
      const name = UI.$('#new-folder-input')?.value?.trim();
      if (name) {
        await API.createFolder(name);
        UI.closeModal();
        this.loadFolders();
        App.refreshStats();
        UI.toast(`Folder "${name}" created`);
      }
    });
  },

  async exportLibrary() {
    const blob = await API.exportLibrary();
    UI.downloadBlob(blob, 'prompt_library.zip');
    UI.toast('Library exported');
  },
};
