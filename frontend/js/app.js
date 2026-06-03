/**
 * Main application bootstrapper.
 */
const App = {
  async init() {
    State.init();

    // Load backend config
    try {
      State.config = await API.getConfig();
      UI.populateSelect('#prompt-type', State.config.prompt_types);
      UI.populateSelect('#agent-role', State.config.agent_roles);
      UI.populateSelect('#output-format', State.config.output_formats);
    } catch (err) {
      console.error('Failed to load config:', err);
    }

    // Initialize pages
    ConvertPage.init();
    LibraryPage.init();
    TemplatesPage.init();
    SettingsPage.init();

    // Navigation
    this.setupNavigation();

    // Modal close
    UI.$('#modal-close').addEventListener('click', () => UI.closeModal());
    UI.$('#modal-overlay').addEventListener('click', e => {
      if (e.target === UI.$('#modal-overlay')) UI.closeModal();
    });

    // Theme toggle in sidebar
    UI.$('#theme-toggle').addEventListener('click', () => {
      const next = State.theme === 'dark' ? 'light' : 'dark';
      State.setTheme(next);
      SettingsPage.updateThemeButtons();
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') UI.closeModal();
    });

    // Initial stats
    this.refreshStats();

    // Show initial page
    this.showPage('convert');
  },

  setupNavigation() {
    UI.$$('.nav-item[data-page]').forEach(item => {
      item.addEventListener('click', () => {
        const page = item.dataset.page;
        State.setPage(page);
        this.showPage(page);
      });
    });
  },

  showPage(page) {
    // Hide all pages
    UI.$$('.page').forEach(p => p.classList.add('hidden'));
    // Show target
    const target = UI.$(`#page-${page}`);
    if (target) target.classList.remove('hidden');

    // Update nav active state
    UI.$$('.nav-item[data-page]').forEach(item => {
      item.classList.toggle('active', item.dataset.page === page);
    });

    // Load page data
    if (page === 'library') LibraryPage.load();
    if (page === 'templates') TemplatesPage.load();
    if (page === 'settings') SettingsPage.load();
  },

  async refreshStats() {
    try {
      const stats = await API.getStats();
      UI.$('#stat-prompts').textContent = stats.total_prompts;
      UI.$('#stat-folders').textContent = stats.total_folders;
    } catch { /* ignore */ }
  },
};

// Boot
document.addEventListener('DOMContentLoaded', () => App.init());
