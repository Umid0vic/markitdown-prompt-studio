/**
 * Application state management.
 */
const State = {
  currentPage: 'convert',
  theme: 'dark',
  tokenBudget: 0,

  // Config from backend
  config: null,

  // Convert page
  files: [],
  conversionResults: [],
  markdownContent: '',
  generatedPrompt: '',
  promptTokens: 0,

  // Library
  folders: [],
  activeFolder: null,
  prompts: [],

  // Templates
  builtinTemplates: [],
  customTemplates: [],

  // Listeners
  _listeners: {},

  on(event, fn) {
    if (!this._listeners[event]) this._listeners[event] = [];
    this._listeners[event].push(fn);
  },

  emit(event, data) {
    (this._listeners[event] || []).forEach(fn => fn(data));
  },

  setPage(page) {
    this.currentPage = page;
    this.emit('pageChange', page);
  },

  setTheme(theme) {
    this.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    this.emit('themeChange', theme);
  },

  setBudget(budget) {
    this.tokenBudget = budget;
    localStorage.setItem('tokenBudget', budget);
    this.emit('budgetChange', budget);
  },

  init() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    this.setTheme(savedTheme);
    const savedBudget = parseInt(localStorage.getItem('tokenBudget') || '0', 10);
    this.tokenBudget = savedBudget;
  }
};
