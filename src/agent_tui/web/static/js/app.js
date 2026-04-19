// static/js/app.js
// Alpine.js components for agent-tui web interface

document.addEventListener('alpine:init', () => {
  Alpine.data('chatApp', () => ({
    message: '',
    isStreaming: false,
    showProjectModal: false,
    currentProject: null,
    
    init() {
      this.$nextTick(() => {
        this.scrollToBottom();
      });
    },
    
    scrollToBottom() {
      const container = this.$refs.messagesContainer;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    },
    
    async sendMessage() {
      if (!this.message.trim() || this.isStreaming) return;
      
      this.isStreaming = true;
      const messageText = this.message;
      this.message = '';
      
      // Trigger HTMX request
      this.$refs.chatForm.dispatchEvent(new Event('submit'));
    },
    
    onStreamComplete() {
      this.isStreaming = false;
      this.$nextTick(() => this.scrollToBottom());
    }
  }));
  
  Alpine.data('approvalModal', () => ({
    show: false,
    toolName: '',
    toolArgs: {},
    toolId: '',
    
    open(toolName, toolArgs, toolId) {
      this.toolName = toolName;
      this.toolArgs = toolArgs;
      this.toolId = toolId;
      this.show = true;
    },
    
    close() {
      this.show = false;
    },
    
    approve() {
      this.$dispatch('tool-approved', { toolId: this.toolId, approved: true });
      this.close();
    },
    
    reject() {
      this.$dispatch('tool-approved', { toolId: this.toolId, approved: false });
      this.close();
    }
  }));
});
