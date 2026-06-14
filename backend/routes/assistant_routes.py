import json
import re

import requests
from flask import Blueprint, current_app, jsonify, request, session

from extensions import db
from models.auth import AssistantIntentFeedback


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
    "user guide": "User Guide",
    "guide": "User Guide",
    "manual": "User Guide",
    "help page": "User Guide",
    "how noobtrade works": "User Guide",
    "how noob trade works": "User Guide",
    "how it works": "User Guide",
    "learn more": "User Guide",
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
    "用户手册": "User Guide",
    "操作手册": "User Guide",
    "使用说明": "User Guide",
    "怎么用": "User Guide",
    "如何使用": "User Guide",
    "工作原理": "User Guide",
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

INTERVAL_ALIASES = {
    "1 minute": "1min",
    "one minute": "1min",
    "one min": "1min",
    "1 min": "1min",
    "1分钟": "1min",
    "一分钟": "1min",
    "5 minute": "5min",
    "five minute": "5min",
    "5 min": "5min",
    "five min": "5min",
    "5分钟": "5min",
    "五分钟": "5min",
    "15 minute": "15min",
    "fifteen minute": "15min",
    "15 min": "15min",
    "fifteen min": "15min",
    "15分钟": "15min",
    "十五分钟": "15min",
    "30 minute": "30min",
    "thirty minute": "30min",
    "30 min": "30min",
    "thirty min": "30min",
    "30分钟": "30min",
    "三十分钟": "30min",
    "半小时": "30min",
    "hourly": "1hour",
    "one hour": "1hour",
    "1 hour": "1hour",
    "60 minute": "1hour",
    "1小时": "1hour",
    "一小时": "1hour",
    "小时线": "1hour",
    "daily": "daily",
    "day chart": "daily",
    "one day": "daily",
    "日线": "daily",
    "每日": "daily",
    "5 day": "5day",
    "five day": "5day",
    "5 days": "5day",
    "five days": "5day",
    "5日": "5day",
    "五日": "5day",
    "五天": "5day",
    "weekly": "weekly",
    "week chart": "weekly",
    "one week": "weekly",
    "周线": "weekly",
    "一周": "weekly",
    "2 week": "2week",
    "two week": "2week",
    "2 weeks": "2week",
    "two weeks": "2week",
    "两周": "2week",
    "2周": "2week",
    "monthly": "monthly",
    "month chart": "monthly",
    "one month": "monthly",
    "月线": "monthly",
    "一月": "monthly",
}

ALLOWED_INTENTS = {
    "navigate", "scroll", "generate", "search", "set_indicator",
    "select_only_indicators", "clear_indicators", "reset_indicators",
    "scan_watchlist", "set_star", "adjust_probability",
    "summarize_probability", "open_historical_pattern", "open_news",
    "load_more_patterns", "set_interval", "sign_out", "language",
    "open_full_market", "view_more_market",
    "greeting", "help", "chat", "blocked_trading", "unknown",
}

SHORT_REPLY_LIBRARY = {
    "en": {
        "ready": "Ready.",
        "blocked_trading": "Manual trading only.",
        "unknown": "I could not understand. Please say it again.",
    },
    "zh": {
        "ready": "我在。",
        "blocked_trading": "请手动操作。",
        "unknown": "无法理解您说的，请再说一遍。",
    },
    "es": {
        "ready": "Listo.",
        "blocked_trading": "Operación manual solamente.",
        "unknown": "No entendí. Repítalo, por favor.",
    },
    "fr": {
        "ready": "Prêt.",
        "blocked_trading": "Trading manuel uniquement.",
        "unknown": "Je n'ai pas compris. Répétez, s'il vous plaît.",
    },
}

