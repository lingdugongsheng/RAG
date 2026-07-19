export const $ = (sel) => document.querySelector(sel);
export const $$ = (sel) => document.querySelectorAll(sel);

export function showToast(message, duration = 3000) {
  const container = document.getElementById('toast-container') || document.body;
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  toast.style.cssText = `
    background:rgba(0,0,0,0.8); color:white; padding:8px 16px; border-radius:20px;
    font-size:0.9rem; margin-bottom:8px; pointer-events:auto;
    animation: fadeSlideUp 0.3s ease;
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.2s';
    setTimeout(() => toast.remove(), 200);
  }, duration);
}

export function isNearBottom(el, threshold = 50) {
  return el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
}

export function renderMarkdown(markdown) {
  if (!markdown) return '';
  const rawHtml = marked.parse(markdown);
  const clean = DOMPurify.sanitize(rawHtml, {
    ALLOWED_TAGS: ['p','b','i','em','strong','code','pre','ul','ol','li','a','br','span','blockquote','h1','h2','h3','h4','h5','h6','table','thead','tbody','tr','th','td'],
    ALLOWED_ATTR: ['href','target','rel','class']
  });
  const template = document.createElement('div');
  template.innerHTML = clean;
  template.querySelectorAll('a').forEach(a => {
    a.setAttribute('target', '_blank');
    a.setAttribute('rel', 'noopener noreferrer');
  });
  return template.innerHTML;
}

/**
 * 主题管理
 */
const THEME_KEY = 'rag_theme_preference';
export function getThemePreference() {
  return localStorage.getItem(THEME_KEY) || 'auto';
}
export function setThemePreference(pref) {
  localStorage.setItem(THEME_KEY, pref);
  applyTheme(pref);
}
export function applyTheme(pref) {
  const root = document.documentElement;
  if (pref === 'dark') {
    root.classList.add('theme-dark');
  } else if (pref === 'light') {
    root.classList.remove('theme-dark');
  } else {
    // auto: 跟随系统
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (prefersDark) {
      root.classList.add('theme-dark');
    } else {
      root.classList.remove('theme-dark');
    }
  }
}