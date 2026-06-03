"""
knowledge_base/mandatory.py — 强制性条文识别与提取

从第一性原理：
1. 识别标准中的强制性条文（以"必须""严禁""应""不应"等词为标志）
2. 提取条文内容、适用范围、违反后果
3. 按领域/专业分类汇总
4. 生成审查检查清单
"""

import re
from typing import Dict, List, Optional

from .schema import MandatoryClause, MandatoryLevel, Standard, EngineeringDomain


# ═══════════════════════════════════════════════════════════════
# 强制性条文识别规则
# ═══════════════════════════════════════════════════════════════

# 强条标志词（中文工程建设标准用语）
MANDATORY_KEYWORDS = [
    # 严格程度：必须 > 严禁 > 应 > 不应/不得
    ("必须", "command"),
    ("严禁", "prohibition"),
    ("应", "requirement"),
    ("不应", "prohibition"),
    ("不得", "prohibition"),
    ("禁止", "prohibition"),
    ("强制执行", "command"),
]

# 条文编号模式
CLAUSE_PATTERN = re.compile(
    r'((?:\d+\.)+\d+)\s*'  # 编号 如 "5.1.1"
    r'([\u4e00-\u9fff（(][^。；\n]{10,300}?(?:[。；]|$))'  # 内容
)

# 强制性条文必需关键词（至少匹配一个）
MANDATORY_CLAUSE_REQUIRED = re.compile(
    r'(必须|严禁|应(?![\u4e00-\u9fff]*[可仅]))|(不得|禁止|强制执行)'
)


# ═══════════════════════════════════════════════════════════════
# 预设的强制性条文（基于真实标准）
# ═══════════════════════════════════════════════════════════════

