<template>
  <view class="page">
    <!-- 顶部标题栏 -->
    <view class="header">
      <text class="title">🎯 工作台</text>
      <text class="subtitle">选择智能体，开始对话</text>
    </view>

    <!-- 智能体选择区 -->
    <view class="card agents-section">
      <view class="section-title">📦 智能体列表</view>
      <view class="agents-grid" v-if="agents.length">
        <view
          v-for="agent in agents"
          :key="agent.id"
          class="agent-item"
          :class="{ active: selectedAgent && selectedAgent.id === agent.id }"
          @click="selectAgent(agent)"
        >
          <text class="agent-icon">{{ agent.icon || '🤖' }}</text>
          <text class="agent-name">{{ agent.name }}</text>
          <text class="agent-desc">{{ agent.description }}</text>
        </view>
      </view>
      <view v-else class="loading">加载中...</view>
    </view>

    <!-- 对话区域 -->
    <view class="card chat-section">
      <view class="section-title">💬 对话</view>

      <!-- 已选智能体信息 -->
      <view v-if="selectedAgent" class="selected-agent">
        <text class="agent-badge">{{ selectedAgent.icon }} {{ selectedAgent.name }}</text>
      </view>

      <!-- 消息列表 -->
      <view class="messages" id="messages">
        <view v-if="!messages.length" class="empty-chat">
          <text>👋 发送消息开始对话</text>
        </view>
        <view
          v-for="(msg, idx) in messages"
          :key="idx"
          class="message-item"
          :class="msg.role === 'user' ? 'user-msg' : 'agent-msg'"
        >
          <view class="msg-bubble">
            <text>{{ msg.content }}</text>
          </view>
        </view>
        <!-- 加载指示 -->
        <view v-if="loading" class="message-item agent-msg">
          <view class="msg-bubble loading">
            <text>思考中...</text>
          </view>
        </view>
      </view>

      <!-- 输入区域 -->
      <view class="input-area">
        <input
          v-model="inputText"
          class="input-box"
          placeholder="输入消息..."
          :disabled="!selectedAgent"
          confirm-type="send"
          @confirm="sendMessage"
        />
        <button class="send-btn" @click="sendMessage" :disabled="!inputText.trim() || loading">
          {{ loading ? '⏳' : '➤' }}
        </button>
      </view>
    </view>
  </view>
</template>

<script>
const API_BASE = 'http://127.0.0.1:5188';

export default {
  data() {
    return {
      agents: [],
      selectedAgent: null,
      messages: [],
      inputText: '',
      loading: false
    };
  },
  onLoad() {
    this.loadAgents();
    this.loadHistory();
  },
  methods: {
    async loadAgents() {
      try {
        const res = await uni.request({
          url: `${API_BASE}/api/v1/agents`,
          method: 'GET'
        });
        if (res.statusCode === 200 && res.data) {
          this.agents = res.data.agents || res.data || [];
        }
      } catch (e) {
        console.error('加载智能体失败', e);
        uni.showToast({ title: '加载智能体失败', icon: 'none' });
      }
    },
    async loadHistory() {
      try {
        const token = uni.getStorageSync('token');
        if (!token) return;
        const res = await uni.request({
          url: `${API_BASE}/api/v1/conversations`,
          method: 'GET',
          header: { Authorization: `Bearer ${token}` }
        });
        if (res.statusCode === 200 && res.data && res.data.length) {
          // 取最近一条会话
          const latest = res.data[0];
          if (latest.messages) {
            this.messages = latest.messages.slice(-10);
          }
        }
      } catch (e) {}
    },
    selectAgent(agent) {
      this.selectedAgent = agent;
      uni.showToast({ title: `已选择: ${agent.name}`, icon: 'none' });
    },
    async sendMessage() {
      const text = this.inputText.trim();
      if (!text || !this.selectedAgent || this.loading) return;

      // 添加用户消息
      this.messages.push({ role: 'user', content: text });
      this.inputText = '';
      this.loading = true;

      try {
        const token = uni.getStorageSync('token');
        const res = await uni.request({
          url: `${API_BASE}/api/v1/main/chat`,
          method: 'POST',
          header: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {})
          },
          data: {
            message: text,
            agent_id: this.selectedAgent.id
          }
        });

        if (res.statusCode === 200 && res.data && res.data.reply) {
          this.messages.push({ role: 'agent', content: res.data.reply });
        } else {
          this.messages.push({ role: 'agent', content: '抱歉，服务暂时不可用。' });
        }
      } catch (e) {
        this.messages.push({ role: 'agent', content: '网络错误，请检查连接。' });
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 20px;
}

.header {
  background: linear-gradient(135deg, #1890ff, #40a9ff);
  color: white;
  padding: 20px 16px 16px;
}

.title {
  font-size: 22px;
  font-weight: bold;
  display: block;
}

.subtitle {
  font-size: 13px;
  opacity: 0.85;
  display: block;
  margin-top: 4px;
}

.card {
  background: #ffffff;
  margin: 12px 16px;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
}

/* 智能体网格 */
.agents-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.agent-item {
  width: calc(50% - 5px);
  background: #f8f8f8;
  border-radius: 10px;
  padding: 14px 12px;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.agent-item.active {
  border-color: #1890ff;
  background: #e6f7ff;
}

.agent-icon {
  font-size: 24px;
  display: block;
  margin-bottom: 6px;
}

.agent-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  display: block;
}

.agent-desc {
  font-size: 12px;
  color: #999;
  display: block;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 已选智能体 */
.selected-agent {
  margin-bottom: 10px;
}

.agent-badge {
  display: inline-block;
  background: #1890ff;
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 13px;
}

/* 消息列表 */
.messages {
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: 12px;
}

.empty-chat {
  text-align: center;
  color: #bbb;
  padding: 30px;
  font-size: 14px;
}

.message-item {
  display: flex;
  margin-bottom: 12px;
}

.user-msg {
  justify-content: flex-end;
}

.agent-msg {
  justify-content: flex-start;
}

.msg-bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-all;
}

.user-msg .msg-bubble {
  background: #1890ff;
  color: white;
  border-bottom-right-radius: 4px;
}

.agent-msg .msg-bubble {
  background: #f0f0f0;
  color: #333;
  border-bottom-left-radius: 4px;
}

.msg-bubble.loading {
  color: #999;
  font-style: italic;
}

/* 输入区 */
.input-area {
  display: flex;
  gap: 10px;
  align-items: center;
}

.input-box {
  flex: 1;
  background: #f5f5f5;
  border-radius: 24px;
  padding: 10px 16px;
  font-size: 14px;
  border: 1px solid #e8e8e8;
}

.send-btn {
  width: 44px;
  height: 44px;
  background: #1890ff;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  border: none;
  padding: 0;
}

.send-btn[disabled] {
  background: #ccc;
}

.loading {
  text-align: center;
  color: #999;
  padding: 20px;
}
</style>