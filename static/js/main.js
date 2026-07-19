import { $, showToast, renderMarkdown, getThemePreference, setThemePreference, applyTheme } from './utils.js';
import { API } from './api.js';
import { store } from './store.js';
import { elements, renderAll, appendMessageElement, scrollToBottomIfNeeded, closeSidebar } from './renderer.js';

let currentAbortController = null;
let userScrolledUpFlag = false;

// 初始化主题
applyTheme(getThemePreference());

/** 发送消息（流式） */
async function sendMessage(userQuery = null) {
  const input = $('#user-input');
  const query = userQuery || input.value.trim();
  if (!query) return;

  if (!userQuery) {
    input.value = '';
    input.style.height = 'auto';
  }

  if (currentAbortController) {
    currentAbortController();
    currentAbortController = null;
    setSendButtonState('idle');
  }

  const conv = store.getCurrent();
  const lastMsg = conv.messages[conv.messages.length - 1];
  if (!lastMsg || lastMsg.role !== 'user' || lastMsg.content !== query) {
    store.addMessage('user', query);
    renderAll();
  }

  store.addMessage('assistant', '');
  const contentDiv = appendMessageElement('assistant', '思考中...');
  let fullContent = '';

  setSendButtonState('streaming');

  const abort = API.chatStream(query, {
    onToken(token) {
      fullContent += token;
      contentDiv.innerHTML = renderMarkdown(fullContent);
      store.updateLastAssistant(fullContent);
      scrollToBottomIfNeeded(false);
    },
    onDone() {
      store.updateLastAssistant(fullContent);
      renderAll();
      scrollToBottomIfNeeded(true);
      setSendButtonState('idle');
      currentAbortController = null;
    },
    onError(err) {
      store.removeLastMessage();
      store.addMessage('assistant', `请求失败：${err.message}`);
      renderAll();
      const lastMsgDiv = elements.messages.lastChild;
      if (lastMsgDiv && lastMsgDiv.classList.contains('message') && lastMsgDiv.classList.contains('assistant')) {
        const btn = document.createElement('button');
        btn.textContent = '重试';
        btn.className = 'retry-btn';
        btn.style.cssText = 'margin-top:8px; padding:4px 12px; border-radius:6px; border:1px solid var(--border); background:var(--ai-msg-bg); cursor:pointer; color:var(--text-primary);';
        btn.addEventListener('click', () => {
          store.removeLastMessage();
          renderAll();
          sendMessage(query);
        });
        lastMsgDiv.querySelector('.message-content')?.appendChild(btn);
      }
      setSendButtonState('idle');
      currentAbortController = null;
      showToast(`错误: ${err.message}`);
    },
    onRetry() {
      showToast('连接超时，正在重试...');
    }
  });

  currentAbortController = abort;
}

function setSendButtonState(state) {
  const btn = elements.sendBtn;
  btn.classList.remove('loading', 'processing');
  if (state === 'streaming') {
    btn.classList.add('loading');
    btn.disabled = false;
    btn.setAttribute('aria-label', '停止生成');
  } else if (state === 'processing') {
    btn.classList.add('processing');
    btn.disabled = true;
    btn.setAttribute('aria-label', '发送中...');
  } else {
    btn.disabled = false;
    btn.setAttribute('aria-label', '发送消息');
  }
}

function handleSendClick() {
  if (currentAbortController) {
    currentAbortController();
    currentAbortController = null;
    setSendButtonState('idle');
    const conv = store.getCurrent();
    const lastMsg = conv.messages[conv.messages.length - 1];
    if (lastMsg && lastMsg.role === 'assistant' && lastMsg.content === '') {
      store.updateLastAssistant('（已中止）');
      renderAll();
    }
    showToast('已停止生成');
  } else {
    sendMessage();
  }
}

/** 上传文件并更新右侧状态和进度条 */
let uploadAbort = null;
async function uploadFile(file) {
  const statusEl = elements.uploadStatus;
  const progressEl = elements.uploadProgress;
  statusEl.textContent = '⏳ 上传中...';
  statusEl.style.color = 'var(--accent-light)';
  progressEl.style.display = 'block';
  progressEl.style.width = '0%';

  if (uploadAbort) uploadAbort();

  const abort = API.uploadFile(file, {
    onStatus({ status, chunks, fileName, message }) {
      if (status === 'done') {
        statusEl.textContent = `✅ ${fileName} (${chunks}块)`;
        progressEl.style.width = '100%';
        setTimeout(() => {
          progressEl.style.display = 'none';
          progressEl.style.width = '0%';
          statusEl.style.color = '';
          statusEl.textContent = '';
        }, 4000);
        showToast('文档处理完成，可以开始提问了');
        const emptyState = $('#empty-state');
        if (emptyState && emptyState.style.display !== 'none') {
          emptyState.querySelector('p').textContent = '文档已就绪，开始提问吧';
        }
      } else if (status === 'error') {
        statusEl.textContent = '❌ 上传失败';
        statusEl.style.color = '#ef4444';
        progressEl.style.display = 'none';
        showToast(`上传失败: ${message}`);
      }
    },
    onProgress(percent) {
      progressEl.style.width = `${percent}%`;
      if (percent >= 100) {
        setTimeout(() => {
          progressEl.style.display = 'none';
          progressEl.style.width = '0%';
        }, 1000);
      }
    }
  });

  uploadAbort = abort;
}

