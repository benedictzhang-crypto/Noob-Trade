import json
import re

import requests
from flask import Blueprint, current_app, jsonify, request


assistant_blueprint = Blueprint("assistant", __name__, url_prefix="/api/assistant")

ALLOWED_PAGES = {
    "dashboard": "Dashboard",
    "home dashboard": "Dashboard",
    "stock": "Stock Trade",
    "stock trade": "Stock Trade",
    "stock analysis": "Stock Trade",
    "trade": "Stock Trade",
    "crypto": "Crypto Trade",
    "crypto trade": "Crypto Trade",
    "portfolio": "Portfolio",
    "holdings": "Portfolio",
    "explore": "Explore",
    "watchlist": "Explore",
    "markets": "Markets",
    "market": "Markets",
    "settings": "Settings",
    "setting": "Settings",
    "myself": "Settings",
    "profile": "Settings",
    "account": "Settings",
    "more": "More",
    "admin": "Admin",
    "股票": "Stock Trade",
    "股票分析": "Stock Trade",
    "加密": "Crypto Trade",
    "设置": "Settings",
    "账户": "Settings",
    "仪表盘": "Dashboard",
    "投资组合": "Portfolio",
    "市场": "Markets",
    "探索": "Explore",
}

TRADING_WORDS = {
    "buy", "sell", "order", "market order", "limit order", "short",
    "买入", "卖出", "下单", "做空", "做多",
}

INDICATOR_ALIASES = {
    "moving average": "MA",
    "ma": "MA",
    "ema": "EMA",
    "exponential moving average": "EMA",
    "macd": "MACD",
    "bollinger bands": "BOLL",
    "bollinger band": "BOLL",
    "bollinger": "BOLL",
    "boll": "BOLL",
    "rsi": "RSI",
    "volume": "Vol",
    "vol": "Vol",
    "kdj": "KDJ",
    "open interest": "OI",
    "oi": "OI",
    "obv": "OBV",
    "on balance volume": "OBV",
    "布林带": "BOLL",
    "布林": "BOLL",
    "成交量": "Vol",
    "均线": "MA",
    "指数均线": "EMA",
}


def _normalize_text(value):
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def _base_intent(intent="chat", confidence=0.5, **kwargs):
    payload = {
        "intent": intent,
        "confidence": confidence,
        "page": None,
        "direction": None,
        "amount": None,
        "symbol": None,
        "indicators": [],
        "active": None,
        "threshold": None,
        "interval": None,
        "language": None,
        "reply": "",
    }
    payload.update(kwargs)
    return payload


def _extract_symbol(text):
    symbol_aliases = {
        "apple": "AAPL",
        "tesla": "TSLA",
        "nvidia": "NVDA",
        "microsoft": "MSFT",
        "amazon": "AMZN",
        "meta": "META",
        "google": "GOOGL",
        "alphabet": "GOOGL",
        "bitcoin": "BTC",
        "ethereum": "ETH",
        "solana": "SOL",
        "spy": "SPY",
    }
    for alias, symbol in symbol_aliases.items():
        if alias in text:
            return symbol

    blocked_words = {
        "stock", "stocks", "trade", "page", "go", "to", "open", "show", "search",
        "generate", "analyze", "analysis", "scroll", "down", "up", "more", "little",
        "dashboard", "portfolio", "market", "markets", "settings", "crypto", "explore",
    }
    tokens = re.findall(r"\b[a-zA-Z]{1,5}\b", text)
    for token in reversed(tokens):
        if token.lower() not in blocked_words:
            return token.upper()
    return None


def _extract_indicators(text):
    found = []
    for phrase, indicator in sorted(INDICATOR_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text):
            if indicator not in found:
                found.append(indicator)
    return found


