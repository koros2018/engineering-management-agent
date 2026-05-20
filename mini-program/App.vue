<script>
export default {
  onLaunch() {
    console.log('App Launch');
    // 检查登录态
    const token = uni.getStorageSync('token');
    if (token) {
      this.checkToken(token);
    }
  },
  onShow() {
    console.log('App Show');
  },
  onHide() {
    console.log('App Hide');
  },
  methods: {
    async checkToken(token) {
      try {
        const res = await uni.request({
          url: 'http://127.0.0.1:5188/api/v1/auth/me',
          method: 'GET',
          header: { Authorization: `Bearer ${token}` }
        });
        if (res.statusCode === 200) {
          getApp().globalData.userInfo = res.data;
        } else {
          uni.removeStorageSync('token');
        }
      } catch (e) {
        // 忽略网络错误
      }
    }
  }
};
</script>

<style>
/* 全局样式 */
page {
  background-color: #f5f5f5;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 14px;
  color: #333333;
}

.container {
  padding: 16px;
}

.card {
  background-color: #ffffff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.btn-primary {
  background-color: #1890ff;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  padding: 12px 24px;
  font-size: 15px;
}

.btn-default {
  background-color: #f0f0f0;
  color: #666666;
  border: none;
  border-radius: 8px;
  padding: 12px 24px;
  font-size: 15px;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.tag-blue { background: #e6f7ff; color: #1890ff; }
.tag-green { background: #f6ffed; color: #52c41a; }
.tag-orange { background: #fff7e6; color: #fa8c16; }
.tag-red { background: #fff1f0; color: #ff4d4f; }

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}
.status-dot.online { background: #52c41a; }
.status-dot.offline { background: #d9d9d9; }
.status-dot.busy { background: #fa8c16; }

.divider {
  height: 1px;
  background: #f0f0f0;
  margin: 12px 0;
}
</style>