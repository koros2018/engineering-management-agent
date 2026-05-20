<template>
  <view class="page">
    <!-- 顶部 -->
    <view class="header">
      <text class="title">📋 审图结果</text>
      <text class="subtitle">查看图纸分析报告详情</text>
    </view>

    <!-- 筛选栏 -->
    <view class="filter-bar">
      <view
        v-for="f in filters"
        :key="f.value"
        class="filter-item"
        :class="{ active: activeFilter === f.value }"
        @click="activeFilter = f.value"
      >
        <text>{{ f.label }}</text>
      </view>
    </view>

    <!-- 当前报告 -->
    <view v-if="currentReport" class="card report-card">
      <view class="report-header">
        <image :src="currentReport.thumb || 'data:image/png;base64,iVBORw0KGgo=='" class="report-thumb"/>
        <view class="report-meta">
          <text class="report-name">{{ currentReport.filename || '图纸报告' }}</text>
          <text class="report-time">{{ currentReport.create_time || '' }}</text>
          <text class="status-badge" :class="'status-' + currentReport.status">
            {{ statusText }}
          </text>
        </view>
      </view>

      <view class="divider"/>

      <!-- 评分 -->
      <view class="score-section" v-if="currentReport.score">
        <text class="score-label">综合评分</text>
        <view class="score-circle">
          <text class="score-num">{{ currentReport.score }}</text>
          <text class="score-unit">/100</text>
        </view>
        <view class="score-bar-wrap">
          <view class="score-bar">
            <view class="score-fill" :style="{ width: currentReport.score + '%' }"></view>
          </view>
        </view>
      </view>

      <view class="divider"/>

      <!-- 摘要 -->
      <view class="summary-section">
        <view class="summary-title">📝 摘要</view>
        <text class="summary-text">{{ currentReport.summary || '无' }}</text>
      </view>

      <view class="divider"/>

      <!-- 问题列表 -->
      <view v-if="currentReport.issues && currentReport.issues.length" class="issues-section">
        <view class="issues-title">⚠️ 发现问题 ({{ currentReport.issues.length }})</view>
        <view
          v-for="(issue, idx) in currentReport.issues"
          :key="idx"
          class="issue-card"
          :class="'issue-' + (issue.level || 'medium')"
        >
          <view class="issue-header">
            <text class="issue-level-icon">{{ getIssueIcon(issue.level) }}</text>
            <text class="issue-level-label">{{ getLevelText(issue.level) }}</text>
          </view>
          <text class="issue-desc">{{ issue.description }}</text>
          <text v-if="issue.location" class="issue-location">📍 {{ issue.location }}</text>
          <text v-if="issue.suggestion" class="issue-suggestion">💡 建议: {{ issue.suggestion }}</text>
        </view>
      </view>

      <!-- 无问题提示 -->
      <view v-else class="no-issue">
        <text>✅ 未发现问题，图纸合格</text>
      </view>

      <view class="divider"/>

      <!-- 操作按钮 -->
      <view class="action-btns">
        <button class="btn-action" @click="downloadReport">📥 导出报告</button>
        <button class="btn-action btn-share" @click="shareReport">🔗 分享</button>
      </view>
    </view>

    <!-- 历史报告列表 -->
    <view class="card history-card">
      <view class="history-title">📋 历史报告</view>
      <view v-if="reports.length" class="reports-list">
        <view
          v-for="(r, idx) in reports"
          :key="idx"
          class="report-item"
          @click="selectReport(r)"
        >
          <view class="report-item-left">
            <text class="report-item-name">{{ r.filename }}</text>
            <text class="report-item-time">{{ r.create_time }}</text>
          </view>
          <view class="report-item-right">
            <text class="report-item-score" :class="{ 'score-pass': r.score >= 60 }">{{ r.score || '--' }}</text>
            <text class="report-item-arrow">›</text>
          </view>
        </view>
      </view>
      <view v-else class="empty-reports">
        <text>暂无历史报告</text>
      </view>
    </view>
  </view>
</template>

<script>
const API_BASE = 'http://127.0.0.1:5188';

