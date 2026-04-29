// static/js/app.js
// Alpine.js components for agent-tui web interface
console.log('[APP] app.js executing');

window.chatApp = function() {
  console.log('[APP] chatApp function called');
  const data = {
    message: '',
    isStreaming: false,
    showProjectModal: false,
    currentProject: null,
    statusText: '',
    errorMessage: '',
    showErrorToast: false,
    currentChatId: null,
    assistantContentBuffer: '',
    editingChatId: null,
    editingChatTitle: '',
    showRenameModal: false,
    showSkills: false,
    _messageSaved: false,

    init() {
      // Use window.PROJECT_CONTEXT if available (set by template)
      if (window.PROJECT_CONTEXT && window.PROJECT_CONTEXT.currentProject) {
        this.currentProject = window.PROJECT_CONTEXT.currentProject;
      }
      
      // Also check URL as fallback
      const match = window.location.pathname.match(/\/chat\/([^\/]+)/);
      this.currentChatId = match ? match[1] : null;
      
      const projectMatch = window.location.pathname.match(/\/project\/([^\/]+)/);
      if (projectMatch && !this.currentProject) this.currentProject = projectMatch[1];
      
      console.log('[APP] chatApp init, chatId:', this.currentChatId, 'projectId:', this.currentProject);
      this.$nextTick(() => this.scrollToBottom());
      window.addEventListener('tool-call-received', (e) => {
        this.$dispatch('open-approval-modal', e.detail);
      });
    },
    navigateToProject(projectId) {
      window.location.href = '/project/' + projectId;
    },
    scrollToBottom() {
      const el = document.getElementById('messages-container');
      if (el) {
        requestAnimationFrame(() => {
          el.scrollTop = el.scrollHeight;
        });
      }
    },
    async sendMessage(chatId) {
      if (!this.message.trim() || this.isStreaming) return;
      this._messageSaved = false;
      const txt = this.message;
      this.addUserMessage(txt);
      this.isStreaming = true;
      this.message = '';
      this.assistantContentBuffer = '';
      if (window.ws && window.ws.readyState === 1) {
        console.log('[CLIENT] Sending message');
        window.ws.send(JSON.stringify({ 
          type: 'chat', 
          message: txt, 
          thread_id: chatId,
          project_id: this.currentProject || null 
        }));
      } else {
        this.isStreaming = false;
        this.errorMessage = 'Not connected';
        this.showErrorToast = true;
        setTimeout(() => this.showErrorToast = false, 5000);
      }
      fetch('/api/chats/' + chatId + '/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'user', content: txt })
      }).catch(e => console.error('Failed to save user message:', e));
    },
    addUserMessage(text) {
      const container = document.getElementById('messages-list');
      if (!container) return;
      const div = document.createElement('div');
      div.className = 'nb-message-user';
      div.innerHTML = '<div class="nb-message-header">You</div><div class="p-4">' + this.esc(text) + '</div>';
      container.appendChild(div);
      this.scrollToBottom();
    },
    addAssistantMessageChunk(text) {
      this.assistantContentBuffer += text;
      const container = document.getElementById('streaming-content');
      const ml = document.getElementById('messages-list');
      let ac = document.getElementById('assistant-content');
      if (!ac) {
        container.dataset.active = 'true';
        const div = document.createElement('div');
        div.className = 'nb-message-assistant';
        div.id = 'current-assistant-message';
        div.innerHTML = '<div class="nb-message-header">Assistant</div><div class="p-4" id="assistant-content"></div>';
        if (ml) ml.appendChild(div);
        ac = document.getElementById('assistant-content');
      }
      if (ac) ac.innerHTML += this.esc(text);
      this.scrollToBottom();
    },
    async finalizeAssistantMessage() {
      const container = document.getElementById('streaming-content');
      if (container) { container.dataset.active = ''; container.innerHTML = ''; }
      const msg = document.getElementById('current-assistant-message');
      if (msg) msg.removeAttribute('id');
      if (this.assistantContentBuffer.trim() && this.currentChatId && !this._messageSaved) {
        this._messageSaved = true;
        try {
          await fetch('/api/chats/' + this.currentChatId + '/messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role: 'assistant', content: this.assistantContentBuffer })
          });
        } catch(e) { console.error('Failed to save assistant message:', e); }
        this.assistantContentBuffer = '';
      }
    },
    esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; },
    showError(msg) { this.errorMessage = msg; this.showErrorToast = true; setTimeout(() => this.showErrorToast = false, 5000); },
    updateStatus(text) { this.statusText = text; },
    async onStreamComplete() {
      this.isStreaming = false;
      await this.finalizeAssistantMessage();
      this.updateStatus('ready');
      this.$nextTick(() => this.scrollToBottom());
    }
  };
  console.log('[APP] Returning data object:', Object.keys(data));
  return data;
};

window.approvalModal = function() {
  return {
    show: false, toolName: '', toolArgs: {}, toolId: '',
    init() {
      this.$el.addEventListener('open-approval-modal', (e) => this.open(e.detail.tool_name, e.detail.tool_args, e.detail.tool_id));
    },
    open(toolName, toolArgs, toolId) { this.toolName = toolName; this.toolArgs = toolArgs || {}; this.toolId = toolId; this.show = true; },
    close() { this.show = false; },
    approve() { if (window.ws && window.ws.readyState === 1) window.ws.send(JSON.stringify({ type: 'approve_tool', tool_id: this.toolId, approved: true })); this.close(); },
    reject() { if (window.ws && window.ws.readyState === 1) window.ws.send(JSON.stringify({ type: 'approve_tool', tool_id: this.toolId, approved: false })); this.close(); }
  };
};

window.ws = null;
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  window.ws = new WebSocket(proto + '//' + location.host + '/ws');
  window.ws.onmessage = (e) => {
    const d = JSON.parse(e.data);
    console.log('[CLIENT] WS:', d.type);
    const el = document.querySelector('[x-data]');
    const app = el && el._x_dataStack && el._x_dataStack[0];
    if (!app) return;
    if (d.type === 'chunk') app.addAssistantMessageChunk && app.addAssistantMessageChunk(d.text);
    else if (d.type === 'message_end') app.onStreamComplete && app.onStreamComplete();
    else if (d.type === 'tool_call') window.dispatchEvent(new CustomEvent('tool-call-received', { detail: d }));
    else if (d.type === 'status') app.updateStatus && app.updateStatus(d.text);
    else if (d.type === 'error') app.showError && app.showError(d.message);
  };
  window.ws.onclose = () => { console.log('WS closed'); setTimeout(connectWS, 1000); };
  window.ws.onerror = (e) => console.error('WS error:', e);
  console.log('[APP] WS connecting...');
}

connectWS();