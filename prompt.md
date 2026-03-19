# 多模型辩论式问答系统（免费版 MVP）需求文档

本文档面向个人初级开发者，聚焦“零服务器或最低成本”实现路径：优先使用免费额度/试用模型、尽量不付服务器费、快速上线可用原型。含范围、流程、功能、非功能、数据结构、接口、提示词、测试、里程碑与风控。

## 1. 目标与范围

- 目标：在不付或尽可能少付基础设施费用前提下，实现“多模型两轮答复 + 裁判总结”的最小可用产品（MVP）。
- 范围：
  - 支持一次提交一个问题。
  - 第一轮：并行调用3个免费或有免费额度的模型（可替代为同平台不同模型/同模型不同配置）。
  - 第二轮：将第一轮三份结果摘要回传给三模型，获得改进稿。
  - 裁判：由指定模型输出融合总结。
  - 输出结构化：结论、理由、差异点、不确定性、后续验证建议。
- 非范围（MVP暂不做）：
  - 用户账号体系、计费。
  - 大规模并发与消息队列。
  - 持久化数据库（使用本地文件或浏览器存储）。
  - 复杂监控/可观测性。
  - 敏感领域专业合规审查（以通用免责声明替代）。

## 2. 约束与前提

- 成本约束：
  - 尽量使用免费额度或免费模型。
  - 无服务器或最低配置：本地运行/无后端模式，或单点轻量后端（可选）。
- 技术前提：
  - 以浏览器前端 + 第三方模型SDK/网关的免费层方式优先（避免服务器费用）。
  - 若某些模型不支持前端直连（出于密钥安全考虑），则使用本地运行后端转发。
- 安全前提：
  - 不在前端暴露私有API密钥；若需密钥，采用本地后端或仅用于自用环境。
  - 输出添加通用免责声明，禁止敏感内容。

## 3. 用户故事与用例

- 用户作为求解者，输入问题，期望：
  - 看到3个模型第一轮独立答案。
  - 看到3个模型在参考其他答案后的改进稿（第二轮）。
  - 看到裁判的最终融合答复，含差异解释与验证建议。
  - 快速响应（理想<15秒；免费模型可能更长，接受<30-60秒）。

主要用例：
1) 提交问题 → 系统并行获取三份初稿 → 汇总 → 发起二轮 → 收集改进稿 → 调用裁判 → 展示结果页。
2) 用户可选择“仅一轮+裁判（省流量）”或“完整两轮”。

## 4. 流程设计

- 步骤0：输入清洗（去空、长度控制）
- 步骤1（Round1）：
  - 并行调用三模型（Free A / Free B / Free C），同一提示模板，要求输出JSON。
- 步骤2（Round2）：
  - 抽取三份核心结论摘要，作为上下文传给三模型，要求给出改进稿JSON。
  - 可配置跳过第二轮（当第一轮高度一致时）。
- 步骤3（Judge）：
  - 将三份改进稿作为输入，交给裁判模型，输出融合答复JSON。
- 步骤4：结果展示与保存（本地浏览器或本地文件）。

可选优化（省钱逻辑）：
- 若第一轮3份结论相似度高（规则：结论文本相似度>0.8或关键词重合度>70%），跳过第二轮，直接裁判。
- 若任意模型超时，使用其余成功结果继续流程。

## 5. 功能需求

- F1 输入与提交
  - 文本输入框，限制10–8000字符；超长截断提示。
  - 开关：是否执行第二轮；是否执行裁判。
- F2 多模型第一轮调用
  - 支持配置3个免费模型端点/适配器。
  - 并发请求，支持超时（默认8–15秒）与重试（1次）。
- F3 第二轮互评/改进
  - 自动构造摘要上下文（只取必要字段，控制Token）。
  - 并发请求，支持超时。
- F4 裁判整合
  - 指定裁判模型（可与三模型之一相同）。
  - 输出结构化JSON：结论、理由、差异、置信度、不确定项、验证建议。
- F5 结果展示
  - 三栏查看第一轮答案；三栏查看第二轮改进稿；裁判总结在顶部。
  - 提供“复制最终答案”按钮。
- F6 基本配置
  - 在页面本地保存配置（如LocalStorage）：是否启用二轮、超时、裁判模型选择。
- F7 错误与超时处理
  - 单模型失败不影响整体；UI中以状态标注。
- F8 免责声明与安全提示
  - 在结果页底部展示通用免责声明。

## 6. 非功能需求

- 性能：单次完整流程目标<30秒（取决于免费模型速率）。
- 可用性：失败可重试；失败不致崩溃。
- 安全：不存储用户隐私到远端；本地存储可清除。

## 7. 数据结构（JSON Schema 草案）

