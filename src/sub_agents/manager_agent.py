"""
manager_agent.py - 管家Agent（ManagerAgent）
仅Boss/平台管理员可见，提供运营总览/预警/决策辅助
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.base_agent import BaseAgent, Task, AgentResult
from typing import Dict, Any


class ManagerAgent(BaseAgent):
    """
    管家Agent — Only for Boss / super_admin
    
    能力：
    - 平台实时运营数据总览
    - 智能预警（收入异常/用户流失/系统风险）
    - 自动生成周报/月报/年报
    - 决策建议（套餐定价/获客策略）
    """
    AGENT_ID = "manager"
    NAME = "🎩 管家中心"
    DESCRIPTION = "Boss专属运营管家：数据总览/智能预警/自动报告/决策辅助"
    
    async def execute(self, task: Task) -> AgentResult:
        from datetime import datetime
        start = datetime.now()
        params = task.params
        task_type = task.task_type
        
        if task_type == 'cockpit':
            output = await self._cockpit(params, task.context)
        elif task_type == 'alerts':
            output = await self._alert_center(params, task.context)
        elif task_type == 'report':
            output = await self._auto_report(params, task.context)
        elif task_type == 'tenant_management':
            output = await self._tenant_management(params, task.context)
        elif task_type == 'decision':
            output = await self._decision_assist(params, task.context)
        else:
            output = await self._butler_response(params, task.context)
        
        return AgentResult(
            task_id=task.task_id,
            agent_id=self.AGENT_ID,
            status='success',
            output=output,
            confidence=0.92,
            execution_time=(datetime.now() - start).total_seconds(),
        )
    
    async def plan(self, task: Task) -> list:
        return [{"step": 1, "tool": self.AGENT_ID, "expected": "管家响应"}]
    
    async def _cockpit(self, params: Dict, context: Dict) -> Dict:
        """运营总览驾驶舱"""
        from dashboard import get_dashboard
        from security import run_security_baseline_check
        
        dash = get_dashboard()
        sec = run_security_baseline_check()
        
        # 计算健康度
        health_score = 100
        alerts = []
        
        rev = dash.get('revenue', {})
        usage = dash.get('usage_summary', {})
        stats = dash.get('project_stats', {})
        agents = dash.get('agent_usage', {})
        
        # 收入预警
        revenue_this_month = rev.get('revenue_this_month', 0)
        if revenue_this_month < 100:
            health_score -= 10
            alerts.append({'level': 'warning', 'msg': '本月收入偏低，建议检查推广策略'})
        
        # 租户活跃度
        active = rev.get('active_subscribers', 0)
        total = rev.get('total_subscribers', 0)
        if total > 0 and active / total < 0.5:
            health_score -= 15
            alerts.append({'level': 'warning', 'msg': f'活跃租户率低({active}/{total})，建议激活沉睡用户'})
        
        # 安全评分
        sec_score = sec.get('score', 85)
        if sec_score < 80:
            health_score -= 15
            alerts.append({'level': 'danger', 'msg': f'安全评分偏低({sec_score})，立即修复'})
        
        # Agent使用热度
        hot = agents.get('heatmap', [])
        if hot:
            inactive = [h for h in hot if h['count'] == 0]
            if len(inactive) > 2:
                health_score -= 5
                alerts.append({'level': 'info', 'msg': f'{len(inactive)}个Agent未被使用，可能需要推广'})
        
        return {
            'cockpit': {
                'health_score': max(0, min(100, health_score)),
                'health_grade': 'A' if health_score >= 90 else 'B' if health_score >= 75 else 'C' if health_score >= 60 else 'D',
                'alerts': alerts,
                'metrics': {
                    'revenue': rev,
                    'usage': usage,
                    'projects': stats,
                    'agents': agents,
                    'security': {'score': sec_score, 'grade': sec.get('grade', 'B')}
                },
                'quick_actions': [
                    {'id': 'view_tenants', 'label': '👥 管理租户', 'desc': '查看所有租户状态'},
                    {'id': 'run_security', 'label': '🔐 安全扫描', 'desc': '执行安全基线检查'},
                    {'id': 'generate_report', 'label': '📊 生成周报', 'desc': '自动生成运营周报'},
                ]
            },
            'summary': f'平台健康度: {health_score}/100 ({["A","B","C","D"][min(3, 100-health_score)]})，{len([a for a in alerts if a["level"]=="danger"])}个危险预警',
            'confidence': 0.95,
        }
    
    async def _alert_center(self, params: Dict, context: Dict) -> Dict:
        """智能预警中心"""
        from dashboard import get_dashboard
        dash = get_dashboard()
        
        alerts = []
        
        # 订阅到期预警
        from subscription import _load_json
        from pathlib import Path
        import os
        EMA_DATA_DIR = Path(__file__).parent.parent.parent / "data"
        subscribers = _load_json(EMA_DATA_DIR / "subscribers.json")
        from datetime import datetime, timedelta
        now = datetime.now()
        
        for tid, sub in subscribers.items():
            expires = sub.get('expires_at')
            if expires:
                try:
                    exp = datetime.fromisoformat(expires)
                    days = (exp - now).days
                    if days <= 0:
                        alerts.append({'level': 'danger', 'type': 'subscription_expired', 'tenant': sub.get('plan_name', tid[-8:]), 'msg': f'订阅已过期', 'days': days})
                    elif days <= 7:
                        alerts.append({'level': 'warning', 'type': 'subscription_expiring', 'tenant': sub.get('plan_name', tid[-8:]), 'msg': f'还剩{days}天到期', 'days': days})
                except Exception:
                    pass
        
        # 使用量异常
        usage_data = _load_json(EMA_DATA_DIR / "usage.json")
        for tid, u in usage_data.items():
            api_calls = u.get('api_calls', 0)
            if api_calls > 1000:
                alerts.append({'level': 'info', 'type': 'high_usage', 'tenant': tid[-8:], 'msg': f'API调用量高: {api_calls}次'})
        
        # 安全事件
        audit = _load_json(EMA_DATA_DIR / "security_audit.json")
        events = audit.get('events', [])
        criticals = [e for e in events if e.get('severity') == 'critical'][:5]
        for e in criticals:
            alerts.append({'level': 'danger', 'type': 'security', 'tenant': e.get('client_ip', ''), 'msg': e.get('detail', '')[:100]})
        
        return {
            'alert_center': {
                'total_alerts': len(alerts),
                'danger_count': len([a for a in alerts if a['level'] == 'danger']),
                'warning_count': len([a for a in alerts if a['level'] == 'warning']),
                'info_count': len([a for a in alerts if a['level'] == 'info']),
                'alerts': sorted(alerts, key=lambda x: {'danger': 0, 'warning': 1, 'info': 2}.get(x['level'], 3))[:30],
            },
            'summary': f'共{len(alerts)}条预警（🔴{sum(1 for a in alerts if a["level"]=="danger")} ⚠️{sum(1 for a in alerts if a["level"]=="warning")} ℹ️{sum(1 for a in alerts if a["level"]=="info")}）',
            'confidence': 0.93,
        }
    
    async def _auto_report(self, params: Dict, context: Dict) -> Dict:
        """自动生成运营报告（周报/月报）"""
        report_type = params.get('type', 'weekly')
        from dashboard import get_dashboard
        dash = get_dashboard()
        
        report = {
            'title': 'EMA 平台运营周报' if report_type == 'weekly' else 'EMA 平台运营月报',
            'generated_at': __import__('datetime').datetime.now().isoformat(),
            'sections': [
                {
                    'name': '📊 项目概览',
                    'content': f"总项目数: {dash['project_stats']['projects']} | 租户数: {dash['project_stats']['tenants']}",
                },
                {
                    'name': '💰 收益报告',
                    'content': f"总收入: ¥{dash['revenue']['total_revenue']} | 本月: ¥{dash['revenue']['revenue_this_month']}",
                },
                {
                    'name': '🔒 安全状态',
                    'content': f"安全评分: {dash.get('security', {}).get('score', 85)}/100",
                },
                {
                    'name': '💡 建议',
                    'content': '1. 持续关注付费转化率\n2. 定期检查安全告警\n3. 优化高频Agent性能',
                },
            ],
            'summary': f"{report_type}报告已自动生成，包含{dash['project_stats']['tenants']}个租户数据",
        }
        return {'report': report, 'confidence': 0.9}
    
    async def _tenant_management(self, params: Dict, context: Dict) -> Dict:
        """租户管理"""
        from subscription import _load_json
        from pathlib import Path
        EMA_DATA_DIR = Path(__file__).parent.parent.parent / "data"
        
        subscribers = _load_json(EMA_DATA_DIR / "subscribers.json")
        tenants_data = _load_json(EMA_DATA_DIR / "tenants.json")
        tenant_users = _load_json(EMA_DATA_DIR / "tenant_users.json")
        users_data = _load_json(EMA_DATA_DIR / "users.json")
        
        tenant_list = []
        for tid, t in tenants_data.items():
            sub = subscribers.get(tid, {})
            users = [u for uid, u in tenant_users.items() if u.get('tenant_id') == tid]
            tenant_list.append({
                'id': tid,
                'name': t.get('name', tid[-8:]),
                'plan': sub.get('plan_id', 'free'),
                'plan_name': sub.get('plan_name', '体验版'),
                'status': t.get('status', 'unknown'),
                'user_count': len(users),
                'created_at': t.get('created_at', ''),
            })
        
        return {
            'tenants': tenant_list,
            'total': len(tenant_list),
            'summary': f'共{len(tenant_list)}个租户，{sum(1 for t in tenant_list if t["status"]=="active")}个活跃',
            'confidence': 0.95,
        }
    
    async def _decision_assist(self, params: Dict, context: Dict) -> Dict:
        """决策辅助"""
        from dashboard import get_dashboard
        dash = get_dashboard()
        rev = dash.get('revenue', {})
        agents_data = dash.get('agent_usage', {}).get('heatmap', [])
        
        suggestions = []
        
        # 收入分析
        plan_dist = rev.get('plan_distribution', {})
        free_count = plan_dist.get('free', 0)
        paid_count = sum(v for k, v in plan_dist.items() if k != 'free')
        total_tenants = free_count + paid_count
        
        if total_tenants > 0:
            conversion_rate = paid_count / total_tenants * 100
            if conversion_rate < 20:
                suggestions.append({
                    'priority': 'high',
                    'title': '付费转化率偏低',
                    'detail': f'当前付费转化率{conversion_rate:.1f}%，建议推出限时优惠活动或增加试用期功能曝光',
                    'expectedImpact': '预计可提升10-15%转化率',
                })
        
        # Agent热度
        if agents_data:
            top_agent = agents_data[0] if agents_data else {'agent_id': 'N/A', 'count': 0}
            least_agent = agents_data[-1] if len(agents_data) > 1 else agents_data[0]
            if top_agent['count'] > least_agent['count'] * 5:
                suggestions.append({
                    'priority': 'medium',
                    'title': '功能使用不均衡',
                    'detail': f'{top_agent["agent_id"]}使用率远高于{least_agent["agent_id"]}，建议引导用户发现更多功能',
                    'expectedImpact': '提升用户粘性',
                })
        
        return {
            'suggestions': suggestions,
            'market_insights': [
                '勘察设计院市场处于数字化升级期，AI辅助设计是刚需',
                '住建局对智能审图的政策支持力度加大',
                '竞品多聚焦单一功能，EMA的全流程闭环是差异化优势',
            ],
            'summary': f'基于当前数据，提出{len(suggestions)}条建议',
            'confidence': 0.85,
        }
    
    async def _butler_response(self, params: Dict, context: Dict) -> Dict:
        return {
            'response': '🎩 管家中心为您服务！\n\n我可以帮您：\n📊 查看运营总览（驾驶舱）\n🚨 检查预警中心\n📝 自动生成报告\n👥 管理所有租户\n💡 提供决策建议\n\n请输入指令或点击功能卡片。',
            'suggestions': ['查看驾驶舱', '检查预警', '生成周报', '管理租户', '决策建议'],
            'confidence': 0.9,
        }
    
    def get_supported_tasks(self) -> list:
        return ['cockpit', 'alerts', 'report', 'tenant_management', 'decision', 'chat']