"""
specs_adapter.py - EMA 标准知识库适配器 v2.0

Phase 27: 升级对接 knowledge_base 新引擎

功能：
1. 桥接旧文件系统 + 新结构化标准库
2. 全文搜索（按编号/名称/领域/关键词）
3. 智能推荐（根据图纸类型推荐相关规范）
4. 强制条文提取
5. 冲突检测
6. 审查检查清单生成
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any

# 旧知识库路径
EMA_KB = Path(__file__).parent.parent.parent / "data" / "standards"


class SpecsAdapter:
    """
    EMA 标准规范适配器 v2.0

    桥接旧文件系统 + 新 knowledge_base 引擎
    """

    def __init__(self):
        # 旧版文件缓存
        self._cache: Dict[str, Dict] = {}
        self._index: List[Dict] = []
        self._loaded = False

        # 新版知识库（懒加载）
        self._kb = None

    @property
    def kb(self):
        """懒加载新知识库"""
        if self._kb is None:
            try:
                from knowledge_base import get_kb
                self._kb = get_kb()
            except ImportError:
                self._kb = None
        return self._kb

    def _ensure_loaded(self):
        if self._loaded:
            return
        self._load_all()
        self._loaded = True

    def _load_all(self):
        """加载旧版文件知识库"""
        self._cache = {}
        self._index = []

        if not EMA_KB.exists():
            return
        for f in sorted(EMA_KB.glob("kb_*.json")):
            if f.name == "kb_index.json":
                continue
            try:
                with open(f, encoding="utf-8") as fh:
                    data = json.load(fh)
                code = data.get("spec_code", "")
                self._cache[code] = data
                self._index.append({
                    "code": code,
                    "name": data.get("spec_name", ""),
                    "category": data.get("category", ""),
                    "version": data.get("version", ""),
                    "sections_count": len(data.get("sections", [])),
                    "requirements_count": len(data.get("key_requirements", [])),
                })
            except Exception:
                continue

    def get_stats(self) -> Dict:
        """获取知识库统计（融合新旧数据）"""
        self._ensure_loaded()

        # 旧版统计
        categories = {}
        total_sections = 0
        total_requirements = 0
        for item in self._index:
            cat = item["category"]
            categories[cat] = categories.get(cat, 0) + 1
            total_sections += item["sections_count"]
            total_requirements += item["requirements_count"]

        # 新版统计
        new_stats = {}
        if self.kb:
            ks = self.kb.get_stats()
            new_stats = {
                "structured_standards": ks.total_standards,
                "mandatory_standards": ks.mandatory_standards,
                "mandatory_clauses": ks.mandatory_clauses,
                "known_conflicts": ks.conflicts,
                "by_level": ks.by_level,
            }

        return {
            "total_standards": len(self._index) + new_stats.get("structured_standards", 0),
            "total_categories": len(categories),
            "total_sections": total_sections,
            "total_requirements": total_requirements,
            "categories": sorted(categories.items(), key=lambda x: -x[1]),
            "structured_kb": new_stats,
            "standards": sorted(self._index, key=lambda x: x["code"]),
        }

    def search(self, query: str, category: str = None, limit: int = 20) -> List[Dict]:
        """搜索规范（融合新旧数据）"""
        self._ensure_loaded()

        results = []

        # 新版知识库搜索
        if self.kb:
            for s in self.kb.find(query):
                results.append({
                    "code": s.code,
                    "name": s.name,
                    "level": s.level.value,
                    "mandatory_level": s.mandatory_level.value,
                    "domains": [d.value for d in s.domains],
                    "keywords": s.keywords,
                    "summary": s.summary[:120],
                    "score": 20,
                    "is_mandatory": s.mandatory_level.is_mandatory,
                    "source": "structured",
                })

        # 旧版文件搜索
        keywords = query.lower().split()
        for code, data in self._cache.items():
            score = 0
            if any(kw in code.lower() for kw in keywords):
                score += 15
            name = data.get("spec_name", "").lower()
            for kw in keywords:
                if kw in name:
                    score += 8
            if category and data.get("category") != category:
                continue
            for section in data.get("sections", []):
                text = (section.get("title", "") + " " + section.get("summary", "")).lower()
                for kw in keywords:
                    if kw in text:
                        score += 3
            for req in data.get("key_requirements", []):
                text = (req.get("title", "") + " " + req.get("requirement", "")).lower()
                for kw in keywords:
                    if kw in text:
                        score += 2

            if score > 0:
                results.append({
                    "code": code,
                    "name": data["spec_name"],
                    "category": data["category"],
                    "version": data.get("version", ""),
                    "summary": data.get("summary", "")[:100],
                    "score": score,
                    "sections_count": len(data.get("sections", [])),
                    "source": "file",
                })

        results.sort(key=lambda x: -x["score"])
        return results[:limit]

    def get_spec(self, code: str) -> Optional[Dict]:
        """获取完整规范详情"""
        self._ensure_loaded()

        # 先查新版
        if self.kb:
            s = self.kb.find(code)
            if s:
                s0 = s[0]
                return {
                    "code": s0.code,
                    "name": s0.name,
                    "level": s0.level.value,
                    "mandatory_level": s0.mandatory_level.value,
                    "domains": [d.label for d in s0.domains],
                    "keywords": s0.keywords,
                    "summary": s0.summary,
                    "version": str(s0.current_version),
                    "mandatory_clauses": [
                        {"clause_id": c.clause_id, "content": c.content, "keywords": c.keywords}
                        for c in self.kb.get_mandatory_clauses(s0.id)
                    ],
                    "superseded": self.kb.detect_version_conflict(s0.code) if self.kb else None,
                }

        # 旧版查找
        return self._cache.get(code)

    def recommend(self, drawing_type: str, drawing_category: str = None) -> List[Dict]:
        """根据图纸类型推荐规范（增强版）"""
        self._ensure_loaded()

        TYPE_TO_CATEGORY = {
            "建筑": ["建筑", "建筑设计", "消防工程", "绿色建筑", "建筑节能", "施工管理", "质量管理"],
            "结构": ["结构工程", "结构", "质量管理", "安全管理"],
            "给排水": ["给排水", "消防工程", "绿色建筑"],
            "电气": ["电气工程", "消防工程", "BIM/信息化"],
            "暖通": ["消防工程", "建筑节能", "绿色建筑", "暖通空调"],
            "总图": ["道路交通", "勘察测绘"],
            "道路": ["道路交通", "桥梁工程", "勘察测绘"],
            "桥梁": ["桥梁工程", "结构工程"],
            "隧道": ["隧道工程", "勘察测绘", "安全管理"],
            "地基": ["结构工程", "勘察测绘", "安全管理"],
            "造价": ["造价工程", "质量管理"],
            "消防": ["消防工程", "建筑"],
            "幕墙": ["建筑", "建筑节能"],
            "节能": ["建筑节能", "绿色建筑"],
        }

        categories = TYPE_TO_CATEGORY.get(drawing_type, ["建筑", "结构"])
        if drawing_category:
            categories.insert(0, drawing_category)

        results = []

        # 新版推荐
        if self.kb:
            from knowledge_base import EngineeringDomain
            try:
                domain_map = {
                    "建筑": EngineeringDomain.ARCHITECTURE,
                    "结构": EngineeringDomain.STRUCTURE,
                    "消防工程": EngineeringDomain.FIRE_PROTECTION,
                    "给排水": EngineeringDomain.WATER_SUPPLY,
                    "电气工程": EngineeringDomain.ELECTRICAL,
                    "暖通空调": EngineeringDomain.HVAC,
                    "道路交通": EngineeringDomain.ROAD,
                    "桥梁工程": EngineeringDomain.BRIDGE,
                    "隧道工程": EngineeringDomain.TUNNEL,
                    "勘察测绘": EngineeringDomain.GEOTECHNICAL,
                    "绿色建筑": EngineeringDomain.GREEN,
                    "建筑节能": EngineeringDomain.GREEN,
                    "施工管理": EngineeringDomain.CONSTRUCTION_MGMT,
                    "质量管理": EngineeringDomain.QUALITY,
                    "安全管理": EngineeringDomain.SAFETY_MGMT,
                    "造价工程": EngineeringDomain.COST,
                    "BIM/信息化": EngineeringDomain.BIM,
                }
                for cat in categories:
                    domain = domain_map.get(cat)
                    if domain:
                        for s in self.kb.list_by_domain(domain):
                            results.append({
                                "code": s.code,
                                "name": s.name,
                                "category": cat,
                                "level": s.level.value,
                                "is_mandatory": s.mandatory_level.is_mandatory,
                                "mandatory_clauses_count": len(self.kb.get_mandatory_clauses(s.id)),
                                "source": "structured",
                            })
            except Exception:
                pass

        # 旧版推荐
        for code, data in self._cache.items():
            cat = data.get("category", "")
            if cat in categories:
                results.append({
                    "code": code,
                    "name": data["spec_name"],
                    "category": cat,
                    "priority": "强制" if any(r.get("mandatory") for r in data.get("key_requirements", [])) else "推荐",
                    "source": "file",
                })

        # 去重
        seen = set()
        unique = []
        for r in results:
            if r["code"] not in seen:
                seen.add(r["code"])
                unique.append(r)

        return unique[:15]

    def lookup_section(self, code: str, section_num: str) -> Optional[Dict]:
        """精确查找规范条款"""
        # 新版查找
        if self.kb:
            s = self.kb.find(code)
            if s:
                clauses = self.kb.get_mandatory_clauses(s[0].id)
                for c in clauses:
                    if c.clause_id == section_num:
                        return {
                            "code": s[0].code,
                            "spec_name": s[0].name,
                            "clause_id": c.clause_id,
                            "content": c.content,
                            "keywords": c.keywords,
                            "scope": c.scope,
                            "source": "structured",
                        }

        # 旧版查找
        spec = self.get_spec(code)
        if not spec:
            return None
        for s in spec.get("sections", []):
            if s.get("section_num") == section_num:
                return {"code": code, "spec_name": spec["spec_name"], **s}
        for r in spec.get("key_requirements", []):
            if r.get("section", "").startswith(section_num):
                return {"code": code, "spec_name": spec["spec_name"], "type": "requirement", **r}
        return None

    def get_mandatory_requirements(self, code: str) -> List[Dict]:
        """获取强制条款（新版优先）"""
        # 新版
        if self.kb:
            s = self.kb.find(code)
            if s:
                return [
                    {"clause_id": c.clause_id, "content": c.content, "keywords": c.keywords, "scope": c.scope}
                    for c in self.kb.get_mandatory_clauses(s[0].id)
                ]

        # 旧版
        spec = self.get_spec(code)
        if not spec:
            return []
        return [r for r in spec.get("key_requirements", []) if r.get("mandatory")]

    def get_conflict_report(self) -> Optional[Dict]:
        """获取冲突检测报告"""
        if self.kb:
            return self.kb.get_conflict_report()
        return None

    def get_review_checklist(self, drawing_type: str) -> List[Dict]:
        """根据图纸类型生成审查检查清单"""
        if not self.kb:
            return []

        from knowledge_base import EngineeringDomain
        domain_map = {
            "建筑": EngineeringDomain.ARCHITECTURE,
            "结构": EngineeringDomain.STRUCTURE,
            "消防": EngineeringDomain.FIRE_PROTECTION,
            "给排水": EngineeringDomain.WATER_SUPPLY,
            "暖通": EngineeringDomain.HVAC,
            "电气": EngineeringDomain.ELECTRICAL,
        }

        domain = domain_map.get(drawing_type, EngineeringDomain.ARCHITECTURE)
        clauses = self.kb.get_review_checklist(domain)

        return [
            {
                "clause_id": c.clause_id,
                "content": c.content,
                "keywords": c.keywords,
                "scope": c.scope,
                "severity": "critical",
            } for c in clauses
        ]


# 全局单例
_specs = SpecsAdapter()

def get_specs_adapter() -> SpecsAdapter:
    return _specs
