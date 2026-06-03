"""
knowledge_base/schema.py — 标准知识库核心数据模型

从第一性原理出发：
1. 标准体系层次：国标(GB) > 行标(JGJ/CJJ/DL...) > 地标(DBxx) > 团标(T/)
2. 强制性层级：强制性条文 > 全文强制 > 推荐性 > 参考性
3. 版本演化：替代关系、废止、局部修订
4. 适用范围：按工程领域/专业/阶段分类
5. 冲突规则：上位法优先、新版本优先、特殊法优先
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════
# 标准层级（上位法 > 下位法）
# ═══════════════════════════════════════════════════════════════

class StandardLevel(str, Enum):
    """标准体系层级"""
    NATIONAL = "national"           # 国家标准 GB/GB/T/GBZ
    INDUSTRY = "industry"           # 行业标准 JGJ/CJJ/DL/SY/HG/SH/NB/JTG/...
    PROVINCIAL = "provincial"       # 地方标准 DBxx
    ENTERPRISE = "enterprise"       # 企业标准 Q/xxx
    ASSOCIATION = "association"     # 团体标准 T/xxx
    INTERNATIONAL = "international" # 国际标准 ISO/IEC

    @property
    def priority(self) -> int:
        """层级优先级（数字越小越高）"""
        return {
            StandardLevel.NATIONAL: 1,
            StandardLevel.INDUSTRY: 2,
            StandardLevel.PROVINCIAL: 3,
            StandardLevel.ASSOCIATION: 4,
            StandardLevel.ENTERPRISE: 5,
            StandardLevel.INTERNATIONAL: 99,
        }[self]


# ═══════════════════════════════════════════════════════════════
# 强制性层级
# ═══════════════════════════════════════════════════════════════

class MandatoryLevel(str, Enum):
    """强制性层级"""
    FULL_MANDATORY = "full_mandatory"         # 全文强制（如 GB 50016）
    PARTIAL_MANDATORY = "partial_mandatory"   # 含强制性条文（如 GB 50300）
    RECOMMENDED = "recommended"               # 推荐性标准（GB/T）
    GUIDANCE = "guidance"                     # 指导性技术文件（GBZ）
    REFERENCE = "reference"                   # 参考性标准

    @property
    def is_mandatory(self) -> bool:
        return self in (MandatoryLevel.FULL_MANDATORY, MandatoryLevel.PARTIAL_MANDATORY)


# ═══════════════════════════════════════════════════════════════
# 工程领域分类
# ═══════════════════════════════════════════════════════════════

class EngineeringDomain(str, Enum):
    """工程领域分类（按勘察设计行业标准体系）"""
    # 建筑类
    ARCHITECTURE = "architecture"         # 建筑设计
    STRUCTURE = "structure"               # 结构工程
    FIRE_PROTECTION = "fire_protection"   # 消防工程
    HVAC = "hvac"                         # 暖通空调
    WATER_SUPPLY = "water_supply"         # 给排水
    ELECTRICAL = "electrical"             # 电气工程
    INTELLIGENT = "intelligent"           # 智能化/弱电

    # 土木类
    ROAD = "road"                         # 道路工程
    BRIDGE = "bridge"                     # 桥梁工程
    TUNNEL = "tunnel"                     # 隧道工程
    GEOTECHNICAL = "geotechnical"         # 岩土/勘察
    SURVEY = "survey"                     # 测绘

    # 市政类
    MUNICIPAL_WATER = "municipal_water"   # 市政给水
    MUNICIPAL_DRAIN = "municipal_drain"   # 市政排水
    GAS = "gas"                           # 燃气工程
    HEATING = "heating"                   # 供热工程
    ENVIRONMENT = "environment"           # 环境工程

    # 工业类
    PIPELINE = "pipeline"                 # 工业管道
    EQUIPMENT = "equipment"               # 设备安装
    POWER = "power"                       # 动力工程
    PETROCHEM = "petrochem"               # 石油化工

    # 管理类
    CONSTRUCTION_MGMT = "construction_mgmt"   # 施工管理
    COST = "cost"                         # 造价工程
    QUALITY = "quality"                   # 质量管理
    SAFETY_MGMT = "safety_mgmt"           # 安全管理
    BIM = "bim"                           # BIM/信息化
    GREEN = "green"                       # 绿色建筑/节能

    @property
    def label(self) -> str:
        labels = {
            "architecture": "建筑设计",
            "structure": "结构工程",
            "fire_protection": "消防工程",
            "hvac": "暖通空调",
            "water_supply": "给排水",
            "electrical": "电气工程",
            "intelligent": "智能化",
            "road": "道路工程",
            "bridge": "桥梁工程",
            "tunnel": "隧道工程",
            "geotechnical": "岩土勘察",
            "survey": "工程测绘",
            "municipal_water": "市政给水",
            "municipal_drain": "市政排水",
            "gas": "燃气工程",
            "heating": "供热工程",
            "environment": "环境工程",
            "pipeline": "工业管道",
            "equipment": "设备安装",
            "power": "动力工程",
            "petrochem": "石油化工",
            "construction_mgmt": "施工管理",
            "cost": "造价工程",
            "quality": "质量管理",
            "safety_mgmt": "安全管理",
            "bim": "BIM/信息化",
            "green": "绿色节能",
        }
        return labels.get(self.value, self.value)


# ═══════════════════════════════════════════════════════════════
# 冲突类型
# ═══════════════════════════════════════════════════════════════

class ConflictType(str, Enum):
    """标准冲突类型"""
    VERSION_SUPERSEDED = "version_superseded"     # 旧版本被替代
    LEVEL_OVERRIDE = "level_override"             # 上位法覆盖下位法
    SPECIAL_OVERRIDE = "special_override"         # 特殊法优于一般法
    CONTRADICTION = "contradiction"               # 直接矛盾
    DUPLICATE = "duplicate"                       # 重复定义
    LOCAL_STRICTER = "local_stricter"             # 地标严于国标


# ═══════════════════════════════════════════════════════════════
# 核心数据模型
# ═══════════════════════════════════════════════════════════════

@dataclass
class MandatoryClause:
    """强制性条文"""
    clause_id: str                     # 条文编号 (如 "5.1.1")
    content: str                       # 条文内容
    keywords: List[str] = field(default_factory=list)  # 关键词
    scope: List[str] = field(default_factory=list)     # 适用范围
    penalty: str = ""                  # 违反后果/罚则
    related_clauses: List[str] = field(default_factory=list)  # 关联条文
    confidence: float = 1.0            # 提取置信度


@dataclass
class StandardVersion:
    """标准版本信息"""
    code: str                          # 标准编号
    year: int                          # 发布年份
    name: str                          # 标准名称
    level: StandardLevel               # 标准层级
    mandatory_level: MandatoryLevel    # 强制性层级
    domains: List[EngineeringDomain] = field(default_factory=list)
    replaced_by: Optional[str] = None  # 被哪个标准替代
    replaces: List[str] = field(default_factory=list)  # 替代了哪些标准
    amendments: List[str] = field(default_factory=list)  # 修订/增补
    publish_date: Optional[date] = None
    effective_date: Optional[date] = None
    abolished_date: Optional[date] = None
    is_active: bool = True


@dataclass
class Standard:
    """标准条目（完整信息）"""
    id: str                            # 唯一标识 (如 "gb50016")
    code: str                          # 标准编号 (如 "GB 50016-2014")
    name: str                          # 标准名称
    name_en: str = ""                  # 英文名
    level: StandardLevel = StandardLevel.NATIONAL
    mandatory_level: MandatoryLevel = MandatoryLevel.RECOMMENDED
    domains: List[EngineeringDomain] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)

    # 版本信息
    current_version: int = 2020        # 当前有效年份
    all_versions: List[StandardVersion] = field(default_factory=list)
    is_active: bool = True

    # 内容
    summary: str = ""                  # 标准摘要
    scope: str = ""                    # 适用范围
    mandatory_clauses: List[MandatoryClause] = field(default_factory=list)
    clause_count: int = 0              # 条文总数
    page_count: int = 0                # 页数

    # 关系
    parent_standards: List[str] = field(default_factory=list)    # 引用的上位标准
    child_standards: List[str] = field(default_factory=list)     # 引用的下位标准
    related_standards: List[str] = field(default_factory=list)   # 相关标准
    conflicts: List["StandardConflict"] = field(default_factory=list)

    # 元数据
    issuing_body: str = ""             # 发布机构
    drafting_body: str = ""            # 起草单位
    tags: List[str] = field(default_factory=list)

    def get_mandatory_count(self) -> int:
        return len(self.mandatory_clauses)

    def get_version_history(self) -> List[StandardVersion]:
        return sorted(self.all_versions, key=lambda v: v.year, reverse=True)

    def is_expired(self) -> bool:
        if not self.is_active:
            return True
        if self.all_versions:
            latest = max(v.year for v in self.all_versions)
            if latest < self.current_version:
                return True
        return False


@dataclass
class StandardConflict:
    """标准冲突记录"""
    id: str
    standard_a: str                    # 标准A编号
    standard_b: str                    # 标准B编号
    conflict_type: ConflictType
    clause_a: str = ""                 # 冲突条文A
    clause_b: str = ""                 # 冲突条文B
    description: str = ""              # 冲突描述
    resolution: str = ""               # 解决方案（按冲突规则）
    resolved_by: str = ""              # 解决的依据
    severity: str = "info"             # critical / warning / info
    tags: List[str] = field(default_factory=list)


@dataclass
class KnowledgeBaseStats:
    """知识库统计"""
    total_standards: int = 0
    by_level: Dict[str, int] = field(default_factory=dict)
    by_domain: Dict[str, int] = field(default_factory=dict)
    mandatory_standards: int = 0
    mandatory_clauses: int = 0
    active_standards: int = 0
    expired_standards: int = 0
    conflicts: int = 0
    last_updated: str = ""
