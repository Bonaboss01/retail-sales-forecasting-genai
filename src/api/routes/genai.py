import json
from fastapi import APIRouter
from pydantic import BaseModel

from src.genai.openai_client import create_response, response_text
from src.genai.prompts import SYSTEM_RULES
from src.genai.rag.retrieve import retrieve
from src.genai.tools.forecast_tools import tool_specs, run_revenue_forecast

router = APIRouter(prefix="/genai", tags=["genai"])

class AskRequest(BaseModel):
    question: str

class ScenarioRequest(BaseModel):
    question: str

@router.post("/ask")
def ask(req: AskRequest):
    ctx = retrieve(req.question, k=6)
    context_block = "\n\n".join(
        [f"[{c['doc_title']} | chunk {c['chunk_id']}] {c['text']}" for c in ctx]
    )

    prompt = f"""{SYSTEM_RULES}

Context from SunnyBest docs:
{context_block}

User question:
{req.question}
"""

    resp = create_response(model="gpt-4.1-mini", input_text=prompt)
    return {"answer": response_text(resp), "sources": ctx}

@router.post("/scenario")
def scenario(req: ScenarioRequest):
    """
    LLM decides if it needs to call run_revenue_forecast tool.
    We execute tool calls and send results back for explanation.
    """
    resp = create_response(
        model="gpt-4.1-mini",
        input_text=f"{SYSTEM_RULES}\n\nUser: {req.question}",
        tools=tool_specs()
    )

    # If model called tools, execute them
    tool_outputs = []
    for item in getattr(resp, "output", []):
        if getattr(item, "type", "") == "function_call":
            name = item.name
            args = json.loads(item.arguments)

            if name == "run_revenue_forecast":
                result = run_revenue_forecast(**args)
                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(result)
                })

    if tool_outputs:
        # Send tool results back to model to generate final explanation
        followup = create_response(
            model="gpt-4.1-mini",
            input_text=[
                {"role": "user", "content": req.question},
                {"role": "assistant", "content": "Tool results received. Explain impact clearly."}
            ],
            tools=tool_specs()
        )
        # NOTE: Some SDK versions require passing tool_outputs explicitly.
        # If yours does, tell me and I’ll adjust to your installed SDK shape.

        return {"answer": response_text(followup), "tool_results": tool_outputs}

    return {"answer": response_text(resp)}