SYMBOL_ALIASES = {
    "aapl": "AAPL",
    "apl": "AAPL",
    "appl": "AAPL",
    "a p l": "AAPL",
    "a p p l": "AAPL",
    "apple": "AAPL",
    "iphone": "AAPL",
    "msft": "MSFT",
    "m s f t": "MSFT",
    "microsoft": "MSFT",
    "tsla": "TSLA",
    "tesla": "TSLA",
    "nvda": "NVDA",
    "nvidia": "NVDA",
    "amzn": "AMZN",
    "amazon": "AMZN",
    "meta": "META",
    "facebook": "META",
    "googl": "GOOGL",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "berkshire": "BRK.B",
    "berkshire hathaway": "BRK.B",
    "brkb": "BRK.B",
    "brk b": "BRK.B",
    "lilly": "LLY",
    "eli lilly": "LLY",
    "broadcom": "AVGO",
    "jpmorgan": "JPM",
    "jp morgan": "JPM",
    "chase": "JPM",
    "visa": "V",
    "exxon": "XOM",
    "exxon mobil": "XOM",
    "unitedhealth": "UNH",
    "united health": "UNH",
    "mastercard": "MA",
    "costco": "COST",
    "johnson and johnson": "JNJ",
    "home depot": "HD",
    "oracle": "ORCL",
    "procter gamble": "PG",
    "merck": "MRK",
    "netflix": "NFLX",
    "abbvie": "ABBV",
    "bank of america": "BAC",
    "coca cola": "KO",
    "coke": "KO",
    "advanced micro devices": "AMD",
    "chevron": "CVX",
    "pepsi": "PEP",
    "pepsico": "PEP",
    "salesforce": "CRM",
    "walmart": "WMT",
    "thermo fisher": "TMO",
    "accenture": "ACN",
    "cisco": "CSCO",
    "mcdonalds": "MCD",
    "mcdonald s": "MCD",
    "abbott": "ABT",
    "ibm": "IBM",
    "international business machines": "IBM",
    "general electric": "GE",
    "ge aerospace": "GE",
    "linde": "LIN",
    "disney": "DIS",
    "adobe": "ADBE",
    "servicenow": "NOW",
    "service now": "NOW",
    "intuit": "INTU",
    "qualcomm": "QCOM",
    "caterpillar": "CAT",
    "texas instruments": "TXN",
    "american express": "AXP",
    "amex": "AXP",
    "applied materials": "AMAT",
    "booking": "BKNG",
    "booking holdings": "BKNG",
    "uber": "UBER",
    "uber technologies": "UBER",
    "goldman": "GS",
    "goldman sachs": "GS",
    "bitcoin": "BTC",
    "btc": "BTC",
    "ethereum": "ETH",
    "eth": "ETH",
    "solana": "SOL",
    "sol": "SOL",
    "bnb": "BNB",
    "binance": "BNB",
    "xrp": "XRP",
    "ripple": "XRP",
    "doge": "DOGE",
    "dogecoin": "DOGE",
    "ada": "ADA",
    "cardano": "ADA",
    "trx": "TRX",
    "tron": "TRX",
    "avax": "AVAX",
    "avalanche": "AVAX",
    "link": "LINK",
    "chainlink": "LINK",
    "ton": "TON",
    "toncoin": "TON",
    "shib": "SHIB",
    "shiba inu": "SHIB",
    "dot": "DOT",
    "polkadot": "DOT",
    "bch": "BCH",
    "bitcoin cash": "BCH",
    "near": "NEAR",
    "ltc": "LTC",
    "litecoin": "LTC",
    "uni": "UNI",
    "uniswap": "UNI",
    "icp": "ICP",
    "apt": "APT",
    "aptos": "APT",
    "etc": "ETC",
    "ethereum classic": "ETC",
    "hbar": "HBAR",
    "hedera": "HBAR",
    "atom": "ATOM",
    "cosmos": "ATOM",
    "fil": "FIL",
    "filecoin": "FIL",
    "arb": "ARB",
    "arbitrum": "ARB",
    "op": "OP",
    "optimism": "OP",
    "sui": "SUI",
    "inj": "INJ",
    "injective": "INJ",
    "sushi": "SUSHI",
    "sushiswap": "SUSHI",
    "okb": "OKB",
    "o k b": "OKB",
    "spy": "SPY",
    "s p y": "SPY",
}


