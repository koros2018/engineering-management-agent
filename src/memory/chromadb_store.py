"""
memory/chromadb_store.py - ChromaDB 长期记忆

提供向量数据库存储：
- 用户对话历史向量化
- 项目特征向量
- 知识库索引
- 相似查询
"""

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────
# ChromaDB Store
# ─────────────────────────────────────────────────────────────────

class ChromaDBStore:
    """
    ChromaDB 长期记忆存储

    功能：
    - 存储对话历史向量
    - 存储项目特征向量
    - 相似查询
    - 自动过期清理
    """

    def __init__(self, persist_dir: str = None):
        if persist_dir is None:
            persist_dir = Path(__file__).parent.parent.parent / "data" / "chromadb"
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = None
        self._collections: Dict[str, Any] = {}

    @property
    def client(self):
        if self._client is None:
            import chromadb
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=chromadb.config.Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )
        return self._client

    def get_collection(self, name: str, metadata: Dict = None):
        """获取或创建 collection"""
        if name not in self._collections:
            try:
                self._collections[name] = self.client.get_collection(name)
            except Exception:
                self._collections[name] = self.client.create_collection(
                    name=name,
                    metadata=metadata or {"description": f"EMA {name} collection"},
                )
        return self._collections[name]

    # ── 对话历史存储 ─────────────────────────────────────────

    def add_conversation(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_id: str = "main",
        metadata: Dict = None,
    ):
        """
        添加对话到历史向量库

        Args:
            session_id: 会话ID
            role: user/agent
            content: 对话内容
            agent_id: 涉及的Agent
            metadata: 附加元数据
        """
        collection = self.get_collection(
            "conversations",
            {"description": "EMA对话历史向量库"}
        )

        import uuid
        doc_id = str(uuid.uuid4())

        collection.add(
            documents=[content],
            metadatas=[{
                "session_id": session_id,
                "role": role,
                "agent_id": agent_id,
                "timestamp": time.time(),
                **(metadata or {})
            }],
            ids=[doc_id],
        )

        return doc_id

    def search_conversations(
        self,
        query: str,
        session_id: str = None,
        limit: int = 5,
    ) -> List[Dict]:
        """
        搜索相关对话历史

        Args:
            query: 查询文本
            session_id: 可选，限制特定会话
            limit: 返回数量

        Returns:
            List[Dict]: 匹配的对话记录
        """
        collection = self.get_collection("conversations")

        where = {"session_id": session_id} if session_id else None

        try:
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                where=where,
            )
        except Exception:
            return []

        matches = []
        if results and results.get('documents'):
            for i, doc in enumerate(results['documents'][0]):
                matches.append({
                    'content': doc,
                    'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                    'distance': results['distances'][0][i] if results.get('distances') else None,
                })

        return matches

    # ── 项目特征存储 ─────────────────────────────────────────

    def add_project(
        self,
        project_id: str,
        project_data: Dict,
        vector: List[float] = None,
    ):
        """存储项目特征向量"""
        collection = self.get_collection(
            "projects",
            {"description": "EMA项目特征向量库"}
        )

        from src.utils import json_dumps
        content = json_dumps(project_data)

        collection.add(
            documents=[content],
            metadatas=[{
                "project_id": project_id,
                "timestamp": time.time(),
            }],
            ids=[project_id],
        )

        return project_id

    def search_projects(self, query: str, limit: int = 5) -> List[Dict]:
        """搜索相似项目"""
        collection = self.get_collection("projects")

        try:
            results = collection.query(
                query_texts=[query],
                n_results=limit,
            )
        except Exception:
            return []

        matches = []
        if results and results.get('documents'):
            from src.utils import json_loads
            for i, doc in enumerate(results['documents'][0]):
                try:
                    data = json_loads(doc)
                except Exception:
                    data = {"raw": doc}
                matches.append({
                    'data': data,
                    'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                    'distance': results['distances'][0][i] if results.get('distances') else None,
                })

        return matches

    # ── 知识库索引 ──────────────────────────────────────────

    def add_knowledge(
        self,
        doc_id: str,
        content: str,
        category: str,
        source: str = "",
        metadata: Dict = None,
    ):
        """添加知识文档到向量库"""
        collection = self.get_collection(
            "knowledge",
            {"description": "EMA知识库向量库"}
        )

        collection.add(
            documents=[content],
            metadatas=[{
                "category": category,
                "source": source,
                "timestamp": time.time(),
                **(metadata or {})
            }],
            ids=[doc_id],
        )

        return doc_id

    def search_knowledge(self, query: str, category: str = None, limit: int = 5) -> List[Dict]:
        """搜索知识库"""
        collection = self.get_collection("knowledge")

        where = {"category": category} if category else None

        try:
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                where=where,
            )
        except Exception:
            return []

        matches = []
        if results and results.get('documents'):
            for i, doc in enumerate(results['documents'][0]):
                matches.append({
                    'content': doc,
                    'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                    'distance': results['distances'][0][i] if results.get('distances') else None,
                })

        return matches

    # ── 管理 ───────────────────────────────────────────────

    def get_recent_conversations(
        self,
        session_id: str,
        limit: int = 10,
    ) -> List[Dict]:
        """
        获取指定会话的最近 N 条对话记录（按时间正序）。

        Returns:
            List[Dict]: [{"role": "user"|"assistant", "content": "...", "timestamp": ...}, ...]
        """
        collection = self.get_collection("conversations")
        try:
            results = collection.get(
                where={"session_id": session_id},
                limit=limit,
                include=["documents", "metadatas"],
            )
        except Exception:
            return []

        records = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"]):
                meta = results["metadatas"][i] if results.get("metadatas") else {}
                records.append({
                    "role": meta.get("role", "unknown"),
                    "content": doc,
                    "timestamp": meta.get("timestamp", 0),
                })

        # 按时间正序排列
        records.sort(key=lambda x: x["timestamp"])
        return records

    def reset(self):
        """重置所有 collection（危险操作）"""
        for name in list(self._collections.keys()):
            try:
                self.client.delete_collection(name)
            except Exception:
                pass
        self._collections.clear()

    def count(self, collection_name: str = "conversations") -> int:
        """获取 collection 文档数量"""
        try:
            col = self.get_collection(collection_name)
            return col.count()
        except Exception:
            return 0


# ─── 全局单例 ────────────────────────────────────────────────────

_chroma_store = None


def get_chroma_store() -> ChromaDBStore:
    global _chroma_store
    if _chroma_store is None:
        _chroma_store = ChromaDBStore()
    return _chroma_store