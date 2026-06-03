"""
knowledge_base/conflict.py — 标准冲突检测与解决引擎

从第一性原理：
1. 上位法优先：国标 > 行标 > 地标 > 团标
2. 新版本优先：新版替代旧版
3. 特殊法优先：专项规范 > 通用规范
4. 地方严于国家：地标更严时适用地标
"""

from datetime import date
from typing import Dict, List, Optional, Set, Tuple

from .schema import (
    ConflictType, Standard, StandardConflict, StandardLevel,
    MandatoryLevel, EngineeringDomain,
)


# ═══════════════════════════════════════════════════════════════
# 版本替代关系
# ═══════════════════════════════════════════════════════════════

# 已知的标准替代关系 (旧版 → 新版)
VERSION_SUPERSEDE: Dict[str, str] = {
    # 建筑
    "GB 50016-2006": "GB 50016-2014",
    "GB 50045-2005": "GB 50016-2014",  # 高规并入建规
    "GB 50016-2014": "GB 50016-2014(2018)",  # 局部修订
    "GB 50352-2005": "GB 50352-2019",
    "GBJ 16-87": "GB 50016-2006",

    # 结构
    "GB 50009-2001": "GB 50009-2012",
    "GB 50010-2002": "GB 50010-2010",
    "GB 50011-2001": "GB 50011-2010",
    "GB 50017-2003": "GB 50017-2017",
    "GB 50007-2002": "GB 50007-2011",
    "GB 50003-2001": "GB 50003-2011",

    # 给排水
    "GB 50015-2003": "GB 50015-2019",
    "GBJ 15-88": "GB 50015-2003",
    "GB 50014-2006": "GB 50014-2021",
    "GB 50013-2006": "GB 50013-2018",

    # 消防
    "GB 50084-2001": "GB 50084-2017",
    "GB 50116-98": "GB 50116-2013",
    "GB 50974-2010": "GB 50974-2014",
    "GB 50222-95": "GB 50222-2017",

    # 暖通
    "GB 50019-2003": "GB 50019-2015",
    "GB 50189-2005": "GB 50189-2015",
    "GB 50243-2002": "GB 50243-2016",

    # 电气
    "GB 50057-94": "GB 50057-2010",
    "GB 50303-2002": "GB 50303-2015",

    # 施工
    "GB 50300-2001": "GB 50300-2013",
    "GB 50500-2008": "GB 50500-2013",

    # 环境
    "GB 3095-1996": "GB 3095-2012",
}


# ═══════════════════════════════════════════════════════════════
# 已知冲突
# ═══════════════════════════════════════════════════════════════

KNOWN_CONFLICTS: List[StandardConflict] = [
    StandardConflict(
        id="conf_001",
        standard_a="GB 50016-2014",
        standard_b="GB 50045-2005",
        conflict_type=ConflictType.VERSION_SUPERSEDED,
        description="《高层民用建筑设计防火规范》GB 50045-2005 已并入《建筑设计防火规范》GB 50016-2014",
        resolution="使用 GB 50016-2014，原 GB 50045-2005 的条文已整合",
        resolved_by="GB 50016-2014 前言",
        severity="warning",
    ),
    StandardConflict(
        id="conf_002",
        standard_a="GB 50016-2014",
        standard_b="GB 50016-2014(2018)",
        conflict_type=ConflictType.VERSION_SUPERSEDED,
        clause_a="7.3.5 消防电梯前室",
        clause_b="7.3.5 消防电梯前室（2018修订版）",
        description="GB 50016-2014(2018局修)对消防电梯前室短边净宽进行了调整（≥2.4m → ≥2.1m）",
        resolution="以2018年局部修订版为准",
        resolved_by="住建部公告2018年第36号",
        severity="warning",
        tags=["消防", "电梯"],
    ),
    StandardConflict(
        id="conf_003",
        standard_a="GB 50011-2010",
        standard_b="JGJ 3-2010",
        conflict_type=ConflictType.SPECIAL_OVERRIDE,
        clause_a="3.4 建筑形体规则性",
        clause_b="3.4 结构布置",
        description="JGJ 3-2010 高层规程对抗震规则性有更严格的要求",
        resolution="高层建筑优先适用 JGJ 3-2010（特殊法优先）",
        resolved_by="GB 50011-2010 1.0.2",
        severity="info",
        tags=["抗震", "高层"],
    ),
    StandardConflict(
        id="conf_004",
        standard_a="GB 50016-2014",
        standard_b="GB 50067-2014",
        conflict_type=ConflictType.SPECIAL_OVERRIDE,
        clause_a="5.3.1 防火分区面积",
        clause_b="5.1.1 汽车库防火分区",
        description="汽车库的防火分区面积要求与一般民用建筑不同",
        resolution="汽车库适用 GB 50067-2014（专项规范优先）",
        resolved_by="GB 50016-2014 1.0.2",
        severity="info",
        tags=["防火分区", "车库"],
    ),
    StandardConflict(
        id="conf_005",
        standard_a="GB 50028-2006",
        standard_b="GB 50028-2020",
        conflict_type=ConflictType.VERSION_SUPERSEDED,
        description="《城镇燃气设计规范》已全文修订为2020版，部分条文技术指标更新",
        resolution="以 GB 50028-2020 版为准，旧版设计应按新版复核",
        resolved_by="住建部公告2020年第148号",
        severity="warning",
        tags=["燃气"],
    ),
]