- Round1 输出（每模型）：
  - {
    "question": string,
    "understanding": string,
    "conclusion": string,
    "reasoning": [string],
    "evidence": [string],
    "confidence": number (0-100)
  }

- Round2 输出（每模型）：
  - {
    "peer_review": {
      "pros": [string],
      "cons": [string],
      "to_verify": [string]
    },
    "revised_final": {
      "conclusion": string,
      "reasons": [string],
      "verifiable_points": [string],
      "confidence": number
    }
  }

- 裁判输出（单个）：
  - {
    "final_answer": {
      "conclusion": string,
      "reasons": [string],
      "verifiable_points": [string],
      "confidence": number
    },
    "adopt_discard_rationale": string,
    "differences_explained": [string],
    "uncertainties": [string],
    "next_steps": [string]
  }

## 8. 接口设计（MVP 两种形态）

- 形态A：纯前端（无后端）——前提是使用不暴露密钥的公共免费推理端点或代理工具（如无需密钥的公开演示端点）。若无法满足，转B。
- 形态B：本地后端（单文件 FastAPI）+ 前端页面
  - POST `/api/debate`
    - 入参：{ "question": string, "enable_round2": boolean, "enable_judge": boolean }
    - 出参：{
      "round1": { "<model>": Round1JSON, ... },
      "round2": { "<model>": Round2JSON, ... } | null,
      "judge": JudgeJSON | null,
      "meta": { "latency_ms": number, "partial_failures": [string] }
    }

## 9. 提示词模板（MVP版）

- Round1 模板（对三模型一致）：
  - 角色：你是严谨、简洁、可验证的回答者。请严格输出JSON，不要额外文本。
  - 内容：
    - 字段：
      - question
      - understanding
      - conclusion
      - reasoning (数组，3–6条)
      - evidence (数组；若无可写“暂无可直接验证的证据”)
      - confidence (0-100)
    - 要求：语言简洁，限制总字数，避免空话。

- Round2 模板：
  - 角色：你是审稿人兼作者，请在阅读其他模型结论摘要后修正自己方案。严格输出JSON。
  - 字段：
    - peer_review.pros / cons / to_verify
    - revised_final.conclusion / reasons / verifiable_points / confidence
  - 注意：指出具体可验证点，去除重复与不一致内容。

- 裁判模板：
  - 角色：你是裁判与编辑，请融合候选改进稿，优先可验证、逻辑一致、覆盖核心要点，严格输出JSON。
  - 字段：
    - final_answer.conclusion / reasons / verifiable_points / confidence
    - adopt_discard_rationale
    - differences_explained
    - uncertainties
    - next_steps

## 10. 免费实现建议与模型选择策略

- 策略优先级：
  - 优先找免费试用/免费层的多模型接入平台或开源推理网关的公开Demo端点。
  - 若必须使用密钥，将三家均换为同一家平台的多个免费/低价模型，或同一模型不同“温度/系统提示”做出差异性，避免多平台账号成本与密钥暴露。
- 过渡方案（节省成本）：
  - Round1：3个“免费或同平台免费档模型/配置差异”。
  - Round2：仅在第一轮分歧大时执行。
  - 裁判：优先使用免费档；若超配额则退化为本地规则裁判（简单投票+打分）。

## 11. MVP 原型实现（本地运行，单文件）

说明：以下代码用“Mock模型适配器”替代真实调用，零成本跑通流程，界面为命令行。你后续只需把`MockModelAdapter`替换为真实免费模型调用即可。代码完整可运行。