def _normalize_text(value):
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def _contains_phrase(text, phrase):
    normalized_phrase = _normalize_text(phrase)
    if not normalized_phrase:
        return False

    if re.search(r"[\u4e00-\u9fff]", normalized_phrase):
        return normalized_phrase in text

    return bool(re.search(rf"(?<![a-z0-9]){re.escape(normalized_phrase)}(?![a-z0-9])", text))


def _detect_reply_language(text="", context=None, payload=None):
    context = context if isinstance(context, dict) else {}
    payload = payload if isinstance(payload, dict) else {}

    raw_text = str(text or "")
    normalized_text = _normalize_text(raw_text)
    if re.search(r"[\u4e00-\u9fff]", raw_text):
        return "zh"
    if any(phrase in normalized_text for phrase in ("hola", "español", "espanol", "gracias", "ayuda", "abrir", "buscar", "escanear", "quiero", "necesito", "noticias")):
        return "es"
    if any(phrase in normalized_text for phrase in ("bonjour", "français", "francais", "merci", "aide", "ouvrir", "chercher", "scanner", "je veux", "j ai besoin", "nouvelles")):
        return "fr"

    for value in (
        payload.get("language"),
        context.get("language"),
    ):
        normalized = _normalize_text(value)
        if normalized in SHORT_REPLY_LIBRARY:
            return normalized

    return "en"


def _short_reply(key, language="en"):
    return SHORT_REPLY_LIBRARY.get(language, SHORT_REPLY_LIBRARY["en"]).get(
        key,
        SHORT_REPLY_LIBRARY["en"].get(key, ""),
    )


def _normalize_symbol_entity(value):
    text = _normalize_text(value)
    if not text:
        return None

    if text in SYMBOL_ALIASES:
        return SYMBOL_ALIASES[text]

    compact = re.sub(r"[^a-z0-9]", "", text)
    if compact in SYMBOL_ALIASES:
        return SYMBOL_ALIASES[compact]

    if compact:
        return compact.upper()
    return None


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
        "side": None,
        "value": None,
        "index": None,
        "interval": None,
        "language": None,
        "reply": "",
    }
    payload.update(kwargs)
    return payload


def _feedback_payload_from_intent(intent_payload):
    if not isinstance(intent_payload, dict):
        return {}

    return {
        "page": intent_payload.get("page"),
        "direction": intent_payload.get("direction"),
        "amount": intent_payload.get("amount"),
        "symbol": intent_payload.get("symbol"),
        "indicators": intent_payload.get("indicators") or [],
        "active": intent_payload.get("active"),
        "threshold": intent_payload.get("threshold"),
        "side": intent_payload.get("side"),
        "value": intent_payload.get("value"),
        "index": intent_payload.get("index"),
        "interval": intent_payload.get("interval"),
        "language": intent_payload.get("language"),
        "confidence": intent_payload.get("confidence"),
    }


