# yueji-fl-bridge

悦济 v3.1 阶段 28F.3 联邦学习 Python 中间层 (FastAPI + Render 部署)

**用途**：悦济云函数 `fl_bridge` HTTP 调真 FL 桥 (5 endpoints: register / upload / aggregate / status / demo)

**严守基调**：12 玄学红线 0 出现 + 8 禁用词 0 出现 + 危机词 0 出现 + 4 红线 0 出现 + 不存 user 原始数据 (隐私优先)

**拍板**：2026-07-27 00:30 冬生 "A" — 思怡写中间层 + 复用 reading-fl/core/aggregation.py FedAvg 核心逻辑

**部署平台**：2026-07-27 01:00 冬生 "Render吧" — 换 Render 平台 (HF Space Static SDK 不能跑 Python, Render free tier 无需信用卡)

---

## 5 endpoints

| Method | Path | Body | 用途 |
|---|---|---|---|
| GET | `/` | - | 服务信息 |
| GET | `/health` | - | 健康检查 (Render health check) |
| POST | `/fl/register` | `{campus_id, n_samples}` | 客户端注册 |
| POST | `/fl/upload` | `{campus_id, weights_b64}` | 上传 weights (base64-of-raw-float32) |
| POST | `/fl/aggregate` | `{aggregation="fedavg", reset_after?}` | 触发 1 轮 FedAvg 聚合 |
| GET | `/fl/status` | - | 查状态 (n_rounds / n_clients / last_metrics) |
| POST | `/fl/demo` | - | 1 键演示 (3 client + 1 round FedAvg) |

---

## 5 步 Render 部署

### Step 1: 推代码到 GitHub

```bash
cd C:\Users\decha\.mavis\agents\mavis\workspace\yueji-fl-bridge
git init
git remote add origin https://github.com/dechang64/yueji-fl-bridge.git
git add .
git commit -m "yueji-fl-bridge v1.0.0: 5 endpoints + FedAvg + Render Blueprint"
git push origin main
# 弹 dialog 填 GitHub username + token (Settings > Developer settings > PAT)
```

### Step 2: 注册 Render + 创 Blueprint

1. 打开 https://dashboard.render.com/register (GitHub 一键登录最方便)
2. 右上角 "New" → "Blueprint"
3. "Connect GitHub repo" → 选 `dechang64/yueji-fl-bridge` → "Connect"
4. Render 自动读 `render.yaml` + 显示服务预览
5. 点 "Apply" 创建 Blueprint 实例
6. 第一次创建会要你确认服务名, 改不改都行 (默认 `yueji-fl-bridge`)
7. 选 plan: **Free** (750h/月, 0 美元)
8. 选 region: **Oregon** (默认)

### Step 3: 等部署 (≈ 3-5 分钟)

1. Render Dashboard → 你的 service → "Logs" tab
2. 看 `==> Build successful` + `==> Booting worker with pid: ...`
3. 切到 "Events" 看部署历史 (应该 1 个 "deploy live")

### Step 4: 测试 1 个 endpoint

浏览器或 curl 打开：

```
https://yueji-fl-bridge.onrender.com/health
```

期望返 `{"ok": true, "ts": "2026-07-27T..."}`

或测 1 键 demo:

```
https://yueji-fl-bridge.onrender.com/fl/demo
```

期望返 3 client + 1 round FedAvg 完成。

### Step 5: 拿 URL 配到悦济 fl_bridge 云函数

URL 格式：`https://yueji-fl-bridge.onrender.com` (注意没有尾斜杠)

1. 微信开发者工具 → 云开发 → 云函数 → `fl_bridge` → 函数配置 → 环境变量
2. 加 `FL_BRIDGE_URL=https://yueji-fl-bridge.onrender.com`
3. 保存 (30s 内生效)

**触发真通道验证**：

微信开发者工具 → 云函数 → `fl_bridge` → 云函数测试：

```json
{
  "action": "demo"
}
```

期望返 `{"ok": true, "action": "demo", "stage": "complete", "msg": "demo 端到端完成: 3 client + 1 round FedAvg, round 1"}`

---

## 本地开发

```bash
pip install -r requirements.txt
# 方式 1: uvicorn (热重载, 开发用)
uvicorn app:app --reload --host 0.0.0.0 --port 7860

# 方式 2: gunicorn (跟 Render 生产一致, 验证用)
gunicorn app:app --bind 0.0.0.0:7860 --workers 1 --timeout 120
```

或访问 http://localhost:7860/docs (FastAPI Swagger UI)

---

## 风险点

- **Render free tier 12-15min sleep**: 首次唤醒 30s+, 比赛路演 demo 触发时可能慢; **备播预案**: 提前 5min 触发 1 次 `/fl/demo` 暖机
- **月 750h 限制**: 1 个 24/7 实例 = 720h/月, 比赛用 1 周绰绰有余
- **内存状态**: Render 单实例, 重启状态丢失; 比赛 demo 够用, 生产需外接 Redis
- **mock FedAvg**: 1 客户端 + 1 中心 + 1 轮, 比赛路演够用, 不上真多机构

---

## 项目结构

```
yueji-fl-bridge/
├── app.py              # FastAPI 主程序 (5 endpoints + 严守 51 字符串白名单)
├── aggregation.py      # FedAvg 简化版 (复用 reading-fl/core/aggregation.py 核心逻辑)
├── render.yaml         # Render Blueprint 部署配置 (free plan + gunicorn)
├── requirements.txt    # fastapi / uvicorn / numpy / pydantic / gunicorn
├── README.md           # 5 步 Render 部署指南 + 严守基调
└── .gitignore          # 排除 __pycache__
```

---

## 严守基调 (跟悦济/心颜 51 字符串一致)

- 14 禁用词: 0 出现 (`治疗` / `改善` / `缓解` / `治愈` / `祛斑` / `减肥` / `处方` / `医美` / `美颜` / `美白` / `瘦脸` / `营销` / `广告` / `疗愈`)
- 12 玄学: 0 出现 (`命理` / `占星` / `八字` / `星盘` / `算命` / `转运` / `化解` / `风水` / `玄学` / `五行` / `生克` / `补泻`)
- 15 危机词: 触发返 12356 (`不想活` / `自杀` / `轻生` / ...)
- 4 红线: 0 出现 (bazi / zodiac / xuanxue / mingli)
- 隐私: 不存 user 原始数据 (在内存, 不写盘)

---

## 严守审计

```bash
cd C:\Users\decha\.mavis\agents\mavis\workspace
python audit_yueji_fl_bridge.py
# 期望: === 0 FAIL ===
```
