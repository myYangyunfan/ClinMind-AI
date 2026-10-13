"""Global configuration for ClinMind-AI system."""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent

# Auto-load .env file if present
ENV_FILE = BASE_DIR / ".env"
def _load_env_file():
    if not ENV_FILE.exists():
        return
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception as e:
        print(f"Warning loading .env: {e}")

_load_env_file()

# Server Config
HOST: str = os.getenv("HOST", "127.0.0.1")
PORT: int = int(os.getenv("PORT", "8000"))
DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

# Directories
STATIC_DIR: Path = BASE_DIR / "static"
DATA_DIR: Path = BASE_DIR / "app" / "data"

# LLM Configuration
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "deepseek")  # "deepseek" | "openai" | "custom" | "offline"
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-chat")

def is_online_llm_active() -> bool:
    if os.getenv("USE_OFFLINE_ONLY", "false").lower() in ("true", "1", "yes"):
        return False
    if LLM_PROVIDER == "deepseek" and DEEPSEEK_API_KEY:
        return True
    if LLM_PROVIDER in ("openai", "custom") and OPENAI_API_KEY:
        return True
    if bool(OPENAI_API_KEY or DEEPSEEK_API_KEY):
        return True
    return False

USE_ONLINE_LLM: bool = is_online_llm_active()

def save_llm_config(provider: str, api_key: str, base_url: str = "", model: str = ""):
    """Dynamically save LLM settings to .env and reload in-memory variables."""
    global LLM_PROVIDER, OPENAI_API_KEY, OPENAI_BASE_URL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, LLM_MODEL, USE_ONLINE_LLM
    
    LLM_PROVIDER = provider
    if provider == "deepseek":
        DEEPSEEK_API_KEY = api_key
        if base_url:
            DEEPSEEK_BASE_URL = base_url
        if model:
            LLM_MODEL = model
        else:
            LLM_MODEL = "deepseek-chat"
    elif provider in ("openai", "custom"):
        OPENAI_API_KEY = api_key
        if base_url:
            OPENAI_BASE_URL = base_url
        if model:
            LLM_MODEL = model
        else:
            LLM_MODEL = "gpt-4o-mini"
    elif provider == "offline":
        os.environ["USE_OFFLINE_ONLY"] = "true"
        USE_ONLINE_LLM = False
        env_lines = [
            "# ClinMind-AI Configuration",
            "USE_OFFLINE_ONLY=true",
            f"LLM_PROVIDER=offline",
            f"LLM_MODEL=offline-rule-engine",
        ]
        try:
            with open(ENV_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(env_lines) + "\n")
        except Exception as e:
            return False, f"写入本地配置失败: {e}"
        return True, "已切换为纯离线高仿真规则引擎模式 (免Key 100%全保真)"

    os.environ["USE_OFFLINE_ONLY"] = "false"
    USE_ONLINE_LLM = is_online_llm_active()

    # Write to .env
    env_lines = [
        "# ClinMind-AI Configuration",
        "USE_OFFLINE_ONLY=false",
        f"LLM_PROVIDER={LLM_PROVIDER}",
        f"DEEPSEEK_API_KEY={DEEPSEEK_API_KEY}",
        f"DEEPSEEK_BASE_URL={DEEPSEEK_BASE_URL}",
        f"OPENAI_API_KEY={OPENAI_API_KEY}",
        f"OPENAI_BASE_URL={OPENAI_BASE_URL}",
        f"LLM_MODEL={LLM_MODEL}",
    ]
    try:
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(env_lines) + "\n")
    except Exception as e:
        print(f"Error persisting .env: {e}")
        return False, f"写入本地配置失败: {e}"

    mode_str = "在线大模型协同" if USE_ONLINE_LLM else "离线规则仿真"
    return True, f"配置已成功保存并生效！当前运行模式: {mode_str}"

# Simulation Engine Parameters
VIRTUAL_TICK_RATE_HZ: float = 1.0  # 1Hz physiology tick
TIME_ACCELERATION_FACTOR: float = 1.0  # 1.0 = real-time, can accelerate virtual clock

# Fatal Red-line Medications (Contraindicated for Stanford Type A Aortic Dissection)
LETHAL_MEDICATION_KEYWORDS = [
    "aspirin", "阿司匹林",
    "ticagrelor", "替格瑞洛",
    "clopidogrel", "氯吡格雷",
    "heparin", "肝素",
    "alteplase", "阿替普酶", "rtpa", "rt-pa",
    "urokinase", "尿激酶",
    "tenecteplase", "替奈普酶",
    "bivalirudin", "比伐卢定",
    "warfarin", "华法林",
    "rivaroxaban", "利伐沙班"
]

# Targeted Anti-hypertensive & Heart Rate Lowering Medications
TARGET_DISSECTION_MEDICATIONS = [
    "esmolol", "艾司洛尔", "betaloc", "美托洛尔", "labetalol", "拉贝洛尔",
    "nitroprusside", "硝普钠", "nicardipine", "尼卡地平", "nitroglycerin", "硝酸甘油"
]
