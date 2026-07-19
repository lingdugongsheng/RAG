import { $, isNearBottom, renderMarkdown } from './utils.js';
import { store } from './store.js';

export const elements = {
  messages: $('#messages'),
  historyList: $('#history-list'),
  chatTitle: $('#chat-header-title'),
  emptyState: $('#empty-state'),
  sendBtn: $('#send-btn'),
  uploadStatus: $('#upload-status-text'),
  uploadProgress: $('#upload-progress-bar'),
  scrollBottomBtn: $('#scroll-bottom-btn'),
  sidebar: $('#sidebar'),
  sidebarOverlay: $('#sidebar-overlay'),
};

export function renderAll() {
  renderHistory();
  renderMessages();
}

function renderHistory() {
  const list = elements.historyList;
  list.innerHTML = '';
  const sorted = Object.values(store.conversations).sort((a, b) => b.createdAt - a.createdAt);
  sorted.forEach(conv => {
    const item = document.createElement('div');
    item.className = `history-item ${conv.id === store.currentId ? 'active' : ''}`;
    item.setAttribute('role', 'listitem');
    item.tabIndex = 0;
    item.innerHTML = `<span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${conv.title}</span>`;
    item.querySelector('span').addEventListener('click', () => {
      store.switchTo(conv.id);
      renderAll();
      if (window.innerWidth <= 768) closeSidebar();
    });
    const delBtn = document.createElement('button');
    delBtn.className = 'delete-btn';
    delBtn.innerHTML = '🗑';
    delBtn.setAttribute('aria-label', '删除对话');
    delBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      store.deleteConversation(conv.id);
      renderAll();
    });
    item.appendChild(delBtn);
    list.appendChild(item);
  });
}

function renderMessages() {
  const conv = store.getCurrent();
  elements.chatTitle.textContent = conv.title;
  elements.messages.innerHTML = '';

  const emptyDiv = document.createElement('div');
  emptyDiv.className = 'empty-state';
  emptyDiv.id = 'empty-state';
  emptyDiv.innerHTML = `<div class="empty-icon">📚</div><h3>欢迎使用 RAG 智能问答</h3><p>上传文档后即可开始提问</p>`;
  elements.messages.appendChild(emptyDiv);

  conv.messages.forEach(msg => appendMessageElement(msg.role, msg.content, false));
  scrollToBottomIfNeeded(true);
}

export function appendMessageElement(role, content, animate = true) {
  const empty = $('#empty-state');
  if (empty) empty.style.display = 'none';

  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${role}`;
  if (!animate) msgDiv.style.animation = 'none';
  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? '我' : 'AI';
  avatar.setAttribute('aria-hidden', 'true');
  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';
  if (role === 'assistant') {
    contentDiv.innerHTML = renderMarkdown(content);
  } else {
    contentDiv.textContent = content;
  }
  msgDiv.appendChild(avatar);
  msgDiv.appendChild(contentDiv);
  elements.messages.appendChild(msgDiv);
  return contentDiv;
}

let userScrolledUp = false;

function setupScrollListener() {
  const container = elements.messages;
  container.addEventListener('scroll', () => {
    const nearBottom = isNearBottom(container, 100);
    if (!nearBottom) {
      userScrolledUp = true;
      elements.scrollBottomBtn.classList.add('visible');
    } else {
      userScrolledUp = false;
      elements.scrollBottomBtn.classList.remove('visible');
    }
  });

  elements.scrollBottomBtn.addEventListener('click', () => {
    container.scrollTop = container.scrollHeight;
    userScrolledUp = false;
    elements.scrollBottomBtn.classList.remove('visible');
  });
}

export function scrollToBottomIfNeeded(force = false) {
  const container = elements.messages;
  if (force || !userScrolledUp) {
    container.scrollTop = container.scrollHeight;
  }
}

export function closeSidebar() {
  elements.sidebar.classList.remove('open');
  elements.sidebarOverlay.classList.remove('active');
}

// 初始化滚动监听
setupScrollListener();