function setupDragDrop() {
  const dropOverlay = $('#drop-overlay');
  let dragCounter = 0;

  document.addEventListener('dragenter', (e) => {
    e.preventDefault();
    dragCounter++;
    if (dragCounter === 1) dropOverlay.classList.add('active');
  });
  document.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dragCounter--;
    if (dragCounter === 0) dropOverlay.classList.remove('active');
  });
  document.addEventListener('dragover', (e) => e.preventDefault());
  document.addEventListener('drop', (e) => {
    e.preventDefault();
    dragCounter = 0;
    dropOverlay.classList.remove('active');
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type === 'application/pdf' || file.name.endsWith('.txt') || file.name.endsWith('.md')) {
        uploadFile(file);
      } else {
        showToast('仅支持 PDF、TXT、MD 文件');
      }
    }
  });
}

/** 导出对话 */
function exportConversations() {
  const jsonStr = store.exportAll();
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `rag-conversations-${new Date().toISOString().slice(0,10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('对话已导出');
}

/** 导入对话 */
function importConversations(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    const result = store.importConversations(e.target.result);
    if (result.success) {
      showToast(`成功导入 ${result.count} 个对话`);
      renderAll();
    } else {
      showToast(result.message || '导入失败');
    }
  };
  reader.readAsText(file);
}

/** 主题切换 */
function cycleTheme() {
  const prefs = ['auto', 'light', 'dark'];
  const current = getThemePreference();
  const currentIdx = prefs.indexOf(current);
  const next = prefs[(currentIdx + 1) % prefs.length];
  setThemePreference(next);
  const icons = { auto: '🌓', light: '☀️', dark: '🌙' };
  $('#theme-toggle-btn').textContent = icons[next];
  showToast(`主题：${next === 'auto' ? '自动' : next === 'light' ? '浅色' : '深色'}`);
}

document.addEventListener('DOMContentLoaded', () => {
  renderAll();

  // 新对话按钮防重复
  $('#new-chat-btn').addEventListener('click', () => {
    if (store.isCurrentConversationEmpty()) {
      renderAll();
      const input = $('#user-input');
      input.value = '';
      input.style.height = 'auto';
      input.focus();
      if (window.innerWidth <= 768) closeSidebar();
      return;
    }
    store.createConversation();
    renderAll();
    const input = $('#user-input');
    input.value = '';
    input.style.height = 'auto';
    input.focus();
    if (window.innerWidth <= 768) closeSidebar();
  });

  $('#send-btn').addEventListener('click', handleSendClick);

  const textarea = $('#user-input');
  textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (currentAbortController) {
        handleSendClick();
      } else {
        sendMessage();
      }
    }
  });
  textarea.addEventListener('input', () => {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
  });

  // 右侧上传触发
  const fileInput = $('#file-input');
  document.querySelector('.file-label').addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      uploadFile(e.target.files[0]);
      e.target.value = '';
    }
  });

  // 移动端菜单
  $('#menu-toggle').addEventListener('click', () => {
    const isOpen = elements.sidebar.classList.toggle('open');
    elements.sidebarOverlay.classList.toggle('active');
    $('#menu-toggle').setAttribute('aria-expanded', isOpen);
  });
  elements.sidebarOverlay.addEventListener('click', closeSidebar);

  // 键盘快捷键
  document.addEventListener('keydown', (e) => {
    // Esc 关闭侧边栏
    if (e.key === 'Escape' && elements.sidebar.classList.contains('open')) {
      closeSidebar();
    }
    // Ctrl/Cmd + N 新对话
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
      e.preventDefault();
      if (store.isCurrentConversationEmpty()) {
        renderAll();
        textarea.focus();
        return;
      }
      store.createConversation();
      renderAll();
      textarea.focus();
      if (window.innerWidth <= 768) closeSidebar();
    }
    // Ctrl/Cmd + K 聚焦输入框
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      textarea.focus();
    }
  });

  // 导出/导入/主题
  $('#export-btn').addEventListener('click', exportConversations);
  $('#import-btn').addEventListener('click', () => $('#import-file-input').click());
  $('#import-file-input').addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      importConversations(e.target.files[0]);
      e.target.value = '';
    }
  });
  $('#theme-toggle-btn').addEventListener('click', cycleTheme);

  setupDragDrop();

  // Markdown 高亮
  if (typeof marked !== 'undefined' && typeof hljs !== 'undefined') {
    marked.setOptions({
      highlight: function(code, lang) {
        const language = hljs.getLanguage(lang) ? lang : 'plaintext';
        return hljs.highlight(code, { language }).value;
      },
      langPrefix: 'hljs language-',
    });
  }

  // 对话切换后聚焦输入框
  store.subscribe(() => {
    const input = $('#user-input');
    if (document.activeElement !== input) {
      setTimeout(() => input.focus(), 0);
    }
  });

  // 初始化主题图标
  const themeIcons = { auto: '🌓', light: '☀️', dark: '🌙' };
  $('#theme-toggle-btn').textContent = themeIcons[getThemePreference()];

  console.log('✨ RAG 前端已就绪（终极优化版）');
});