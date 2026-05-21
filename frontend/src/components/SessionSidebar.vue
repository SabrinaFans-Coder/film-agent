<script setup lang="ts">
import { ref, computed } from 'vue'
import { useChatStore } from '../stores/chat'

const store = useChatStore()
const searchQuery = ref('')

const filteredSessions = computed(() => {
  if (!searchQuery.value.trim()) return store.sessions
  const q = searchQuery.value.toLowerCase()
  return store.sessions.filter(s =>
    (s.last_preview || '').toLowerCase().includes(q)
  )
})
</script>

<template>
  <aside class="sidebar">
    <h1 class="logo">Film-Agent</h1>
    <button class="new-chat-btn" @click="store.newSession()">+ 新对话</button>
    <input
      v-model="searchQuery"
      class="search-input"
      placeholder="搜索对话..."
      type="text"
    />
    <div class="session-list">
      <div
        v-for="s in filteredSessions"
        :key="s.session_id"
        :class="['session-item', { active: s.session_id === store.currentSessionId, unhealthy: !s.healthy }]"
        @click="store.selectSession(s.session_id)"
      >
        <div class="session-preview" :title="s.last_preview">
          <span v-if="!s.healthy" class="warn-icon" title="此对话工具调用链断裂，建议删除">⚠ </span>
          {{ s.last_preview || '新对话' }}
        </div>
        <div class="session-meta">
          <span class="session-count">{{ s.message_count }} 条消息</span>
          <button class="delete-btn" @click.stop="store.deleteCurrentSession(s.session_id)" :title="!s.healthy ? '建议删除此失效对话' : '删除'">✕</button>
        </div>
      </div>
      <div v-if="store.sessions.length === 0" class="empty-hint">
        暂无对话，开始聊天吧
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 280px;
  height: 100vh;
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  padding: 20px;
  border-right: 1px solid var(--border-color);
  flex-shrink: 0;
}
.logo {
  font-family: 'Righteous', sans-serif;
  font-size: 24px;
  color: var(--accent);
  margin-bottom: 20px;
}
.new-chat-btn {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--accent);
  background: transparent;
  color: var(--accent);
  border-radius: 8px;
  font-size: 14px;
  transition: all 200ms;
}
.new-chat-btn:hover {
  background: var(--accent);
  color: var(--bg-primary);
}
.search-input {
  width: 100%;
  padding: 8px 12px;
  margin-top: 8px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
}
.search-input:focus { border-color: var(--accent); }
.search-input::placeholder { color: var(--text-muted); }
.session-list {
  flex: 1;
  overflow-y: auto;
  margin-top: 8px;
}
.session-item {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 200ms;
}
.session-item:hover {
  background: var(--border-color);
}
.session-item.active {
  background: var(--bg-tertiary);
}
.session-item.unhealthy {
  border-left: 3px solid var(--danger);
}
.warn-icon { font-size: 12px; }
.session-preview {
  font-size: 13px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
  font-size: 11px;
  color: var(--text-muted);
}
.delete-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 14px;
  padding: 2px 6px;
  border-radius: 4px;
  transition: color 200ms;
}
.delete-btn:hover {
  color: var(--danger);
  background: rgba(239, 68, 68, 0.1);
}
.empty-hint {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 20px 0;
}
</style>
