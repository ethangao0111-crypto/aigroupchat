from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json
import random
import time
import jieba
from typing import Dict, Any, List

app = FastAPI()

# 允许所有CORS请求，实际部署时应限制
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，实际部署时应指定前端的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件，用于提供 index.html
app.mount("/static_files", StaticFiles(directory="static_files"), name="static_files")

def now_ms():
    return int(time.time() * 1000)

class RoundResult:
    def __init__(self, model_id: str, round_index: int, structured: Dict[str, Any], latency_ms: int, ok: bool=True, err: str=""):
        self.model_id = model_id
        self.round_index = round_index
        self.structured = structured
        self.latency_ms = latency_ms
        self.ok = ok
        self.err = err

# ---------- Mock 模型（免费演示用） ----------
class MockModelAdapter:
    def __init__(self, model_id: str, style_hint: str):
        self.model_id = model_id
        self.style_hint = style_hint

    async def call_json(self, prompt: str, timeout_s: float = 10.0) -> Dict[str, Any]:
        # 模拟网络延迟与轻微风格差异
        await asyncio.sleep(random.uniform(0.2, 0.8))
        
        prompt_obj = json.loads(prompt)
        
        if prompt_obj.get("type") == "round1":
            return {
                "question": prompt_obj["question"],
                "understanding": f"已理解核心问题与边界，风格：{self.style_hint}",
                "conclusion": f"基于{self.style_hint}，建议采用分层编排与裁判融合。",
                "reasoning": ["并行获取多答案", "二轮互评修正", "裁判融合定稿"],
                "evidence": ["暂无可直接验证的证据（示例）"],
                "confidence": random.randint(55, 75)
            }
        elif prompt_obj.get("type") == "round2":
            peers = prompt_obj["peer_conclusions"]
            # 模拟根据peer conclusions进行修订
            revised_conclusion = f"结合{self.style_hint}与他方意见，采用可跳过第二轮的自适应策略。"
            for model_id, conc in peers.items():
                if model_id != self.model_id and random.random() > 0.5: # 模拟采纳部分意见
                    revised_conclusion += f" 并参考了{model_id}的'{conc[:10]}...'观点。"
            
            return {
                "peer_review": {
                    "pros": ["结构清晰", "可扩展"],
                    "cons": ["证据不足", "成本未量化"],
                    "to_verify": ["接口超时策略有效性", "成本控制效果"]
                },
                "revised_final": {
                    "conclusion": revised_conclusion,
                    "reasons": ["降低成本", "保证一致性"],
                    "verifiable_points": ["相似度阈值>0.8时跳过二轮", "超时即早停"],
                    "confidence": random.randint(60, 80)
                }
            }
        elif prompt_obj.get("type") == "judge":
            cands = prompt_obj["candidates"]
            # 简单融合：选置信度最高者为主，合并可验证点
            best = None
            for k, v in cands.items():
                if v and ("confidence" in v):
                    if best is None or v["confidence"] > best["confidence"]:
                        best = v
            merged_points = []
            for v in cands.values():
                if v and v.get("verifiable_points"):
                    merged_points.extend(v["verifiable_points"])
            merged_points = list(dict.fromkeys(merged_points))[:6]
            
            final_conclusion = best["conclusion"] if best else "综合采用多数一致结论。"
            
            return {
                "final_answer": {
                    "conclusion": final_conclusion,
                    "reasons": ["一致性最佳", "可验证点明确"],
                    "verifiable_points": merged_points or ["进行小范围实验验证"],
                    "confidence": best["confidence"] if best else 65
                },
                "adopt_discard_rationale": "采纳置信度高且理由充分的方案，舍弃重复与无依据部分。",
                "differences_explained": ["在是否跳过第二轮与超时策略上存在细微差异"],
                "uncertainties": ["不同问题类型对阈值的适配性"],
                "next_steps": ["灰度测试阈值", "记录成本与延迟作为反馈"]
            }
        return {}

# ---------- 关键词提取和相似度判断 (简化版) ----------
def extract_keywords(text: str) -> List[str]:
    # 使用jieba进行中文分词
    # 移除停用词等高级功能可在实际应用中添加
    words = [word.strip() for word in jieba.lcut(text) if len(word.strip()) > 1]
    return list(set(words))

def calculate_keyword_similarity(text1: str, text2: str) -> float:
    keywords1 = set(extract_keywords(text1))
    keywords2 = set(extract_keywords(text2))
    
    if not keywords1 and not keywords2:
        return 1.0 # 都为空，认为完全相似
    
    intersection = len(keywords1.intersection(keywords2))
    union = len(keywords1.union(keywords2))
    
    if union == 0:
        return 0.0 # 避免除以零，如果都没有关键词则返回0
        
    return intersection / union

