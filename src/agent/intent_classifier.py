"""
agent/intent_classifier.py - 意图识别

分析用户消息，判断：
1. 应该路由到哪个 Sub-Agent
2. 任务类型是什么
3. 需要什么参数
"""

import os
import re
from datetime import datetime
from typing import Dict


# ─────────────────────────────────────────────────────────────────
# 意图规则引擎
# ─────────────────────────────────────────────────────────────────

# 关键词 → Agent 映射
AGENT_KEYWORDS = {
    'tech_rd': [
        '图纸', '解析', '分析', '识别', '图层', 'DWG', 'DXF', 'PDF',
        '工程量', '提量', '算量', '设计优化', '审图', '审图规则',
        '蓝图', 'CAD', '建筑', '结构', '机电', '暖通', '给排水',
        '智能审图', '合规审查', '审查', '文档', '设计说明',
        '技术交底', '工程量清单', '招投标', '端到端', '流水线',
    ],
    'safety_compliance': [
        '安全', '合规', '消防', '防火', '疏散', '排烟', '验收',
        '规范', '国标', '标准', '违反', '违规', '隐患', '结构安全',
        '荷载', '抗震', '审查', '检查',
    ],
    'market_sales': [
        '市场', '销售', '客户', '投标', '商务', '报价', '方案',
        '竞品', '需求', '商机', '合同', '招标', '标书',
    ],
    'engineering_delivery': [
        '施工', '交付', '进度', '计划', '竣工', '验收', '项目',
        '工期', '组织', '方案', '技术交底', '核定单', '联系单',
        'SOP', 'sop', 'MOP', 'mop', 'EOP', 'eop', 'LCC', 'lcc',
        '标准操作程序', '维护操作', '紧急操作', '生命周期成本',
    ],
    'cost_benefit': [
        '成本', '预算', '造价', '结算', '变更', '签证', '效益',
        '经济', '投资', '回报', '算量', '清单', '报价', '价格',
        '费用', '多少钱', '省钱', '超支', '费率',
    ],
    'customer_service': [
        '客服', '服务', '支持', '帮助', 'FAQ', '常见问题', '培训',
        '工单', '回访', '满意度', '反馈', '问题',
    ],
}

# 意图 → 任务类型映射
INTENT_TASK_MAP = {
    # tech_rd
    'parse_blueprint': 'parse',
    'classify_blueprint': 'classify',
    'analyze_blueprint': 'analyze',
    'review_blueprint': 'review',
    'extract_quantities': 'extract_quantities',
    'optimize_design': 'optimize',
    'full_analysis': 'full_analysis',
    # 通用
    'chat': 'chat',
    'help': 'chat',
}

# Agent 默认任务类型
AGENT_DEFAULT_TASK = {
    'tech_rd': 'full_analysis',
    'safety_compliance': 'review',
    'market_sales': 'chat',
    'engineering_delivery': 'chat',
    'cost_benefit': 'chat',
    'customer_service': 'chat',
}


# ─────────────────────────────────────────────────────────────────
# IntentClassifier
# ─────────────────────────────────────────────────────────────────

