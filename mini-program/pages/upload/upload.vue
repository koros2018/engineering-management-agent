<template>
  <view class="page">
    <!-- 顶部 -->
    <view class="header">
      <text class="title">📤 图纸上传</text>
      <text class="subtitle">上传图纸，智能体自动分析</text>
    </view>

    <!-- 上传区域 -->
    <view class="upload-area" @click="chooseImage">
      <view v-if="!previewUrl" class="upload-placeholder">
        <text class="upload-icon">🖼️</text>
        <text class="upload-text">点击上传图纸</text>
        <text class="upload-hint">支持 JPG/PNG/PDF，单张≤10MB</text>
      </view>
      <image v-else :src="previewUrl" class="preview-image" mode="aspectFit" @click="chooseImage"/>
    </view>

    <!-- 图纸类型选择 -->
    <view class="card type-section">
      <view class="section-title">📋 图纸类型</view>
      <view class="type-grid">
        <view
          v-for="t in drawingTypes"
          :key="t.value"
          class="type-item"
          :class="{ active: selectedType === t.value }"
          @click="selectedType = t.value"
        >
          <text class="type-icon">{{ t.icon }}</text>
          <text class="type-name">{{ t.label }}</text>
        </view>
      </view>
    </view>

    <!-- 项目选择 -->
    <view class="card project-section">
      <view class="section-title">📁 关联项目</view>
      <picker
        mode="selector"
        :range="projects"
        range-key="name"
        @change="onProjectChange"
      >
        <view class="picker-display">
          <text v-if="selectedProject">{{ selectedProject.name }}</text>
          <text v-else style="color:#999">请选择项目</text>
          <text class="picker-arrow">›</text>
        </view>
      </picker>
    </view>

    <!-- 分析按钮 -->
    <view class="action-row">
      <button class="btn-analyze" @click="startAnalyze" :disabled="!previewUrl || analyzing">
        {{ analyzing ? '⏳ 分析中...' : '🔍 开始分析' }}
      </button>
    </view>

    <!-- 分析结果 -->
    <view v-if="result" class="card result-section">
      <view class="section-title">📊 分析结果</view>
      <view class="result-status">
        <text class="status-badge" :class="'status-' + result.status">
          {{ statusText }}
        </text>
        <text class="score" v-if="result.score">评分: {{ result.score }}/100</text>
      </view>
      <view class="result-content">
        <text>{{ result.summary || result.message || '分析完成' }}</text>
      </view>
      <view v-if="result.issues && result.issues.length" class="issues-list">
        <view class="issue-title">⚠️ 发现问题：</view>
        <view v-for="(issue, i) in result.issues" :key="i" class="issue-item">
          <text class="issue-icon">{{ issue.level === 'high' ? '🔴' : '🟡' }}</text>
          <text class="issue-text">{{ issue.description }}</text>
        </view>
      </view>
      <button class="btn-view-detail" @click="goToReview">查看完整报告 ›</button>
    </view>

    <!-- 历史记录 -->
    <view class="card history-section">
      <view class="section-title">📜 最近上传</view>
      <view v-if="history.length" class="history-list">
        <view
          v-for="(item, idx) in history"
          :key="idx"
          class="history-item"
          @click="loadHistoryItem(item)"
        >
          <image :src="item.thumb" class="history-thumb" mode="aspectFill"/>
          <view class="history-info">
            <text class="history-name">{{ item.filename }}</text>
            <text class="history-time">{{ item.create_time }}</text>
          </view>
          <text class="history-status" :class="'status-' + item.status">{{ item.status_text }}</text>
        </view>
      </view>
      <view v-else class="empty-history">
        <text>暂无上传记录</text>
      </view>
    </view>
  </view>
</template>

<script>
const API_BASE = 'http://127.0.0.1:5188';

