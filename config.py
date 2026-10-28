import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

class Config:
    # 路径配置
    BASE_DIR = Path(__file__).resolve().parent
    raw_data_dir = os.getenv("DATA_DIR", "./omni_data")
    if os.path.isabs(raw_data_dir):
        DATA_DIR = Path(raw_data_dir).resolve()
    else:
        DATA_DIR = (BASE_DIR / raw_data_dir).resolve()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RECORDINGS_DIR = DATA_DIR / "recordings"
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR = DATA_DIR / "temp"
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # LLM 配置
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").strip()
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus").strip()

    # ASR 配置 (dashscope | volcengine | openai | mock)
    ASR_PROVIDER = os.getenv("ASR_PROVIDER", "dashscope").lower().strip()
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "").strip() or OPENAI_API_KEY

    # 火山引擎 (Volcengine) ASR 配置
    VOLC_APPID = os.getenv("VOLC_APPID", "").strip()
    VOLC_ACCESS_TOKEN = os.getenv("VOLC_ACCESS_TOKEN", "").strip()
    VOLC_RESOURCE_ID = os.getenv("VOLC_RESOURCE_ID", "volc.seedasr.sauc.duration").strip()
    VOLC_CLUSTER = os.getenv("VOLC_CLUSTER", "volcengine_input_common").strip()
    VOLC_ACCESS_KEY = os.getenv("VOLC_ACCESS_KEY", "").strip()
    VOLC_SECRET_KEY = os.getenv("VOLC_SECRET_KEY", "").strip()

    # 音频采集参数
    SAMPLE_RATE = 16000
    CHANNELS = 1
    CHUNK_DURATION_MS = 30
    CHUNK_SIZE = int(SAMPLE_RATE * (CHUNK_DURATION_MS / 1000.0))
    VAD_MODE = 2

    # 切片触发策略
    MAX_SLICE_SECONDS = float(os.getenv("MAX_SLICE_SECONDS", "300"))
    MIN_SILENCE_CUT_SECONDS = float(os.getenv("MIN_SILENCE_CUT_SECONDS", "120"))
    SILENCE_DURATION_SECONDS = float(os.getenv("SILENCE_DURATION_SECONDS", "3.0"))

    # 对讲交互热键与 TTS 配置 (默认采用笔记本免 Fn 的单键【右 Alt】)
    INTERCOM_KEY = os.getenv("INTERCOM_KEY", "Alt_R").strip()
    ENABLE_TTS = os.getenv("ENABLE_TTS", "true").lower() in ("1", "true", "yes")

    @classmethod
    def get_intercom_display_key(cls) -> str:
        k = cls.INTERCOM_KEY.lower().strip()
        if k in ("alt_r", "right_alt", "right alt", "右alt"):
            return "右 Alt"
        return cls.INTERCOM_KEY
    TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge-tts").lower().strip() # edge-tts | volcengine
    TTS_VOICE = os.getenv("TTS_VOICE", "zh-CN-YunxiNeural").strip()
    VOLC_TTS_VOICE_TYPE = os.getenv("VOLC_TTS_VOICE_TYPE", "BV001_streaming").strip()
    VOLC_TTS_CLUSTER = os.getenv("VOLC_TTS_CLUSTER", "volcano_tts").strip()

    @classmethod
    def has_llm_key(cls) -> bool:
        return bool(cls.OPENAI_API_KEY)

    @classmethod
    def has_asr_key(cls) -> bool:
        if cls.ASR_PROVIDER == "dashscope":
            return bool(cls.DASHSCOPE_API_KEY)
        elif cls.ASR_PROVIDER == "volcengine":
            return bool(cls.VOLC_APPID and (cls.VOLC_ACCESS_TOKEN or cls.VOLC_ACCESS_KEY))
        elif cls.ASR_PROVIDER == "openai":
            return bool(cls.OPENAI_API_KEY)
        return False
