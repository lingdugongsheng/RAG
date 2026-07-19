class ConversationStore {
  constructor() {
    this.STORAGE_KEY = 'rag_conversations_v2';
    this.CURRENT_KEY = 'rag_current_id';
    this.conversations = {};
    this.currentId = null;
    this.listeners = [];
    this._load();
  }

  subscribe(fn) {
    this.listeners.push(fn);
    return () => { this.listeners = this.listeners.filter(l => l !== fn); };
  }

  _notify() {
    this.listeners.forEach(fn => fn(this.conversations, this.currentId));
  }

  _load() {
    const raw = localStorage.getItem(this.STORAGE_KEY);
    this.conversations = raw ? JSON.parse(raw) : {};
    this.currentId = localStorage.getItem(this.CURRENT_KEY) || null;
    if (Object.keys(this.conversations).length === 0) {
      this.currentId = this.createConversation();
    } else if (!this.currentId || !this.conversations[this.currentId]) {
      this.currentId = Object.keys(this.conversations)[0];
      localStorage.setItem(this.CURRENT_KEY, this.currentId);
    }
    this._notify();
  }

  _save() {
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.conversations));
    this._notify();
  }

  createConversation() {
    const id = 'conv_' + Date.now() + Math.random().toString(36).slice(2, 6);
    this.conversations[id] = { id, title: '新对话', messages: [], createdAt: Date.now() };
    this.currentId = id;
    localStorage.setItem(this.CURRENT_KEY, id);
    this._save();
    return id;
  }

  isCurrentConversationEmpty() {
    const conv = this.getCurrent();
    return conv && conv.messages.length === 0 && conv.title === '新对话';
  }

  getCurrent() {
    if (!this.currentId || !this.conversations[this.currentId]) {
      this.currentId = Object.keys(this.conversations)[0] || this.createConversation();
    }
    return this.conversations[this.currentId];
  }

  switchTo(id) {
    if (this.conversations[id]) {
      this.currentId = id;
      localStorage.setItem(this.CURRENT_KEY, id);
      this._notify();
    }
  }

  deleteConversation(id) {
    if (!confirm('确定删除这个对话吗？')) return;
    delete this.conversations[id];
    if (this.currentId === id) {
      const ids = Object.keys(this.conversations);
      this.currentId = ids.length > 0 ? ids[0] : this.createConversation();
      localStorage.setItem(this.CURRENT_KEY, this.currentId);
    }
    this._save();
  }

  addMessage(role, content) {
    const conv = this.getCurrent();
    const msg = { role, content, timestamp: Date.now() };
    conv.messages.push(msg);
    if (role === 'user' && conv.title === '新对话') {
      conv.title = content.substring(0, 30) + (content.length > 30 ? '...' : '');
    }
    this._save();
    return msg;
  }

  updateLastAssistant(content) {
    const conv = this.getCurrent();
    const lastMsg = conv.messages[conv.messages.length - 1];
    if (lastMsg && lastMsg.role === 'assistant') {
      lastMsg.content = content;
      this._save();
    }
  }

  removeLastMessage() {
    const conv = this.getCurrent();
    conv.messages.pop();
    this._save();
  }

  /** 导出全部对话为 JSON 字符串 */
  exportAll() {
    return JSON.stringify(this.conversations, null, 2);
  }

  /** 导入对话（合并，跳过重复ID） */
  importConversations(jsonStr) {
    try {
      const data = JSON.parse(jsonStr);
      if (typeof data !== 'object') throw new Error('无效格式');
      let added = 0;
      for (const [id, conv] of Object.entries(data)) {
        if (!this.conversations[id]) {
          this.conversations[id] = conv;
          added++;
        }
      }
      if (added === 0) {
        return { success: false, message: '没有新对话被导入（可能已存在）' };
      }
      // 若当前对话不存在，切换到第一个导入的
      if (!this.currentId || !this.conversations[this.currentId]) {
        this.currentId = Object.keys(this.conversations)[0];
      }
      this._save();
      return { success: true, count: added };
    } catch (e) {
      return { success: false, message: '文件格式错误' };
    }
  }
}

export const store = new ConversationStore();