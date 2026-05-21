<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useChatStore } from '../stores/chat'
import MessageBubble from './MessageBubble.vue'

const store = useChatStore()
const input = ref('')
const msgList = ref<HTMLElement>()

watch(() => store.messages.length, async () => {
  await nextTick()
  if (msgList.value) {
    msgList.value.scrollTop = msgList.value.scrollHeight
  }
})

async function sendMessage() {
  if (!input.value.trim() || store.isStreaming) return

  const msg = input.value
  input.value = ''

  store.addMessage({ role: 'user', content: msg, timestamp: new Date().toISOString() })
  store.isStreaming = true
  store.addMessage({ role: 'assistant', content: '', timestamp: new Date().toISOString() })

  try {
    const es = store.streamChat(msg)
    es.addEventListener('session', (e: MessageEvent) => {
      store.currentSessionId = e.data
    })
    es.addEventListener('token', (e: MessageEvent) => {
      const msgs = store.messages
      const last = msgs[msgs.length - 1]
      if (last && last.role === 'assistant') {
        last.content += e.data
      }
    })
    es.addEventListener('done', () => {
      store.isStreaming = false
      store.refreshSessions()
      es.close()
    })
    es.addEventListener('error', () => {
      store.isStreaming = false
      es.close()
    })
  } catch {
    store.isStreaming = false
  }
}
</script>

<template>
  <main class="chat-panel">
    <header class="chat-header">
      <span class="session-label">
        {{ store.currentSessionId ? store.currentSessionId.slice(0, 8) + '...' : '新对话' }}
      </span>
    </header>

    <div class="message-list" ref="msgList">
      <div v-if="store.messages.length === 0" class="welcome">
        <h2>Film-Agent</h2>
        <p>影视讨论助手 — 可以聊电影、查信息、求推荐</p>
      </div>
      <MessageBubble
        v-for="(msg, i) in store.messages"
        :key="i"
        :role="msg.role"
        :content="msg.content"
        :timestamp="msg.timestamp"
        :is-streaming="store.isStreaming && i === store.messages.length - 1 && msg.role === 'assistant'"
      />
    </div>

    <div class="input-area">
      <textarea
        v-model="input"
        @keydown.enter.exact.prevent="sendMessage()"
        placeholder="输入消息，Enter 发送..."
        rows="2"
        :disabled="store.isStreaming"
      ></textarea>
      <button class="send-btn" @click="sendMessage" :disabled="store.isStreaming">发送</button>
      <a href="/export/stats" class="stats-btn">统计</a>
    </div>
  </main>
</template>

<style scoped>
.chat-panel {
  flex: 1;
  height: 100vh;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}
.session-label {
  font-size: 13px;
  color: var(--text-muted);
  font-family: monospace;
}
.export-btn, .stats-btn {
  padding: 6px 12px;
  border: 1px solid var(--text-muted);
  background: transparent;
  color: var(--text-secondary);
  border-radius: 6px;
  font-size: 12px;
  text-decoration: none;
  transition: all 200ms;
}
.export-btn:hover, .stats-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
}
.welcome {
  text-align: center;
  margin: auto;
  opacity: 0.5;
}
.welcome h2 {
  font-family: 'Righteous', sans-serif;
  font-size: 36px;
  color: var(--accent);
  margin-bottom: 8px;
}
.welcome p {
  color: var(--text-secondary);
  font-size: 14px;
}
.input-area {
  display: flex;
  gap: 8px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  align-items: center;
  flex-shrink: 0;
}
textarea {
  flex: 1;
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-primary);
  resize: none;
  font-size: 14px;
  outline: none;
}
textarea:focus {
  border-color: var(--accent);
}
textarea:disabled {
  opacity: 0.5;
}
.send-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  background: var(--accent);
  color: #121212;
  font-weight: 600;
  font-size: 14px;
  transition: opacity 200ms;
}
.send-btn:disabled {
  opacity: 0.5;
}
.send-btn:hover:not(:disabled) {
  opacity: 0.9;
}
.stats-btn {
  white-space: nowrap;
}
</style>