class IntentClassifier:
    """
    意图识别器

    根据用户消息关键词，判断：
    1. agent_id：路由到哪个 Agent
    2. task_type：执行什么任务
    3. confidence：置信度
    """

    def __init__(self):
        self._agent_keywords = AGENT_KEYWORDS
        self._intent_map = INTENT_TASK_MAP
        self._default_task = AGENT_DEFAULT_TASK

    async def classify(self, message: str) -> Dict:
        """
        分析用户消息，返回意图

        Args:
            message: 用户消息（自然语言）

        Returns:
            {
                'agent_id': str,      # 目标Agent
                'task_type': str,     # 任务类型
                'intent': str,        # 意图标签
                'confidence': float,  # 置信度 0-1
                'params': dict,        # 提取的参数
            }
        """
        message_lower = message.lower()
        scores = {}

        # 计算每个 Agent 的匹配分数
        for agent_id, keywords in self._agent_keywords.items():
            score = 0
            matched = []
            for kw in keywords:
                if kw.lower() in message_lower:
                    score += 1
                    matched.append(kw)
            if score > 0:
                scores[agent_id] = {
                    'score': score,
                    'matched': matched,
                }

        # 选择最高分
        if scores:
            best_agent = max(scores.items(), key=lambda x: x[1]['score'])
            agent_id = best_agent[0]
            matched_count = best_agent[1]['score']
            confidence = min(matched_count / 3.0, 0.95)  # 最多3个关键词封顶
        else:
            # 默认路由到 tech_rd
            agent_id = 'tech_rd'
            confidence = 0.4

        # 判断任务类型
        task_type = self._infer_task_type(message_lower, agent_id)

        return {
            'agent_id': agent_id,
            'task_type': task_type,
            'intent': f'{agent_id}:{task_type}',
            'confidence': confidence,
            'params': self._extract_params(message),
        }

    def _infer_task_type(self, message: str, agent_id: str) -> str:
        """根据消息内容推断任务类型"""
        if agent_id == 'tech_rd':
            # 无文件时，greeting/chat 类返回 chat
            file_keywords = ['图纸', 'dwg', 'dxf', 'pdf', '上传', '文件', 'cad', '蓝图']
            has_file = any(k in message for k in file_keywords)
            if not has_file:
                if any(k in message for k in ['你好', 'hi', 'hello', '介绍', '你是谁', '帮助', 'help', '功能', '能力', '做什么', '能']):
                    return 'chat'
            if any(k in message for k in ['解析', '解析图纸', '读取']):
                return 'parse'
            elif any(k in message for k in ['识别', '分类', '类型']):
                return 'classify'
            elif any(k in message for k in ['审查', '审图', '合规审查', '规则', '检查问题']):
                return 'review'
            elif any(k in message for k in ['文档', '设计说明', '技术交底', '工程量清单', '招投标', '标书']):
                return 'documents'
            elif any(k in message for k in ['端到端', '流水线', '全流程', '一键', '全部']):
                return 'full_pipeline'
            elif any(k in message for k in ['工程量', '提量', '算量', '数量']):
                return 'extract_quantities'
            elif any(k in message for k in ['优化', '改进', '建议']):
                return 'optimize'
            elif any(k in message for k in ['分析', '完整分析', '全面分析']):
                return 'full_analysis'
            else:
                return 'chat'  # 默认 chat（无需图纸）

        elif agent_id == 'safety_compliance':
            if any(k in message for k in ['消防', '防火', '疏散']):
                return 'fire_review'
            elif any(k in message for k in ['结构', '荷载', '抗震']):
                return 'structural_review'
            elif any(k in message for k in ['合规', '规范', '标准']):
                return 'compliance_review'
            else:
                return 'review'

        elif agent_id == 'market_sales':
            return 'chat'

        elif agent_id == 'engineering_delivery':
            return 'chat'

        elif agent_id == 'cost_benefit':
            return 'chat'

        elif agent_id == 'customer_service':
            return 'chat'

        return self._default_task.get(agent_id, 'chat')

    def _extract_params(self, message: str) -> Dict:
        """从消息中提取参数：文件路径、日期、数量等"""
        params: Dict = {}

        # 提取文件路径（Unix/Windows 风格）
        path_pattern = r"(?:[\\'\"]?)((?:/[\\w.\\-]+)+|(?:[A-Za-z]:\\\\[\\w .\\-]+(?:\\\\[\\w .\\-]+)*))"
        paths = re.findall(path_pattern, message)
        if paths:
            params['file_paths'] = [p for p in paths if os.path.sep in p]

        # 提取日期（YYYY-MM-DD / YYYY/MM/DD / YYYY年M月D日）
        date_patterns = [
            r'(\\d{4}[/-]\\d{1,2}[/-]\\d{1,2})',
            r'(\\d{4}年\\d{1,2}月\\d{1,2}日?)',
        ]
        dates = []
        for pat in date_patterns:
            dates.extend(re.findall(pat, message))
        if dates:
            params['dates'] = dates

        # 提取数量（数字+单位）
        qty_pattern = r'(\\d+(?:\\.\\d+)?\\s*(?:个|件|份|套|台|kg|KG|吨|米|m|M|㎡|万元|元|%|天|周|月|年))'
        quantities = re.findall(qty_pattern, message)
        if quantities:
            params['quantities'] = quantities

        # 提取纯数字（可能是编号、ID等）
        number_pattern = r'\\b(\\d{4,})\\b'
        numbers = re.findall(number_pattern, message)
        if numbers:
            params['numbers'] = numbers

        return params


class RuleBasedIntentClassifier(IntentClassifier):
    """基于规则引擎的意图分类器（当前实现）"""

    pass  # 与基类相同


# 导出单例
_classifier = None


def get_intent_classifier() -> IntentClassifier:
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier