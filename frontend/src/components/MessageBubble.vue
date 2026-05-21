<script setup lang="ts">
defineProps<{
  role: string
  content: string
  timestamp: string
  isStreaming?: boolean
}>()
</script>

<template>
  <div :class="['bubble', role]">
    <div class="bubble-header">
      <span class="role-label">{{ role === 'user' ? 'You' : 'Assistant' }}</span>
      <span class="time">{{ timestamp.slice(11, 16) }}</span>
    </div>
    <div class="bubble-content">
      {{ content }}
      <span v-if="isStreaming" class="streaming-cursor">|</span>
    </div>
  </div>
</template>

<style scoped>
.bubble {
  max-width: 75%;
  margin-bottom: 16px;
}
.bubble.user {
  align-self: flex-end;
}
.bubble.assistant {
  align-self: flex-start;
}
.bubble-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 4px;
  font-size: 12px;
}
.role-label {
  font-weight: 600;
  color: var(--text-secondary);
}
.time {
  color: var(--text-muted);
}
.bubble-content {
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 14px;
  white-space: pre-wrap;
}
.user .bubble-content {
  background: var(--bubble-user);
}
.assistant .bubble-content {
  background: var(--bubble-assistant);
}
.streaming-cursor {
  animation: blink 0.8s infinite;
  color: var(--accent);
  font-weight: 700;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
