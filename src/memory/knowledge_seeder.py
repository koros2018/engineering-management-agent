"""
memory/knowledge_seeder.py - 知识库种子数据

预置常用工程规范到 ChromaDB knowledge collection，
让 RAG 检索在项目初期就能返回有意义的结果。

用法:
    python -m memory.knowledge_seeder          # 种子数据
    python -m memory.knowledge_seeder --check    # 检查知识库状态
    python -m memory.knowledge_seeder --reset    # 重置后重新种子
"""

import json
import sys
import os

# 确保 src 在 path 里
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from memory.chromadb_store import get_chroma_store

# 种子数据文件路径（相对于项目根目录）
SEED_DATA_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'data', 'seed_knowledge.json'
)

def _load_seed_data() -> list:
    """从外部 JSON 文件加载种子数据"""
    data_path = os.environ.get("EMA_SEED_DATA_PATH", SEED_DATA_PATH)
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # 兜底：文件不存在时返回空列表
    print(f"  ⚠️  种子数据文件不存在: {data_path}")
    return []


def seed_knowledge(reset: bool = False):
    """将种子数据写入 ChromaDB knowledge collection"""
    store = get_chroma_store()

    if reset:
        print("[reset] 清空知识库 collection...")
        store.reset()

    # 检查是否已有数据
    existing = store.count("knowledge")
    if existing > 0 and not reset:
        print(f"  ✅ 知识库已有 {existing} 条记录，跳过种子")
        return

    seed_data = _load_seed_data()
    if not seed_data:
        return

    print(f"  写入 {len(seed_data)} 条工程规范种子数据...")

    for doc in seed_data:
        store.add_knowledge(
            doc_id=doc["doc_id"],
            content=doc["content"],
            category=doc["category"],
            source=doc["source"],
        )

    total = store.count("knowledge")
    print(f"  ✅ 知识库种子完成，共 {total} 条记录")


def check_knowledge():
    """检查知识库状态"""
    store = get_chroma_store()

    print("═══════════════════════════════════════════")
    print("  知识库状态")
    print("═══════════════════════════════════════════")

    for name in ["conversations", "projects", "knowledge"]:
        count = store.count(name)
        print(f"  {name}: {count} 条")

    # 测试搜索
    print("\n  测试搜索：'消防疏散距离'")
    results = store.search_knowledge("消防疏散距离", limit=3)
    for r in results:
        print(f"    - {r['content'][:50]}... (dist: {r['distance']:.4f})")

    print("═══════════════════════════════════════════")


# ─── CLI ─────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--reset" in args:
        seed_knowledge(reset=True)
    elif "--check" in args:
        check_knowledge()
    else:
        seed_knowledge()
