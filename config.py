import sys
import os
from pathlib import Path
from dotenv import load_dotenv

if getattr(sys, 'frozen', False):
    APP_ROOT = Path(sys.executable).resolve().parent
else:
    APP_ROOT = Path(__file__).resolve().parent

# 加载 .env 文件 (优先可执行程序根目录)
for p in [APP_ROOT / ".env", Path.cwd() / ".env", Path(__file__).parent / ".env"]:
    if p.exists():
        load_dotenv(dotenv_path=p, override=True)
        break

class Config:
    # 路径配置
    BASE_DIR = APP_ROOT
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

    # 切片触发策略 (针对会议室自然语流调优：30s~90s 动态短句切割，大幅降低 ASR 尾部截断与长音频丢词)
    MAX_SLICE_SECONDS = float(os.getenv("MAX_SLICE_SECONDS", "90"))
    MIN_SILENCE_CUT_SECONDS = float(os.getenv("MIN_SILENCE_CUT_SECONDS", "30"))
    SILENCE_DURATION_SECONDS = float(os.getenv("SILENCE_DURATION_SECONDS", "2.0"))

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
    # TTS 三角色音色配置 (会议男声 vs 全网科普女声 vs 敏捷研发架构师男声)
    TTS_VOICE_MEETING = os.getenv("TTS_VOICE_MEETING", "zh-CN-YunxiNeural").strip()        # 会议记录播报：云希 (自然男声，严肃严谨)
    TTS_VOICE_GENERAL = os.getenv("TTS_VOICE_GENERAL", "zh-CN-XiaoxiaoNeural").strip()      # 全网通识播报：晓晓 (知性女声，温和科普)
    TTS_VOICE_INSTRUCTION = os.getenv("TTS_VOICE_INSTRUCTION", "zh-CN-YunjianNeural").strip() # 敏捷指令播报：云健 (沉稳干练架构师男声)

    VOLC_TTS_VOICE_TYPE = os.getenv("VOLC_TTS_VOICE_TYPE", "BV001_streaming").strip()
    VOLC_TTS_VOICE_MEETING = os.getenv("VOLC_TTS_VOICE_MEETING", "BV002_streaming").strip() # 火山通用男声
    VOLC_TTS_VOICE_GENERAL = os.getenv("VOLC_TTS_VOICE_GENERAL", "BV001_streaming").strip() # 火山通用女声
    VOLC_TTS_VOICE_INSTRUCTION = os.getenv("VOLC_TTS_VOICE_INSTRUCTION", "BV004_streaming").strip() # 火山技术男声
    VOLC_TTS_CLUSTER = os.getenv("VOLC_TTS_CLUSTER", "volcano_tts").strip()

    # 敏捷高频自进化与改进指令模式开关 (支持口语指令"改进一下"直通工单入库)
    ENABLE_DEV_INSTRUCTION_MODE = os.getenv("ENABLE_DEV_INSTRUCTION_MODE", "true").lower() in ("1", "true", "yes")

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

    @classmethod
    def save_settings(cls, updates: dict) -> bool:
        """
        持久化更新配置项到 .env 文件，并实时同步 cls 属性和 os.environ
        """
        for k, v in updates.items():
            str_val = str(v).strip()
            os.environ[k] = str_val
            if hasattr(cls, k):
                orig = getattr(cls, k)
                if isinstance(orig, bool):
                    setattr(cls, k, str_val.lower() in ("1", "true", "yes"))
                elif isinstance(orig, int):
                    try:
                        setattr(cls, k, int(str_val))
                    except ValueError:
                        setattr(cls, k, str_val)
                elif isinstance(orig, float):
                    try:
                        setattr(cls, k, float(str_val))
                    except ValueError:
                        setattr(cls, k, str_val)
                else:
                    setattr(cls, k, str_val)

        # 写入 .env 文件
        target_env = cls.BASE_DIR / ".env"
        lines = []
        if target_env.exists():
            try:
                lines = target_env.read_text(encoding="utf-8").splitlines()
            except Exception:
                try:
                    lines = target_env.read_text(encoding="gbk", errors="ignore").splitlines()
                except Exception:
                    lines = []

        updated_keys = set()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") or not stripped or "=" not in stripped:
                new_lines.append(line)
                continue
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                updated_keys.add(key)
            else:
                new_lines.append(line)

        # 追加未在原文件中出现的新配置项
        for k, v in updates.items():
            if k not in updated_keys:
                new_lines.append(f"{k}={v}")

        try:
            target_env.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            return True
        except Exception as e:
            print(f"[Config] 保存 .env 失败: {e}")
            return False