def _rule_based_intent(transcript, context=None):
    text = _normalize_text(transcript)
    context = context or {}
    if not text:
        return _base_intent("unknown", 0.2, reply="I did not catch that.")

    if any(word in text for word in TRADING_WORDS):
        return _base_intent(
            "blocked_trading",
            0.98,
            reply="Voice trading orders are disabled. I can control analysis and navigation only.",
        )

    if any(phrase in text for phrase in ("sign out", "log out", "logout", "退出登录", "登出")):
        return _base_intent("sign_out", 0.96)

    indicators = _extract_indicators(text)
    selected_indicators = {
        str(item).upper()
        for item in context.get("selectedIndicators", [])
        if item
    }
    if indicators:
        if any(phrase in text for phrase in ("clear", "turn off all", "disable all", "清空", "关闭所有")):
            return _base_intent("clear_indicators", 0.98)

        if any(phrase in text for phrase in ("reset", "default", "restore", "重置", "默认")):
            return _base_intent("reset_indicators", 0.98)

        if any(phrase in text for phrase in ("only", "only use", "just", "只", "仅", "solo", "seulement")):
            return _base_intent("select_only_indicators", 0.96, indicators=indicators)

        if any(phrase in text for phrase in ("remove", "turn off", "disable", "unselect", "deselect", "取消", "关闭", "移除")):
            return _base_intent("set_indicator", 0.96, indicators=indicators, active=False)

        if any(phrase in text for phrase in ("select", "pick", "want", "use", "add", "include", "turn on", "enable", "choose", "选择", "勾选", "打开", "加入")):
            return _base_intent("set_indicator", 0.96, indicators=indicators, active=True)

        first_indicator = indicators[0]
        should_enable = first_indicator.upper() not in selected_indicators
        return _base_intent("set_indicator", 0.93, indicators=[first_indicator], active=should_enable)

    page_hits = []
    for phrase, page in ALLOWED_PAGES.items():
        if phrase in text:
            page_hits.append((len(phrase), page))
    if page_hits and any(verb in text for verb in ("go", "open", "show", "switch", "navigate", "进入", "打开", "切换")):
        page = sorted(page_hits, reverse=True)[0][1]
        return _base_intent("navigate", 0.96, page=page, reply=f"Opened {page}.")

    if any(phrase in text for phrase in ("top", "顶部", "haut", "arriba del todo")) and any(phrase in text for phrase in ("scroll", "go", "back", "到")):
        return _base_intent("scroll", 0.94, direction="top", amount="full")

    if any(phrase in text for phrase in ("bottom", "底部", "bas", "abajo del todo")) and any(phrase in text for phrase in ("scroll", "go", "到")):
        return _base_intent("scroll", 0.94, direction="bottom", amount="full")

    scrollish = any(phrase in text for phrase in ("scroll", "scorll", "scrool", "move", "page", "滚动", "下滑", "上滑"))
    if scrollish and any(phrase in text for phrase in ("down", "lower", "下", "abajo", "bas")):
        amount = "small" if any(phrase in text for phrase in ("little", "bit", "一点", "un poco", "un peu")) else "normal"
        return _base_intent("scroll", 0.94, direction="down", amount=amount)

    if scrollish and any(phrase in text for phrase in ("up", "higher", "上", "arriba", "haut")):
        amount = "small" if any(phrase in text for phrase in ("little", "bit", "一点", "un poco", "un peu")) else "normal"
        return _base_intent("scroll", 0.94, direction="up", amount=amount)

    if any(phrase in text for phrase in ("scan", "扫描", "scanner", "escanear")) and any(phrase in text for phrase in ("watchlist", "star", "favorite", "自选", "星标")):
        match = re.search(r"(\d{1,3}(?:\.\d+)?)\s*(?:%|percent)?", text)
        threshold = float(match.group(1)) if match else None
        return _base_intent("scan_watchlist", 0.92, threshold=threshold)

    if any(phrase in text for phrase in ("star", "favorite", "favourite", "watchlist", "星标", "自选", "收藏")):
        is_remove = any(phrase in text for phrase in ("remove", "delete", "unstar", "cancel", "取消", "移除", "删除"))
        symbol = _extract_symbol(text) or context.get("symbol")
        if symbol:
            return _base_intent("set_star", 0.94, symbol=symbol, active=not is_remove)

    if any(phrase in text for phrase in ("generate", "analyze", "analyse", "生成", "分析")):
        return _base_intent("generate", 0.86, symbol=_extract_symbol(text))

    if any(phrase in text for phrase in ("search", "quote", "price", "look up", "搜索", "查询", "价格")):
        return _base_intent("search", 0.86, symbol=_extract_symbol(text))

    return _base_intent("chat", 0.45)