def _extract_symbol(text):
    normalized_text = _normalize_text(text)
    framed_text = f" {normalized_text} "
    for alias, symbol in sorted(SYMBOL_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if f" {alias} " in framed_text:
            return symbol

    blocked_words = {
        "stock", "stocks", "trade", "page", "go", "to", "open", "show", "search",
        "generate", "analyze", "analysis", "scroll", "down", "up", "more", "little",
        "dashboard", "portfolio", "market", "markets", "settings", "crypto", "explore",
        "full", "board", "pool", "universe", "guide", "manual", "user", "learn",
    }
    tokens = re.findall(r"\b[a-zA-Z]{1,5}\b", text)
    for token in reversed(tokens):
        if token.lower() not in blocked_words:
            return _normalize_symbol_entity(token)
    return None


def _extract_indicators(text):
    found = []
    for phrase, indicator in sorted(INDICATOR_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text):
            if indicator not in found:
                found.append(indicator)
    return found


def _extract_interval(text):
    for phrase, interval in sorted(INTERVAL_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if phrase in text:
            return interval
    return None


def _extract_first_number(text):
    match = re.search(r"(\d{1,3}(?:\.\d+)?)", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _extract_ordinal_index(text):
    ordinal_words = {
        "first": 1,
        "one": 1,
        "second": 2,
        "two": 2,
        "third": 3,
        "three": 3,
        "fourth": 4,
        "four": 4,
        "fifth": 5,
        "five": 5,
        "第一个": 1,
        "第一": 1,
        "第二": 2,
        "第三": 3,
        "第四": 4,
        "第五": 5,
    }
    for phrase, index in ordinal_words.items():
        if phrase in text:
            return index
    number = _extract_first_number(text)
    return int(number) if number else None


def _rule_based_intent(transcript, context=None):
    text = _normalize_text(transcript)
    context = context or {}
    reply_language = _detect_reply_language(transcript, context)
    if not text:
        return _base_intent("unknown", 0.2, language=reply_language, reply=_short_reply("unknown", reply_language))

    if any(_contains_phrase(text, phrase) for phrase in ("hey", "hi", "hello", "are you there", "noob trade", "assistant", "你好", "在吗", "你在吗", "嗨", "hola", "bonjour")):
        return _base_intent("greeting", 0.96, language=reply_language, reply=_short_reply("ready", reply_language))

    if any(word in text for word in TRADING_WORDS):
        return _base_intent(
            "blocked_trading",
            0.98,
            language=reply_language,
            reply=_short_reply("blocked_trading", reply_language),
        )

    if any(phrase in text for phrase in ("sign out", "log out", "logout", "退出登录", "登出")):
        return _base_intent("sign_out", 0.96)

    historical_words = ("historical", "history", "pattern", "matched", "match", "similar", "moment", "window", "历史", "相似", "时刻", "窗口")
    if any(phrase in text for phrase in ("load more", "show more", "more history", "more patterns", "加载更多", "更多历史")) and any(word in text for word in historical_words):
        return _base_intent("load_more_patterns", 0.94)

    if any(phrase in text for phrase in ("open", "show", "look", "see", "打开", "看看", "看一下")) and any(word in text for word in historical_words):
        return _base_intent("open_historical_pattern", 0.95, index=_extract_ordinal_index(text))

    news_words = ("news", "headline", "headlines", "market news", "latest news", "新闻", "资讯", "消息", "noticias", "actualidad", "nouvelles", "actualites", "actualités")
    if any(word in text for word in news_words) and any(phrase in text for phrase in ("open", "show", "read", "look", "see", "go", "打开", "查看", "看看", "去", "abrir", "mostrar", "ver", "ouvrir", "afficher", "voir")):
        return _base_intent("open_news", 0.94, language=reply_language)

    guide_questions = (
        "how noobtrade works", "how noob trade works", "how does noobtrade work",
        "how does noob trade work", "what is noobtrade", "what does noobtrade do",
        "how it works", "user guide", "learn more", "help page",
        "怎么用", "如何使用", "工作原理", "用户手册", "操作手册", "使用说明",
    )
    if any(phrase in text for phrase in guide_questions):
        return _base_intent("navigate", 0.95, page="User Guide", language=reply_language)

    full_market_phrases = (
        "full market", "full market board", "open full market", "stock pool",
        "stock universe", "all stocks", "show all stocks", "market board",
        "full stock board", "全市场", "打开全市场", "股票池", "打开股票池",
        "全部股票", "所有股票", "完整股票列表", "mercado completo",
        "todas las acciones", "liste complete actions", "liste complète actions",
    )
    if any(phrase in text for phrase in full_market_phrases):
        return _base_intent("open_full_market", 0.96, language=reply_language)

    view_more_market_phrases = (
        "view more stocks", "show more stocks", "load more stocks", "more stocks",
        "view more market", "show more market", "load more market",
        "查看更多股票", "加载更多股票", "显示更多股票", "更多股票", "查看更多市场",
        "ver mas acciones", "ver más acciones", "mostrar mas acciones", "mostrar más acciones",
        "voir plus actions", "afficher plus actions",
    )
    if any(phrase in text for phrase in view_more_market_phrases):
        return _base_intent("view_more_market", 0.96, language=reply_language)

    probability_words = ("probability", "chance", "odds", "概率", "几率")
    if any(word in text for word in probability_words):
        side = "down" if any(phrase in text for phrase in ("down", "downside", "fall", "drop", "下跌", "向下")) else "up"
        value = _extract_first_number(text)
        if any(phrase in text for phrase in ("set", "change", "adjust", "drag", "move", "调", "调整", "拖", "改")) and value is not None:
            return _base_intent("adjust_probability", 0.94, side=side, value=value)
        return _base_intent("summarize_probability", 0.9, side=side, value=value)

    if any(phrase in text for phrase in ("upside to", "downside to", "set upside", "set downside", "drag upside", "drag downside", "把上涨", "把下跌", "上涨调到", "下跌调到")):
        side = "down" if any(phrase in text for phrase in ("down", "downside", "下跌", "向下")) else "up"
        value = _extract_first_number(text)
        if value is not None:
            return _base_intent("adjust_probability", 0.94, side=side, value=value)

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

    requested_interval = _extract_interval(text)
    if requested_interval and any(phrase in text for phrase in (
        "interval", "chart", "time frame", "timeframe", "switch", "change",
        "周期", "图表", "切换", "换到", "intervalo", "grafico", "gráfico",
        "cambiar", "intervalle", "graphique", "changer",
    )):
        return _base_intent("set_interval", 0.94, interval=requested_interval, language=reply_language)

    page_hits = []
    for phrase, page in ALLOWED_PAGES.items():
        if phrase in text:
            page_hits.append((len(phrase), page))
    if page_hits and any(verb in text for verb in ("go", "open", "show", "switch", "navigate", "进入", "打开", "切换")):
        page = sorted(page_hits, reverse=True)[0][1]
        return _base_intent("navigate", 0.96, page=page, language=reply_language)

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

    scan_phrases = (
        "scan", "scan watchlist", "scan saved", "batch generate",
        "full indicator scan", "full indicators scan",
        "扫描", "扫描自选", "星标扫描", "集体generate", "批量generate", "全指标扫描",
        "scanner", "escanear",
    )
    if any(phrase in text for phrase in scan_phrases):
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
                "enum": sorted(ALLOWED_INTENTS),
            },
            "confidence": {"type": "number"},
            "page": {"type": ["string", "null"]},
            "direction": {"type": ["string", "null"], "enum": ["up", "down", "top", "bottom", None]},
            "amount": {"type": ["string", "null"], "enum": ["small", "normal", "large", "full", None]},
            "symbol": {"type": ["string", "null"]},
            "indicators": {"type": "array", "items": {"type": "string"}},
            "active": {"type": ["boolean", "null"]},
            "threshold": {"type": ["number", "null"]},
            "side": {"type": ["string", "null"], "enum": ["up", "down", None]},
            "value": {"type": ["number", "null"]},
            "index": {"type": ["number", "null"]},
            "interval": {"type": ["string", "null"]},
            "language": {"type": ["string", "null"], "enum": ["en", "zh", "es", "fr", None]},
            "reply": {"type": "string"},
        },
        "required": [
            "intent", "confidence", "page", "direction", "amount", "symbol",
            "indicators", "active", "threshold", "side", "value", "index",
            "interval", "language", "reply",
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
        "allowedPages": ["Dashboard", "Stock Trade", "Crypto Trade", "Portfolio", "Explore", "Markets", "Settings", "More", "User Guide", "Admin"],
        "allowedIndicators": ["MA", "EMA", "MACD", "BOLL", "RSI", "Vol", "KDJ", "OI", "OBV"],
        "shortReplyBank": SHORT_REPLY_LIBRARY,
        "rules": [
            "Return one UI command intent only.",
            "Do not place trading orders. Buy/sell/order requests must be blocked_trading.",
            "Never write a long assistant response. The reply field must be empty or one short phrase from shortReplyBank in the user's language.",
            "For executable commands such as scan_watchlist, generate, search, set_star, navigate, open_news, open_full_market, view_more_market, or set_indicator, leave reply empty; the frontend will say the action status.",
            "If the user says open news, show news, 打开新闻, 看新闻, abrir noticias, or ouvrir les nouvelles, return open_news.",
            "If the user asks how NoobTrade works, user guide, learn more, 怎么用, 如何使用, 工作原理, or 用户手册, return navigate page User Guide.",
            "If the user says open full market, stock pool, all stocks, 股票池, 全市场, 全部股票, or 所有股票, return open_full_market.",
            "If the user says view more stocks, load more stocks, 查看更多股票, or 加载更多股票, return view_more_market.",
            "If the user says batch generate, scan saved names, full indicator scan, 星标扫描, 集体generate, or 全指标扫描, return scan_watchlist.",
            "If the user asks to switch chart intervals like 5 minute, daily, 月线, or 周线, return set_interval with interval 1min, 5min, 15min, 30min, 1hour, daily, 5day, weekly, 2week, or monthly.",
            "If the user uses an imperative command or a first-person request like I want, I need, 我要, 我想, quiero, necesito, je veux, or j'ai besoin, still return the matching action intent.",
            "If the user asks to go to stock trade page, return navigate page Stock Trade.",
            "Do not treat words like stock, trade, page, dashboard, portfolio, settings as stock tickers.",
            "Indicator names are strong entities. RSI alone should toggle/select RSI. I want RSI should select RSI. Remove RSI should unselect RSI.",
            "Star/favorite/watchlist commands should return set_star with the ticker or current context symbol.",
            "Probability slider commands like set upside to 3 percent or 把上涨调到3% should return adjust_probability with side and value.",
            "Questions like what is the upside probability should return summarize_probability.",
            "Historical pattern requests like open a historical moment or 打开一个历史时刻我看看 should return open_historical_pattern.",
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
                        "text": "You are Noob Trade's cloud intent router. Output strict JSON matching the schema. Never write prose outside JSON, and never put long prose in reply.",
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


def _coerce_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_bool(value):
    if isinstance(value, bool):
        return value

    normalized = _normalize_text(value)
    if normalized in {"true", "yes", "on", "enable", "select", "add", "pick", "选择", "打开", "加入"}:
        return True
    if normalized in {"false", "no", "off", "disable", "remove", "unselect", "deselect", "取消", "关闭", "移除"}:
        return False
    return None


def _normalize_page_entity(value):
    normalized = _normalize_text(value)
    return ALLOWED_PAGES.get(normalized)


def _normalize_indicator_entity(value):
    normalized = _normalize_text(value)
    if not normalized:
        return ""
    return INDICATOR_ALIASES.get(normalized, str(value or "").strip().upper())


def _intent_from_rasa_parse(parsed, transcript, context):
    intent_info = parsed.get("intent") if isinstance(parsed, dict) else {}
    intent_name = str((intent_info or {}).get("name") or "unknown")
    if intent_name not in ALLOWED_INTENTS:
        intent_name = "chat"

    confidence = _coerce_float((intent_info or {}).get("confidence")) or 0.0
    intent_payload = _base_intent(intent_name, confidence)
    indicators = []

    for entity in parsed.get("entities", []) if isinstance(parsed, dict) else []:
        if not isinstance(entity, dict):
            continue

        entity_name = str(entity.get("entity") or "").lower()
        value = entity.get("value")

        if entity_name in {"indicator", "indicators"}:
            indicator = _normalize_indicator_entity(value)
            if indicator and indicator not in indicators:
                indicators.append(indicator)
        elif entity_name == "page":
            intent_payload["page"] = _normalize_page_entity(value) or intent_payload["page"]
        elif entity_name == "symbol":
            intent_payload["symbol"] = _normalize_symbol_entity(value) or intent_payload["symbol"]
        elif entity_name == "direction":
            direction = _normalize_text(value)
            if direction in {"up", "down", "top", "bottom"}:
                intent_payload["direction"] = direction
        elif entity_name == "amount":
            amount = _normalize_text(value)
            if amount in {"small", "normal", "large", "full"}:
                intent_payload["amount"] = amount
        elif entity_name == "active":
            intent_payload["active"] = _coerce_bool(value)
        elif entity_name == "threshold":
            intent_payload["threshold"] = _coerce_float(value)
        elif entity_name == "side":
            side = _normalize_text(value)
            if side in {"up", "down"}:
                intent_payload["side"] = side
        elif entity_name == "value":
            intent_payload["value"] = _coerce_float(value)
        elif entity_name == "index":
            number = _coerce_float(value)
            intent_payload["index"] = int(number) if number is not None else intent_payload["index"]
        elif entity_name == "interval":
            intent_payload["interval"] = str(value or "").strip() or intent_payload["interval"]
        elif entity_name == "language":
            language = _normalize_text(value)
            if language in {"en", "zh", "es", "fr"}:
                intent_payload["language"] = language

    if indicators:
        intent_payload["indicators"] = indicators

    text = _normalize_text(transcript)
    if intent_payload["intent"] == "set_indicator":
        if not intent_payload["indicators"]:
            intent_payload["indicators"] = _extract_indicators(text)
        if intent_payload["active"] is None:
            intent_payload["active"] = not any(
                phrase in text
                for phrase in ("remove", "turn off", "disable", "unselect", "deselect", "取消", "关闭", "移除")
            )

    if intent_payload["intent"] in {"generate", "search", "set_star"} and not intent_payload["symbol"]:
        intent_payload["symbol"] = _extract_symbol(text) or context.get("symbol")

    if intent_payload["symbol"]:
        intent_payload["symbol"] = _normalize_symbol_entity(intent_payload["symbol"]) or intent_payload["symbol"]

    if intent_payload["intent"] == "scan_watchlist" and intent_payload["threshold"] is None:
        intent_payload["threshold"] = _extract_first_number(text)

    if intent_payload["intent"] == "adjust_probability":
        if intent_payload["side"] is None:
            intent_payload["side"] = "down" if any(phrase in text for phrase in ("down", "downside", "fall", "drop", "下跌", "向下")) else "up"
        if intent_payload["value"] is None:
            intent_payload["value"] = _extract_first_number(text)

    if intent_payload["intent"] == "open_historical_pattern" and intent_payload["index"] is None:
        intent_payload["index"] = _extract_ordinal_index(text)

    return intent_payload


def _rasa_intent(transcript, context):
    base_url = current_app.config.get("ASSISTANT_RASA_URL")
    if not base_url:
        return None

    response = requests.post(
        f"{str(base_url).rstrip('/')}/model/parse",
        json={"text": transcript},
        timeout=float(current_app.config.get("ASSISTANT_INTENT_TIMEOUT_SECONDS", 3.5)),
    )
    response.raise_for_status()
    return _intent_from_rasa_parse(response.json(), transcript, context)


def _finalize_intent_payload(intent_payload, transcript, context):
    if not isinstance(intent_payload, dict):
        return intent_payload

    cleaned_payload = dict(intent_payload)
    language = _detect_reply_language(transcript, context, cleaned_payload)
    cleaned_payload["language"] = language
    if cleaned_payload.get("symbol"):
        cleaned_payload["symbol"] = _normalize_symbol_entity(cleaned_payload.get("symbol")) or cleaned_payload.get("symbol")

    if cleaned_payload.get("intent") in {"generate", "search", "set_star"} and not cleaned_payload.get("symbol"):
        cleaned_payload["symbol"] = _extract_symbol(_normalize_text(transcript)) or context.get("symbol")

    if cleaned_payload.get("symbol"):
        cleaned_payload["symbol"] = _normalize_symbol_entity(cleaned_payload.get("symbol")) or cleaned_payload.get("symbol")

    intent = cleaned_payload.get("intent")
    if intent in {
        "generate", "search", "scan_watchlist", "set_star", "navigate",
        "open_news", "open_full_market", "view_more_market", "set_indicator",
        "set_interval", "open_historical_pattern", "load_more_patterns",
        "clear_indicators", "reset_indicators", "select_only_indicators",
        "adjust_probability",
    }:
        cleaned_payload["reply"] = ""
    elif intent in {"greeting", "help", "chat"}:
        cleaned_payload["reply"] = _short_reply("ready", language)
    elif intent == "blocked_trading":
        cleaned_payload["reply"] = _short_reply("blocked_trading", language)
    elif intent == "unknown":
        cleaned_payload["reply"] = _short_reply("unknown", language)
    elif len(str(cleaned_payload.get("reply") or "")) > 48:
        cleaned_payload["reply"] = ""

    return cleaned_payload


def _intent_response(source, intent_payload, transcript, context):
    return jsonify({
        "source": source,
        "intent": _finalize_intent_payload(intent_payload, transcript, context),
    })


@assistant_blueprint.route("/intent", methods=["POST"])
def parse_intent():
    payload = request.get_json(silent=True) or {}
    transcript = str(payload.get("transcript") or "").strip()
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}

    rule_intent = _rule_based_intent(transcript, context)
    if rule_intent["confidence"] >= 0.92:
        return _intent_response("rules", rule_intent, transcript, context)

    provider = current_app.config.get("ASSISTANT_INTENT_PROVIDER", "openai")
    should_try_rasa = provider in {"rasa", "auto"} or bool(current_app.config.get("ASSISTANT_RASA_URL"))

    if should_try_rasa:
        try:
            rasa_intent = _rasa_intent(transcript, context)
            if rasa_intent and float(rasa_intent.get("confidence") or 0) >= 0.5:
                return _intent_response("rasa", rasa_intent, transcript, context)
        except Exception as error:
            current_app.logger.warning("Rasa assistant intent failed: %s", error)

    try:
        cloud_intent = _openai_intent(transcript, context)
        if cloud_intent and float(cloud_intent.get("confidence") or 0) >= 0.5:
            return _intent_response("openai", cloud_intent, transcript, context)
    except Exception as error:
        current_app.logger.warning("Cloud assistant intent failed: %s", error)

    return _intent_response("rules", rule_intent, transcript, context)


@assistant_blueprint.route("/feedback", methods=["POST"])
def save_feedback():
    payload = request.get_json(silent=True) or {}
    transcript = str(payload.get("transcript") or "").strip()
    prediction = payload.get("prediction") if isinstance(payload.get("prediction"), dict) else {}
    correction = payload.get("correction") if isinstance(payload.get("correction"), dict) else {}

    if not transcript:
        return jsonify({"message": "Transcript is required."}), 400

    user_id = session.get("user_id")
    feedback = AssistantIntentFeedback(
        user_id=user_id if isinstance(user_id, int) else None,
        transcript=transcript,
        predicted_intent=str(prediction.get("intent") or "unknown")[:80],
        predicted_entities=_feedback_payload_from_intent(prediction),
        corrected_intent=(str(correction.get("intent"))[:80] if correction.get("intent") else None),
        corrected_entities=_feedback_payload_from_intent(correction),
        language=str(payload.get("language") or prediction.get("language") or "en")[:12],
        source=str(payload.get("source") or "voice")[:32],
        context_payload=payload.get("context") if isinstance(payload.get("context"), dict) else {},
    )

    db.session.add(feedback)
    db.session.commit()
    return jsonify({"status": "ok", "id": feedback.id})
