import { defineStore } from "pinia";
import { ref } from "vue";
import {
  listSessions,
  getMessages,
  deleteSession as apiDeleteSession,
  streamChat as apiStreamChat,
  type SessionInfo,
  type HistoryMessage,
  type SessionListResponse,
} from "../api";

export const useChatStore = defineStore("chat", () => {
  const currentSessionId = ref<string | null>(null);
  const sessions = ref<SessionInfo[]>([]);
  const messages = ref<HistoryMessage[]>([]);
  const isStreaming = ref(false);

  async function refreshSessions() {
    try {
      const data: SessionListResponse = await listSessions();
      sessions.value = data.sessions;
    } catch {
      sessions.value = [];
    }
  }

  async function selectSession(id: string) {
    currentSessionId.value = id;
    try {
      const data = await getMessages(id);
      messages.value = data.messages;
    } catch {
      messages.value = [];
    }
  }

  function newSession() {
    currentSessionId.value = null;
    messages.value = [];
  }

  function addMessage(msg: HistoryMessage) {
    messages.value.push(msg);
  }

  function streamChat(message: string, sessionId?: string): EventSource {
    return apiStreamChat(
      message,
      sessionId ?? currentSessionId.value ?? undefined
    );
  }

  async function deleteCurrentSession(id: string) {
    await apiDeleteSession(id);
    if (currentSessionId.value === id) {
      currentSessionId.value = null;
      messages.value = [];
    }
    await refreshSessions();
  }

  return {
    currentSessionId,
    sessions,
    messages,
    isStreaming,
    refreshSessions,
    selectSession,
    newSession,
    addMessage,
    streamChat,
    deleteCurrentSession,
  };
});
