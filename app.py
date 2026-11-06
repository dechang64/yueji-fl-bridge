"""
yueji-fl-bridge: 悦济 v3.1 阶段 28F.2 联邦学习 Python 中间层
部署: Render (https://yueji-fl-bridge.onrender.com, free tier)
调用: 悦济云函数 fl_bridge 走 process.env.FL_BRIDGE_URL HTTP 调 5 endpoints

严守基调: 12 玄学红线 0 出现 + 8 禁用词 0 出现 + 危机词 0 出现 + 4 红线 0 出现 + 不存 user 原始数据
拍板 (2026-07-27 00:30 冬生 'A'): 思怡写中间层 + 复用 reading-fl/core/aggregation.py FedAvg
换平台 (2026-07-27 01:00 冬生 'Render吧'): HF Space Static SDK 不能跑 Python, 改 Render free tier

5 endpoints:
  POST /fl/register   {campus_id, n_samples}          → {campus_id, n_samples, registered_at}
  POST /fl/upload     {campus_id, weights_b64}         → {campus_id, upload_id, bytes_received}
  POST /fl/aggregate  {aggregation="fedavg", reset_after?} → {round_idx, n_clients, aggregated_at, global_weights_b64, global_metrics}
  GET  /fl/status                                       → {n_rounds, n_clients, last_round_at, last_metrics}
  POST /fl/demo                                         → {demo_id, n_clients, round_idx, aggregated_at, msg}
"""

import os
import sys
import uuid
import time
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, conint, constr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aggregation import fedavg_aggregate

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("yueji-fl-bridge")

app = FastAPI(
    title="yueji-fl-bridge",
    description="悦济 v3.1 联邦学习 Python 中间层 (Render 部署, 悦济 fl_bridge 云函数调用)",
    version="1.0.0",
)

# 跨域 (悦济云函数调没 cookie, CORS 放开)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS","*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 内存状态 (Render free 单实例, 比赛 demo 够用) ──
class FLState:
    def __init__(self):
        self.clients: Dict[str, dict] = {}  # campus_id -> {n_samples, registered_at}
        self.uploads: Dict[str, dict] = {}  # upload_id -> {campus_id, bytes_received, uploaded_at, weights_b64}
        self.rounds: List[dict] = []        # [{round_idx, n_clients, aggregated_at, global_metrics}]

    def reset(self):
        self.clients.clear()
        self.uploads.clear()
        self.rounds.clear()


state = FLState()


# ── Request/Response models ──
class RegisterRequest(BaseModel):
    campus_id: constr(max_length=64)
    n_samples: conint(ge=1, le=10_000_000)


class RegisterResponse(BaseModel):
    campus_id: str
    n_samples: int
    registered_at: str


class UploadRequest(BaseModel):
    campus_id: str
    weights_b64: str = Field(..., description="base64-of-raw-float32-buffer")


class UploadResponse(BaseModel):
    campus_id: str
    upload_id: str
    bytes_received: int


class AggregateRequest(BaseModel):
    aggregation: str = "fedavg"
    reset_after: bool = False


class AggregateResponse(BaseModel):
    round_idx: int
    n_clients: int
    aggregated_at: str
    global_weights_b64: str
    global_metrics: dict


class StatusResponse(BaseModel):
    n_rounds: int
    n_clients: int
    last_round_at: Optional[str]
    last_metrics: Optional[dict]


class DemoResponse(BaseModel):
    demo_id: str
    n_clients: int
    round_idx: int
    aggregated_at: str
    msg: str


# ── 健康检查 ──
@app.get("/")
def root():
    return {
        "service": "yueji-fl-bridge",
        "version": "1.0.0",
        "endpoints": ["/fl/register", "/fl/upload", "/fl/aggregate", "/fl/status", "/fl/demo"],
        "msg": "悦济 v3.1 联邦学习 Python 中间层",
    }


@app.get("/health")
def health():
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}


# ── 5 endpoints ──
@app.post("/fl/register", response_model=RegisterResponse)
def fl_register(req: RegisterRequest):
    state.clients[req.campus_id] = {
        "n_samples": req.n_samples,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    log.info(f"register: {req.campus_id}, n_samples={req.n_samples}")
    return RegisterResponse(
        campus_id=req.campus_id,
        n_samples=req.n_samples,
        registered_at=state.clients[req.campus_id]["registered_at"],
    )


@app.post("/fl/upload", response_model=UploadResponse)
def fl_upload(req: UploadRequest):
    if req.campus_id not in state.clients:
        raise HTTPException(status_code=400, detail=f"campus_id {req.campus_id} 未注册, 请先 /fl/register")
    if len(req.weights_b64) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="weights_b64 > 10MB, 太大")

    upload_id = str(uuid.uuid4())
    bytes_received = len(req.weights_b64)
    state.uploads[upload_id] = {
        "campus_id": req.campus_id,
        "bytes_received": bytes_received,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "weights_b64": req.weights_b64,
    }
    log.info(f"upload: {req.campus_id} -> upload_id={upload_id}, bytes={bytes_received}")
    return UploadResponse(
        campus_id=req.campus_id,
        upload_id=upload_id,
        bytes_received=bytes_received,
    )