# ---------- Orchestrator ----------
class FreeMVPOrchestrator:
    def __init__(self):
        self.models = {
            "free_a": MockModelAdapter("free_a", "审慎风格"),
            "free_b": MockModelAdapter("free_b", "进取风格"),
            "free_c": MockModelAdapter("free_c", "保守风格"),
        }
        self.judge_id = "free_c"

    async def round1(self, question: str) -> Dict[str, RoundResult]:
        tasks = []
        for mid, adapter in self.models.items():
            payload = json.dumps({"type": "round1", "question": question})
            tasks.append(self._call_adapter(mid, adapter, payload, 1))
        results = await asyncio.gather(*tasks)
        return {r.model_id: r for r in results}

    async def round2(self, question: str, r1_structured: Dict[str, Any]) -> Dict[str, RoundResult]:
        peer_conclusions = {mid: data["conclusion"] for mid, data in r1_structured.items()}
        tasks = []
        for mid, adapter in self.models.items():
            payload = json.dumps({"type": "round2", "question": question, "peer_conclusions": peer_conclusions})
            tasks.append(self._call_adapter(mid, adapter, payload, 2))
        results = await asyncio.gather(*tasks)
        return {r.model_id: r for r in results}

    async def judge(self, question: str, candidates: Dict[str, Any]) -> RoundResult:
        adapter = self.models[self.judge_id]
        payload = json.dumps({"type": "judge", "question": question, "candidates": candidates})
        return await self._call_adapter(self.judge_id, adapter, payload, 99)

    async def _call_adapter(self, mid: str, adapter: MockModelAdapter, payload: str, round_idx: int) -> RoundResult:
        start = now_ms()
        try:
            data = await adapter.call_json(payload, timeout_s=12.0)
            return RoundResult(mid, round_idx, data, now_ms() - start, ok=True)
        except Exception as e:
            return RoundResult(mid, round_idx, {}, now_ms() - start, ok=False, err=str(e))

    async def run(self, question: str, enable_round2: bool=True, enable_judge: bool=True) -> Dict[str, Any]:
        full_result = {
            "round1": {},
            "round2": None,
            "judge": None,
            "similarities": {} # 用于存储相似度信息
        }

        # Round1
        r1_results = await self.round1(question)
        full_result["round1"] = {k: v.structured for k, v in r1_results.items()}
        r1_ok_structured = {k: v.structured for k, v in r1_results.items() if v.ok}

        # 计算Round1相似度
        model_ids = list(r1_ok_structured.keys())
        if len(model_ids) > 1:
            for i in range(len(model_ids)):
                for j in range(i + 1, len(model_ids)):
                    model1 = model_ids[i]
                    model2 = model_ids[j]
                    conclusion1 = r1_ok_structured[model1].get("conclusion", "")
                    conclusion2 = r1_ok_structured[model2].get("conclusion", "")
                    
                    similarity = calculate_keyword_similarity(conclusion1, conclusion2)
                    full_result["similarities"][f"r1_{model1}_vs_{model2}"] = round(similarity * 100, 2)
                    
                    # 按照用户需求，这里不直接跳过第二轮，而是记录相似度

        do_round2 = enable_round2 and len(r1_ok_structured) >= 2

        if do_round2:
            r2_results = await self.round2(question, r1_ok_structured)
            full_result["round2"] = {k: v.structured for k, v in r2_results.items()}
            r2_ok_structured = {k: v.structured for k, v in r2_results.items() if v.ok}
            
            # 计算Round2相似度 (可选，如果用户需要)
            # ... 类似Round1的相似度计算逻辑

        judge_res = {}
        if enable_judge:
            candidates = {}
            if full_result["round2"]: # 如果有第二轮结果，则用第二轮的改进稿作为候选
                for k, v in full_result["round2"].items():
                    candidates[k] = v.get("revised_final")
            else: # 无二轮时，用一轮结论构造候选
                for k, v in r1_ok_structured.items():
                    candidates[k] = {
                        "conclusion": v.get("conclusion"),
                        "reasons": v.get("reasoning", []),
                        "verifiable_points": v.get("evidence", []),
                        "confidence": v.get("confidence", 60)
                    }
            judge_r = await self.judge(question, candidates)
            if judge_r.ok:
                judge_res = judge_r.structured
            full_result["judge"] = judge_res

        return full_result

# FastAPI 路由
@app.get("/", response_class=FileResponse)
async def read_root():
    return FileResponse("static_files/index.html")

class DebateRequest(BaseModel):
    question: str
    enable_round2: bool = True
    enable_judge: bool = True

@app.post("/api/debate")
async def debate_endpoint(req: DebateRequest):
    if not req.question:
        return {"error": "Question is required"}, 400

    orchestrator = FreeMVPOrchestrator()
    result = await orchestrator.run(req.question, req.enable_round2, req.enable_judge)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
