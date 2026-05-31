"""
specs_adapter.py - EMA 国标知识库适配器（完全独立，零外部依赖）

功能：
1. 索引并加载 EMA 自有国标知识库
2. 全文搜索（按规范编号/名称/类别/关键词）
3. 智能推荐（根据图纸类型推荐相关规范）
4. 规范条款提取（按章节号精确查询）
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any

# EMA 自有知识库路径
EMA_KB = Path(__file__).parent.parent.parent / "data" / "standards"


class SpecsAdapter:
    """EMA 国标规范适配器"""

    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._index: List[Dict] = []
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        self._load_all()
        self._loaded = True

    def _load_all(self):
        """加载 EMA 自有知识库"""
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
        """获取知识库统计"""
        self._ensure_loaded()
        categories = {}
        total_sections = 0
        total_requirements = 0
        for item in self._index:
            cat = item["category"]
            categories[cat] = categories.get(cat, 0) + 1
            total_sections += item["sections_count"]
            total_requirements += item["requirements_count"]

        return {
            "total_standards": len(self._index),
            "total_categories": len(categories),
            "total_sections": total_sections,
            "total_requirements": total_requirements,
            "categories": sorted(categories.items(), key=lambda x: -x[1]),
            "standards": sorted(self._index, key=lambda x: x["code"]),
        }

    def search(self, query: str, category: str = None, limit: int = 20) -> List[Dict]:
        """搜索规范"""
        self._ensure_loaded()
        keywords = query.lower().split()
        results = []

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
                })

        results.sort(key=lambda x: -x["score"])
        return results[:limit]

    def get_spec(self, code: str) -> Optional[Dict]:
        """获取完整规范"""
        self._ensure_loaded()
        return self._cache.get(code)

    def recommend(self, drawing_type: str, drawing_category: str = None) -> List[Dict]:
        """根据图纸类型推荐规范"""
        self._ensure_loaded()

        TYPE_TO_CATEGORY = {
            "建筑": ["建筑", "消防工程", "绿色建筑", "建筑节能", "施工管理", "质量管理"],
            "结构": ["结构工程", "质量管理", "安全管理"],
            "给排水": ["给排水", "消防工程", "绿色建筑"],
            "电气": ["电气工程", "消防工程", "BIM/信息化"],
            "暖通": ["消防工程", "建筑节能", "绿色建筑"],
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
        for code, data in self._cache.items():
            cat = data.get("category", "")
            if cat in categories:
                results.append({
                    "code": code,
                    "name": data["spec_name"],
                    "category": cat,
                    "priority": "强制" if any(r.get("mandatory") for r in data.get("key_requirements", [])) else "推荐",
                })

        return results[:10]

    def lookup_section(self, code: str, section_num: str) -> Optional[Dict]:
        """精确查找规范条款"""
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
        """获取强制条款"""
        spec = self.get_spec(code)
        if not spec:
            return []
        return [r for r in spec.get("key_requirements", []) if r.get("mandatory")]


# 全局单例
_specs = SpecsAdapter()

def get_specs_adapter() -> SpecsAdapter:
    return _specs