@app.post("/fl/aggregate", response_model=AggregateResponse)
def fl_aggregate(req: AggregateRequest):
    if req.aggregation not in ("fedavg", "task_aware"):
        raise HTTPException(status_code=400, detail=f"aggregation 必须是 fedavg 或 task_aware, 当前: {req.aggregation}")

    if not state.uploads:
        raise HTTPException(status_code=400, detail="无 uploads, 请先 /fl/upload")

    # 取所有 uploads 的 weights + 对应 client 的 n_samples
    client_weights_b64 = []
    client_data_sizes = []
    for upload_id, u in state.uploads.items():
        client_weights_b64.append(u["weights_b64"])
        # 找对应 client 的 n_samples
        n = state.clients.get(u["campus_id"], {}).get("n_samples", 1)
        client_data_sizes.append(n)

    log.info(f"aggregate: {req.aggregation}, n_clients={len(client_weights_b64)}")

    # FedAvg
    try:
        result = fedavg_aggregate(client_weights_b64, client_data_sizes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"聚合失败: {e}")

    round_idx = len(state.rounds) + 1
    aggregated_at = datetime.now(timezone.utc).isoformat()
    state.rounds.append({
        "round_idx": round_idx,
        "n_clients": len(client_weights_b64),
        "aggregated_at": aggregated_at,
        "global_metrics": result["global_metrics"],
    })

    if req.reset_after:
        state.uploads.clear()

    return AggregateResponse(
        round_idx=round_idx,
        n_clients=len(client_weights_b64),
        aggregated_at=aggregated_at,
        global_weights_b64=result["global_weights_b64"],
        global_metrics=result["global_metrics"],
    )


@app.get("/fl/status", response_model=StatusResponse)
def fl_status():
    last = state.rounds[-1] if state.rounds else None
    return StatusResponse(
        n_rounds=len(state.rounds),
        n_clients=len(state.clients),
        last_round_at=last["aggregated_at"] if last else None,
        last_metrics=last["global_metrics"] if last else None,
    )


@app.post("/fl/demo", response_model=DemoResponse)
def fl_demo():
    """1 键演示: 内部生成 3 client + 随机 weights + 1 轮 FedAvg"""
    demo_id = f"demo-{int(time.time() * 1000)}"
    clients = [
        {"campus_id": f"{demo_id}-user-A", "n_samples": 100},
        {"campus_id": f"{demo_id}-user-B", "n_samples": 200},
        {"campus_id": f"{demo_id}-user-C", "n_samples": 300},
    ]

    # 1. register 3 clients
    for cli in clients:
        state.clients[cli["campus_id"]] = {
            "n_samples": cli["n_samples"],
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }

    # 2. upload 3 weights (deterministic LCG, 14*32=448 floats)
    import base64
    import numpy as np
    for i, cli in enumerate(clients):
        seed = i + 1
        s = seed
        arr = np.zeros(14 * 32, dtype=np.float32)
        for j in range(len(arr)):
            s = (s * 9301 + 49297) % 233280
            arr[j] = ((s / 233280) * 2 - 1) * 0.1
        weights_b64 = base64.b64encode(arr.tobytes()).decode("utf-8")
        upload_id = str(uuid.uuid4())
        state.uploads[upload_id] = {
            "campus_id": cli["campus_id"],
            "bytes_received": len(weights_b64),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "weights_b64": weights_b64,
        }

    # 3. aggregate
    client_weights_b64 = [u["weights_b64"] for u in state.uploads.values()]
    client_data_sizes = [state.clients[u["campus_id"]]["n_samples"] for u in state.uploads.values()]
    result = fedavg_aggregate(client_weights_b64, client_data_sizes)

    round_idx = len(state.rounds) + 1
    aggregated_at = datetime.now(timezone.utc).isoformat()
    state.rounds.append({
        "round_idx": round_idx,
        "n_clients": len(client_weights_b64),
        "aggregated_at": aggregated_at,
        "global_metrics": result["global_metrics"],
    })

    log.info(f"demo: {demo_id}, n_clients={len(clients)}, round={round_idx}")

    return DemoResponse(
        demo_id=demo_id,
        n_clients=len(clients),
        round_idx=round_idx,
        aggregated_at=aggregated_at,
        msg=f"demo 端到端完成: 3 client + 1 round FedAvg, round {round_idx}",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
