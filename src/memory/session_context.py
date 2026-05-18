"""
memory/session_context.py - 短期会话记忆

管理当前会话的上下文：
- 对话历史摘要
- 当前任务状态
- 临时数据
"""

import json
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────
# SessionContext
# ─────────────────────────────────────────────────────────────────

class SessionContext:
    """
    短期会话记忆

    管理：
    - session_id → 上下文
    - 对话历史（截断保留最近 N 条）
    - 当前活动任务
    - 临时文件路径
    """

    MAX_HISTORY = 50  # 保留最近50条消息

    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            storage_dir = Path(__file__).parent.parent.parent / "data" / "sessions"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 内存中的会话上下文
        self._sessions: Dict[str, Dict] = defaultdict(self._new_session)
        self._last_access: Dict[str, float] = {}

    def _new_session(self) -> Dict:
        return {
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'messages': [],
            'active_task': None,
            'data': {},
        }

    # ── 会话管理 ─────────────────────────────────────────────

    def get(self, session_id: str) -> Dict:
        """获取会话上下文"""
        self._last_access[session_id] = time.time()
        return self._sessions[session_id]

    def create(self, session_id: str = None) -> str:
        """创建新会话"""
        if session_id is None:
            session_id = f"session_{int(time.time() * 1000)}"
        self._sessions[session_id] = self._new_session()
        self._last_access[session_id] = time.time()
        return session_id

    def destroy(self, session_id: str):
        """销毁会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
        if session_id in self._last_access:
            del self._last_access[session_id]

    # ── 消息历史 ─────────────────────────────────────────────

    def add_message(self, session_id: str, role: str, content: str, metadata: Dict = None):
        """添加消息到历史"""
        session = self.get(session_id)
        session['messages'].append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {},
        })
        # 截断保留最近 N 条
        if len(session['messages']) > self.MAX_HISTORY:
            session['messages'] = session['messages'][-self.MAX_HISTORY:]
        session['last_updated'] = datetime.now().isoformat()

    def get_history(self, session_id: str, limit: int = None) -> List[Dict]:
        """获取对话历史"""
        session = self.get(session_id)
        history = session.get('messages', [])
        if limit:
            return history[-limit:]
        return history

    def clear_history(self, session_id: str):
        """清空对话历史"""
        session = self.get(session_id)
        session['messages'] = []
        session['last_updated'] = datetime.now().isoformat()

    # ── 任务状态 ─────────────────────────────────────────────

    def set_active_task(self, session_id: str, task_id: str, task_info: Dict = None):
        """设置当前活动任务"""
        session = self.get(session_id)
        session['active_task'] = {
            'task_id': task_id,
            'task_info': task_info or {},
            'started_at': datetime.now().isoformat(),
        }

    def get_active_task(self, session_id: str) -> Optional[Dict]:
        """获取当前活动任务"""
        session = self.get(session_id)
        return session.get('active_task')

    def clear_active_task(self, session_id: str):
        """清除当前活动任务"""
        session = self.get(session_id)
        session['active_task'] = None

    # ── 临时数据 ─────────────────────────────────────────────

    def set_data(self, session_id: str, key: str, value: Any):
        """存储临时数据"""
        session = self.get(session_id)
        session['data'][key] = value

    def get_data(self, session_id: str, key: str, default: Any = None) -> Any:
        """获取临时数据"""
        session = self.get(session_id)
        return session['data'].get(key, default)

    # ── 持久化 ─────────────────────────────────────────────

    def save(self, session_id: str):
        """将会话保存到磁盘"""
        session = self.get(session_id)
        path = self.storage_dir / f"{session_id}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(session, f, ensure_ascii=False, indent=2)

    def load(self, session_id: str) -> bool:
        """从磁盘加载会话"""
        path = self.storage_dir / f"{session_id}.json"
        if not path.exists():
            return False
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self._sessions[session_id] = json.load(f)
            self._last_access[session_id] = time.time()
            return True
        except Exception:
            return False

    def list_sessions(self) -> List[str]:
        """列出所有会话ID"""
        return list(self._sessions.keys())

    def cleanup_old_sessions(self, max_age_seconds: int = 86400):
        """清理超过 max_age 秒的会话"""
        now = time.time()
        to_delete = [
            sid for sid, last in self._last_access.items()
            if now - last > max_age_seconds
        ]
        for sid in to_delete:
            self.destroy(sid)


# ─── 全局单例 ────────────────────────────────────────────────────

_session_context = None


def get_session_context() -> SessionContext:
    global _session_context
    if _session_context is None:
        _session_context = SessionContext()
    return _session_context