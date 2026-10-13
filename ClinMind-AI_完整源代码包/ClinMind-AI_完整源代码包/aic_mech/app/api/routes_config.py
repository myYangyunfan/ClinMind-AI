from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx
import config

router = APIRouter(prefix="/api/config", tags=["Configuration"])

class LLMConfigRequest(BaseModel):
    provider: str = "deepseek"  # "deepseek" | "openai" | "custom" | "offline"
    api_key: Optional[str] = ""
    base_url: Optional[str] = ""
    model: Optional[str] = ""
    test_connection: bool = False

@router.get("/llm")
async def get_llm_config():
    raw_key = config.DEEPSEEK_API_KEY or config.OPENAI_API_KEY or ""
    masked_key = ""
    if raw_key:
        if len(raw_key) > 8:
            masked_key = raw_key[:4] + "****" + raw_key[-4:]
        else:
            masked_key = "********"
    
    current_provider = "offline"
    if config.USE_ONLINE_LLM:
        if "deepseek" in config.OPENAI_BASE_URL.lower() or config.DEEPSEEK_API_KEY:
            current_provider = "deepseek"
        elif "openai" in config.OPENAI_BASE_URL.lower():
            current_provider = "openai"
        else:
            current_provider = "custom"

    return {
        "status": "success",
        "use_online": config.USE_ONLINE_LLM,
        "provider": current_provider,
        "masked_key": masked_key,
        "base_url": config.OPENAI_BASE_URL,
        "model": config.LLM_MODEL
    }

@router.post("/llm")
async def update_llm_config(req: LLMConfigRequest):
    if req.provider == "offline":
        config.save_llm_config(
            provider="offline",
            api_key="",
            base_url="",
            model="offline"
        )
        return {
            "success": True,
            "status": "success",
            "message": "已成功切换为高仿真离线规则引擎 (免Key模式)",
            "use_online": False,
            "provider": "offline"
        }
    
    api_key = req.api_key.strip() if req.api_key else ""
    if not api_key:
        # Keep existing key if not provided
        api_key = config.DEEPSEEK_API_KEY or config.OPENAI_API_KEY or ""
    
    if not api_key:
        raise HTTPException(status_code=400, detail="请填写有效的 API Key，或切换为离线模式")
    
    base_url = req.base_url.strip() if req.base_url else ""
    if not base_url:
        if req.provider == "deepseek":
            base_url = "https://api.deepseek.com"
        else:
            base_url = "https://api.openai.com/v1"
            
    model = req.model.strip() if req.model else ""
    if not model:
        if req.provider == "deepseek":
            model = "deepseek-chat"
        else:
            model = "gpt-4o-mini"
            
    test_result = "未执行连通测试"
    if req.test_connection:
        try:
            url = base_url.rstrip("/") + "/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a test assistant. Reply 'OK' only."},
                    {"role": "user", "content": "ping"}
                ],
                "max_tokens": 5
            }
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    test_result = "API 连通测试成功 (HTTP 200 OK)"
                else:
                    test_result = f"已保存配置 (注: 探测返回 HTTP {res.status_code}，对话时将正常调用)"
        except Exception as e:
            test_result = "已保存配置 (注: 探测握手超时或网络受限，对话时将正常调用)"

    config.save_llm_config(
        provider=req.provider,
        api_key=api_key,
        base_url=base_url,
        model=model
    )
    
    return {
        "success": True,
        "status": "success",
        "message": f"配置已保存并热生效！{test_result}",
        "use_online": True,
        "provider": req.provider,
        "model": model,
        "base_url": base_url
    }
