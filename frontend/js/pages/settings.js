/**
 * Settings page logic.
 */
const SettingsPage = {
  init() {
    UI.$('#theme-dark-btn').addEventListener('click', () => {
      State.setTheme('dark');
      this.updateThemeButtons();
    });

    UI.$('#theme-light-btn').addEventListener('click', () => {
      State.setTheme('light');
      this.updateThemeButtons();
    });

    UI.$$('.budget-preset').forEach(btn => {
      btn.addEventListener('click', () => {
        const budget = parseInt(btn.dataset.budget, 10);
        State.setBudget(budget);
        UI.$('#budget-custom').value = budget || '';
        this.updateBudgetButtons();
        UI.toast(`Token budget: ${budget === 0 ? 'unlimited' : UI.formatNumber(budget)}`);
      });
    });

    UI.$('#budget-custom').addEventListener('change', e => {
      const val = parseInt(e.target.value, 10) || 0;
      State.setBudget(val);
      this.updateBudgetButtons();
    });
  },

  load() {
    this.updateThemeButtons();
    this.updateBudgetButtons();
    this.loadStats();
    UI.$('#budget-custom').value = State.tokenBudget || '';
  },

  updateThemeButtons() {
    UI.$('#theme-dark-btn').classList.toggle('btn-primary', State.theme === 'dark');
    UI.$('#theme-light-btn').classList.toggle('btn-primary', State.theme === 'light');
    // Update sidebar toggle icon
    UI.$('#theme-toggle').textContent = State.theme === 'dark' ? '☀' : '🌙';
  },

  updateBudgetButtons() {
    UI.$$('.budget-preset').forEach(btn => {
      btn.classList.toggle('btn-primary', parseInt(btn.dataset.budget, 10) === State.tokenBudget);
    });
  },

  async loadStats() {
    const stats = await API.getStats();
    UI.$('#settings-stats').innerHTML =
      UI.metricHtml('Prompts', stats.total_prompts) +
      UI.metricHtml('Folders', stats.total_folders) +
      UI.metricHtml('Tags', stats.total_tags) +
      UI.metricHtml('Favorites', stats.favorites);
  },
};
