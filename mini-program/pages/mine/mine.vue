<template>
  <view class="page">
    <!-- 用户信息 -->
    <view class="profile-section">
      <view v-if="userInfo" class="profile-card">
        <view class="avatar-wrap">
          <image v-if="userInfo.avatar" :src="userInfo.avatar" class="avatar"/>
          <text v-else class="avatar-placeholder">{{ userInfo.nickname ? userInfo.nickname[0] : '👤' }}</text>
        </view>
        <view class="profile-info">
          <text class="nickname">{{ userInfo.nickname || '未登录用户' }}</text>
          <text class="user-id">ID: {{ userInfo.id || '--' }}</text>
        </view>
        <button class="btn-edit" @click="editProfile">✏️</button>
      </view>
      <view v-else class="login-prompt" @click="doLogin">
        <text class="login-icon">👤</text>
        <text class="login-text">点击登录</text>
        <text class="login-hint">登录后享受完整服务</text>
      </view>
    </view>

    <!-- 套餐信息 -->
    <view class="card package-section">
      <view class="section-title">📦 我的套餐</view>
      <view v-if="subscription" class="package-info">
        <view class="package-header">
          <text class="package-name">{{ subscription.plan_name || '免费版' }}</text>
          <text class="package-status" :class="'status-' + subscription.status">
            {{ statusText }}
          </text>
        </view>
        <view class="package-detail">
          <view class="package-item">
            <text class="p-label">额度剩余</text>
            <text class="p-value">{{ subscription.quota_remain || 0 }} 次</text>
          </view>
          <view class="package-item">
            <text class="p-label">到期时间</text>
            <text class="p-value">{{ subscription.expire_time || '无限' }}</text>
          </view>
        </view>
        <view v-if="subscription.plan_name" class="upgrade-hint">
          <text>🔥 升级到专业版，解锁无限额度</text>
        </view>
      </view>
      <view v-else class="package-empty">
        <text>暂无套餐信息</text>
        <button class="btn-upgrade" @click="goToSubscribe">立即订阅</button>
      </view>
    </view>

    <!-- 订阅计划 -->
    <view class="card plans-section">
      <view class="section-title">💎 订阅方案</view>
      <view class="plans-list">
        <view
          v-for="plan in plans"
          :key="plan.id"
          class="plan-item"
          :class="{ recommended: plan.recommended }"
        >
          <view v-if="plan.recommended" class="plan-badge">推荐</view>
          <text class="plan-name">{{ plan.name }}</text>
          <view class="plan-price">
            <text class="price-num">¥{{ plan.price }}</text>
            <text class="price-period">/{{ plan.period }}</text>
          </view>
          <view class="plan-features">
            <text v-for="(f, i) in plan.features" :key="i" class="feature-item">✓ {{ f }}</text>
          </view>
          <button class="btn-subscribe" @click="subscribePlan(plan)">
            {{ plan.name.includes('免费') ? '当前方案' : '立即订阅' }}
          </button>
        </view>
      </view>
    </view>

    <!-- 功能菜单 -->
    <view class="card menu-section">
      <view
        v-for="(item, idx) in menuItems"
        :key="idx"
        class="menu-item"
        @click="onMenuClick(item)"
      >
        <text class="menu-icon">{{ item.icon }}</text>
        <text class="menu-label">{{ item.label }}</text>
        <text class="menu-arrow">›</text>
      </view>
    </view>

    <!-- 微信登录面板 -->
    <view v-if="showLoginPanel" class="login-panel-overlay" @click="showLoginPanel = false">
      <view class="login-panel" @click.stop>
        <text class="panel-title">微信一键登录</text>
        <text class="panel-desc">授权获取您的微信信息完成登录</text>
        <button class="btn-wechat-login" open-type="getPhoneNumber" @getphonenumber="onGetPhoneNumber">
          🔵 微信授权登录
        </button>
        <button class="btn-cancel" @click="showLoginPanel = false">取消</button>
      </view>
    </view>
  </view>
</template>

<script>
import config from '@/common/config.js';
const API_BASE = config.apiBase;