# ═══════════════════════════════════════════════════════════════
# 冲突检测与解决引擎
# ═══════════════════════════════════════════════════════════════

class ConflictDetector:
    """
    标准冲突检测引擎

    检测规则（优先级从高到低）：
    1. 上位法优先原则：国标 > 行标 > 地标
    2. 新版本优先原则：新版替代旧版
    3. 特殊法优先原则：专项规范 > 通用规范
    4. 地方严于国家原则：地标更严时适用
    """

    # 领域专项规范映射（特殊 → 通用）
    DOMAIN_SPECIALTY: Dict[str, List[str]] = {
        "gb50067": ["gb50016"],     # 车库防火 → 建规
        "gb50974": ["gb50016"],     # 消防给水 → 建规
        "gb50038": ["gb50016", "gb50010"],  # 人防 → 建规+混规
        "jgj3": ["gb50011", "gb50010"],     # 高层 → 抗规+混规
        "gb51251": ["gb50016"],     # 防排烟 → 建规
        "gb50174": ["gb50352", "gb50057"],  # 数据中心 → 统一标准+防雷
    }

    def __init__(self):
        self._conflicts: List[StandardConflict] = list(KNOWN_CONFLICTS)
        self._supersede_map: Dict[str, str] = dict(VERSION_SUPERSEDE)

    # ── 检测 ───────────────────────────────────────────────

    def detect_all(self, standards: List[Standard]) -> List[StandardConflict]:
        """全面检测所有冲突"""
        conflicts = []

        # 1. 检查版本替代
        for s in standards:
            for v in s.all_versions:
                if v.code in self._supersede_map:
                    conflicts.append(StandardConflict(
                        id=f"vs_{v.code}",
                        standard_a=v.code,
                        standard_b=self._supersede_map[v.code],
                        conflict_type=ConflictType.VERSION_SUPERSEDED,
                        description=f"{v.code} 已被 {self._supersede_map[v.code]} 替代",
                        resolution=f"应使用 {self._supersede_map[v.code]}",
                        severity="warning",
                    ))

        # 2. 检查专项vs通用
        conflicts.extend(self._check_specialty(standards))

        # 3. 检查已知冲突
        code_set = {s.code for s in standards}
        for kc in KNOWN_CONFLICTS:
            if kc.standard_a in code_set or kc.standard_b in code_set:
                if kc.id not in {c.id for c in conflicts}:
                    conflicts.append(kc)

        return conflicts

    def _check_specialty(self, standards: List[Standard]) -> List[StandardConflict]:
        """检查专项规范与通用规范的潜在冲突"""
        results = []
        code_map = {s.id: s for s in standards}

        for special_id, general_ids in self.DOMAIN_SPECIALTY.items():
            special = code_map.get(special_id)
            if not special:
                continue
            for gid in general_ids:
                general = code_map.get(gid)
                if general:
                    results.append(StandardConflict(
                        id=f"sp_{special_id}_{gid}",
                        standard_a=special.code,
                        standard_b=general.code,
                        conflict_type=ConflictType.SPECIAL_OVERRIDE,
                        description=f"{special.name}（专项）与 {general.name}（通用）存在适用范围重叠",
                        resolution=f"专项工程优先适用{special.code}",
                        resolved_by=f"{special.code} 1.0.2 适用范围",
                        severity="info",
                    ))
        return results

    def detect_version(self, code: str) -> Optional[str]:
        """检测标准是否已被替代"""
        return self._supersede_map.get(code)

    def is_superseded(self, code: str) -> bool:
        return code in self._supersede_map

    # ── 解决 ───────────────────────────────────────────────

    def resolve(self, conflict: StandardConflict) -> Dict:
        """自动解决冲突（按规则优先级）"""
        resolution = {
            'conflict_id': conflict.id,
            'rule_applied': str(conflict.conflict_type),
            'action': 'keep_current',
            'explanation': '',
        }

        if conflict.conflict_type == ConflictType.VERSION_SUPERSEDED:
            resolution['action'] = 'use_newer'
            resolution['explanation'] = f'使用新版本 {conflict.standard_b}'
        elif conflict.conflict_type == ConflictType.LEVEL_OVERRIDE:
            resolution['action'] = 'follow_higher_level'
            resolution['explanation'] = f'遵循上位法 {conflict.standard_a}'
        elif conflict.conflict_type == ConflictType.SPECIAL_OVERRIDE:
            resolution['action'] = 'follow_special'
            resolution['explanation'] = f'本项目适用专项规范 {conflict.standard_a}'
        elif conflict.conflict_type == ConflictType.LOCAL_STRICTER:
            resolution['action'] = 'follow_stricter'
            resolution['explanation'] = f'地标要求更严格，按地标执行'
        else:
            resolution['action'] = 'manual_review'
            resolution['explanation'] = '需人工判断'

        return resolution

    def resolve_by_hierarchy(self, a: Standard, b: Standard) -> Standard:
        """按标准层级决定哪个优先"""
        if a.level.priority < b.level.priority:
            return a  # a层级更高
        if b.level.priority < a.level.priority:
            return b  # b层级更高

        # 同级：判断强制性
        if a.mandatory_level.is_mandatory and not b.mandatory_level.is_mandatory:
            return a
        if b.mandatory_level.is_mandatory and not a.mandatory_level.is_mandatory:
            return b

        # 默认返回年份更新的
        return a if a.current_version >= b.current_version else b

    # ── 报告 ───────────────────────────────────────────────

    def generate_report(self, standards: List[Standard]) -> Dict:
        """生成冲突检测报告"""
        conflicts = self.detect_all(standards)

        by_type = {}
        by_severity = {}
        for c in conflicts:
            t = c.conflict_type.value
            by_type[t] = by_type.get(t, 0) + 1
            by_severity[c.severity] = by_severity.get(c.severity, 0) + 1

        superseded_codes = [c.standard_a for c in conflicts
                           if c.conflict_type == ConflictType.VERSION_SUPERSEDED]

        return {
            'total_conflicts': len(conflicts),
            'by_type': by_type,
            'by_severity': by_severity,
            'superseded_standards': superseded_codes,
            'conflicts': [
                {
                    'id': c.id,
                    'type': c.conflict_type.value,
                    'standards': f"{c.standard_a} vs {c.standard_b}",
                    'description': c.description,
                    'resolution': c.resolution,
                    'severity': c.severity,
                } for c in conflicts
            ],
        }

    def get_effective_standard(self, code: str, standards: List[Standard]) -> Optional[Standard]:
        """获取标准的最新有效版本"""
        # 检查是否被替代
        if code in self._supersede_map:
            new_code = self._supersede_map[code]
            for s in standards:
                if s.code.startswith(new_code[:10]):  # 模糊匹配
                    return s

        # 直接匹配
        for s in standards:
            if s.code == code:
                return s
        return None


# 单例
_detector = None

def get_detector() -> ConflictDetector:
    global _detector
    if _detector is None:
        _detector = ConflictDetector()
    return _detector
