// 全局配置 - 修改此文件即可切换 API 环境
const config = {
  // API 基地址 (不含末尾斜杠)
  apiBase: getApp().globalData?.apiBase || 'http://127.0.0.1:5188',
};

export default config;
