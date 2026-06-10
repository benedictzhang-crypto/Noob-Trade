from pathlib import Path


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "assistant_nlu" / "data" / "generated_synthetic.yml"

PAGES = [
    ("Stock Trade", ["stock trade", "stock analysis", "stocks", "trade page", "股票分析"]),
    ("Crypto Trade", ["crypto trade", "crypto analysis", "bitcoin page", "加密分析"]),
    ("Dashboard", ["dashboard", "home", "main page", "仪表盘"]),
    ("Portfolio", ["portfolio", "holdings", "positions", "投资组合"]),
    ("Explore", ["explore", "market explorer", "stock list", "探索"]),
    ("Markets", ["markets", "market page", "行情"]),
    ("Settings", ["settings", "account settings", "profile", "设置"]),
    ("Admin", ["admin", "admin dashboard", "管理员"]),
]

INDICATORS = [
    ("MA", ["MA", "moving average", "均线"]),
    ("EMA", ["EMA", "exponential moving average", "指数均线"]),
    ("MACD", ["MACD", "macd indicator"]),
    ("BOLL", ["BOLL", "Bollinger", "Bollinger bands", "布林带"]),
    ("RSI", ["RSI", "rsi indicator"]),
    ("Vol", ["Vol", "volume", "成交量"]),
    ("KDJ", ["KDJ", "kdj indicator"]),
    ("OI", ["OI", "open interest"]),
    ("OBV", ["OBV", "on balance volume"]),
]

SYMBOLS = [
    ("AAPL", ["AAPL", "Apple"]),
    ("NVDA", ["NVDA", "Nvidia"]),
    ("MSFT", ["MSFT", "Microsoft"]),
    ("TSLA", ["TSLA", "Tesla"]),
    ("META", ["META", "Meta"]),
    ("GOOGL", ["GOOGL", "Google"]),
    ("AMZN", ["AMZN", "Amazon"]),
    ("SPY", ["SPY", "spy"]),
    ("BTC", ["BTC", "Bitcoin"]),
    ("ETH", ["ETH", "Ethereum"]),
]

THRESHOLDS = ["55", "60", "65", "70", "75", "80", "88", "90", "93"]
PROB_VALUES = ["1", "1.5", "2", "2.5", "3", "4", "5", "7", "10"]


def entity(value, entity_name):
    return f"[{value}]({entity_name})"


def unique_take(items, limit):
    seen = set()
    output = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
        if len(output) >= limit:
            break
    return output