PRESET_MANDATORY_CLAUSES: Dict[str, List[MandatoryClause]] = {
    # GB 50016 — 建筑设计防火规范 (核心消防强条)
    "gb50016": [
        MandatoryClause(clause_id="5.3.1",
            content="除本规范另有规定外，不同耐火等级建筑的允许建筑高度或层数、防火分区最大允许建筑面积应符合表5.3.1的规定。",
            keywords=["防火分区", "耐火等级", "建筑面积"],
            scope=["所有民用建筑"],
            related_clauses=["5.3.2", "5.3.3", "5.3.4"]),
        MandatoryClause(clause_id="5.5.8",
            content="公共建筑内每个防火分区或一个防火分区的每个楼层，其安全出口的数量应经计算确定，且不应少于2个。",
            keywords=["安全出口", "疏散", "防火分区"],
            scope=["公共建筑"],
            penalty="不符合时将导致消防验收不合格",
            related_clauses=["5.5.9", "5.5.10"]),
        MandatoryClause(clause_id="5.5.17",
            content="公共建筑的安全疏散距离应符合表5.5.17的规定。",
            keywords=["疏散距离", "安全出口", "走道"],
            scope=["公共建筑"],
            related_clauses=["5.5.29"]),
        MandatoryClause(clause_id="6.4.1",
            content="疏散楼梯间应符合下列规定：1 楼梯间应能天然采光和自然通风，并宜靠外墙设置...",
            keywords=["疏散楼梯", "采光", "通风", "防烟"],
            scope=["所有建筑"],
            related_clauses=["6.4.2", "6.4.3"]),
        MandatoryClause(clause_id="7.1.8",
            content="消防车道应符合下列要求：车道的净宽度和净空高度均不应小于4.0m...",
            keywords=["消防车道", "净宽", "净高"],
            scope=["所有建筑"],
            penalty="消防车无法通行将导致重大安全隐患"),
        MandatoryClause(clause_id="8.1.2",
            content="民用建筑、厂房、仓库、储罐（区）和堆场周围应设置室外消火栓系统。",
            keywords=["消火栓", "消防给水"],
            scope=["工业与民用建筑"]),
    ],

    # GB 50011 — 建筑抗震设计规范
    "gb50011": [
        MandatoryClause(clause_id="3.1.1",
            content="抗震设防的所有建筑应按现行国家标准《建筑工程抗震设防分类标准》确定其抗震设防类别及其抗震设防标准。",
            keywords=["抗震设防", "设防类别", "设防标准"],
            scope=["所有建筑"]),
        MandatoryClause(clause_id="3.4.1",
            content="建筑设计应根据抗震概念设计的要求明确建筑形体的规则性。不规则的建筑应按规定采取加强措施；特别不规则的建筑应进行专门研究和论证，采取特别的加强措施；严重不规则的建筑不应采用。",
            keywords=["规则性", "不规则", "加强措施", "抗震概念设计"],
            scope=["所有建筑"],
            penalty="严重不规则建筑不应采用"),
        MandatoryClause(clause_id="5.1.1",
            content="各类建筑结构的地震作用，应符合下列规定：1 一般情况下，应至少在建筑结构的两个主轴方向分别计算水平地震作用...",
            keywords=["地震作用", "计算方向", "双向"],
            scope=["所有建筑"]),
        MandatoryClause(clause_id="5.5.1",
            content="表5.5.1所列各类结构应进行多遇地震作用下的抗震变形验算，其楼层内最大的弹性层间位移应符合下式要求。",
            keywords=["变形验算", "层间位移", "弹性"],
            scope=["多高层建筑"]),
    ],

    # GB 50009 — 建筑结构荷载规范
    "gb50009": [
        MandatoryClause(clause_id="3.1.2",
            content="建筑结构设计时，对不同荷载应采用不同的代表值。对永久荷载应采用标准值作为代表值...",
            keywords=["荷载", "代表值", "标准值"],
            scope=["所有结构设计"]),
        MandatoryClause(clause_id="3.2.3",
            content="对于承载能力极限状态，应按荷载的基本组合或偶然组合计算荷载组合的效应设计值。",
            keywords=["承载能力", "荷载组合", "极限状态"],
            scope=["所有结构设计"]),
    ],

    # GB 50300 — 建筑工程施工质量验收统一标准
    "gb50300": [
        MandatoryClause(clause_id="3.0.3",
            content="建筑工程施工质量应按下列要求进行验收：1 工程质量验收均应在施工单位自检合格的基础上进行...",
            keywords=["质量验收", "自检", "程序"],
            scope=["建筑工程"],
            penalty="违反验收程序将导致工程质量无法保证"),
        MandatoryClause(clause_id="5.0.4",
            content="单位（子单位）工程质量验收合格应符合下列规定：1 所含分部（子分部）工程的质量均应验收合格...",
            keywords=["验收合格", "分部", "质量控制"],
            scope=["建筑工程"]),
    ],

    # GB 50500 — 建设工程工程量清单计价规范
    "gb50500": [
        MandatoryClause(clause_id="3.1.1",
            content="使用国有资金投资的建设工程发承包，必须采用工程量清单计价。",
            keywords=["国有资金", "工程量清单", "计价"],
            scope=["国有投资项目"],
            penalty="违反将被认定为招标无效"),
        MandatoryClause(clause_id="3.1.5",
            content="措施项目中的安全文明施工费必须按国家或省级、行业建设主管部门的规定计算，不得作为竞争性费用。",
            keywords=["安全文明施工费", "不可竞争"],
            scope=["所有建设工程"],
            penalty="低于规定标准将被废标"),
        MandatoryClause(clause_id="4.1.2",
            content="招标工程量清单必须作为招标文件的组成部分，其准确性和完整性应由招标人负责。",
            keywords=["工程量清单", "准确性", "完整性"],
            scope=["招标"],
            penalty="清单错漏由招标人承担风险"),
    ],

    # GB 50010 — 混凝土结构设计规范
    "gb50010": [
        MandatoryClause(clause_id="3.3.2",
            content="结构设计时，应根据结构在施工和使用期间的环境条件和设计使用年限确定混凝土材料的耐久性要求。",
            keywords=["混凝土", "耐久性", "设计使用年限", "环境"],
            scope=["混凝土结构"]),
        MandatoryClause(clause_id="4.1.2",
            content="混凝土结构的承载能力极限状态计算应包括下列内容：1 结构构件的正截面承载力计算...",
            keywords=["承载能力", "截面", "承载力"],
            scope=["混凝土结构"]),
    ],

    # GB 50736 — 民用建筑供暖通风与空气调节设计规范
    "gb50736": [
        MandatoryClause(clause_id="4.1.1",
            content="供暖、通风与空气调节系统的设计应遵循国家有关节能减排政策，采用合理的节能技术措施。",
            keywords=["节能", "减排", "热回收"],
            scope=["民用建筑暖通"]),
        MandatoryClause(clause_id="5.2.1",
            content="集中供暖系统的热媒参数应根据安全、卫生、经济及使用要求确定。",
            keywords=["热媒", "供暖", "参数"],
            scope=["集中供暖"]),
    ],
}