export default {
  data() {
    return {
      activeFilter: 'all',
      currentReport: null,
      reports: [],
      filters: [
        { label: '全部', value: 'all' },
        { label: '通过', value: 'pass' },
        { label: '警告', value: 'warning' },
        { label: '不通过', value: 'fail' }
      ]
    };
  },
  onLoad() {
    this.loadFromCache();
    this.loadReports();
  },
  computed: {
    statusText() {
      const map = { pass: '通过', warning: '需复核', fail: '不通过', pending: '待处理' };
      return map[this.currentReport?.status] || '完成';
    }
  },
  methods: {
    loadFromCache() {
      try {
        const cached = uni.getStorageSync('currentResult');
        if (cached) {
          this.currentReport = JSON.parse(cached);
        }
      } catch (e) {}
      if (!this.currentReport) {
        // 默认示例报告
        this.currentReport = {
          filename: 'A栋施工图-v2.pdf',
          create_time: '2026-05-20 09:15',
          status: 'pass',
          score: 85,
          summary: '图纸整体质量良好，结构完整，标注清晰，满足施工要求。层高、轴线、尺寸标注均符合规范。发现2处轻微问题，建议复核后使用。',
          issues: [
            {
              level: 'medium',
              description: '卫生间隔墙厚度标注不明确，可能导致施工偏差',
              location: 'A-01平面图 / B区',
              suggestion: '建议补充墙厚标注或引用标准图集'
            },
            {
              level: 'low',
              description: '楼梯平台标高与楼梯踏步高不一致',
              location: '楼梯剖面图 / 2层',
              suggestion: '复核楼梯各层标高数据'
            }
          ]
        };
      }
    },
    async loadReports() {
      try {
        const token = uni.getStorageSync('token');
        // 模拟数据，实际从API获取
        this.reports = [];
      } catch (e) {}
    },
    selectReport(r) {
      this.currentReport = r;
      uni.showToast({ title: '加载报告', icon: 'none' });
    },
    getIssueIcon(level) {
      const map = { high: '🔴', medium: '🟡', low: '🟢' };
      return map[level] || '🟡';
    },
    getLevelText(level) {
      const map = { high: '严重', medium: '中等', low: '轻微' };
      return map[level] || '中等';
    },
    downloadReport() {
      uni.showToast({ title: '报告导出中...', icon: 'loading' });
      setTimeout(() => {
        uni.showToast({ title: '导出功能开发中', icon: 'none' });
      }, 1000);
    },
    shareReport() {
      uni.showToast({ title: '分享功能开发中', icon: 'none' });
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
  background: linear-gradient(135deg, #fa8c16, #ffa940);
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

.filter-bar {
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  background: white;
  overflow-x: auto;
}

.filter-item {
  padding: 6px 16px;
  border-radius: 20px;
  background: #f0f0f0;
  color: #666;
  font-size: 13px;
  white-space: nowrap;
}

.filter-item.active {
  background: #fa8c16;
  color: white;
  font-weight: 500;
}

.card {
  background: #ffffff;
  margin: 12px 16px;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.report-header {
  display: flex;
  gap: 14px;
  margin-bottom: 12px;
}

.report-thumb {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  background: #e8e8e8;
}

.report-meta {
  flex: 1;
}

.report-name {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  display: block;
}

.report-time {
  font-size: 12px;
  color: #999;
  display: block;
  margin-top: 2px;
}

.status-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  margin-top: 4px;
}

.status-pass { background: #f6ffed; color: #52c41a; }
.status-warning { background: #fff7e6; color: #fa8c16; }
.status-fail { background: #fff1f0; color: #ff4d4f; }

.divider {
  height: 1px;
  background: #f0f0f0;
  margin: 12px 0;
}

/* 评分 */
.score-section {
  display: flex;
  align-items: center;
  gap: 14px;
}

.score-label {
  font-size: 13px;
  color: #999;
}

.score-circle {
  display: flex;
  align-items: baseline;
}

.score-num {
  font-size: 28px;
  font-weight: bold;
  color: #fa8c16;
}

.score-unit {
  font-size: 13px;
  color: #ccc;
}

.score-bar-wrap {
  flex: 1;
}

.score-bar {
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  background: linear-gradient(90deg, #fa8c16, #ff7a45);
  border-radius: 3px;
}

/* 摘要 */
.summary-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.summary-text {
  font-size: 13px;
  line-height: 1.7;
  color: #555;
}

/* 问题 */
.issues-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
}

.issue-card {
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
}

.issue-high { background: #fff1f0; border-left: 3px solid #ff4d4f; }
.issue-medium { background: #fff7e6; border-left: 3px solid #fa8c16; }
.issue-low { background: #f6ffed; border-left: 3px solid #52c41a; }

.issue-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.issue-level-icon {
  font-size: 14px;
}

.issue-level-label {
  font-size: 12px;
  font-weight: 500;
}

.issue-high .issue-level-label { color: #ff4d4f; }
.issue-medium .issue-level-label { color: #fa8c16; }
.issue-low .issue-level-label { color: #52c41a; }

.issue-desc {
  font-size: 13px;
  color: #333;
  line-height: 1.5;
  display: block;
}

.issue-location, .issue-suggestion {
  font-size: 12px;
  color: #888;
  display: block;
  margin-top: 4px;
}

.no-issue {
  text-align: center;
  color: #52c41a;
  padding: 20px;
  font-size: 14px;
}

/* 操作按钮 */
.action-btns {
  display: flex;
  gap: 10px;
}

.btn-action {
  flex: 1;
  background: #f0f0f0;
  color: #666;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  padding: 10px;
}

.btn-share {
  background: #e6f7ff;
  color: #1890ff;
}

/* 历史 */
.history-title {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
}

.reports-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.report-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 8px;
}

.report-item-left {
  flex: 1;
}

.report-item-name {
  font-size: 13px;
  color: #333;
  display: block;
}

.report-item-time {
  font-size: 12px;
  color: #999;
  display: block;
  margin-top: 2px;
}

.report-item-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.report-item-score {
  font-size: 18px;
  font-weight: bold;
  color: #ccc;
}

.report-item-score.score-pass {
  color: #52c41a;
}

.report-item-arrow {
  font-size: 18px;
  color: #ccc;
}

.empty-reports {
  text-align: center;
  color: #bbb;
  padding: 20px;
}
</style>