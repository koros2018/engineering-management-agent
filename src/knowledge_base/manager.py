"""
knowledge_base/manager.py — 知识库管理器

统一管理标准库的所有操作：
- 标准查询（按编号/名称/领域/层级）
- 强制条文提取
- 冲突检测
- 审查检查清单生成
- 统计报告
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .schema import (
    EngineeringDomain, MandatoryLevel, StandardLevel,
    Standard, StandardConflict, MandatoryClause, KnowledgeBaseStats,
)
from .taxonomy import CORE_STANDARDS, get_standards_by_domain, get_mandatory_standards
from .mandatory import MandatoryClauseExtractor, get_extractor
from .conflict import ConflictDetector, get_detector


class KnowledgeBase:
    """
    标准知识库管理器

    单一入口，管理所有知识库功能。
    """

    def __init__(self):
        self._standards: List[Standard] = list(CORE_STANDARDS)
        self._mandatory = get_extractor()
        self._conflict = get_detector()
        self._by_id: Dict[str, Standard] = {}
        self._by_code: Dict[str, Standard] = {}
        self._index_built = False

    def _ensure_index(self):
        """构建索引"""
        if self._index_built:
            return
        for s in self._standards:
            self._by_id[s.id] = s
            # 用纯数字编号作为 key
            code_key = ''.join(c for c in s.code if c.isdigit())
            self._by_code[code_key] = s
        self._index_built = True

    # ── 查询 ────────────────────────────────────────────────

    def get(self, standard_id: str) -> Optional[Standard]:
        self._ensure_index()
        return self._by_id.get(standard_id)

    def find(self, keyword: str) -> List[Standard]:
        """模糊搜索"""
        self._ensure_index()
        results = []
        kw = keyword.lower()
        for s in self._standards:
            if kw in s.code.lower() or kw in s.name.lower():
                results.append(s)
                continue
            for k in s.keywords:
                if kw in k.lower():
                    results.append(s)
                    break
        return results

    def list_by_domain(self, domain: EngineeringDomain) -> List[Standard]:
        return [s for s in self._standards if domain in s.domains]

    def list_mandatory(self) -> List[Standard]:
        return [s for s in self._standards if s.mandatory_level.is_mandatory]

    def list_active(self) -> List[Standard]:
        return [s for s in self._standards if s.is_active]

    def list_all(self) -> List[Standard]:
        return list(self._standards)

    # ── 强制条文 ────────────────────────────────────────────

    def get_mandatory_clauses(self, standard_id: str) -> List[MandatoryClause]:
        return self._mandatory.get_clauses(standard_id)

    def get_review_checklist(self, domain: EngineeringDomain) -> List[MandatoryClause]:
        standards = self.list_by_domain(domain)
        return self._mandatory.get_checklist(domain, standards)

    def to_review_rules(self) -> List[Dict]:
        """导出为审查规则"""
        return self._mandatory.to_review_rules(self._standards)

    # ── 冲突检测 ────────────────────────────────────────────

    def detect_conflicts(self) -> List[StandardConflict]:
        return self._conflict.detect_all(self._standards)

    def detect_version_conflict(self, code: str) -> Optional[str]:
        return self._conflict.detect_version(code)

    def get_conflict_report(self) -> Dict:
        return self._conflict.generate_report(self._standards)

    def get_effective(self, code: str) -> Optional[Standard]:
        return self._conflict.get_effective_standard(code, self._standards)

    # ── 统计 ────────────────────────────────────────────────

    def get_stats(self) -> KnowledgeBaseStats:
        """获取知识库统计"""
        by_level = {}
        by_domain = {}
        mandatory_count = 0
        mandatory_clause_count = 0
        active_count = 0
        expired_count = 0

        for s in self._standards:
            # 层级统计
            lv = s.level.value
            by_level[lv] = by_level.get(lv, 0) + 1

            # 领域统计
            for d in s.domains:
                by_domain[d.value] = by_domain.get(d.value, 0) + 1

            # 强制标准
            if s.mandatory_level.is_mandatory:
                mandatory_count += 1
                clauses = self._mandatory.get_clauses(s.id)
                mandatory_clause_count += len(clauses)

            # 有效/废止
            if s.is_active:
                active_count += 1
            else:
                expired_count += 1

        conflicts = self._conflict.detect_all(self._standards)

        return KnowledgeBaseStats(
            total_standards=len(self._standards),
            by_level=by_level,
            by_domain=by_domain,
            mandatory_standards=mandatory_count,
            mandatory_clauses=mandatory_clause_count,
            active_standards=active_count,
            expired_standards=expired_count,
            conflicts=len(conflicts),
            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

    def stats_summary(self) -> str:
        """生成可读的统计摘要"""
        s = self.get_stats()
        lines = [
            f"📚 标准知识库统计",
            f"━━━━━━━━━━━━━━━━━━━━━━━",
            f"标准总数: {s.total_standards}",
            f"  国标: {s.by_level.get('national', 0)}",
            f"  行标: {s.by_level.get('industry', 0)}",
            f"  有效: {s.active_standards} | 废止: {s.expired_standards}",
            f"",
            f"📋 强制性条文: {s.mandatory_clauses} 条",
            f"   涉及 {s.mandatory_standards} 个强制标准",
            f"",
            f"🔗 已知冲突: {s.conflicts} 处",
            f"",
            f"📂 领域覆盖:",
        ]
        for d, c in sorted(s.by_domain.items(), key=lambda x: -x[1]):
            domain_label = EngineeringDomain(d).label if d in [e.value for e in EngineeringDomain] else d
            lines.append(f"   {domain_label}: {c} 个标准")
        return '\n'.join(lines)

    # ── 导入导出 ────────────────────────────────────────────

    def export_json(self, path: str):
        """导出为JSON"""
        data = {
            'standards': [
                {
                    'id': s.id,
                    'code': s.code,
                    'name': s.name,
                    'level': s.level.value,
                    'mandatory_level': s.mandatory_level.value,
                    'domains': [d.value for d in s.domains],
                    'keywords': s.keywords,
                    'summary': s.summary,
                    'current_version': s.current_version,
                    'mandatory_clauses': [
                        {
                            'clause_id': c.clause_id,
                            'content': c.content,
                            'keywords': c.keywords,
                            'scope': c.scope,
                        } for c in self._mandatory.get_clauses(s.id)
                    ],
                } for s in self._standards
            ],
            'conflicts': [
                {
                    'id': c.id,
                    'type': c.conflict_type.value,
                    'standards': f"{c.standard_a} vs {c.standard_b}",
                    'description': c.description,
                    'resolution': c.resolution,
                } for c in self._conflict.detect_all(self._standards)
            ],
            'generated_at': datetime.now().isoformat(),
        }
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2))


# 单例
_kb = None

def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