# ═══════════════════════════════════════════════════════════════
# 强制条文提取器
# ═══════════════════════════════════════════════════════════════

class MandatoryClauseExtractor:
    """
    强制性条文提取引擎

    功能：
    1. 从标准文本中识别强制性条文
    2. 按领域/专业分类
    3. 生成审查检查清单
    4. 输出摘要报告
    """

    def extract_from_text(self, text: str, standard_code: str) -> List[MandatoryClause]:
        """从文本中提取强制性条文"""
        clauses = []

        # 先检查预设
        if standard_code in PRESET_MANDATORY_CLAUSES:
            return PRESET_MANDATORY_CLAUSES[standard_code]

        # 自动识别模式
        for match in CLAUSE_PATTERN.finditer(text):
            clause_id = match.group(1)
            content = match.group(2).strip()

            # 检查是否包含强制性关键词
            if MANDATORY_CLAUSE_REQUIRED.search(content):
                # 提取关键词
                kw = self._extract_keywords(content)

                clauses.append(MandatoryClause(
                    clause_id=clause_id,
                    content=content,
                    keywords=kw,
                    confidence=0.85,
                ))

        return clauses

    def get_checklist(self, domain: EngineeringDomain,
                      standards: List[Standard]) -> List[MandatoryClause]:
        """生成某领域的审查检查清单"""
        checklist = []
        for s in standards:
            if domain in s.domains and s.mandatory_level.is_mandatory:
                clauses = self.get_clauses(s.id)
                checklist.extend(clauses)
        return checklist

    def get_clauses(self, standard_id: str) -> List[MandatoryClause]:
        """获取特定标准的强制条文"""
        if standard_id in PRESET_MANDATORY_CLAUSES:
            return PRESET_MANDATORY_CLAUSES[standard_id]
        return []

    def summarize(self, standards: List[Standard]) -> Dict:
        """汇总所有强制条文"""
        total = 0
        by_domain = {}
        by_standard = {}

        for s in standards:
            clauses = self.get_clauses(s.id)
            if not clauses:
                continue

            by_standard[s.code] = {
                'name': s.name,
                'count': len(clauses),
                'clauses': [c.clause_id for c in clauses],
            }
            total += len(clauses)

            for d in s.domains:
                if d.value not in by_domain:
                    by_domain[d.value] = {'count': 0, 'standards': []}
                by_domain[d.value]['count'] += len(clauses)
                by_domain[d.value]['standards'].append(s.code)

        return {
            'total_clauses': total,
            'standards_count': len(by_standard),
            'by_standard': by_standard,
            'by_domain': by_domain,
        }

    def to_review_rules(self, standards: List[Standard]) -> List[Dict]:
        """将强制条文转换为审查规则"""
        rules = []
        for s in standards:
            clauses = self.get_clauses(s.id)
            for c in clauses:
                rules.append({
                    'rule_id': f"{s.id}_{c.clause_id}",
                    'standard_code': s.code,
                    'standard_name': s.name,
                    'clause_id': c.clause_id,
                    'content': c.content,
                    'keywords': c.keywords,
                    'scope': c.scope,
                    'severity': 'critical',
                    'check_type': 'mandatory_clause',
                    'domains': [d.value for d in s.domains],
                })
        return rules

    def _extract_keywords(self, text: str) -> List[str]:
        """从条文中提取关键词"""
        technical_terms = {
            '防火分区', '疏散', '耐火等级', '消防', '抗震', '荷载', '承载力',
            '钢筋', '混凝土', '强度', '配筋率', '裂缝', '挠度', '变形',
            '安全出口', '楼梯', '电梯', '消火栓', '喷淋', '报警', '防排烟',
            '给水', '排水', '通风', '空调', '供暖', '电气', '防雷',
            '质量验收', '检验批', '安全检查', '隐患', '防护', '材料',
            '施工', '验收', '节能', '绿色', '无障碍',
        }
        return [t for t in technical_terms if t in text]


# 单例
_extractor = None

def get_extractor() -> MandatoryClauseExtractor:
    global _extractor
    if _extractor is None:
        _extractor = MandatoryClauseExtractor()
    return _extractor
