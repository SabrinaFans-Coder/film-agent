<script setup lang="ts">
import { ref, onMounted } from 'vue'
import SessionSidebar from './components/SessionSidebar.vue'
import ChatPanel from './components/ChatPanel.vue'
import MyRatings from './components/MyRatings.vue'
import { useChatStore } from './stores/chat'

const store = useChatStore()
store.refreshSessions()

const activeTab = ref<'chat' | 'ratings'>('chat')
const isDark = ref(true)

function toggleTheme() {
  isDark.value = !isDark.value
  document.body.classList.toggle('light', !isDark.value)
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}

onMounted(() => {
  const saved = localStorage.getItem('theme')
  if (saved === 'light') {
    isDark.value = false
    document.body.classList.add('light')
  }
})
</script>

<template>
  <div class="app-layout">
    <SessionSidebar v-if="activeTab === 'chat'" />
    <ChatPanel v-if="activeTab === 'chat'" />
    <MyRatings v-if="activeTab === 'ratings'" />

    <div class="top-bar">
      <div class="tabs">
        <button :class="['tab', { active: activeTab === 'chat' }]" @click="activeTab = 'chat'">对话</button>
        <button :class="['tab', { active: activeTab === 'ratings' }]" @click="activeTab = 'ratings'">我的评分</button>
      </div>
      <button class="theme-toggle" @click="toggleTheme" :title="isDark ? '切换浅色' : '切换深色'">
        {{ isDark ? '☀' : '☾' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  position: relative;
}

.top-bar {
  position: fixed;
  top: 8px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 200;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 4px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.2);
}

.tabs {
  display: flex;
  gap: 2px;
}

.tab {
  padding: 6px 16px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  border-radius: 7px;
  font-size: 13px;
  font-weight: 500;
  transition: all 200ms;
}
.tab:hover { color: var(--text-primary); }
.tab.active {
  background: var(--accent);
  color: #121212;
}

.theme-toggle {
  width: 32px;
  height: 32px;
  border-radius: 16px;
  border: 1px solid var(--border-color);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 200ms;
  flex-shrink: 0;
}
.theme-toggle:hover {
  background: var(--accent);
  color: #121212;
  border-color: var(--accent);
}
</style>
