# yueji-fl-bridge aggregation
# 悦济 v3.1 阶段 28F.2: 简化 FedAvg, 复用 reading-fl/core/aggregation.py 核心逻辑
# 严守基调: 12 玄学红线 0 出现 + 不存 user 原始数据 (隐私优先)

import numpy as np
from typing import List, Dict, Optional


def fedavg_aggregate(
    client_weights_b64: List[str],
    client_data_sizes: List[int],
) -> Dict:
    """
    FedAvg 聚合 (简化版, 比赛路演用)
    复用 reading-fl/core/aggregation.py FedAvg 类的核心逻辑 (按 n_samples 加权平均)
    """
    if not client_weights_b64:
        raise ValueError("client_weights_b64 不能为空")
    if len(client_weights_b64) != len(client_data_sizes):
        raise ValueError("client_weights_b64 和 client_data_sizes 长度不一致")

    # 1. decode base64 → float32 buffer → 1D vector (简化: 假设 1D weights)
    client_arrays = []
    for b64 in client_weights_b64:
        raw = np.frombuffer(_b64decode(b64), dtype=np.float32)
        client_arrays.append(raw)

    n_features = client_arrays[0].shape[0]
    for arr in client_arrays:
        if arr.shape[0] != n_features:
            raise ValueError(
                f"客户端 weights 维度不一致: 期望 {n_features}, 实际 {arr.shape[0]}"
            )

    # 2. 按 n_samples 加权平均 (跟 reading-fl FedAvg 一致)
    total = sum(client_data_sizes)
    if total <= 0:
        raise ValueError("client_data_sizes 总和必须 > 0")

    aggregated = np.zeros(n_features, dtype=np.float32)
    for arr, n in zip(client_arrays, client_data_sizes):
        aggregated += (n / total) * arr

    # 3. 简单 metrics (mock: 跟 samples 线性关系, 比赛 demo 够用)
    n_clients = len(client_arrays)
    global_metrics = {
        "n_clients": n_clients,
        "total_samples": total,
        "avg_weight_norm": float(np.linalg.norm(aggregated) / max(n_clients, 1)),
    }

    # 4. encode → base64
    global_weights_b64 = _b64encode(aggregated.tobytes())

    return {
        "global_weights_b64": global_weights_b64,
        "global_metrics": global_metrics,
    }


def _b64decode(s: str) -> bytes:
    import base64
    return base64.b64decode(s.encode("utf-8"))


def _b64encode(b: bytes) -> str:
    import base64
    return base64.b64encode(b).decode("utf-8")
