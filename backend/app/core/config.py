"""应用配置：集中读取环境变量，避免散落在业务代码中。"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RULES_PATH = Path(os.getenv("RULES_PATH", str(BASE_DIR / "data" / "rules.yaml")))

APP_NAME = "合规哨兵 API"
APP_VERSION = "0.3.0"

# 环境标识：prod 时关闭 /docs 与 /openapi.json，对外契约只以 docs/openapi.yaml 为准
APP_ENV = os.getenv("APP_ENV", "dev").strip().lower()
IS_PROD = APP_ENV in {"prod", "production"}

DISCLAIMER = (
    "本工具仅提供内容风险自查参考，不构成法律意见，不替代平台审核，"
    "不保证发布结果。涉及具体法律问题请咨询专业律师。"
)

# 500 对外统一文案：不暴露堆栈与内部实现，堆栈只写服务端日志
INTERNAL_ERROR_MESSAGE = "服务暂时不可用，请稍后重试"
RATE_LIMIT_MESSAGE_TEMPLATE = "本次检测额度已用完，约 {minutes} 分钟后可再次检测"

MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "20000"))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "60"))
# 埋点与检测分开计配额：埋点量大且失败无用户可感知后果，共用配额会挤掉正常检测
EVENTS_RATE_LIMIT_PER_HOUR = int(os.getenv("EVENTS_RATE_LIMIT_PER_HOUR", "300"))

# 限流桶容量上限：被扫描器刷 IP 时先清理空桶、再淘汰最久未访问的桶，防内存无界增长
RATE_LIMIT_MAX_BUCKETS = int(os.getenv("RATE_LIMIT_MAX_BUCKETS", "5000"))

_DEFAULT_DEV_CORS_ORIGINS = ("http://127.0.0.1:8000", "http://localhost:8000")


def _parse_origins(raw: str) -> list[str]:
    return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]


# CORS 白名单：生产只允许环境变量里显式列出的域名；未配置时不放行任何跨域来源
CORS_ALLOW_ORIGINS = _parse_origins(
    os.getenv(
        "CORS_ALLOW_ORIGINS",
        "" if IS_PROD else ",".join(_DEFAULT_DEV_CORS_ORIGINS),
    )
)

# LLM 增强为可选项：未配置密钥时自动降级为模板建议
LLM_ENABLED = bool(os.getenv("LLM_API_KEY"))
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
# 2 秒是产品承诺的降级时限（docs/ARCHITECTURE.md 第 4 节），不得改大
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "2"))