```python
# filename: mvp_free_debate.py
# 运行：python mvp_free_debate.py

import asyncio
import json
import random
import time
from typing import Dict, Any, List

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
        # 简化：根据style_hint生成不同“结论口吻”
        if '"type":"round1"' in prompt:
            return {
                "question": json.loads(prompt)["question"],
                "understanding": "已理解核心问题与边界",
                "conclusion": f"基于{self.style_hint}，建议采用分层编排与裁判融合。",
                "reasoning": ["并行获取多答案", "二轮互评修正", "裁判融合定稿"],
                "evidence": ["暂无可直接验证的证据（示例）"],
                "confidence": random.randint(55, 75)
            }
        elif '"type":"round2"' in prompt:
            body = json.loads(prompt)
            peers = body["peer_conclusions"]
            return {
                "peer_review": {
                    "pros": ["结构清晰", "可扩展"],
                    "cons": ["证据不足", "成本未量化"],
                    "to_verify": ["接口超时策略有效性", "成本控制效果"]
                },
                "revised_final": {
                    "conclusion": f"结合{self.style_hint}与他方意见，采用可跳过第二轮的自适应策略。",
                    "reasons": ["降低成本", "保证一致性"],
                    "verifiable_points": ["相似度阈值>0.8时跳过二轮", "超时即早停"],
                    "confidence": random.randint(60, 80)
                }
            }
        elif '"type":"judge"' in prompt:
            body = json.loads(prompt)
            cands = body["candidates"]
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
            return {
                "final_answer": {
                    "conclusion": best["conclusion"] if best else "综合采用多数一致结论。",
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
        # Round1
        r1 = await self.round1(question)
        r1_ok = {k: v.structured for k, v in r1.items() if v.ok}

        # 判断是否跳过Round2
        do_round2 = enable_round2 and len(r1_ok) >= 2

        r2_ok = {}
        if do_round2:
            r2 = await self.round2(question, r1_ok)
            r2_ok = {k: v.structured for k, v in r2.items() if v.ok}

        judge_res = {}
        if enable_judge:
            candidates = {}
            if r2_ok:
                for k, v in r2_ok.items():
                    candidates[k] = v.get("revised_final")
            else:
                # 无二轮时，用一轮结论构造候选
                for k, v in r1_ok.items():
                    candidates[k] = {
                        "conclusion": v.get("conclusion"),
                        "reasons": v.get("reasoning", []),
                        "verifiable_points": v.get("evidence", []),
                        "confidence": v.get("confidence", 60)
                    }
            judge_r = await self.judge(question, candidates)
            if judge_r.ok:
                judge_res = judge_r.structured

        # 汇总
        return {
            "round1": {k: v.structured for k, v in r1.items()},
            "round2": r2_ok if do_round2 else None,
            "judge": judge_res if enable_judge else None
        }

# ---------- CLI ----------
async def main():
    print("=== 免费版多模型辩论式问答 MVP ===")
    q = input("请输入你的问题：").strip()
    orchestrator = FreeMVPOrchestrator()
    result = await orchestrator.run(q, enable_round2=True, enable_judge=True)
    print("\n--- 裁判最终答复 ---")
    print(json.dumps(result.get("judge", {}), ensure_ascii=False, indent=2))
    print("\n--- 第一轮 ---")
    print(json.dumps(result.get("round1", {}), ensure_ascii=False, indent=2))
    if result.get("round2") is not None:
        print("\n--- 第二轮 ---")
        print(json.dumps(result.get("round2", {}), ensure_ascii=False, indent=2))
    print("\n提示：此为Mock演示。接入真实免费模型时，替换MockModelAdapter.call_json逻辑。")

if __name__ == "__main__":
    asyncio.run(main())
```

接入真实免费模型时的改造点：
- 把`MockModelAdapter`替换为对应免费接口的适配器（保留`call_json(prompt)`签名）。
- 让模型直接输出JSON（通过提示要求），后端不再需要复杂解析。
- 如需前端页面，可用一个静态`<html>`+`<textarea>`+`<button>`+`fetch`接后端`/api/debate`，把结果以`<pre>`渲染。

## 12. 验收标准（MVP）

- 功能：
  - 能在本地完成一次完整“Round1→Round2→Judge”流程。
  - 单模型失败不阻塞整体，仍能产出裁判结果。
- 质量：
  - 输出为有效JSON，字段完整。
  - 用3个不同风格（或不同配置）的模型能产生可比差异。
- 性能：
  - 绝大多数请求在60秒内完成（免费端点可能较慢）。
- 可用性：
  - 具备重试与超时。
  - 有通用免责声明。

## 13. 风险与缓解

- 免费接口不稳定/速率限制：
  - 增加退化策略：跳过第二轮、减少上下文长度、降低并发。
- 密钥安全：
  - 优先无后端+公共免费端点（若合规）；否则后端本地运行，不暴露密钥到前端。
- 质量不稳定：
  - 要求JSON输出+Schema校验；裁判做一致性检查。

## 14. 里程碑

- M1（1–2天）：跑通Mock版本（上面代码）。
- M2（2–4天）：接入1个免费模型适配器，调通JSON输出。
- M3（5–7天）：接入3个免费/免费额度模型或同平台不同配置；完成二轮与裁判。
- M4（1–2天）：增加前端极简页、免责声明、超时/重试、可选跳过第二轮。

## 15. 免责声明（模板）

- 本系统基于多模型自动生成，仅供参考；不构成任何医疗、法律、金融等专业建议。输出可能存在不准确或过时信息，请在关键场景中进行独立验证。

如需，我可以在此MVP基础上提供：
- 前端极简页面`<html>`示例代码（调用本地后端、展示JSON结果）。
- 真实免费模型的`ModelAdapter`模板（按你选择的免费来源定制）。