def build_examples():
    examples = {
        "navigate": [],
        "scroll": [],
        "generate": [],
        "search": [],
        "set_indicator": [],
        "select_only_indicators": [],
        "clear_indicators": [],
        "reset_indicators": [],
        "scan_watchlist": [],
        "set_star": [],
        "adjust_probability": [],
        "summarize_probability": [],
        "open_historical_pattern": [],
        "open_news": [],
        "load_more_patterns": [],
        "set_interval": [],
        "sign_out": [],
        "language": [],
        "greeting": [],
        "help": [],
        "blocked_trading": [],
        "chat": [],
    }

    for page_value, aliases in PAGES:
        for alias in aliases:
            page = entity(page_value if alias.isascii() else alias, "page")
            examples["navigate"].extend([
                f"go to {page}",
                f"open {page}",
                f"show me {page}",
                f"switch to {page}",
                f"navigate to {page}",
                f"take me to {page}",
                f"I want the {page}",
                f"can you open {page}",
                f"进入 {page}",
                f"打开 {page}",
                f"切换到 {page}",
                f"去 {page}",
                f"abrir {page}",
                f"ir a {page}",
                f"ouvrir {page}",
            ])

    scroll_directions = [
        ("down", "down", ["scroll down", "move down", "go lower", "page down", "scrolling down", "scorlling down", "往下滚", "向下滚动"]),
        ("up", "up", ["scroll up", "move up", "go higher", "page up", "往上滚", "向上滚动"]),
        ("bottom", "bottom", ["go to bottom", "scroll to bottom", "到底部", "去底部"]),
        ("top", "top", ["go to top", "scroll to top", "back to top", "到顶部", "回顶部"]),
    ]
    for direction_value, amount, phrases in scroll_directions:
        for phrase in phrases:
            examples["scroll"].extend([
                phrase,
                f"{phrase} a little bit",
                f"{phrase} more",
                f"{phrase} please",
                f"{phrase} just a bit",
                f"{phrase} {entity(direction_value, 'direction')}",
                f"{phrase} {entity(amount, 'amount')}",
            ])

    for symbol_value, aliases in SYMBOLS:
        for alias in aliases:
            symbol = entity(symbol_value if alias.isascii() else alias, "symbol")
            examples["generate"].extend([
                f"generate {symbol}",
                f"run generate for {symbol}",
                f"analyze {symbol}",
                f"forecast {symbol}",
                f"generate probability for {symbol}",
                f"start analysis on {symbol}",
                f"帮我分析 {symbol}",
                f"生成 {symbol}",
            ])
            examples["search"].extend([
                f"search {symbol}",
                f"look up {symbol}",
                f"show price for {symbol}",
                f"quote {symbol}",
                f"find {symbol}",
                f"查询 {symbol}",
                f"搜索 {symbol}",
            ])
            examples["set_star"].extend([
                f"star {symbol}",
                f"favorite {symbol}",
                f"add {symbol} to watchlist",
                f"save {symbol} as favorite",
                f"unstar {symbol}",
                f"remove {symbol} from watchlist",
                f"取消 {symbol} 星标",
                f"给 {symbol} 加星标",
            ])
            examples["blocked_trading"].extend([
                f"buy {symbol}",
                f"sell {symbol}",
                f"place a market order for {symbol}",
                f"place a limit order for {symbol}",
                f"go long {symbol}",
                f"short {symbol}",
                f"买入 {symbol}",
                f"卖出 {symbol}",
            ])

    for indicator_value, aliases in INDICATORS:
        for alias in aliases:
            indicator = entity(indicator_value if alias.isascii() else alias, "indicator")
            examples["set_indicator"].extend([
                indicator,
                f"select {indicator}",
                f"pick {indicator}",
                f"I want {indicator}",
                f"use {indicator}",
                f"turn on {indicator}",
                f"enable {indicator}",
                f"add {indicator}",
                f"remove {indicator}",
                f"turn off {indicator}",
                f"disable {indicator}",
                f"unselect {indicator}",
                f"deselect {indicator}",
                f"选择 {indicator}",
                f"勾选 {indicator}",
                f"取消 {indicator}",
                f"关闭 {indicator}",
            ])

    for first_value, first_aliases in INDICATORS:
        for second_value, second_aliases in INDICATORS:
            if first_value == second_value:
                continue
            first = entity(first_value, "indicator")
            second = entity(second_value, "indicator")
            examples["select_only_indicators"].extend([
                f"only use {first} and {second}",
                f"just {first} and {second}",
                f"select only {first} plus {second}",
                f"keep only {first} {second}",
                f"只选 {first} 和 {second}",
            ])

    examples["clear_indicators"].extend([
        "clear all indicators",
        "turn off all indicators",
        "remove every indicator",
        "disable all indicators",
        "no indicators",
        "清空所有指标",
        "关闭所有指标",
        "取消全部指标",
    ])
    examples["reset_indicators"].extend([
        "reset indicators",
        "restore default indicators",
        "go back to default indicators",
        "default indicator setup",
        "重置指标",
        "恢复默认指标",
    ])

    for threshold in THRESHOLDS:
        value = entity(threshold, "threshold")
        examples["scan_watchlist"].extend([
            f"scan watchlist above {value} percent",
            f"scan starred stocks at {value}%",
            f"scan my favorites over {value}",
            f"find favorites with probability above {value}",
            f"scan watchlist",
            f"scan my starred list",
            f"扫描自选 {value}%",
            f"扫描星标股票 {value}%",
        ])

    for value_text in PROB_VALUES:
        value = entity(value_text, "value")
        threshold = entity(value_text, "threshold")
        examples["adjust_probability"].extend([
            f"set upside probability to {value} percent",
            f"drag upside to {value}%",
            f"move upside slider to {value}",
            f"set downside probability to {value} percent",
            f"drag downside to {value}%",
            f"move downside slider to {value}",
            f"把上涨概率调到 {value}%",
            f"把下跌概率调到 {value}%",
        ])
        examples["summarize_probability"].extend([
            "what is the upside probability",
            "what is the downside probability",
            f"what is upside probability at {threshold}%",
            f"what is downside probability at {threshold}%",
            f"tell me the chance above {threshold}%",
            f"上涨 {threshold}% 概率是多少",
            f"下跌 {threshold}% 概率是多少",
        ])

    for index in ["first", "second", "third", "fourth", "fifth"]:
        examples["open_historical_pattern"].extend([
            "open a historical moment",
            "show me a similar historical window",
            f"open the {entity(index, 'index')} historical pattern",
            f"show the {entity(index, 'index')} match",
            "let me see a historical case",
            "打开一个历史时刻",
            "看一个相似历史窗口",
        ])
    examples["load_more_patterns"].extend([
        "load more historical patterns",
        "show more matches",
        "more historical windows",
        "load more similar cases",
        "加载更多历史相似",
        "更多历史窗口",
    ])
    examples["open_news"].extend([
        "open news",
        "show news",
        "read latest news",
        "open market news",
        "show me market headlines",
        "I want news",
        "I need the news",
        "打开新闻",
        "查看新闻",
        "我想看新闻",
        "我要打开新闻",
        "看一下市场新闻",
        "abrir noticias",
        "mostrar noticias",
        "quiero ver noticias",
        "necesito noticias",
        "ouvrir les nouvelles",
        "afficher les nouvelles",
        "je veux voir les nouvelles",
        "j'ai besoin des nouvelles",
    ])

    for interval in ["daily", "weekly", "monthly", "1 day", "1 week", "1 month"]:
        examples["set_interval"].extend([
            f"set interval to {entity(interval, 'interval')}",
            f"use {entity(interval, 'interval')} candles",
            f"switch timeframe to {entity(interval, 'interval')}",
            f"切换周期到 {entity(interval, 'interval')}",
        ])

    examples["sign_out"].extend([
        "log out",
        "sign out",
        "logout",
        "leave my account",
        "退出登录",
        "登出",
    ])
    for language in [("en", "English"), ("zh", "Chinese"), ("es", "Spanish"), ("fr", "French")]:
        examples["language"].extend([
            f"switch to {entity(language[0], 'language')}",
            f"use {language[1]}",
            f"change language to {language[1]}",
        ])
    examples["greeting"].extend([
        "hey",
        "hi",
        "hello",
        "hello assistant",
        "hey NoobTrade",
        "NoobTrade",
        "assistant",
        "are you there",
        "you there",
        "can you hear me",
        "wake up",
        "I need help",
        "I have a question",
        "what can I ask you",
        "what can you help me with",
        "你好",
        "嗨",
        "在吗",
        "你在吗",
        "小助手",
        "我有问题",
        "帮我一下",
        "hola",
        "bonjour",
        "salut",
        "estás ahí",
        "tu es là",
    ])
    examples["help"].extend([
        "help",
        "what can you do",
        "show commands",
        "how can I use voice",
        "帮助",
        "你会什么",
    ])
    examples["chat"].extend([
        "what are you",
        "tell me about Noob Trade",
        "介绍一下这个平台",
        "what is this platform",
        "how does Noob Trade work",
        "is this investment advice",
        "explain the dashboard",
        "what is Generate",
        "why do indicators matter",
        "这个平台是做什么的",
        "Noob Trade 怎么用",
        "Generate 是什么",
    ])

    examples["navigate"].extend([
        "show me the stock thing",
        "where do I analyze stocks",
        "take me to the place for stocks",
        "I need the stock screen",
        "open the chart page",
        "go back to my account page",
        "where are my settings",
        "let me see my saved stuff",
        "show my positions",
        "where is the crypto part",
        "bring up bitcoin tools",
        "I want the coin page",
        "take me home",
        "go to the main screen",
        "打开股票那个页面",
        "去看股票分析",
        "回到账户那里",
        "打开设置那里",
        "我要看加密货币",
        "去主页",
    ])
    examples["scroll"].extend([
        "keep going",
        "a bit more",
        "more",
        "less",
        "go further",
        "not enough keep moving",
        "move the page",
        "down a little",
        "up a little",
        "I want to see what's below",
        "show the lower part",
        "bring me back up",
        "再往下点",
        "再往上一点",
        "继续往下",
        "下面还有吗",
        "上去一点",
    ])
    examples["generate"].extend([
        "check this stock",
        "run the model",
        "tell me the odds",
        "what is the probability for this one",
        "do the forecast",
        "analyze the current symbol",
        "give me the prediction",
        "see if this can go up",
        "run NoobTrade on this",
        "帮我算一下概率",
        "看一下这个股票会不会涨",
        "跑一下模型",
        "生成一下当前股票",
        "我要generate",
        "我想生成这个",
        "please generate this",
        "I want generate",
        "I need generate",
        "quiero generate",
        "necesito analizar esto",
        "je veux generate",
        "j'ai besoin d'analyser ça",
    ])
    examples["search"].extend([
        "pull up Apple",
        "can you find Nvidia",
        "show me Tesla",
        "what is Microsoft doing",
        "open the quote",
        "find the ticker",
        "I want to look at Bitcoin",
        "查一下苹果",
        "看一下英伟达",
        "找一下特斯拉",
        "我要search",
        "我想查询这个",
        "please search this",
        "quiero buscar esto",
        "necesito el precio",
        "je veux chercher ça",
    ])
    examples["set_indicator"].extend([
        "put RSI on",
        "throw RSI in",
        "I need momentum",
        "show momentum",
        "remove momentum",
        "hide moving averages",
        "don't use EMA",
        "get rid of volume",
        "volume is not needed",
        "use Bollinger too",
        "add the bands",
        "remove the bands",
        "I want trend indicators",
        "turn trend off",
        "把RSI打开",
        "不要EMA",
        "加上布林带",
        "去掉成交量",
    ])
    examples["select_only_indicators"].extend([
        "focus only on momentum",
        "just use the main signal indicators",
        "only keep RSI and MACD",
        "strip it down to Bollinger and MACD",
        "只保留RSI和MACD",
        "只看布林带和MACD",
    ])
    examples["scan_watchlist"].extend([
        "scan my saved names",
        "check all my favorites",
        "run the watchlist",
        "which favorites look good",
        "find good setups from my stars",
        "show me starred names above sixty",
        "scan everything I starred",
        "扫描我收藏的股票",
        "看看自选里面哪个概率高",
        "我要scan",
        "我想扫描自选",
        "please scan",
        "I want you to scan",
        "quiero escanear favoritos",
        "necesito scan",
        "je veux scanner mes favoris",
    ])
    examples["set_star"].extend([
        "save this one",
        "keep this stock",
        "add this to my list",
        "remember this symbol",
        "remove this one from my list",
        "don't keep this anymore",
        "star the current stock",
        "unstar the current stock",
        "把这个加到自选",
        "收藏当前这个",
        "取消收藏这个",
        "我要加星标",
        "我想取消星标",
        "please star this",
        "quiero guardar esto",
        "necesito quitar favorito",
        "je veux ajouter aux favoris",
    ])
    examples["adjust_probability"].extend([
        "move the upside slider higher",
        "make the upside target three",
        "what if I want two percent up",
        "change the drop slider",
        "set the loss side to two",
        "make downside smaller",
        "drag the green probability",
        "drag the red probability",
        "把上涨那个滑块调高",
        "把下跌那个调低",
    ])
    examples["summarize_probability"].extend([
        "what are the odds now",
        "did the probability change",
        "explain the probability",
        "how likely is it to go up",
        "how likely is it to fall",
        "这个上涨机会多少",
        "现在概率怎么样",
    ])
    examples["open_historical_pattern"].extend([
        "show me what happened before",
        "open a past case",
        "show similar history",
        "what did similar setups do",
        "let me inspect one match",
        "open that historical card",
        "看看以前类似的时候",
        "打开一个过去案例",
    ])
    examples["load_more_patterns"].extend([
        "more past cases",
        "show additional history",
        "give me more similar moments",
        "还有更多类似的吗",
        "多加载几个历史案例",
    ])

    polite_prefixes = [
        "please",
        "can you",
        "could you",
        "I need you to",
        "assistant",
        "Noob Trade",
        "I want",
        "I need",
        "quiero",
        "necesito",
        "je veux",
        "j'ai besoin de",
    ]
    polite_suffixes = [
        "now",
        "please",
        "for me",
        "a little faster",
    ]
    for intent, items in list(examples.items()):
        augmented = list(items)
        for item in items:
            if item.startswith(("打开", "切换", "进入", "去", "选择", "勾选", "取消", "关闭", "生成", "查询", "搜索", "扫描", "把", "上涨", "下跌", "加载", "更多", "退出", "登出", "你好", "介绍", "查看", "看一下")):
                augmented.append(f"请 {item}")
                augmented.append(f"帮我 {item}")
                augmented.append(f"我要 {item}")
                augmented.append(f"我想 {item}")
                continue

            for prefix in polite_prefixes:
                augmented.append(f"{prefix} {item}")
            for suffix in polite_suffixes:
                augmented.append(f"{item} {suffix}")
        examples[intent] = augmented

    limits = {
        "navigate": 230,
        "scroll": 170,
        "generate": 170,
        "search": 130,
        "set_indicator": 360,
        "select_only_indicators": 180,
        "clear_indicators": 30,
        "reset_indicators": 30,
        "scan_watchlist": 135,
        "set_star": 145,
        "adjust_probability": 145,
        "summarize_probability": 120,
        "open_historical_pattern": 90,
        "open_news": 60,
        "load_more_patterns": 30,
        "set_interval": 40,
        "sign_out": 20,
        "language": 35,
        "greeting": 80,
        "help": 20,
        "blocked_trading": 75,
        "chat": 20,
    }

    return {intent: unique_take(items, limits[intent]) for intent, items in examples.items()}


def write_yaml(examples):
    lines = [
        'version: "3.1"',
        "",
        "nlu:",
    ]
    total = 0
    for intent, items in examples.items():
        lines.append(f"  - intent: {intent}")
        lines.append("    examples: |")
        for item in items:
            lines.append(f"      - {item}")
            total += 1
        lines.append("")

    OUTPUT_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return total


if __name__ == "__main__":
    count = write_yaml(build_examples())
    print(f"Wrote {count} synthetic NLU examples to {OUTPUT_PATH}")
