"""
memory/sensenova_embedding.py - 商汤云 Embedding 适配器

使用商汤云 (SenseNova) API 替代 NVIDIA API 做 ChromaDB embedding。
商汤云 API 兼容 OpenAI /embeddings 接口。

环境变量：
    SENSENOVA_API_KEY: 商汤云 API Key（必填）
    SENSENOVA_EMBEDDING_MODEL: embedding 模型名（默认: nova-embedding-stable）

用法：
    from memory.sensenova_embedding import SensenovaEmbeddingFunction

    embedding_fn = SensenovaEmbeddingFunction()
    collection = client.create_collection(
        name="my_collection",
        embedding_function=embedding_fn,
    )
"""

import json
import os
import socket
import urllib.error
import urllib.request
from typing import List, Union

# ─── 配置 ──────────────────────────────────────────────────

SENSENOVA_BASE_URL = os.environ.get("SENSENOVA_BASE_URL", "https://token.sensenova.cn/v1")
SENSENOVA_API_KEY = os.environ.get("SENSENOVA_API_KEY", "")
SENSENOVA_EMBEDDING_MODEL = os.environ.get("SENSENOVA_EMBEDDING_MODEL", "nova-embedding-stable")

# ─── API 调用 ────────────────────────────────────────────────

def _call_embeddings_api(texts: List[str], model: str = SENSENOVA_EMBEDDING_MODEL) -> List[List[float]]:
    """
    调用商汤云 embedding API（OpenAI 兼容格式）

    返回: 每个文本对应的 embedding 向量列表
    """
    socket_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(60)
        url = f"{SENSENOVA_BASE_URL}/embeddings"
        payload = json.dumps({
            "model": model,
            "input": texts,
            "encoding_format": "float",
        }).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SENSENOVA_API_KEY}",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            # OpenAI 兼容返回格式: {"data": [{"embedding": [...], "index": 0}, ...]}
            data = result.get("data", [])
            # 按 index 排序确保顺序一致
            data.sort(key=lambda x: x.get("index", 0))
            return [item["embedding"] for item in data]
    except Exception as e:
        raise RuntimeError(f"商汤云 Embedding API 调用失败: {e}") from e
    finally:
        socket.setdefaulttimeout(socket_timeout)


# ─── ChromaDB Embedding Function 接口 ──────────────────────

class SensenovaEmbeddingFunction:
    """
    商汤云 Embedding Function，适配 ChromaDB 的 embedding_function 接口。

    ChromaDB 调用方式:
        embedding_fn(documents: List[str]) -> List[List[float]]

    示例:
        ef = SensenovaEmbeddingFunction()
        vectors = ef(["这是一个测试", "另一个文档"])
    """

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        base_url: str = None,
    ):
        self.api_key = api_key or SENSENOVA_API_KEY
        self.model = model or SENSENOVA_EMBEDDING_MODEL
        self.base_url = base_url or SENSENOVA_BASE_URL

        if not self.api_key:
            raise ValueError(
                "商汤云 API Key 未配置。请设置环境变量 SENSENOVA_API_KEY。"
            )

    def __call__(self, documents: List[str]) -> List[List[float]]:
        """
        将文档列表转换为 embedding 向量。

        Args:
            documents: 文本列表

        Returns:
            每个文本对应的 embedding 向量列表
        """
        if not documents:
            return []

        # 商汤云 API 每次最多支持 2048 个输入，这里分批处理
        batch_size = 100  # 安全批次大小
        all_embeddings = []

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            embeddings = _call_embeddings_api(batch, self.model)
            all_embeddings.extend(embeddings)

        return all_embeddings


# ─── 便捷函数 ────────────────────────────────────────────────

def get_embedding(text: str) -> List[float]:
    """获取单个文本的 embedding 向量"""
    result = _call_embeddings_api([text])
    return result[0] if result else []


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """计算两个向量的余弦相似度"""
    import math
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