def _intent_schema():
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "navigate", "scroll", "generate", "search", "set_indicator",
                    "select_only_indicators", "clear_indicators", "reset_indicators",
                    "scan_watchlist", "set_star", "set_interval", "sign_out", "language",
                    "help", "chat", "blocked_trading", "unknown",
                ],
            },
            "confidence": {"type": "number"},
            "page": {"type": ["string", "null"]},
            "direction": {"type": ["string", "null"], "enum": ["up", "down", "top", "bottom", None]},
            "amount": {"type": ["string", "null"], "enum": ["small", "normal", "large", "full", None]},
            "symbol": {"type": ["string", "null"]},
            "indicators": {"type": "array", "items": {"type": "string"}},
            "active": {"type": ["boolean", "null"]},
            "threshold": {"type": ["number", "null"]},
            "interval": {"type": ["string", "null"]},
            "language": {"type": ["string", "null"], "enum": ["en", "zh", "es", "fr", None]},
            "reply": {"type": "string"},
        },
        "required": [
            "intent", "confidence", "page", "direction", "amount", "symbol",
            "indicators", "active", "threshold", "interval", "language", "reply",
        ],
    }


def _extract_openai_text(payload):
    if isinstance(payload, dict) and payload.get("output_text"):
        return payload["output_text"]

    for item in payload.get("output", []) if isinstance(payload, dict) else []:
        for content in item.get("content", []) if isinstance(item, dict) else []:
            if isinstance(content, dict) and content.get("text"):
                return content["text"]
    return ""


def _openai_intent(transcript, context):
    api_key = current_app.config.get("OPENAI_API_KEY")
    if not api_key:
        return None

    prompt = {
        "transcript": transcript,
        "context": context,
        "allowedPages": ["Dashboard", "Stock Trade", "Crypto Trade", "Portfolio", "Explore", "Markets", "Settings", "More", "Admin"],
        "allowedIndicators": ["MA", "EMA", "MACD", "BOLL", "RSI", "Vol", "KDJ", "OI", "OBV"],
        "rules": [
            "Return one UI command intent only.",
            "Do not place trading orders. Buy/sell/order requests must be blocked_trading.",
            "If the user asks to go to stock trade page, return navigate page Stock Trade.",
            "Do not treat words like stock, trade, page, dashboard, portfolio, settings as stock tickers.",
            "Indicator names are strong entities. RSI alone should toggle/select RSI. I want RSI should select RSI. Remove RSI should unselect RSI.",
            "Star/favorite/watchlist commands should return set_star with the ticker or current context symbol.",
            "Use scroll only when the transcript clearly asks for scrolling or a follow-up scroll.",
        ],
    }
    body = {
        "model": current_app.config.get("ASSISTANT_INTENT_MODEL", "gpt-4o-mini"),
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "You are Noob Trade's cloud intent router. Output strict JSON matching the schema. No prose outside JSON.",
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": json.dumps(prompt, ensure_ascii=False)}],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "noob_trade_voice_intent",
                "strict": True,
                "schema": _intent_schema(),
            }
        },
    }
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=float(current_app.config.get("ASSISTANT_INTENT_TIMEOUT_SECONDS", 3.5)),
    )
    response.raise_for_status()
    raw_text = _extract_openai_text(response.json())
    if not raw_text:
        return None
    parsed = json.loads(raw_text)
    return parsed if isinstance(parsed, dict) else None


@assistant_blueprint.route("/intent", methods=["POST"])
def parse_intent():
    payload = request.get_json(silent=True) or {}
    transcript = str(payload.get("transcript") or "").strip()
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}

    rule_intent = _rule_based_intent(transcript, context)
    if rule_intent["confidence"] >= 0.92:
        return jsonify({"source": "rules", "intent": rule_intent})

    try:
        cloud_intent = _openai_intent(transcript, context)
        if cloud_intent and float(cloud_intent.get("confidence") or 0) >= 0.5:
            return jsonify({"source": "openai", "intent": cloud_intent})
    except Exception as error:
        current_app.logger.warning("Cloud assistant intent failed: %s", error)

    return jsonify({"source": "rules", "intent": rule_intent})