export default {
  data() {
    return {
      userInfo: null,
      subscription: null,
      plans: [],
      showLoginPanel: false,
      menuItems: [
        { icon: '📊', label: '使用记录', action: 'history' },
        { icon: '💳', label: '我的订单', action: 'orders' },
        { icon: '🧾', label: '发票申请', action: 'invoice' },
        { icon: '🔔', label: '消息通知', action: 'notifications' },
        { icon: '⚙️', label: '设置', action: 'settings' },
        { icon: '❓', label: '帮助与反馈', action: 'help' },
        { icon: 'ℹ️', label: '关于', action: 'about' },
        { icon: '🚪', label: '退出登录', action: 'logout' }
      ]
    };
  },
  onLoad() {
    this.checkLogin();
    this.loadSubscription();
    this.loadPlans();
  },
  computed: {
    statusText() {
      const map = { active: '有效', expired: '已过期', trial: '试用中' };
      return map[this.subscription?.status] || '未知';
    }
  },
  methods: {
    checkLogin() {
      try {
        const token = uni.getStorageSync('token');
        const userStr = uni.getStorageSync('userInfo');
        if (token && userStr) {
          this.userInfo = JSON.parse(userStr);
        } else {
          this.userInfo = null;
        }
      } catch (e) {
        this.userInfo = null;
      }
    },
    async loadSubscription() {
      try {
        const token = uni.getStorageSync('token');
        if (!token) return;
        const res = await uni.request({
          url: `${API_BASE}/api/v1/subscription/status`,
          method: 'GET',
          header: { Authorization: `Bearer ${token}` }
        });
        if (res.statusCode === 200 && res.data) {
          this.subscription = res.data;
        }
      } catch (e) {}
      // 默认显示
      if (!this.subscription) {
        this.subscription = {
          plan_name: '免费版',
          status: 'active',
          quota_remain: 5,
          expire_time: '无限'
        };
      }
    },
    async loadPlans() {
      try {
        const res = await uni.request({
          url: `${API_BASE}/api/v1/subscription/plans`,
          method: 'GET'
        });
        if (res.statusCode === 200 && res.data) {
          this.plans = res.data.plans || res.data || [];
        }
      } catch (e) {}
      if (!this.plans.length) {
        this.plans = [
          {
            id: 1,
            name: '免费版',
            price: 0,
            period: '永久',
            recommended: false,
            features: ['5次分析/日', '基础智能体', '社区支持']
          },
          {
            id: 2,
            name: '专业版',
            price: 99,
            period: '月',
            recommended: true,
            features: ['无限次分析', '全部智能体', '优先响应', '专业支持']
          },
          {
            id: 3,
            name: '企业版',
            price: 299,
            period: '月',
            recommended: false,
            features: ['无限次', '团队协作', 'API调用', '专属客服']
          }
        ];
      }
    },
    doLogin() {
      this.showLoginPanel = true;
    },
    async onGetPhoneNumber(e) {
      if (!e.detail || !e.detail.code) {
        uni.showToast({ title: '请允许授权', icon: 'none' });
        return;
      }
      try {
        const res = await uni.request({
          url: `${API_BASE}/api/v1/auth/wechat-qr`,
          method: 'POST',
          data: { code: e.detail.code }
        });
        if (res.statusCode === 200 && res.data) {
          const { token, user } = res.data;
          uni.setStorageSync('token', token);
          uni.setStorageSync('userInfo', JSON.stringify(user));
          this.userInfo = user;
          this.showLoginPanel = false;
          uni.showToast({ title: '登录成功', icon: 'success' });
        } else {
          // 演示模式：模拟登录成功
          const mockUser = { id: 'demo_' + Date.now(), nickname: '微信用户', avatar: '' };
          uni.setStorageSync('token', 'demo_token_' + Date.now());
          uni.setStorageSync('userInfo', JSON.stringify(mockUser));
          this.userInfo = mockUser;
          this.showLoginPanel = false;
          uni.showToast({ title: '登录成功(演示)', icon: 'success' });
        }
      } catch (e) {
        uni.showToast({ title: '登录失败', icon: 'none' });
      }
    },
    editProfile() {
      uni.showToast({ title: '功能开发中', icon: 'none' });
    },
    goToSubscribe() {
      uni.showToast({ title: '请选择订阅方案', icon: 'none' });
    },
    async subscribePlan(plan) {
      if (plan.price === 0) {
        uni.showToast({ title: '当前免费方案', icon: 'none' });
        return;
      }
      try {
        const token = uni.getStorageSync('token');
        if (!token) {
          this.showLoginPanel = true;
          return;
        }
        const res = await uni.request({
          url: `${API_BASE}/api/v1/subscription/subscribe`,
          method: 'POST',
          header: { Authorization: `Bearer ${token}` },
          data: { plan_id: plan.id }
        });
        if (res.statusCode === 200) {
          uni.showToast({ title: '订阅成功', icon: 'success' });
          this.loadSubscription();
        }
      } catch (e) {
        uni.showToast({ title: '订阅请求失败', icon: 'none' });
      }
    },
    onMenuClick(item) {
      const { action } = item;
      switch (action) {
        case 'logout':
          uni.showModal({
            title: '确认退出',
            content: '确定要退出登录吗？',
            success: (res) => {
              if (res.confirm) {
                uni.removeStorageSync('token');
                uni.removeStorageSync('userInfo');
                this.userInfo = null;
                this.subscription = null;
                uni.showToast({ title: '已退出', icon: 'success' });
              }
            }
          });
          break;
        case 'history':
          uni.showToast({ title: '使用记录开发中', icon: 'none' });
          break;
        case 'orders':
          uni.showToast({ title: '订单功能开发中', icon: 'none' });
          break;
        case 'settings':
          uni.showToast({ title: '设置开发中', icon: 'none' });
          break;
        default:
          uni.showToast({ title: item.label + '开发中', icon: 'none' });
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

/* 用户信息 */
.profile-section {
  background: linear-gradient(135deg, #722ed1, #9254de);
  padding: 20px 16px 16px;
}

.profile-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: rgba(255,255,255,0.15);
  border-radius: 12px;
  padding: 16px;
}

.avatar-wrap {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  overflow: hidden;
  background: rgba(255,255,255,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar {
  width: 100%;
  height: 100%;
}

.avatar-placeholder {
  font-size: 24px;
  color: white;
}

.profile-info {
  flex: 1;
}

.nickname {
  font-size: 18px;
  font-weight: 600;
  color: white;
  display: block;
}

.user-id {
  font-size: 12px;
  color: rgba(255,255,255,0.7);
  display: block;
  margin-top: 2px;
}

.btn-edit {
  background: rgba(255,255,255,0.2);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 16px;
  padding: 8px 12px;
}

/* 未登录 */
.login-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 30px;
  background: rgba(255,255,255,0.15);
  border-radius: 12px;
  cursor: pointer;
}

.login-icon {
  font-size: 40px;
  margin-bottom: 10px;
}

.login-text {
  font-size: 17px;
  color: white;
  font-weight: 600;
}

.login-hint {
  font-size: 13px;
  color: rgba(255,255,255,0.7);
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

/* 套餐 */
.package-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.package-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.package-status {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
}

.status-active { background: #f6ffed; color: #52c41a; }
.status-expired { background: #fff1f0; color: #ff4d4f; }
.status-trial { background: #fff7e6; color: #fa8c16; }

.package-detail {
  display: flex;
  gap: 20px;
}

.package-item {
  display: flex;
  flex-direction: column;
}

.p-label {
  font-size: 12px;
  color: #999;
}

.p-value {
  font-size: 15px;
  font-weight: 500;
  color: #333;
  margin-top: 2px;
}

.upgrade-hint {
  margin-top: 10px;
  font-size: 13px;
  color: #fa8c16;
  text-align: center;
}

.package-empty {
  text-align: center;
  color: #999;
  padding: 20px 0;
}

.btn-upgrade {
  margin-top: 12px;
  background: #722ed1;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 10px 24px;
  font-size: 14px;
}

/* 订阅方案 */
.plans-list {
  display: flex;
  gap: 10px;
}

.plan-item {
  flex: 1;
  background: #fafafa;
  border-radius: 10px;
  padding: 14px 10px;
  text-align: center;
  position: relative;
  border: 2px solid transparent;
}

.plan-item.recommended {
  border-color: #722ed1;
  background: #f9f0ff;
}

.plan-badge {
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%);
  background: #722ed1;
  color: white;
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 10px;
}

.plan-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 8px;
}

.plan-price {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 2px;
  margin-bottom: 10px;
}

.price-num {
  font-size: 22px;
  font-weight: bold;
  color: #722ed1;
}

.price-period {
  font-size: 12px;
  color: #999;
}

.plan-features {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 10px;
}

.feature-item {
  font-size: 11px;
  color: #666;
}

.btn-subscribe {
  background: #722ed1;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  padding: 7px 10px;
}

/* 菜单 */
.menu-item {
  display: flex;
  align-items: center;
  padding: 14px 0;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
}

.menu-item:last-child {
  border-bottom: none;
}

.menu-icon {
  font-size: 18px;
  margin-right: 12px;
}

.menu-label {
  flex: 1;
  font-size: 14px;
  color: #333;
}

.menu-arrow {
  font-size: 18px;
  color: #ccc;
}

/* 登录面板 */
.login-panel-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  z-index: 999;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.login-panel {
  background: white;
  border-radius: 16px 16px 0 0;
  padding: 30px 24px 40px;
  width: 100%;
  text-align: center;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 8px;
}

.panel-desc {
  font-size: 13px;
  color: #999;
  display: block;
  margin-bottom: 24px;
}

.btn-wechat-login {
  background: #07c160;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  padding: 14px;
  width: 100%;
  margin-bottom: 12px;
}

.btn-cancel {
  background: #f0f0f0;
  color: #666;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  padding: 12px;
  width: 100%;
}
</style>