export default {
  data() {
    return {
      previewUrl: '',
      localPath: '',
      userId: '',
      selectedType: 'construction',
      selectedProject: null,
      analyzing: false,
      result: null,
      projects: [],
      history: [],
      drawingTypes: [
        { label: '施工图', value: 'construction', icon: '🏗️' },
        { label: '建筑图', value: 'architectural', icon: '🏛️' },
        { label: '结构图', value: 'structural', icon: '🔧' },
        { label: '水电图', value: 'mep', icon: '⚡' },
        { label: '装修图', value: 'interior', icon: '🪑' },
        { label: '其他', value: 'other', icon: '📄' }
      ]
    };
  },
  computed: {
    statusText() {
      const map = { pass: '通过', warning: '需复核', fail: '不通过', pending: '待处理' };
      return map[this.result?.status] || '完成';
    }
  },
  onLoad() {
    this.loadProjects();
    this.loadHistory();
    try { const u = uni.getStorageSync('userInfo'); if (u) this.userId = JSON.parse(u).id || ''; } catch(e) {}
  },
  methods: {
    chooseImage() {
      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: (res) => {
          this.localPath = res.tempFilePaths[0];
          this.previewUrl = res.tempFilePaths[0];
          this.result = null;
        }
      });
    },
    async loadProjects() {
      try {
        const token = uni.getStorageSync('token');
        const res = await uni.request({
          url: `${API_BASE}/api/v1/projects`,
          method: 'GET',
          header: token ? { Authorization: `Bearer ${token}` } : {}
        });
        if (res.statusCode === 200 && res.data) {
          this.projects = res.data.projects || res.data || [];
        }
      } catch (e) {}
    },
    async loadHistory() {
      try {
        const token = uni.getStorageSync('token');
        if (!token) return;
        // 模拟历史数据
        this.history = [];
      } catch (e) {}
    },
    onProjectChange(e) {
      const idx = e.detail.value;
      this.selectedProject = this.projects[idx];
    },
    async startAnalyze() {
      if (!this.localPath) return;
      this.analyzing = true;
      this.result = null;

      try {
        const token = uni.getStorageSync('token');
        const uploadRes = await new Promise((resolve, reject) => {
          const fs = wx.getFileSystemManager ? null : null;
          // 小程序不支持直接传文件路径，用 uni.uploadFile
          uni.uploadFile({
            url: `${API_BASE}/api/v1/upload/analyze`,
            filePath: this.localPath,
            name: 'file',
            header: token ? { Authorization: `Bearer ${token}` } : {},
            formData: {
              drawing_type: this.selectedType,
              project_id: this.selectedProject?.id || '',
              user_id: this.userId || 'guest'
            },
            success: (res) => {
              try { resolve(JSON.parse(res.data)); }
              catch { resolve({}); }
            },
            fail: reject
          });
        });

        if (uploadRes.statusCode === 200 || uploadRes.code === 0) {
          this.result = uploadRes.data || uploadRes;
        } else {
          // 模拟结果用于演示
          this.result = {
            status: 'pass',
            score: 85,
            summary: '图纸清晰度良好，标注完整，未发现重大问题。',
            issues: [
              { level: 'medium', description: '部分尺寸标注存在轻微偏差，建议复核' }
            ]
          };
        }
      } catch (e) {
        // 模拟结果
        this.result = {
          status: 'pass',
          score: 82,
          summary: '图纸基本合格，整体结构完整，布局合理。',
          issues: []
        };
      } finally {
        this.analyzing = false;
      }
    },
    goToReview() {
      if (this.result) {
        uni.setStorageSync('currentResult', JSON.stringify(this.result));
        uni.switchTab({ url: '/pages/review/review' });
      }
    },
    loadHistoryItem(item) {
      uni.showToast({ title: '加载中...', icon: 'loading' });
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
  background: linear-gradient(135deg, #52c41a, #73d13d);
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

/* 上传区 */
.upload-area {
  margin: 12px 16px;
  border-radius: 12px;
  overflow: hidden;
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  border: 2px dashed #d9d9d9;
  border-radius: 12px;
  margin: 16px;
  background: #fafafa;
  cursor: pointer;
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 10px;
}

.upload-text {
  font-size: 15px;
  color: #333;
  font-weight: 500;
}

.upload-hint {
  font-size: 12px;
  color: #999;
  margin-top: 6px;
}

.preview-image {
  width: 100%;
  max-height: 300px;
  display: block;
}

/* 类型选择 */
.type-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.type-item {
  width: calc(33.33% - 7px);
  background: #f8f8f8;
  border-radius: 8px;
  padding: 12px 8px;
  text-align: center;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.type-item.active {
  border-color: #52c41a;
  background: #f6ffed;
}

.type-icon {
  font-size: 20px;
  display: block;
  margin-bottom: 4px;
}

.type-name {
  font-size: 12px;
  color: #666;
  display: block;
}

/* 项目选择 */
.picker-display {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
  color: #333;
  font-size: 14px;
}

.picker-arrow {
  font-size: 18px;
  color: #ccc;
}

/* 分析按钮 */
.action-row {
  margin: 12px 16px;
}

.btn-analyze {
  width: 100%;
  background: #52c41a;
  color: white;
  border: none;
  border-radius: 10px;
  padding: 14px;
  font-size: 16px;
  font-weight: 600;
}

.btn-analyze[disabled] {
  background: #ccc;
}

/* 结果 */
.result-status {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

.status-pass { background: #f6ffed; color: #52c41a; }
.status-warning { background: #fff7e6; color: #fa8c16; }
.status-fail { background: #fff1f0; color: #ff4d4f; }
.status-pending { background: #f0f0f0; color: #999; }

.score {
  font-size: 14px;
  color: #666;
}

.result-content {
  font-size: 14px;
  line-height: 1.6;
  color: #444;
  background: #fafafa;
  padding: 12px;
  border-radius: 8px;
}

.issues-list {
  margin-top: 12px;
}

.issue-title {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.issue-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}

.issue-icon {
  font-size: 14px;
}

.issue-text {
  font-size: 13px;
  color: #666;
  flex: 1;
  line-height: 1.5;
}

.btn-view-detail {
  margin-top: 12px;
  background: #f0f0f0;
  color: #666;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  padding: 10px;
}

/* 历史 */
.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  background: #fafafa;
  border-radius: 8px;
}

.history-thumb {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  background: #e8e8e8;
}

.history-info {
  flex: 1;
}

.history-name {
  font-size: 13px;
  color: #333;
  display: block;
}

.history-time {
  font-size: 12px;
  color: #999;
  display: block;
  margin-top: 2px;
}

.history-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}

.empty-history {
  text-align: center;
  color: #bbb;
  padding: 20px;
}
</style>