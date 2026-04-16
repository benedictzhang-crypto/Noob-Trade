<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import ChartPanel from './components/ChartPanel.vue'
import IndicatorSelector from './components/IndicatorSelector.vue'
import MatchedPatterns from './components/MatchedPatterns.vue'
import PredictionSummary from './components/PredictionSummary.vue'
import SearchBar from './components/SearchBar.vue'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'
const chartIntervals = ['daily', '5day', 'weekly', '2week', 'monthly']
const publicPages = ['Home', 'Sign In', 'Register', 'Verify Email', 'Reset Password', 'Reset Password Confirm']
const authenticatedPages = ['Dashboard', 'Trade', 'Portfolio', 'Explore', 'Markets', 'Myself', 'More']

const activePage = ref('Home')
const isAuthenticated = ref(false)
const symbolInput = ref('AAPL')
const activeSymbol = ref('AAPL')
const selectedChartInterval = ref('daily')
const currentExploreTab = ref('Watchlist')
const exploreViewMode = ref('ranked')
const exploreSearchQuery = ref('')
const isSearching = ref(false)
const isGenerating = ref(false)
const errorMessage = ref('')
const authMessage = ref('')
const portfolioMessage = ref('')
const portfolioAdjustments = ref({})
const pendingPortfolioActions = ref({})
const pendingAdminStatusUpdates = ref({})
const pendingAdminPasswordResets = ref({})
const adminPasswordResetDrafts = ref({})
const feedRefreshKey = ref(getHourRefreshKey())
const deferredInstallPrompt = ref(null)
const installMessage = ref('')
const showInstallGuide = ref(false)
const marketNewsFeed = ref([])
const replayPattern = ref(null)
const replayInterval = ref('daily')
const csrfToken = ref('')
const analysisCache = ref({})
const portfolioSparklineSeries = ref({})

let feedRefreshTimer = null
let beforeInstallHandler = null
let explorePrefetchTimer = null
const pendingAnalysisPrefetch = new Set()

const indicators = ref([
  { name: 'MA', active: true },
  { name: 'EMA', active: true },
  { name: 'MACD', active: true },
  { name: 'BOLL', active: true },
  { name: 'RSI', active: false },
  { name: 'Vol', active: true },
  { name: 'KDJ', active: false },
  { name: 'OI', active: false },
  { name: 'OBV', active: false }
])

const stockResponse = ref(createDefaultResponse())
const currentUser = ref(null)
const cashBalance = ref(86420)
const adminUsers = ref([])
const adminMessage = ref('')
const isAdminLoading = ref(false)
const signInForm = ref({
  email: '',
  password: ''
})
const verificationForm = ref({
  email: '',
  code: ''
})
const registrationForm = ref({
  fullName: '',
  email: '',
  password: ''
})
const resetPasswordForm = ref({
  email: '',
  code: '',
  newPassword: ''
})
const resetPasswordRequestForm = ref({
  email: ''
})
const portfolioForm = ref({
  accountName: 'Family Account',
  symbol: '',
  shares: 10
})
const holdings = ref(createInitialHoldings())
const transactionHistory = ref(createInitialTransactions())

const marketOverviewCards = [
  { name: 'S&P 500', level: '5,214.08', change: '+0.42%', tone: 'positive' },
  { name: 'NASDAQ 100', level: '18,102.44', change: '+0.78%', tone: 'positive' },
  { name: 'Dow Jones', level: '39,842.12', change: '+0.19%', tone: 'positive' },
  { name: 'VIX', level: '14.82', change: '-1.14%', tone: 'negative' }
]

const lastSixMonths = [
  { key: '2025-10', label: 'Oct' },
  { key: '2025-11', label: 'Nov' },
  { key: '2025-12', label: 'Dec' },
  { key: '2026-01', label: 'Jan' },
  { key: '2026-02', label: 'Feb' },
  { key: '2026-03', label: 'Mar' }
]

const publicFeatureRows = [
  {
    title: 'Guided analysis',
    description: 'Move from raw price action to an informed decision with probability, risk, stop, and sell guidance.'
  },
  {
    title: 'User dashboard',
    description: 'Give regular users a real workspace with balances, watchlists, portfolio context, and recent activity.'
  },
  {
    title: 'Reports and history',
    description: 'Track every simulated trade, review outcomes, and package simple reports for class deliverables.'
  }
]

const starredSymbols = ref(['AAPL', 'NVDA', 'TSLA', 'SPY'])

const dashboardAnnouncements = [
  {
    label: 'Desk note',
    detail: 'Your watchlist is leaning toward large-cap tech leadership and rebound setups this week.',
    tag: '5 / 10'
  },
  {
    label: 'Risk prompt',
    detail: 'Review stop-loss placement on TSLA before increasing exposure in any high-beta name.',
    tag: 'Today'
  }
]

const exploreTabs = ['Watchlist', 'Top Movers', 'Gainers', 'Volume Leaders']

const exploreRankings = {
  Watchlist: [
    { symbol: 'AAPL', name: 'Apple Inc.', category: 'Large Cap', price: '$184.25', notional: '$2.87T', change: '+1.28%', tone: 'positive' },
    { symbol: 'NVDA', name: 'NVIDIA Corp.', category: 'AI Leaders', price: '$911.70', notional: '$2.24T', change: '+2.61%', tone: 'positive' },
    { symbol: 'TSLA', name: 'Tesla Inc.', category: 'Momentum', price: '$380.30', notional: '$1.21T', change: '-1.07%', tone: 'negative' },
    { symbol: 'MSFT', name: 'Microsoft', category: 'Software', price: '$426.14', notional: '$3.16T', change: '+0.84%', tone: 'positive' },
    { symbol: 'AMZN', name: 'Amazon', category: 'Consumer Tech', price: '$188.44', notional: '$1.96T', change: '+0.58%', tone: 'positive' }
  ],
  'Top Movers': [
    { symbol: 'SMCI', name: 'Super Micro', category: 'Servers', price: '$1,038.12', notional: '$61.9B', change: '+6.42%', tone: 'positive' },
    { symbol: 'PLTR', name: 'Palantir', category: 'Software', price: '$29.52', notional: '$63.2B', change: '+4.13%', tone: 'positive' },
    { symbol: 'COIN', name: 'Coinbase', category: 'Exchange', price: '$268.17', notional: '$65.4B', change: '+3.84%', tone: 'positive' },
    { symbol: 'MDB', name: 'MongoDB', category: 'Cloud', price: '$406.80', notional: '$29.6B', change: '-2.91%', tone: 'negative' },
    { symbol: 'SNOW', name: 'Snowflake', category: 'Data Cloud', price: '$178.72', notional: '$58.7B', change: '-2.14%', tone: 'negative' }
  ],
  Gainers: [
    { symbol: 'ARM', name: 'Arm Holdings', category: 'Semis', price: '$171.06', notional: '$179.2B', change: '+5.22%', tone: 'positive' },
    { symbol: 'CRWD', name: 'CrowdStrike', category: 'Cybersecurity', price: '$352.60', notional: '$87.1B', change: '+4.17%', tone: 'positive' },
    { symbol: 'META', name: 'Meta Platforms', category: 'Internet', price: '$521.48', notional: '$1.33T', change: '+2.82%', tone: 'positive' },
    { symbol: 'NFLX', name: 'Netflix', category: 'Streaming', price: '$643.15', notional: '$279.6B', change: '+2.24%', tone: 'positive' },
    { symbol: 'SHOP', name: 'Shopify', category: 'Commerce', price: '$87.90', notional: '$113.4B', change: '+1.95%', tone: 'positive' }
  ],
  'Volume Leaders': [
    { symbol: 'SPY', name: 'SPDR S&P 500 ETF', category: 'ETF', price: '$520.44', notional: '$478.2M', change: '+0.38%', tone: 'positive' },
    { symbol: 'QQQ', name: 'Invesco QQQ', category: 'ETF', price: '$447.22', notional: '$219.4M', change: '+0.72%', tone: 'positive' },
    { symbol: 'TSLA', name: 'Tesla Inc.', category: 'Auto', price: '$380.30', notional: '$176.5M', change: '-1.07%', tone: 'negative' },
    { symbol: 'AAPL', name: 'Apple Inc.', category: 'Large Cap', price: '$184.25', notional: '$142.8M', change: '+1.28%', tone: 'positive' },
    { symbol: 'AMD', name: 'AMD', category: 'Semis', price: '$197.43', notional: '$118.7M', change: '+1.09%', tone: 'positive' }
  ]
}

const reportHighlights = [
  { title: 'Weekly Trade Review', value: '12 orders', detail: '4 wins · 3 losses · 5 open' },
  { title: 'Pattern Accuracy', value: '67%', detail: 'Last 30 closed simulations' },
  { title: 'Risk Discipline', value: '82%', detail: 'Stops respected on recent exits' },
  { title: 'Cash Utilization', value: '31%', detail: 'Capital currently deployed' }
]

const reportSections = [
  { name: 'Executive Summary', detail: 'Explain current positioning, best setup, and main risk in one paragraph.' },
  { name: 'Trade Journal', detail: 'List entries, exits, and what the user learned from each move.' },
  { name: 'Performance Attribution', detail: 'Separate gains from momentum names versus rebound names.' },
  { name: 'Risk Review', detail: 'Highlight drawdown, concentration, and sizing issues that need attention.' }
]

const moreFeatures = [
  'Public entry pages for unauthenticated users, including registration and sign-in flow.',
  'Authenticated dashboard with total assets, a six-month curve, and self-selected stock monitoring.',
  'Trade workspace that supports buy or sell decisions with a connected trade ticket.',
  'Explore board for ranked stock scanning before drilling into Trade.',
  'Markets and More pages for market context, product story, and feedback channels.'
]

const feedbackChannels = [
  { label: 'Feedback Email', value: 'zzzzhly@126.com', href: 'mailto:zzzzhly@126.com' },
  { label: 'Research Requests', value: 'zzzzhly@126.com', href: 'mailto:zzzzhly@126.com' },
  {
    label: 'Product Notes',
    value: '@NoobTrade123 on X',
    href: 'https://x.com/NoobTrade123'
  }
]

const newsFeeds = {
  default: [
    {
      title: 'US index breadth improves as growth names reclaim leadership',
      source: 'Market Pulse',
      time: '11 min ago',
      summary: 'Large-cap tech and semis are lifting index internals while defensive names cool off.'
    },
    {
      title: 'Treasury yields pause, giving momentum setups more room',
      source: 'Macro Desk',
      time: '28 min ago',
      summary: 'Lower yield pressure is helping higher-beta stocks stabilize near breakout zones.'
    },
    {
      title: 'Analysts focus on follow-through quality after recent rallies',
      source: 'Street Wire',
      time: '52 min ago',
      summary: 'Traders are looking for stronger volume confirmation before extending risk.'
    }
  ],
  AAPL: [
    {
      title: 'Apple supply chain commentary keeps attention on margin resilience',
      source: 'Equity Wire',
      time: '12 min ago',
      summary: 'Investors are watching whether product mix supports upside into the next earnings cycle.'
    },
    {
      title: 'AAPL options flow leans constructive near recent support',
      source: 'Flow Tracker',
      time: '33 min ago',
      summary: 'Short-dated positioning suggests traders are leaning for a rebound scenario.'
    },
    {
      title: 'Analysts debate upgrade path after recent pullback',
      source: 'Street Notes',
      time: '1 hr ago',
      summary: 'The discussion is shifting from valuation pressure to quality of the next leg higher.'
    }
  ],
  TSLA: [
    {
      title: 'Tesla sentiment remains split as traders watch post-event follow-through',
      source: 'Momentum Wire',
      time: '9 min ago',
      summary: 'The tape is volatile, but there is growing interest in reaction around key support.'
    },
    {
      title: 'TSLA intraday flow picks up into active retail session',
      source: 'Flow Tracker',
      time: '24 min ago',
      summary: 'Retail participation is amplifying both breakout attempts and failed reversals.'
    },
    {
      title: 'Street targets diverge while traders focus on execution windows',
      source: 'Street Notes',
      time: '58 min ago',
      summary: 'The stock is trading more like a momentum instrument than a slow trend name.'
    }
  ],
  NVDA: [
    {
      title: 'NVDA keeps leadership bid as AI complex attracts new capital',
      source: 'Semis Desk',
      time: '7 min ago',
      summary: 'Relative strength remains high, but traders are watching for extension risk.'
    },
    {
      title: 'Chip basket strength improves market-wide risk appetite',
      source: 'Macro Desk',
      time: '26 min ago',
      summary: 'Broader market tone is still being dictated by semiconductor performance.'
    },
    {
      title: 'Momentum traders rotate toward cleaner continuation setups',
      source: 'Trend Watch',
      time: '49 min ago',
      summary: 'High-volume consolidation is becoming the preferred entry structure.'
    }
  ]
}

const postFeeds = {
  default: [
    {
      handle: '@macroflow',
      tone: 'Bullish',
      post: 'Index structure looks healthier when breadth improves together with semis. Watching continuation quality, not just the headline move.'
    },
    {
      handle: '@tapejournal',
      tone: 'Neutral',
      post: 'Still seeing traders wait for confirmation candles before adding risk. Good reminder that trend quality matters more than excitement.'
    },
    {
      handle: '@risknotes',
      tone: 'Cautious',
      post: 'If yields reverse higher again, some of the cleanest breakout setups could lose momentum fast.'
    }
  ],
  AAPL: [
    {
      handle: '@appleflow',
      tone: 'Bullish',
      post: 'AAPL still looks like one of the cleaner large-cap mean-reversion candidates if buyers defend this zone.'
    },
    {
      handle: '@chartstation',
      tone: 'Neutral',
      post: 'Watching whether Apple can reclaim trend alignment with stronger volume. Setup is improving but not complete.'
    },
    {
      handle: '@optionsdesk',
      tone: 'Bullish',
      post: 'Call buyers were active again. If spot holds, the next push could happen quickly.'
    }
  ],
  TSLA: [
    {
      handle: '@teslatape',
      tone: 'High Beta',
      post: 'TSLA is still a trader stock first. Great upside when it works, but the stop needs to stay disciplined.'
    },
    {
      handle: '@trendpilot',
      tone: 'Bullish',
      post: 'If Tesla prints a cleaner base, the rebound probability goes up meaningfully.'
    },
    {
      handle: '@risknotes',
      tone: 'Cautious',
      post: 'This one can shake out weak hands fast, so waiting for the higher-quality trigger is reasonable.'
    }
  ],
  NVDA: [
    {
      handle: '@semisignals',
      tone: 'Bullish',
      post: 'NVDA is still the market’s leadership tell. When it behaves well, risk appetite broadens.'
    },
    {
      handle: '@executionlab',
      tone: 'Neutral',
      post: 'Momentum is strong, but entries matter. Chasing extended candles usually lowers the quality of the trade.'
    },
    {
      handle: '@aiflowdesk',
      tone: 'Bullish',
      post: 'The biggest edge right now is identifying clean continuation structures, not guessing tops.'
    }
  ]
}

const top50Symbols = [
  'AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'BRK.B', 'LLY', 'AVGO', 'JPM',
  'V', 'XOM', 'UNH', 'MA', 'COST', 'JNJ', 'HD', 'ORCL', 'PG', 'MRK',
  'NFLX', 'ABBV', 'BAC', 'KO', 'AMD', 'CVX', 'PEP', 'CRM', 'WMT', 'TMO',
  'ACN', 'CSCO', 'MCD', 'ABT', 'IBM', 'GE', 'LIN', 'DIS', 'ADBE', 'NOW',
  'INTU', 'QCOM', 'CAT', 'TXN', 'AXP', 'AMAT', 'BKNG', 'UBER', 'GS', 'SPY'
]

const fullBoardSeedMeta = {
  AAPL: { name: 'Apple Inc.', category: 'Large Cap', price: '$184.25', notional: '$2.87T', change: '+1.28%', tone: 'positive' },
  MSFT: { name: 'Microsoft Corporation', category: 'Software', price: '$426.14', notional: '$3.16T', change: '+0.84%', tone: 'positive' },
  NVDA: { name: 'NVIDIA Corporation', category: 'AI Leaders', price: '$911.70', notional: '$2.24T', change: '+2.61%', tone: 'positive' },
  AMZN: { name: 'Amazon.com, Inc.', category: 'Consumer Tech', price: '$188.44', notional: '$1.96T', change: '+0.58%', tone: 'positive' },
  GOOGL: { name: 'Alphabet Inc. Class A', category: 'Internet', price: '--', notional: '--', change: '--', tone: 'neutral' },
  META: { name: 'Meta Platforms, Inc.', category: 'Internet', price: '$521.48', notional: '$1.33T', change: '+2.82%', tone: 'positive' },
  'BRK.B': { name: 'Berkshire Hathaway Inc. Class B', category: 'Financials', price: '--', notional: '--', change: '--', tone: 'neutral' },
  LLY: { name: 'Eli Lilly and Company', category: 'Healthcare', price: '--', notional: '--', change: '--', tone: 'neutral' },
  AVGO: { name: 'Broadcom Inc.', category: 'Semis', price: '--', notional: '--', change: '--', tone: 'neutral' },
  JPM: { name: 'JPMorgan Chase & Co.', category: 'Financials', price: '--', notional: '--', change: '--', tone: 'neutral' },
  GOOG: { name: 'Alphabet Inc. Class C', category: 'Internet', price: '--', notional: '--', change: '--', tone: 'neutral' },
  TSLA: { name: 'Tesla Inc.', category: 'Momentum', price: '$380.30', notional: '$1.21T', change: '-1.07%', tone: 'negative' },
  NFLX: { name: 'Netflix', category: 'Streaming', price: '$643.15', notional: '$279.6B', change: '+2.24%', tone: 'positive' },
  AMD: { name: 'AMD', category: 'Semis', price: '$197.43', notional: '$118.7M', change: '+1.09%', tone: 'positive' },
  SPY: { name: 'SPDR S&P 500 ETF', category: 'ETF', price: '$520.44', notional: '$478.2M', change: '+0.38%', tone: 'positive' },
}

const newsHeadlineTemplates = [
  'Institutional flows keep attention on {symbol} as rotation continues across large-cap leadership.',
  '{symbol} stays on the active watchlist as traders monitor continuation quality into the next session.',
  'Desk conversations around {symbol} focus on whether price can hold trend structure with cleaner volume.',
  '{symbol} moves back into the top discussion set as market breadth improves around core leaders.',
  'Portfolio managers are reassessing {symbol} after fresh momentum and relative-strength confirmation.',
  '{symbol} remains in focus as traders compare current setup quality with prior rebound structures.',
  'Cross-asset calm is helping {symbol} regain attention among higher-conviction watchlists.',
  'Analyst desks note that {symbol} is attracting fresh interest after another constructive tape response.'
]

const newsSummaryTemplates = [
  'The key question is whether the next push comes with stronger breadth, cleaner closes, and more disciplined participation.',
  'Short-term traders are looking for confirmation that the current move can hold without losing volume support.',
  'The setup is being judged on follow-through quality rather than on a single headline or gap move.',
  'Market participants are watching if leadership can persist long enough to justify a stronger directional bias.',
  'The discussion is centered on how current tape behavior compares with prior high-quality continuation phases.',
  'Attention is on whether buyers can defend higher lows while keeping downside volatility contained.'
]

const newsSourcePool = ['Reuters Desk', 'Bloomberg Pulse', 'CNBC Markets', 'WSJ Wire', 'Barron\'s Brief', 'Market Pulse']

const socialTonePool = ['Bullish', 'Neutral', 'Constructive', 'Cautious', 'Momentum', 'Watching']
const socialHandlePool = ['@deskflow', '@marketjournal', '@riskpilot', '@alphawire', '@openingtape', '@macrostation']
const socialPostTemplates = [
  '{symbol} is back on the radar. The main thing now is whether the next rotation keeps quality instead of just speed.',
  'I care less about the headline and more about whether {symbol} can hold its structure once the first burst fades.',
  '{symbol} still looks tradable, but only if follow-through keeps improving on the next few sessions.',
  'The best read on {symbol} is still tape quality: tighter pullbacks, better closes, and less failed extension.',
  'If {symbol} keeps attracting clean buyers, the whole market tone gets easier to trust.',
  'Watching whether {symbol} stays orderly. Good setups usually look obvious before they look exciting.'
]

const visiblePages = computed(() => {
  if (!isAuthenticated.value) {
    return publicPages
  }

  if (currentUser.value?.isAdmin) {
    return [...authenticatedPages, 'Admin']
  }

  return authenticatedPages
})
const selectedIndicators = computed(() => indicators.value.filter((indicator) => indicator.active))
const appliedIndicatorSet = computed(() => new Set(
  stockResponse.value?.request?.indicators
  || stockResponse.value?.patternAnalysis?.selectedIndicators
  || []
))
const appliedIndicators = computed(() => indicators.value
  .filter((indicator) => appliedIndicatorSet.value.has(indicator.name))
  .map((indicator) => ({ ...indicator, active: true })))
const newsFeed = computed(() => marketNewsFeed.value.length ? marketNewsFeed.value : buildHourlyNewsFeed(activeSymbol.value, feedRefreshKey.value))
const scrollingNewsFeed = computed(() => [...newsFeed.value, ...newsFeed.value])
const socialFeed = computed(() => buildHourlySocialFeed(activeSymbol.value, feedRefreshKey.value))
const marketFocusLabel = computed(() => {
  if (activeSymbol.value && top50Symbols.includes(activeSymbol.value)) {
    return 'Hot Market'
  }

  return 'Hot Market'
})
const currentUserName = computed(() => currentUser.value?.fullName || 'Guest')
const currentUserCode = computed(() => formatAdminUserCode(currentUser.value?.displayCode ?? currentUser.value?.id))
const currentExploreRows = computed(() => exploreRankings[currentExploreTab.value] || exploreRankings.Watchlist)
const allExploreRows = computed(() => {
  const merged = new Map()

  Object.values(exploreRankings).flat().forEach((row) => {
    if (!merged.has(row.symbol)) {
      merged.set(row.symbol, row)
    }
  })

  return [...merged.values()]
})
const fullMarketBoardRows = computed(() => {
  const mergedLookup = new Map(allExploreRows.value.map((row) => [row.symbol, row]))

  return top50Symbols.map((symbol) => {
    const mergedRow = mergedLookup.get(symbol)
    const seededRow = fullBoardSeedMeta[symbol]

    if (mergedRow) {
      return mergedRow
    }

    if (seededRow) {
      return {
        symbol,
        ...seededRow
      }
    }

    return {
      symbol,
      name: symbol,
      category: 'S&P 500',
      price: '--',
      notional: '--',
      change: '--',
      tone: 'neutral'
    }
  })
})
const visibleExploreRows = computed(() => {
  if (exploreViewMode.value === 'full') {
    return fullMarketBoardRows.value
  }

  return currentExploreRows.value
})
const filteredExploreRows = computed(() => {
  const query = exploreSearchQuery.value.trim().toUpperCase()

  if (!query) {
    return visibleExploreRows.value
  }

  return allExploreRows.value.filter((row) => {
    const symbol = String(row.symbol || '').toUpperCase()
    const name = String(row.name || '').toUpperCase()
    const category = String(row.category || '').toUpperCase()
    return symbol.includes(query) || name.includes(query) || category.includes(query)
  })
})
const portfolioSymbols = computed(() => {
  return [...new Set(holdings.value.map((holding) => String(holding.symbol || '').trim().toUpperCase()).filter(Boolean))]
})
const starredLookup = computed(() => new Set(starredSymbols.value))
const dashboardWatchlistRows = computed(() => {
  return starredSymbols.value
    .map((symbol) => {
      const marketRow = allExploreRows.value.find((row) => row.symbol === symbol)
      if (marketRow) {
        return {
          symbol: marketRow.symbol,
          price: marketRow.price,
          change: marketRow.change,
          tone: marketRow.tone,
          note: marketRow.category
        }
      }

      if (stockResponse.value?.stock?.symbol === symbol) {
        const currentPrice = Number(stockResponse.value.stock.currentPrice || 0)
        const previousClose = Number(stockResponse.value.stock.previousClose || currentPrice)
        const changePct = previousClose ? (((currentPrice - previousClose) / previousClose) * 100) : 0
        return {
          symbol,
          price: formatCurrency(currentPrice),
          change: formatPercent(changePct),
          tone: changePct >= 0 ? 'positive' : 'negative',
          note: 'Recently viewed'
        }
      }

      return {
        symbol,
        price: '--',
        change: '--',
        tone: 'neutral',
        note: 'Saved star'
      }
    })
})
const mobileNavPages = computed(() => visiblePages.value)
const isAppleMobile = computed(() => {
  if (typeof navigator === 'undefined') {
    return false
  }

  const userAgent = navigator.userAgent || ''
  return /iPhone|iPad|iPod/i.test(userAgent)
})
const isStandaloneMode = computed(() => {
  if (typeof window === 'undefined') {
    return false
  }

  return window.matchMedia?.('(display-mode: standalone)').matches || window.navigator.standalone === true
})
const canInstallApp = computed(() => !isStandaloneMode.value && (Boolean(deferredInstallPrompt.value) || isAppleMobile.value))
const dataSourceMeta = computed(() => {
  if (stockResponse.value.dataSource === 'live') {
    return {
      label: 'Live API',
      description: 'Connected market feed',
      tone: 'live'
    }
  }

  if (stockResponse.value.dataSource === 'cached') {
    return {
      label: 'Cached Data',
      description: 'Postgres market cache',
      tone: 'live'
    }
  }

  return {
    label: 'Mock Data',
    description: 'Fallback sample feed',
    tone: 'mock'
  }
})

const holdingsWithMetrics = computed(() => {
  const totalMarketValue = holdings.value.reduce((sum, holding) => sum + (holding.shares * getTrackedPrice(holding.symbol)), 0)

  return holdings.value.map((holding) => {
    const currentPrice = getTrackedPrice(holding.symbol)
    const marketValue = holding.shares * currentPrice
    const pnl = marketValue - (holding.shares * holding.costBasis)
    const allocation = totalMarketValue ? (marketValue / totalMarketValue) * 100 : 0

    return {
      ...holding,
      currentPrice,
      marketValue,
      pnl,
      allocation
    }
  })
})

const portfolioSummary = computed(() => {
  const marketValue = holdingsWithMetrics.value.reduce((sum, holding) => sum + holding.marketValue, 0)
  const totalCost = holdingsWithMetrics.value.reduce((sum, holding) => sum + (holding.shares * holding.costBasis), 0)
  const totalPnl = marketValue - totalCost
  const biggestPosition = holdingsWithMetrics.value.reduce((leader, holding) => {
    if (!leader || holding.marketValue > leader.marketValue) {
      return holding
    }
    return leader
  }, null)
  const topWinner = holdingsWithMetrics.value.reduce((leader, holding) => {
    if (!leader || holding.pnl > leader.pnl) {
      return holding
    }
    return leader
  }, null)

  return {
    marketValue,
    totalCost,
    totalPnl,
    biggestPosition,
    topWinner
  }
})

const totalAssetValue = computed(() => portfolioSummary.value.marketValue)
const sixMonthStartValue = 0
const sixMonthPnl = computed(() => totalAssetValue.value - sixMonthStartValue)
const sixMonthPnlPercent = computed(() => (sixMonthStartValue ? (sixMonthPnl.value / sixMonthStartValue) * 100 : 0))
const dashboardAssetPoints = computed(() => buildPortfolioTimeline(holdingsWithMetrics.value, lastSixMonths.map((item) => item.key)))
const dashboardAssetPath = computed(() => buildMiniChartPath(dashboardAssetPoints.value))
const dashboardAreaPath = computed(() => buildMiniAreaPath(dashboardAssetPoints.value))
const dashboardYAxis = computed(() => buildAxisLabels(dashboardAssetPoints.value))
const dashboardXAxis = lastSixMonths.map((item) => item.label)

const dashboardStats = computed(() => {
  const openPositions = holdingsWithMetrics.value.length
  const totalValue = cashBalance.value + portfolioSummary.value.marketValue

  return [
    { label: 'Total Managed Assets', value: formatCurrency(totalAssetValue.value), note: 'All saved stock accounts combined' },
    { label: 'Cash Reserve', value: formatCurrency(cashBalance.value), note: 'Separate dry powder for new trades' },
    { label: 'Open Positions', value: String(openPositions), note: 'Saved holdings across your accounts' },
    { label: 'Recent P/L', value: formatSignedCurrency(portfolioSummary.value.totalPnl), note: 'Marked against saved cost basis' }
  ]
})

const portfolioChartPoints = computed(() => dashboardAssetPoints.value)
const portfolioChartPath = computed(() => buildMiniChartPath(portfolioChartPoints.value))
const portfolioAreaPath = computed(() => buildMiniAreaPath(portfolioChartPoints.value))
const portfolioYAxis = computed(() => buildAxisLabels(portfolioChartPoints.value))

const replayChartData = computed(() => {
  if (!replayPattern.value) {
    return { series: {}, history: { daily: [] } }
  }

  const interval = replayPattern.value.timeframe || 'daily'
  const candles = replayPattern.value.historicalCandles || []

  return {
    series: {
      [interval]: candles
    },
    history: {
      daily: candles
    }
  }
})

const recentTransactions = computed(() => transactionHistory.value.slice(0, 8))

const historySummary = computed(() => {
  const buyCount = transactionHistory.value.filter((item) => item.side === 'Buy').length
  const sellCount = transactionHistory.value.filter((item) => item.side === 'Sell').length
  const totalTurnover = transactionHistory.value.reduce((sum, item) => sum + item.total, 0)

  return [
    { label: 'Total Orders', value: String(transactionHistory.value.length), note: 'All recorded simulated trades' },
    { label: 'Buy Orders', value: String(buyCount), note: 'Entries added to the journal' },
    { label: 'Sell Orders', value: String(sellCount), note: 'Exits recorded in history' },
    { label: 'Turnover', value: formatCurrency(totalTurnover), note: 'Gross transaction value' }
  ]
})

const reportMetrics = computed(() => {
  const sellOrders = transactionHistory.value.filter((item) => item.side === 'Sell')
  const closedOrderRate = transactionHistory.value.length ? (sellOrders.length / transactionHistory.value.length) * 100 : 0
  const positiveHoldings = holdingsWithMetrics.value.filter((holding) => holding.pnl > 0).length
  const positiveRate = holdingsWithMetrics.value.length ? (positiveHoldings / holdingsWithMetrics.value.length) * 100 : 0

  return [
    { label: 'Report Date', value: 'March 22, 2026', note: 'Latest class-ready snapshot' },
    { label: 'Portfolio P/L', value: formatSignedCurrency(portfolioSummary.value.totalPnl), note: 'Current marked performance' },
    { label: 'Closed Order Rate', value: `${closedOrderRate.toFixed(0)}%`, note: 'Share of exits versus all orders' },
    { label: 'Holding Win Rate', value: `${positiveRate.toFixed(0)}%`, note: 'Current positions above cost basis' }
  ]
})

onMounted(() => {
  ensureCsrfToken().catch(() => {})
  restoreAuthenticatedSession().catch(() => {})
  refreshFeedClock()
  feedRefreshTimer = window.setInterval(refreshFeedClock, 60 * 1000)
  loadMarketNews()

  beforeInstallHandler = (event) => {
    event.preventDefault()
    deferredInstallPrompt.value = event
  }

  window.addEventListener('beforeinstallprompt', beforeInstallHandler)
})

watch([activeSymbol, feedRefreshKey], () => {
  loadMarketNews()
})

onBeforeUnmount(() => {
  if (feedRefreshTimer) {
    window.clearInterval(feedRefreshTimer)
  }

  if (explorePrefetchTimer) {
    window.clearTimeout(explorePrefetchTimer)
  }

  if (beforeInstallHandler) {
    window.removeEventListener('beforeinstallprompt', beforeInstallHandler)
  }
})

async function triggerInstall() {
  installMessage.value = ''

  if (deferredInstallPrompt.value) {
    deferredInstallPrompt.value.prompt()
    const result = await deferredInstallPrompt.value.userChoice

    if (result?.outcome === 'accepted') {
      installMessage.value = 'Noob Trade is being added as an app on this device.'
    } else {
      installMessage.value = 'Install was dismissed. You can trigger it again any time.'
    }

    deferredInstallPrompt.value = null
    return
  }

  if (isAppleMobile.value) {
    showInstallGuide.value = true
    return
  }

  installMessage.value = 'Open this page in Chrome, Edge, or Safari desktop and use the install button in the browser chrome.'
}

async function loadMarketNews() {
  try {
    const response = await fetch(`${API_BASE_URL}/market-news?symbol=${encodeURIComponent(activeSymbol.value)}&limit=5`)
    const payload = await parseJsonResponse(
      response,
      'The server returned a non-JSON response while loading market news.'
    )

    if (!response.ok) {
      throw new Error(payload.message || 'Could not load market news.')
    }

    marketNewsFeed.value = Array.isArray(payload.items) ? payload.items : []
  } catch (error) {
    marketNewsFeed.value = buildHourlyNewsFeed(activeSymbol.value, feedRefreshKey.value)
  }
}

function createDefaultResponse() {
  return {
    dataSource: 'mock',
    request: {
      symbol: 'AAPL',
      interval: 'daily',
      indicators: ['MA', 'EMA', 'MACD', 'BOLL', 'Vol']
    },
    stock: {
      symbol: 'AAPL',
      companyName: 'Apple Inc.',
      sector: 'Technology',
      industry: 'Consumer Electronics',
      currentPrice: 184.25,
      previousClose: 181.9,
      open: 182.4,
      volume: 3245600,
      week52High: 205.8,
      week52Low: 121.35
    },
    patternAnalysis: {
      selectedIndicators: ['MA', 'EMA', 'MACD', 'BOLL', 'Vol'],
      probabilityOfIncrease: 90,
      probabilityOfDecrease: 55,
      avgReturn: 6.8,
      maxDrawdown: -4.9,
      matchedPatternsCount: 20,
      quantConfidence: 0.91,
      signalClassification: 'Bullish Bias',
      futureFiveDayProbabilities: {
        up: [
          { threshold: 1, probability: 90 },
          { threshold: 5, probability: 80 },
          { threshold: 10, probability: 30 }
        ],
        down: [
          { threshold: 1, probability: 55 },
          { threshold: 5, probability: 20 },
          { threshold: 10, probability: 5 }
        ]
      },
      recommendedSellPrice: 198.4,
      recommendedSellDate: 'Within 5 trading days',
      stopLossPrice: 178.8,
      matchedHistoricalPatterns: [
        {
          patternName: 'DAILY 30-bar setup',
          matchScore: 91,
          date: '2026-03-10',
          symbol: 'AAPL',
          timeframe: 'daily',
          windowSize: 30,
          returnPct: 8.42,
          maxDrawdown: -3.8
        },
        {
          patternName: 'DAILY 30-bar setup',
          matchScore: 87,
          date: '2026-02-24',
          symbol: 'NVDA',
          timeframe: 'daily',
          windowSize: 30,
          returnPct: 6.21,
          maxDrawdown: -4.2
        },
        {
          patternName: 'DAILY 30-bar setup',
          matchScore: 82,
          date: '2026-01-15',
          symbol: 'TSLA',
          timeframe: 'daily',
          windowSize: 30,
          returnPct: 5.14,
          maxDrawdown: -5.6
        }
      ],
      highFitHistoricalPaths: [
        { label: 'AAPL continuation path', fitScore: 91, status: 'AAPL ended on 2026-03-10' },
        { label: 'NVDA momentum path', fitScore: 87, status: 'NVDA ended on 2026-02-24' },
        { label: 'TSLA rebound path', fitScore: 82, status: 'TSLA ended on 2026-01-15' }
      ]
    },
    chartData: {
      series: {
        daily: [
          { date: '2026-03-10', open: 186.8, high: 188.5, low: 185.4, close: 187.9, volume: 1270000 },
          { date: '2026-03-11', open: 187.9, high: 189.1, low: 186.0, close: 186.7, volume: 1120000 },
          { date: '2026-03-12', open: 186.7, high: 187.8, low: 184.5, close: 185.1, volume: 1200000 },
          { date: '2026-03-13', open: 185.1, high: 186.3, low: 183.2, close: 184.0, volume: 1090000 },
          { date: '2026-03-16', open: 184.0, high: 185.8, low: 182.9, close: 184.9, volume: 980000 },
          { date: '2026-03-17', open: 184.9, high: 186.8, low: 184.0, close: 186.0, volume: 1030000 },
          { date: '2026-03-18', open: 186.0, high: 187.3, low: 184.9, close: 185.3, volume: 970000 },
          { date: '2026-03-19', open: 185.3, high: 186.6, low: 183.8, close: 184.25, volume: 1010000 }
        ],
        '5day': [
          { date: '2026-02-28', open: 175.8, high: 186.4, low: 172.4, close: 182.6, volume: 23200000 },
          { date: '2026-03-19', open: 182.6, high: 189.1, low: 182.2, close: 184.25, volume: 16500000 }
        ],
        weekly: [
          { date: '2026-W09', open: 175.8, high: 186.4, low: 172.4, close: 182.6, volume: 23200000 },
          { date: '2026-W11', open: 182.6, high: 189.1, low: 182.2, close: 184.25, volume: 16500000 }
        ],
        '2week': [
          { date: '2026-H1', open: 175.8, high: 186.4, low: 172.4, close: 182.6, volume: 23200000 },
          { date: '2026-H2', open: 182.6, high: 189.1, low: 182.2, close: 184.25, volume: 16500000 }
        ],
        monthly: [
          { date: '2025-10', open: 154.2, high: 162.5, low: 149.8, close: 160.6, volume: 19200000 },
          { date: '2025-11', open: 160.6, high: 168.0, low: 158.2, close: 166.9, volume: 20100000 },
          { date: '2025-12', open: 166.9, high: 172.8, low: 163.9, close: 171.5, volume: 21400000 },
          { date: '2026-01', open: 171.5, high: 177.6, low: 169.7, close: 175.8, volume: 20600000 },
          { date: '2026-02', open: 175.8, high: 186.4, low: 172.4, close: 182.6, volume: 23200000 },
          { date: '2026-03', open: 182.6, high: 189.1, low: 182.2, close: 184.25, volume: 16500000 }
        ]
      }
    }
  }
}

function createInitialHoldings() {
  return [
    { accountName: 'Main Account', addedMonth: '2025-10', symbol: 'AAPL', name: 'Apple Inc.', shares: 120, costBasis: 176.2, thesis: 'Rebound candidate', risk: 'Low' },
    { accountName: 'Family Growth', addedMonth: '2025-12', symbol: 'NVDA', name: 'NVIDIA Corp.', shares: 18, costBasis: 884.1, thesis: 'Leadership trend', risk: 'Medium' },
    { accountName: 'Family Swing', addedMonth: '2026-02', symbol: 'TSLA', name: 'Tesla Inc.', shares: 28, costBasis: 392.8, thesis: 'High-beta swing', risk: 'High' }
  ]
}

function createInitialTransactions() {
  return [
    { id: 1, date: '2026-03-21', symbol: 'AAPL', side: 'Buy', quantity: 20, price: 181.4, total: 3628, status: 'Filled' },
    { id: 2, date: '2026-03-20', symbol: 'NVDA', side: 'Sell', quantity: 5, price: 905.1, total: 4525.5, status: 'Filled' },
    { id: 3, date: '2026-03-19', symbol: 'TSLA', side: 'Buy', quantity: 10, price: 384.7, total: 3847, status: 'Filled' },
    { id: 4, date: '2026-03-18', symbol: 'SPY', side: 'Buy', quantity: 12, price: 518.6, total: 6223.2, status: 'Filled' }
  ]
}

function createDemoUser(override = {}) {
  return {
    fullName: 'example noob trade',
    email: 'demo@noobtrade.app',
    riskProfile: 'Balanced',
    membership: 'Regular User',
    joinedAt: 'March 2026',
    ...override
  }
}

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return 'TBD'
  }

  const numericValue = Number(value)
  return `${numericValue > 0 ? '+' : ''}${numericValue}%`
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(value)
}

function formatSignedCurrency(value) {
  const numericValue = Number(value || 0)
  const formattedValue = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(Math.abs(numericValue))

  return `${numericValue >= 0 ? '+' : '-'}${formattedValue}`
}

function buildMiniChartPath(values) {
  if (!values.length) {
    return ''
  }

  const width = 100
  const height = 100
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = Math.max(max - min, 1)

  return values
    .map((value, index) => {
      const x = values.length === 1 ? 50 : (index / (values.length - 1)) * width
      const y = height - (((value - min) / span) * height)
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
    })
    .join(' ')
}

function buildMiniAreaPath(values) {
  if (!values.length) {
    return ''
  }

  return `${buildMiniChartPath(values)} L 100 100 L 0 100 Z`
}

function buildAxisLabels(values, steps = 4) {
  if (!values.length) {
    return []
  }

  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = Math.max(max - min, 1)

  return Array.from({ length: steps + 1 }, (_, index) => {
    const value = max - ((span / steps) * index)
    return formatCurrency(Math.round(value))
  })
}

function buildPortfolioTimeline(positions, monthKeys) {
  return monthKeys.map((monthKey) => {
    return positions.reduce((sum, holding) => {
      if (!holding.addedMonth || holding.addedMonth > monthKey) {
        return sum
      }

      return sum + holding.marketValue
    }, 0)
  })
}

function getDefaultAddedMonth() {
  return lastSixMonths[lastSixMonths.length - 1].key
}

function getTrackedPrice(symbol) {
  if (symbol === stockResponse.value.stock.symbol) {
    return Number(stockResponse.value.stock.currentPrice)
  }

  const exploreRow = allExploreRows.value.find((row) => row.symbol === symbol)
  if (exploreRow) {
    return Number(String(exploreRow.price || '').replace('$', '').replace(',', ''))
  }

  const starredRow = dashboardWatchlistRows.value.find((row) => row.symbol === symbol)
  if (starredRow) {
    return Number(String(starredRow.price || '').replace('$', '').replace(',', ''))
  }

  return 100
}

function buildSparklinePoints(values) {
  if (!Array.isArray(values) || values.length < 2) {
    return ''
  }

  const numericValues = values.map((value) => Number(value) || 0)
  const min = Math.min(...numericValues)
  const max = Math.max(...numericValues)
  const range = max - min || 1

  return numericValues
    .map((value, index) => {
      const x = (index / Math.max(numericValues.length - 1, 1)) * 100
      const y = 100 - (((value - min) / range) * 100)
      return `${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
}

function getPortfolioSparkline(symbol) {
  const cleanedSymbol = String(symbol || '').trim().toUpperCase()
  return portfolioSparklineSeries.value[cleanedSymbol] || null
}

async function loadPortfolioSparkline(symbol) {
  const cleanedSymbol = String(symbol || '').trim().toUpperCase()

  if (!cleanedSymbol || portfolioSparklineSeries.value[cleanedSymbol]?.state === 'ready') {
    return
  }

  if (stockResponse.value?.dataSource === 'live' && stockResponse.value?.stock?.symbol === cleanedSymbol) {
    const currentSeries = stockResponse.value?.chartData?.series?.daily || []
    const currentValues = currentSeries.slice(-5).map((item) => Number(item.close)).filter((value) => Number.isFinite(value))

    if (currentValues.length >= 2) {
      portfolioSparklineSeries.value = {
        ...portfolioSparklineSeries.value,
        [cleanedSymbol]: {
          state: 'ready',
          values: currentValues,
          points: buildSparklinePoints(currentValues),
        }
      }
      return
    }
  }

  portfolioSparklineSeries.value = {
    ...portfolioSparklineSeries.value,
    [cleanedSymbol]: {
      ...(portfolioSparklineSeries.value[cleanedSymbol] || {}),
      state: 'loading',
    }
  }

  try {
    const query = new URLSearchParams({
      indicators: getSelectedIndicators().join(','),
      interval: 'daily',
      prefetch: '1',
    })
    const response = await fetch(`${API_BASE_URL}/stock/${cleanedSymbol}?${query.toString()}`)

    if (!response.ok) {
      throw new Error('Could not load sparkline data.')
    }

    const payload = await response.json()
    const dailySeries = payload?.chartData?.series?.daily || []
    const values = dailySeries.slice(-5).map((item) => Number(item.close)).filter((value) => Number.isFinite(value))

    portfolioSparklineSeries.value = {
      ...portfolioSparklineSeries.value,
      [cleanedSymbol]: {
        state: payload?.dataSource === 'live' && values.length >= 2 ? 'ready' : 'unavailable',
        values,
        points: payload?.dataSource === 'live' && values.length >= 2 ? buildSparklinePoints(values) : '',
      }
    }
  } catch {
    portfolioSparklineSeries.value = {
      ...portfolioSparklineSeries.value,
      [cleanedSymbol]: {
        state: 'unavailable',
        values: [],
        points: '',
      }
    }
  }
}

async function syncPortfolioSparklines(symbols) {
  const tasks = symbols.map((symbol) => loadPortfolioSparkline(symbol))
  await Promise.all(tasks)
}

function getSelectedIndicators() {
  return indicators.value
    .filter((indicator) => indicator.active)
    .map((indicator) => indicator.name)
}

function toggleIndicator(indicatorName) {
  indicators.value = indicators.value.map((indicator) => {
    if (indicator.name === indicatorName) {
      return { ...indicator, active: !indicator.active }
    }

    return indicator
  })
}

function navigateTo(page) {
  const normalizedPage = page === 'Analysis' ? 'Trade' : page

  if (visiblePages.value.includes(normalizedPage)) {
    activePage.value = normalizedPage
    authMessage.value = ''

    if (normalizedPage === 'Reset Password') {
      resetPasswordRequestForm.value.email = resetPasswordForm.value.email || resetPasswordRequestForm.value.email
    }

    if (normalizedPage === 'Admin' && currentUser.value?.isAdmin) {
      loadAdminUsers()
    }
  }
}

function selectPopularSymbol(symbol) {
  symbolInput.value = symbol
  runSearch()
}

function savePortfolioHolding() {
  const cleanedSymbol = portfolioForm.value.symbol.trim().toUpperCase()
  const shares = Number(portfolioForm.value.shares)

  if (!portfolioForm.value.accountName.trim() || !cleanedSymbol || !shares || shares <= 0) {
    portfolioMessage.value = 'Please enter account name, stock symbol, and a valid share count.'
    return
  }

  if (!/^[A-Z]{1,10}$/.test(cleanedSymbol)) {
    portfolioMessage.value = 'Please enter a valid stock symbol using letters only.'
    return
  }

  holdings.value.unshift({
    accountName: portfolioForm.value.accountName.trim(),
    addedMonth: getDefaultAddedMonth(),
    symbol: cleanedSymbol,
    name: `${cleanedSymbol} Holdings`,
    shares,
    costBasis: getTrackedPrice(cleanedSymbol),
    thesis: 'User-saved portfolio position',
    risk: 'Custom'
  })

  portfolioMessage.value = `${cleanedSymbol} was added to ${portfolioForm.value.accountName.trim()}. Dashboard and Portfolio totals are now synced.`
  portfolioForm.value = {
    accountName: portfolioForm.value.accountName,
    symbol: '',
    shares: 10
  }
}

function getHoldingKey(holding) {
  return `${holding.accountName}-${holding.symbol}-${holding.addedMonth}`
}

function getPortfolioAdjustment(holding) {
  const key = getHoldingKey(holding)
  const value = Number(portfolioAdjustments.value[key])
  return value > 0 ? value : 1
}

function setPortfolioAdjustment(holding, value) {
  const key = getHoldingKey(holding)
  portfolioAdjustments.value = {
    ...portfolioAdjustments.value,
    [key]: value
  }
}

function getPendingPortfolioAction(holding) {
  return pendingPortfolioActions.value[getHoldingKey(holding)] || null
}

function startPortfolioAction(holding, action) {
  const key = getHoldingKey(holding)
  pendingPortfolioActions.value = {
    ...pendingPortfolioActions.value,
    [key]: action
  }
}

function clearPortfolioAction(holding) {
  const key = getHoldingKey(holding)
  const nextActions = { ...pendingPortfolioActions.value }
  delete nextActions[key]
  pendingPortfolioActions.value = nextActions
}

function reducePortfolioHolding(holding) {
  const key = getHoldingKey(holding)
  const reductionShares = getPortfolioAdjustment(holding)
  const holdingIndex = holdings.value.findIndex((item) => getHoldingKey(item) === key)

  if (holdingIndex < 0) {
    portfolioMessage.value = 'This holding could not be found.'
    return
  }

  if (reductionShares >= holdings.value[holdingIndex].shares) {
    holdings.value.splice(holdingIndex, 1)
    portfolioMessage.value = `${holding.symbol} was removed from ${holding.accountName}.`
  } else {
    holdings.value[holdingIndex] = {
      ...holdings.value[holdingIndex],
      shares: holdings.value[holdingIndex].shares - reductionShares
    }
    portfolioMessage.value = `${reductionShares} shares were removed from ${holding.symbol} in ${holding.accountName}.`
  }

  delete portfolioAdjustments.value[key]
  clearPortfolioAction(holding)
}

function removePortfolioHolding(holding) {
  const key = getHoldingKey(holding)
  const holdingIndex = holdings.value.findIndex((item) => getHoldingKey(item) === key)

  if (holdingIndex < 0) {
    portfolioMessage.value = 'This holding could not be found.'
    return
  }

  holdings.value.splice(holdingIndex, 1)
  delete portfolioAdjustments.value[key]
  clearPortfolioAction(holding)
  portfolioMessage.value = `${holding.symbol} was fully removed from ${holding.accountName}.`
}

function confirmPortfolioAction(holding) {
  const action = getPendingPortfolioAction(holding)

  if (action === 'reduce') {
    reducePortfolioHolding(holding)
    return
  }

  if (action === 'remove') {
    removePortfolioHolding(holding)
  }
}

function openAnalysis(symbol = activeSymbol.value) {
  if (!isAuthenticated.value) {
    activePage.value = 'Sign In'
    authMessage.value = 'Please sign in first to access the trade workspace.'
    return
  }

  symbolInput.value = symbol
  activePage.value = 'Trade'

  if (symbol !== activeSymbol.value) {
    runSearch()
  }
}

function buildAnalysisCacheKey(symbol, analysisMode = 'full') {
  return [
    String(symbol || '').trim().toUpperCase(),
    selectedChartInterval.value,
    getSelectedIndicators().join(','),
    analysisMode
  ].join('|')
}

async function fetchStockAnalysis(symbol, { prefetch = false, analysisMode = 'full' } = {}) {
  const cleanedSymbol = String(symbol || '').trim().toUpperCase()
  const cacheKey = buildAnalysisCacheKey(cleanedSymbol, analysisMode)

  if (analysisCache.value[cacheKey]) {
    return analysisCache.value[cacheKey]
  }

  const query = new URLSearchParams({
    indicators: getSelectedIndicators().join(','),
    analysis: analysisMode,
  })
  query.set('interval', selectedChartInterval.value)

  if (prefetch) {
    query.set('prefetch', '1')
  }

  const response = await fetch(`${API_BASE_URL}/stock/${cleanedSymbol}?${query.toString()}`)

  if (!response.ok) {
    throw new Error('The server could not return stock data right now.')
  }

  const data = await response.json()
  analysisCache.value = {
    ...analysisCache.value,
    [cacheKey]: data
  }

  return data
}

async function primeAnalysisCache(symbol) {
  const cleanedSymbol = String(symbol || '').trim().toUpperCase()

  if (!cleanedSymbol || pendingAnalysisPrefetch.has(cleanedSymbol) || !isAuthenticated.value) {
    return
  }

  const cacheKey = buildAnalysisCacheKey(cleanedSymbol, 'search')
  if (analysisCache.value[cacheKey]) {
    return
  }

  pendingAnalysisPrefetch.add(cleanedSymbol)

  try {
    await fetchStockAnalysis(cleanedSymbol, { prefetch: true, analysisMode: 'search' })
  } catch {
    // Prefetch should stay silent and never block the main UX.
  } finally {
    pendingAnalysisPrefetch.delete(cleanedSymbol)
  }
}

async function runSearch(source = 'search') {
  const cleanedSymbol = symbolInput.value.trim().toUpperCase()

  if (!cleanedSymbol) {
    errorMessage.value = 'Please enter a stock symbol before searching.'
    return
  }

  if (!/^[A-Z]{1,10}$/.test(cleanedSymbol)) {
    errorMessage.value = 'Please enter a valid symbol using letters only, such as AAPL.'
    return
  }

  if (!isAuthenticated.value) {
    activePage.value = 'Sign In'
    authMessage.value = 'Sign in to run stock analysis and place trades.'
    return
  }

  const isGenerateAction = source === 'generate'
  if (isGenerateAction) {
    isGenerating.value = true
  } else {
    isSearching.value = true
  }
  errorMessage.value = ''

  try {
    const data = await fetchStockAnalysis(cleanedSymbol, {
      analysisMode: isGenerateAction ? 'full' : 'search'
    })

    stockResponse.value = data
    activeSymbol.value = data.stock.symbol
    symbolInput.value = data.stock.symbol
    activePage.value = 'Trade'
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        window.scrollTo({ top: 0, behavior: 'smooth' })
      })
    })
  } catch (error) {
    errorMessage.value =
      'We could not load stock data. Please make sure the Flask backend is running and try again.'
    console.error(error)
  } finally {
    if (isGenerateAction) {
      isGenerating.value = false
    } else {
      isSearching.value = false
    }
  }
}

function getHourRefreshKey(now = new Date()) {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}-${String(now.getHours()).padStart(2, '0')}`
}

function refreshFeedClock() {
  const nextKey = getHourRefreshKey()

  if (nextKey !== feedRefreshKey.value) {
    feedRefreshKey.value = nextKey
  }
}

function hashSeed(input) {
  return [...String(input)].reduce((hash, char) => ((hash * 31) + char.charCodeAt(0)) % 1000003, 7)
}

function buildFocusUniverse(symbol, refreshKey) {
  const baseIndex = hashSeed(`${symbol || 'market'}-${refreshKey}`) % top50Symbols.length
  const pool = []

  if (symbol && top50Symbols.includes(symbol)) {
    pool.push(symbol)
  }

  for (let index = 0; index < top50Symbols.length && pool.length < 5; index += 1) {
    const candidate = top50Symbols[(baseIndex + index) % top50Symbols.length]
    if (!pool.includes(candidate)) {
      pool.push(candidate)
    }
  }

  return pool
}

function buildHourlyNewsFeed(symbol, refreshKey) {
  const specificFeed = newsFeeds[symbol]
  const seed = hashSeed(`${symbol || 'market'}-news-${refreshKey}`)
  const baseFeed = (specificFeed?.length ? specificFeed : []).map((story) => ({
    ...story,
    href: story.href || buildGoogleNewsLink(symbol || 'market', story.title)
  }))
  const selectedSymbols = buildFocusUniverse(symbol, refreshKey)

  const generatedStories = selectedSymbols.map((focusSymbol, index) => {
    const titleTemplate = newsHeadlineTemplates[(seed + index) % newsHeadlineTemplates.length]
    const summaryTemplate = newsSummaryTemplates[(seed + index * 3) % newsSummaryTemplates.length]
    const source = newsSourcePool[(seed + index * 5) % newsSourcePool.length]
    const minutesAgo = 8 + (((seed + index * 17) % 6) * 11)

    return {
      title: titleTemplate.replaceAll('{symbol}', focusSymbol),
      source,
      time: minutesAgo >= 60 ? `${Math.floor(minutesAgo / 60)} hr ago` : `${minutesAgo} min ago`,
      summary: summaryTemplate,
      href: buildGoogleNewsLink(focusSymbol, titleTemplate.replaceAll('{symbol}', focusSymbol)),
      symbol: focusSymbol
    }
  })

  return [...baseFeed, ...generatedStories].slice(0, 5)
}

function buildGoogleNewsLink(symbol, title) {
  const query = `${symbol} stock news ${title}`
  return `https://news.google.com/search?q=${encodeURIComponent(query)}`
}

function formatAdminUserCode(userId) {
  const numericId = Number(userId || 0)
  return `#${String(Math.max(numericId, 0)).padStart(6, '0')}`
}

function isStarredSymbol(symbol) {
  return starredLookup.value.has(symbol)
}

function toggleStarredSymbol(symbol) {
  const cleanedSymbol = String(symbol || '').trim().toUpperCase()

  if (!cleanedSymbol) {
    return
  }

  if (isStarredSymbol(cleanedSymbol)) {
    starredSymbols.value = starredSymbols.value.filter((item) => item !== cleanedSymbol)
    return
  }

  starredSymbols.value = [...starredSymbols.value, cleanedSymbol]
}

watch(
  () => [
    activePage.value,
    currentExploreTab.value,
    exploreSearchQuery.value,
    selectedChartInterval.value,
    getSelectedIndicators().join(',')
  ],
  () => {
    if (explorePrefetchTimer) {
      window.clearTimeout(explorePrefetchTimer)
    }

    if (activePage.value !== 'Explore') {
      return
    }

    explorePrefetchTimer = window.setTimeout(() => {
      filteredExploreRows.value.slice(0, 3).forEach((row) => {
        primeAnalysisCache(row.symbol)
      })
    }, 250)
  },
  { immediate: true }
)

watch(
  () => [isAuthenticated.value, portfolioSymbols.value.join('|')],
  ([authenticated]) => {
    if (!authenticated || !portfolioSymbols.value.length) {
      return
    }

    syncPortfolioSparklines(portfolioSymbols.value)
  },
  { immediate: true }
)

watch(
  () => [stockResponse.value?.dataSource, stockResponse.value?.stock?.symbol, stockResponse.value?.chartData?.series?.daily?.length || 0],
  () => {
    const symbol = stockResponse.value?.stock?.symbol

    if (!symbol || stockResponse.value?.dataSource !== 'live') {
      return
    }

    const values = (stockResponse.value?.chartData?.series?.daily || [])
      .slice(-5)
      .map((item) => Number(item.close))
      .filter((value) => Number.isFinite(value))

    if (values.length < 2) {
      return
    }

    portfolioSparklineSeries.value = {
      ...portfolioSparklineSeries.value,
      [symbol]: {
        state: 'ready',
        values,
        points: buildSparklinePoints(values),
      }
    }
  },
  { immediate: true }
)

function buildHourlySocialFeed(symbol, refreshKey) {
  const specificFeed = postFeeds[symbol]
  const seed = hashSeed(`${symbol || 'market'}-social-${refreshKey}`)

  if (specificFeed?.length) {
    return specificFeed.map((post, index) => ({
      ...post,
      handle: socialHandlePool[(seed + index) % socialHandlePool.length],
      tone: socialTonePool[(seed + index * 2) % socialTonePool.length],
      href: buildXSearchLink(symbol || 'stocks', post.post)
    }))
  }

  return buildFocusUniverse(symbol, refreshKey)
    .slice(0, 4)
    .map((focusSymbol, index) => ({
      handle: socialHandlePool[(seed + index) % socialHandlePool.length],
      tone: socialTonePool[(seed + index * 2) % socialTonePool.length],
      post: socialPostTemplates[(seed + index * 3) % socialPostTemplates.length].replaceAll('{symbol}', focusSymbol),
      href: buildXSearchLink(focusSymbol, socialPostTemplates[(seed + index * 3) % socialPostTemplates.length].replaceAll('{symbol}', focusSymbol))
    }))
}

function buildXSearchLink(symbol, postText) {
  const query = `${symbol} stock ${postText}`
  return `https://x.com/search?q=${encodeURIComponent(query)}&src=typed_query&f=live`
}

async function parseJsonResponse(response, fallbackMessage) {
  const rawText = await response.text()

  if (!rawText) {
    return { message: fallbackMessage }
  }

  try {
    return JSON.parse(rawText)
  } catch {
    throw new Error(fallbackMessage)
  }
}

async function ensureCsrfToken() {
  if (csrfToken.value) {
    return csrfToken.value
  }

  const response = await fetch(`${API_BASE_URL}/auth/csrf-token`, {
    credentials: 'same-origin'
  })
  const payload = await parseJsonResponse(
    response,
    'Could not initialize a secure session for this page.'
  )

  if (!response.ok) {
    throw new Error(payload.message || 'Could not initialize a secure session.')
  }

  csrfToken.value = payload.csrfToken || ''
  return csrfToken.value
}

async function secureFetch(url, options = {}) {
  const method = String(options.method || 'GET').toUpperCase()
  const headers = {
    ...(options.headers || {})
  }

  if (method !== 'GET' && method !== 'HEAD') {
    headers['X-CSRF-Token'] = await ensureCsrfToken()
  }

  return fetch(url, {
    ...options,
    headers,
    credentials: 'same-origin'
  })
}

function applyAuthenticatedState(user, message = '') {
  currentUser.value = user
  isAuthenticated.value = true
  activePage.value = 'Dashboard'
  authMessage.value = message
}

async function restoreAuthenticatedSession() {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/session`, {
      credentials: 'same-origin'
    })

    if (!response.ok) {
      return false
    }

    const payload = await parseJsonResponse(
      response,
      'Could not restore the active session.'
    )

    csrfToken.value = payload.csrfToken || csrfToken.value

    if (!payload.authenticated || !payload.user) {
      return false
    }

    applyAuthenticatedState(payload.user, '')
    return true
  } catch {
    return false
  }
}

async function submitSignIn() {
  if (!signInForm.value.email || !signInForm.value.password) {
    authMessage.value = 'Please enter both email and password.'
    return
  }

  authMessage.value = 'Signing you in...'

  try {
    const response = await secureFetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        email: signInForm.value.email,
        password: signInForm.value.password
      })
    })
    const payload = await parseJsonResponse(
      response,
      'The server returned a non-JSON response. Please make sure the Flask backend is running.'
    )

    if (!response.ok) {
      if (payload.requiresEmailVerification) {
        verificationForm.value.email = signInForm.value.email
        activePage.value = 'Verify Email'
      }
      throw new Error(payload.message || 'Could not sign you in.')
    }

    csrfToken.value = payload.csrfToken || csrfToken.value
    applyAuthenticatedState(
      payload.user,
      payload.message || `Welcome back, ${payload.user.fullName}.`
    )
    restoreAuthenticatedSession().catch(() => {})
  } catch (error) {
    authMessage.value = error.message || 'Could not sign you in right now.'
  }
}

async function requestEmailVerification() {
  if (!verificationForm.value.email) {
    authMessage.value = 'Please enter your email address.'
    return
  }

  authMessage.value = 'Sending verification code...'

  try {
    const response = await secureFetch(`${API_BASE_URL}/auth/verify-email/request`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        email: verificationForm.value.email
      })
    })
    const payload = await parseJsonResponse(
      response,
      'The server returned a non-JSON response while requesting email verification.'
    )

    if (!response.ok) {
      throw new Error(payload.message || 'Could not send the verification code.')
    }

    authMessage.value = payload.message || 'Verification email sent.'
  } catch (error) {
    authMessage.value = error.message || 'Could not send the verification code right now.'
  }
}

async function submitEmailVerification() {
  if (!verificationForm.value.email || !verificationForm.value.code) {
    authMessage.value = 'Please enter both email and verification code.'
    return
  }

  authMessage.value = 'Verifying your email...'

  try {
    const response = await secureFetch(`${API_BASE_URL}/auth/verify-email/confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        email: verificationForm.value.email,
        code: verificationForm.value.code
      })
    })
    const payload = await parseJsonResponse(
      response,
      'The server returned a non-JSON response while verifying your email.'
    )

    if (!response.ok) {
      throw new Error(payload.message || 'Could not verify your email.')
    }

    signInForm.value.email = verificationForm.value.email
    authMessage.value = payload.message || 'Your email has been verified.'
    activePage.value = 'Sign In'
  } catch (error) {
    authMessage.value = error.message || 'Could not verify your email right now.'
  }
}

async function submitRegistration() {
  if (!registrationForm.value.fullName || !registrationForm.value.email || !registrationForm.value.password) {
    authMessage.value = 'Please complete name, email, and password to create the account.'
    return
  }

  authMessage.value = 'Creating your account...'

  try {
    const response = await secureFetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        fullName: registrationForm.value.fullName,
        email: registrationForm.value.email,
        password: registrationForm.value.password
      })
    })
    const payload = await parseJsonResponse(
      response,
      'The server returned a non-JSON response. Please make sure the Flask backend is running.'
    )

    if (!response.ok) {
      throw new Error(payload.message || 'Could not create your account.')
    }

    signInForm.value = {
      email: payload.user.email,
      password: ''
    }
    csrfToken.value = payload.csrfToken || csrfToken.value

    if (payload.requiresEmailVerification) {
      verificationForm.value = {
        email: payload.user.email,
        code: ''
      }
      activePage.value = 'Verify Email'
      authMessage.value = payload.message || `Account created for ${payload.user.fullName}. Verify your email to continue.`
      return
    }

    currentUser.value = payload.user
    isAuthenticated.value = true
    activePage.value = 'Dashboard'
    authMessage.value = payload.message || `Welcome to Noob Trade, ${payload.user.fullName}.`
  } catch (error) {
    authMessage.value = error.message || 'Could not create your account right now.'
  }
}

async function requestPasswordReset() {
  if (!resetPasswordRequestForm.value.email) {
    authMessage.value = 'Please enter your email address.'
    return
  }

  authMessage.value = 'Sending password reset code...'

  try {
    const response = await secureFetch(`${API_BASE_URL}/auth/password-reset/request`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        email: resetPasswordRequestForm.value.email
      })
    })
    const payload = await parseJsonResponse(
      response,
      'The server returned a non-JSON response while requesting a password reset.'
    )

    if (!response.ok) {
      throw new Error(payload.message || 'Could not send the password reset code.')
    }

    resetPasswordForm.value.email = resetPasswordRequestForm.value.email
    resetPasswordForm.value.code = ''
    resetPasswordForm.value.newPassword = ''
    authMessage.value = payload.message || 'Password reset email sent.'
    activePage.value = 'Reset Password Confirm'
  } catch (error) {
    authMessage.value = error.message || 'Could not send the password reset code right now.'
  }
}

async function submitPasswordReset() {
  if (!resetPasswordForm.value.email || !resetPasswordForm.value.code || !resetPasswordForm.value.newPassword) {
    authMessage.value = 'Please complete email, verification code, and new password.'
    return
  }

  authMessage.value = 'Resetting your password...'

  try {
    const response = await secureFetch(`${API_BASE_URL}/auth/password-reset/confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        email: resetPasswordForm.value.email,
        code: resetPasswordForm.value.code,
        newPassword: resetPasswordForm.value.newPassword
      })
    })
    const payload = await parseJsonResponse(
      response,
      'The server returned a non-JSON response while resetting your password.'
    )

    if (!response.ok) {
      throw new Error(payload.message || 'Could not reset your password.')
    }

    signInForm.value.email = resetPasswordForm.value.email
    signInForm.value.password = ''
    authMessage.value = payload.message || 'Your password has been updated.'
    activePage.value = 'Sign In'
  } catch (error) {
    authMessage.value = error.message || 'Could not reset your password right now.'
  }
}

async function loadAdminUsers() {
  if (!currentUser.value?.isAdmin) {
    adminMessage.value = 'Admin access is required.'
    return
  }

  isAdminLoading.value = true
  adminMessage.value = ''

  try {
    const response = await secureFetch(`${API_BASE_URL}/auth/users`)
    const payload = await response.json()

    if (!response.ok) {
      throw new Error(payload.message || 'Could not load registered users.')
    }

    adminUsers.value = payload.users || []
  } catch (error) {
    adminMessage.value = error.message || 'Could not load registered users right now.'
  } finally {
    isAdminLoading.value = false
  }
}

async function updateAdminUserStatus(user, isDisabled) {
  if (!currentUser.value?.isAdmin) {
    adminMessage.value = 'Admin access is required.'
    return
  }

  adminMessage.value = `${isDisabled ? 'Disabling' : 'Re-enabling'} ${user.email}...`
  pendingAdminStatusUpdates.value = {
    ...pendingAdminStatusUpdates.value,
    [String(user?.id ?? '')]: true
  }

  try {
    const response = await secureFetch(`${API_BASE_URL}/auth/users/${user.id}/status`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        isDisabled
      })
    })
    const payload = await response.json()

    if (!response.ok) {
      throw new Error(payload.message || 'Could not update this user.')
    }

    adminUsers.value = adminUsers.value.map((item) => item.id === user.id ? payload.user : item)
    adminMessage.value = payload.message || `${isDisabled ? 'Disabled' : 'Re-enabled'} ${user.email}.`
  } catch (error) {
    adminMessage.value = error.message || 'Could not update this user right now.'
  } finally {
    const nextPending = { ...pendingAdminStatusUpdates.value }
    delete nextPending[String(user?.id ?? '')]
    pendingAdminStatusUpdates.value = nextPending
  }
}

async function resetAdminUserPassword(user) {
  if (!currentUser.value?.isAdmin) {
    adminMessage.value = 'Admin access is required.'
    return
  }

  const key = String(user?.id ?? '')
  const draftPassword = adminPasswordResetDrafts.value[key] ?? ''

  if (!draftPassword) {
    adminMessage.value = 'Please enter a new password before submitting the reset.'
    return
  }

  adminMessage.value = `Resetting password for ${user.email}...`
  pendingAdminPasswordResets.value = {
    ...pendingAdminPasswordResets.value,
    [key]: true
  }

  try {
    const response = await secureFetch(`${API_BASE_URL}/auth/users/${user.id}/reset-password`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        newPassword: draftPassword
      })
    })
    const payload = await response.json()

    if (!response.ok) {
      throw new Error(payload.message || 'Could not reset this password.')
    }

    adminMessage.value = payload.message || `Password reset for ${user.email} was successful.`
    const nextDrafts = { ...adminPasswordResetDrafts.value }
    delete nextDrafts[key]
    adminPasswordResetDrafts.value = nextDrafts
  } catch (error) {
    adminMessage.value = error.message || 'Could not reset this password right now.'
  } finally {
    const nextPending = { ...pendingAdminPasswordResets.value }
    delete nextPending[key]
    pendingAdminPasswordResets.value = nextPending
  }
}

function openAdminPasswordReset(user) {
  const key = String(user?.id ?? '')
  adminPasswordResetDrafts.value = {
    ...adminPasswordResetDrafts.value,
    [key]: adminPasswordResetDrafts.value[key] ?? ''
  }
  adminMessage.value = `Enter a new password for ${user.email}.`
}

function cancelAdminPasswordReset(user) {
  const key = String(user?.id ?? '')
  const nextDrafts = { ...adminPasswordResetDrafts.value }
  delete nextDrafts[key]
  adminPasswordResetDrafts.value = nextDrafts
}

function signOut() {
  secureFetch(`${API_BASE_URL}/auth/logout`, {
    method: 'POST'
  }).catch(() => {})
  isAuthenticated.value = false
  currentUser.value = null
  activePage.value = 'Home'
  authMessage.value = ''
  adminUsers.value = []
  adminMessage.value = ''
  pendingAdminStatusUpdates.value = {}
  pendingAdminPasswordResets.value = {}
  adminPasswordResetDrafts.value = {}
  csrfToken.value = ''
  signInForm.value = {
    email: '',
    password: ''
  }
  verificationForm.value = {
    email: '',
    code: ''
  }
  resetPasswordForm.value = {
    email: '',
    code: '',
    newPassword: ''
  }
}

function openHistoricalReplay(pattern) {
  replayPattern.value = pattern
  replayInterval.value = pattern?.timeframe || 'daily'
}

function closeHistoricalReplay() {
  replayPattern.value = null
}

if (import.meta.env.DEV && typeof window !== 'undefined') {
  window.__NOOB_TRADE_E2E__ = {
    signIn() {
      currentUser.value = createDemoUser()
      isAuthenticated.value = true
      activePage.value = 'Dashboard'
      authMessage.value = ''

      return {
        activePage: activePage.value,
        activeSymbol: activeSymbol.value,
        isAuthenticated: isAuthenticated.value
      }
    },
    signOut() {
      signOut()
    },
    applyResponse(responseData) {
      stockResponse.value = responseData
      activeSymbol.value = responseData.stock.symbol
      symbolInput.value = responseData.stock.symbol
      selectedChartInterval.value = responseData.request.interval
      errorMessage.value = ''

      return {
        activePage: activePage.value,
        activeSymbol: activeSymbol.value,
        errorMessage: errorMessage.value
      }
    },
    async search(symbol, options = {}) {
      if (options.interval) {
        selectedChartInterval.value = options.interval
      }

      if (Array.isArray(options.indicators)) {
        const desiredIndicators = new Set(options.indicators)
        indicators.value = indicators.value.map((indicator) => ({
          ...indicator,
          active: desiredIndicators.has(indicator.name)
        }))
      }

      symbolInput.value = symbol
      await runSearch()

      return {
        activePage: activePage.value,
        activeSymbol: activeSymbol.value,
        errorMessage: errorMessage.value
      }
    },
    setPage(page) {
      const normalizedPage = page === 'Analysis' ? 'Trade' : page
      if (visiblePages.value.includes(normalizedPage)) {
        activePage.value = normalizedPage
      }
    },
    setInterval(interval) {
      if (chartIntervals.includes(interval)) {
        selectedChartInterval.value = interval
      }

      return {
        selectedInterval: selectedChartInterval.value
      }
    },
    getState() {
      return {
        activePage: activePage.value,
        activeSymbol: activeSymbol.value,
        errorMessage: errorMessage.value,
        selectedInterval: selectedChartInterval.value,
        isAuthenticated: isAuthenticated.value
      }
    }
  }
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="topbar-brand-block">
        <div class="topbar-brand">Noob Trade</div>
        <div class="topbar-brand-meta">
          {{ isAuthenticated ? '' : 'Stock analysis platform for new traders' }}
        </div>
      </div>

      <nav class="topbar-nav">
        <button
          v-for="page in visiblePages"
          :key="page"
          class="topbar-link"
          :class="{ active: activePage === page }"
          @click="navigateTo(page)"
        >
          {{ page }}
        </button>
      </nav>

      <div class="topbar-actions">
        <button
          v-if="canInstallApp"
          class="topbar-button secondary"
          @click="triggerInstall"
        >
          Install App
        </button>
        <template v-if="isAuthenticated">
          <button class="topbar-button" @click="signOut">Sign out</button>
        </template>
        <template v-else>
          <button class="topbar-button secondary" @click="navigateTo('Sign In')">Sign In</button>
          <button class="topbar-button" @click="navigateTo('Register')">Create Account</button>
        </template>
      </div>
    </header>

    <main v-if="!isAuthenticated && activePage === 'Home'" class="product-page public-page">
      <section class="hero-surface public-hero">
        <div class="public-hero-copy">
          <p class="eyebrow">Public Home</p>
          <h1 class="page-title">Learn the tape before you risk real money.</h1>
          <p class="page-subtitle">
            Noob Trade gives unauthenticated visitors a clear story: search-driven stock analysis,
            guided decision support, and a mock trading workflow that becomes richer after sign-in.
          </p>
          <div class="hero-actions">
            <button class="topbar-button" @click="navigateTo('Register')">Create an account</button>
            <button class="topbar-button secondary" @click="navigateTo('Sign In')">I already have access</button>
          </div>
        </div>

        <div class="public-hero-visual">
          <div class="public-hero-panel">
            <span class="section-chip">Preview</span>
            <h2>Before login</h2>
            <p>See what the product does, what data it will help track, and why the dashboard matters.</p>
          </div>
          <div class="public-hero-metrics">
            <article v-for="card in publicFeatureRows" :key="card.title" class="public-feature-item">
              <strong>{{ card.title }}</strong>
              <p>{{ card.description }}</p>
            </article>
          </div>
        </div>
      </section>

      <section class="home-feature-strip">
        <article class="stat-card home-feature-card">
          <p>Core Workspace</p>
          <h2>Trade + Explore</h2>
          <span>Scan the market, compare setups, and step into a guided trade workflow.</span>
        </article>
        <article class="stat-card home-feature-card">
          <p>User Account View</p>
          <h2>Portfolio View</h2>
          <span>Track holdings, position value, and your account story after signing in.</span>
        </article>
      </section>
    </main>

    <main v-else-if="!isAuthenticated && activePage === 'Sign In'" class="product-page auth-page">
      <section class="auth-shell">
        <article class="auth-card">
          <p class="eyebrow">User Authentication</p>
          <h1>Sign in to your workspace</h1>
          <p class="page-subtitle">
            Sign in with your registered email and password to open your Noob Trade dashboard.
          </p>

          <form @submit.prevent="submitSignIn">
            <div v-if="authMessage" class="status-message loading-message">
              {{ authMessage }}
            </div>

            <div class="auth-form-grid">
              <label class="auth-field">
                <span>Email</span>
                <input v-model="signInForm.email" type="email" placeholder="noobtrade@example.com" />
              </label>
              <label class="auth-field">
                <span>Password</span>
                <input v-model="signInForm.password" type="password" placeholder="Enter your password" />
              </label>
            </div>

            <div class="auth-actions">
              <button class="topbar-button" type="submit">Sign In</button>
              <button class="topbar-button secondary" type="button" @click="navigateTo('Register')">Create New Account</button>
            </div>
          </form>

          <div class="auth-actions">
            <button class="topbar-button secondary" type="button" @click="navigateTo('Verify Email')">Verify Email</button>
            <button class="topbar-button secondary" type="button" @click="navigateTo('Reset Password')">Forgot Password</button>
          </div>
        </article>
      </section>
    </main>

    <main v-else-if="!isAuthenticated && activePage === 'Register'" class="product-page auth-page">
      <section class="auth-shell">
        <article class="auth-card">
          <p class="eyebrow">New User Registration</p>
          <h1>Create your Noob Trade account</h1>
          <p class="page-subtitle">
            Create an account with your email and password. Regular users must verify by email, while the preconfigured admin accounts can sign in directly.
          </p>

          <form @submit.prevent="submitRegistration">
            <div v-if="authMessage" class="status-message loading-message">
              {{ authMessage }}
            </div>

            <div class="auth-form-grid two-columns">
              <label class="auth-field">
                <span>Full Name</span>
                <input v-model="registrationForm.fullName" type="text" placeholder="example noob trade" />
              </label>
              <label class="auth-field">
                <span>Email</span>
                <input v-model="registrationForm.email" type="email" placeholder="noobtrade@example.com" />
              </label>
              <label class="auth-field">
                <span>Password</span>
                <input v-model="registrationForm.password" type="password" placeholder="Create a password" />
                <small class="auth-field-hint">Use at least 8 characters and include one special symbol such as _, !, or #.</small>
              </label>
            </div>

            <div class="auth-actions">
              <button class="topbar-button" type="submit">Create Account</button>
              <button class="topbar-button secondary" type="button" @click="navigateTo('Sign In')">Back to Sign In</button>
            </div>
          </form>
        </article>
      </section>
    </main>

    <main v-else-if="!isAuthenticated && activePage === 'Verify Email'" class="product-page auth-page">
      <section class="auth-shell">
        <article class="auth-card">
          <p class="eyebrow">Email Verification</p>
          <h1>Verify your email</h1>
          <p class="page-subtitle">
            Enter the verification code from your inbox. You can also resend a fresh code if needed.
          </p>

          <form @submit.prevent="submitEmailVerification">
            <div v-if="authMessage" class="status-message loading-message">
              {{ authMessage }}
            </div>

            <div class="auth-form-grid">
              <label class="auth-field">
                <span>Email</span>
                <input v-model="verificationForm.email" type="email" placeholder="noobtrade@example.com" />
              </label>
              <label class="auth-field">
                <span>Verification Code</span>
                <input v-model="verificationForm.code" type="text" inputmode="numeric" placeholder="123456" />
              </label>
            </div>

            <div class="auth-actions">
              <button class="topbar-button" type="submit">Verify Email</button>
              <button class="topbar-button secondary" type="button" @click="requestEmailVerification">Resend Code</button>
            </div>
          </form>

          <div class="auth-actions">
            <button class="topbar-button secondary" type="button" @click="navigateTo('Sign In')">Back to Sign In</button>
          </div>
        </article>
      </section>
    </main>

    <main v-else-if="!isAuthenticated && activePage === 'Reset Password'" class="product-page auth-page">
      <section class="auth-shell">
        <article class="auth-card">
          <p class="eyebrow">Password Recovery</p>
          <h1>Request a password reset code</h1>
          <p class="page-subtitle">
            Enter your email and we will send a verification code. After that, you will move to the reset password page.
          </p>

          <form @submit.prevent="requestPasswordReset">
            <div v-if="authMessage" class="status-message loading-message">
              {{ authMessage }}
            </div>

            <div class="auth-form-grid">
              <label class="auth-field">
                <span>Email</span>
                <input v-model="resetPasswordRequestForm.email" type="email" placeholder="noobtrade@example.com" />
              </label>
            </div>

            <div class="auth-actions">
              <button class="topbar-button" type="submit">Send Reset Code</button>
              <button class="topbar-button secondary" type="button" @click="navigateTo('Reset Password Confirm')">I already have a code</button>
            </div>
          </form>

          <div class="auth-actions">
            <button class="topbar-button secondary" type="button" @click="navigateTo('Sign In')">Back to Sign In</button>
          </div>
        </article>
      </section>
    </main>

    <main v-else-if="!isAuthenticated && activePage === 'Reset Password Confirm'" class="product-page auth-page">
      <section class="auth-shell">
        <article class="auth-card">
          <p class="eyebrow">Password Recovery</p>
          <h1>Reset your password</h1>
          <p class="page-subtitle">
            Enter the verification code from your email, then create a new password to finish the reset.
          </p>

          <form @submit.prevent="submitPasswordReset">
            <div v-if="authMessage" class="status-message loading-message">
              {{ authMessage }}
            </div>

            <div class="auth-form-grid two-columns">
              <label class="auth-field">
                <span>Email</span>
                <input v-model="resetPasswordForm.email" type="email" placeholder="noobtrade@example.com" />
              </label>
              <label class="auth-field">
                <span>Verification Code</span>
                <input v-model="resetPasswordForm.code" type="text" inputmode="numeric" placeholder="123456" />
              </label>
              <label class="auth-field">
                <span>New Password</span>
                <input v-model="resetPasswordForm.newPassword" type="password" placeholder="Create a new password" />
                <small class="auth-field-hint">Use at least 8 characters and include one special symbol such as _, !, or #.</small>
              </label>
            </div>

            <div class="auth-actions">
              <button class="topbar-button" type="submit">Update Password</button>
              <button class="topbar-button secondary" type="button" @click="navigateTo('Reset Password')">Send a new code</button>
            </div>
          </form>

          <div class="auth-actions">
            <button class="topbar-button secondary" type="button" @click="navigateTo('Sign In')">Back to Sign In</button>
          </div>
        </article>
      </section>
    </main>

    <main v-else-if="activePage === 'Dashboard'" class="product-page">
      <section class="hero-surface compact dashboard-landing">
        <div class="dashboard-balance-panel">
          <p class="eyebrow">Dashboard</p>
          <h1 class="page-title">Total assets and watchlist at a glance.</h1>
          <p class="page-subtitle">
            This is the authenticated home page: a cleaner Noob Trade version of an exchange dashboard, with account value,
            six-month movement, and fast entry points into your core workflow.
          </p>

          <div class="dashboard-balance-row">
            <div>
              <span class="dashboard-label">Total Asset Estimate</span>
              <strong class="dashboard-balance-value">{{ formatCurrency(totalAssetValue) }}</strong>
            </div>
            <span class="dashboard-currency-chip">USD</span>
          </div>

          <div class="dashboard-performance">
            <span>6M Performance</span>
            <strong :class="sixMonthPnl >= 0 ? 'positive' : 'negative'">
              {{ formatSignedCurrency(sixMonthPnl) }} ({{ formatPercent(sixMonthPnlPercent.toFixed(2)) }})
            </strong>
          </div>

          <div class="dashboard-action-row">
            <button class="topbar-button" @click="navigateTo('Portfolio')">Open Portfolio</button>
            <button class="topbar-button secondary" @click="navigateTo('Explore')">Open Explore</button>
          </div>
        </div>

        <div class="dashboard-chart-panel">
          <div class="dashboard-chart-copy">
            <span class="section-chip">6 Month Equity Curve</span>
            <span class="dashboard-chart-note">Cash + active holdings</span>
          </div>

          <div class="dashboard-mini-chart">
            <div class="dashboard-chart-grid"></div>
            <div class="dashboard-axis dashboard-axis-y">
              <span v-for="label in dashboardYAxis" :key="label">{{ label }}</span>
            </div>
            <div class="dashboard-axis dashboard-axis-x">
              <span v-for="label in dashboardXAxis" :key="label">{{ label }}</span>
            </div>
            <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
              <defs>
                <linearGradient id="dashboardFill" x1="0%" x2="0%" y1="0%" y2="100%">
                  <stop offset="0%" stop-color="rgba(255, 138, 0, 0.28)" />
                  <stop offset="100%" stop-color="rgba(255, 138, 0, 0.02)" />
                </linearGradient>
              </defs>
              <path class="dashboard-area" :d="dashboardAreaPath" fill="url(#dashboardFill)" />
              <path class="dashboard-line-shadow" :d="dashboardAssetPath" />
              <path class="dashboard-line" :d="dashboardAssetPath" />
            </svg>
          </div>
        </div>
      </section>

      <section class="stats-strip dashboard-summary-strip">
        <article v-for="stat in dashboardStats" :key="stat.label" class="stat-card dashboard-stat-card">
          <p>{{ stat.label }}</p>
          <h2>{{ stat.value }}</h2>
          <span>{{ stat.note }}</span>
        </article>
      </section>

      <section class="dashboard-grid">
        <article class="table-surface dashboard-card">
          <div class="table-header">
            <h2>Self-Selected Stocks</h2>
            <span class="section-chip">{{ starredSymbols.length }} saved</span>
          </div>
          <div v-if="dashboardWatchlistRows.length" class="data-table">
            <div class="data-row data-head dashboard-watchlist-head">
              <span>Symbol</span>
              <span>Price</span>
              <span>1D</span>
              <span>Star</span>
            </div>
            <div v-for="row in dashboardWatchlistRows" :key="row.symbol" class="data-row dashboard-watchlist-row">
              <button class="watchlist-link explore-symbol-link" @click="openAnalysis(row.symbol)">{{ row.symbol }}</button>
              <span>{{ row.price }}</span>
              <strong :class="row.tone">{{ row.change }}</strong>
              <button
                type="button"
                class="star-toggle"
                :class="{ active: isStarredSymbol(row.symbol) }"
                :aria-label="isStarredSymbol(row.symbol) ? `Remove ${row.symbol} from starred stocks` : `Star ${row.symbol}`"
                @click="toggleStarredSymbol(row.symbol)"
              >
                {{ isStarredSymbol(row.symbol) ? '★' : '☆' }}
              </button>
            </div>
          </div>
          <div v-else class="empty-state empty-state--compact">
            Star stocks in Explore and they will appear here as your self-selected list.
          </div>
        </article>

        <article class="table-surface dashboard-card">
          <div class="table-header">
            <h2>Favorites Flow</h2>
            <button class="chip active" @click="navigateTo('Explore')">Open Explore</button>
          </div>
          <div class="dashboard-card-grid">
            <div class="dashboard-mini-card">
              <span>Saved stars</span>
              <strong>{{ starredSymbols.length }}</strong>
              <small>Your favorite names stay pinned to the dashboard.</small>
            </div>
            <div class="dashboard-mini-card">
              <span>Current focus</span>
              <strong>{{ activeSymbol }}</strong>
              <small>Search in Trade or Explore, then star the names you want to keep visible.</small>
            </div>
            <div class="dashboard-mini-card">
              <span>Best next step</span>
              <strong>Star from Explore</strong>
              <small>Use the right-side star icon to add or remove symbols instantly.</small>
            </div>
          </div>
        </article>

        <article class="table-surface dashboard-card">
          <div class="table-header">
            <h2>Desk Notices</h2>
            <span class="section-chip">Updated today</span>
          </div>
          <div class="task-list">
            <div v-for="notice in dashboardAnnouncements" :key="notice.label" class="task-row">
              <strong>{{ notice.label }}</strong>
              <span>{{ notice.detail }}</span>
              <small>{{ notice.tag }}</small>
            </div>
          </div>
        </article>

        <article class="table-surface dashboard-card">
          <div class="table-header">
            <h2>Recent Activity</h2>
            <span class="section-chip">Latest orders</span>
          </div>
          <div class="activity-list">
            <div v-for="item in recentTransactions.slice(0, 4)" :key="item.id" class="activity-row">
              <strong>{{ item.side }} {{ item.symbol }}</strong>
              <span>{{ item.quantity }} shares</span>
              <small>{{ item.date }}</small>
            </div>
          </div>
        </article>
      </section>
    </main>

    <main v-else-if="activePage === 'Trade'" class="dashboard-layout">
      <section class="column panel left-panel">
        <div class="panel-topbar brand-bar">
          <div class="brand-mark">
            <span class="brand-title trade-title">Trade</span>
          </div>
          <button class="menu-button" type="button">≡</button>
        </div>

        <div class="search-block">
          <h1>Noob Trade Desk</h1>
          <p class="page-lead">
            Search a symbol, evaluate pattern context, compare historical matches, and decide whether to buy or sell.
          </p>
          <div class="source-banner" :class="`source-banner--${dataSourceMeta.tone}`">
            <span class="source-banner-label">Data Source</span>
            <strong>{{ dataSourceMeta.label }}</strong>
            <small>{{ dataSourceMeta.description }}</small>
          </div>

          <SearchBar
            v-model="symbolInput"
            :error-message="errorMessage"
            :is-loading="isSearching"
            @search="runSearch('search')"
            @select-popular="selectPopularSymbol"
          />
        </div>

        <div class="market-card market-card-stack">
          <div class="section-header">Market Overview</div>
          <div class="market-stack">
            <article
              v-for="card in marketOverviewCards"
              :key="card.name"
              class="market-stack-card"
            >
              <span class="market-stack-name">{{ card.name }}</span>
              <strong :class="card.tone">{{ card.change }}</strong>
              <small>{{ card.level }}</small>
            </article>
          </div>
        </div>
      </section>

      <section class="column panel center-panel">
        <div class="panel-topbar">
          <div class="panel-heading-group">
            <h2>{{ activeSymbol }} Trade Setup</h2>
            <span class="source-pill" :class="`source-pill--${dataSourceMeta.tone}`">
              {{ dataSourceMeta.label }}
            </span>
          </div>
        </div>

        <ChartPanel
          :active-indicators="appliedIndicators"
          :active-symbol="activeSymbol"
          :chart-data="stockResponse.chartData"
          :chart-intervals="chartIntervals"
          :company-name="stockResponse.stock.companyName"
          :industry="stockResponse.stock.industry"
          :selected-interval="selectedChartInterval"
          :sector="stockResponse.stock.sector"
          @update:selected-interval="selectedChartInterval = $event"
        />

        <IndicatorSelector
          :indicators="indicators"
          :is-loading="isGenerating"
          @run-analysis="runSearch('generate')"
          @toggle-indicator="toggleIndicator"
        />
      </section>

      <section class="column panel right-panel">
        <div class="panel-topbar">
          <div class="panel-heading-group">
            <h2>{{ activeSymbol }} Forecast</h2>
            <span class="source-pill" :class="`source-pill--${dataSourceMeta.tone}`">
              {{ dataSourceMeta.label }}
            </span>
          </div>
        </div>

        <PredictionSummary
          :format-percent="formatPercent"
          :request-data="stockResponse.request"
          :analysis-data="stockResponse.patternAnalysis"
        />

        <MatchedPatterns
          :matched-patterns="stockResponse.patternAnalysis.matchedHistoricalPatterns"
          :high-fit-paths="stockResponse.patternAnalysis.highFitHistoricalPaths"
          @open-replay="openHistoricalReplay"
        />

      </section>
    </main>

    <main v-else-if="activePage === 'Explore'" class="product-page">
      <section class="hero-surface compact explore-hero">
        <div>
          <p class="eyebrow">Explore</p>
          <h1 class="page-title">{{ exploreViewMode === 'full' ? 'Full market board for scrolling the entire list.' : 'Ranked market board for scanning all stocks.' }}</h1>
          <p class="page-subtitle">
            {{ exploreViewMode === 'full'
              ? 'This full-board mode is built for scrolling through the complete market list in one long page before jumping into Trade.'
              : 'This is the broad market discovery page: rankings, movers, gainers, and volume leaders in one place before you drill into Trade.' }}
          </p>
        </div>
      </section>

      <section class="explore-toolbar">
        <label class="explore-search-field">
          <span>Search stocks</span>
          <input
            v-model="exploreSearchQuery"
            type="search"
            placeholder="Search symbol or company"
          />
        </label>
        <div class="table-filters">
          <button
            v-for="tab in exploreTabs"
            :key="tab"
            class="chip"
            :class="{ active: currentExploreTab === tab }"
            @click="exploreViewMode = 'ranked'; currentExploreTab = tab"
          >
            {{ tab }}
          </button>
        </div>
        <div class="explore-toolbar-actions">
          <button
            class="topbar-button secondary"
            @click="exploreViewMode = exploreViewMode === 'full' ? 'ranked' : 'full'"
          >
            {{ exploreViewMode === 'full' ? 'Back To Ranked View' : 'Open Full Market Board' }}
          </button>
        </div>
      </section>

      <section class="explore-layout" :class="{ 'explore-layout--full': exploreViewMode === 'full' }">
        <article class="table-surface">
          <div class="table-header">
            <h2>{{ exploreSearchQuery ? 'Search Results' : exploreViewMode === 'full' ? 'Full Market Board' : currentExploreTab }}</h2>
            <span class="section-chip">Ranked</span>
          </div>

          <div class="data-table">
            <div class="data-row data-head explore-head">
              <span>Symbol</span>
              <span>Name</span>
              <span>Category</span>
              <span>Price</span>
              <span>Market Value</span>
              <span>1D</span>
              <span>Star</span>
            </div>
            <div
              v-for="row in filteredExploreRows"
              :key="row.symbol + row.category"
              class="data-row explore-row"
            >
              <button
                class="watchlist-link explore-symbol-link"
                @mouseenter="primeAnalysisCache(row.symbol)"
                @focus="primeAnalysisCache(row.symbol)"
                @click="openAnalysis(row.symbol)"
              >
                {{ row.symbol }}
              </button>
              <span>{{ row.name }}</span>
              <span>{{ row.category }}</span>
              <span>{{ row.price }}</span>
              <span>{{ row.notional }}</span>
              <strong :class="row.tone">{{ row.change }}</strong>
              <button
                type="button"
                class="star-toggle"
                :class="{ active: isStarredSymbol(row.symbol) }"
                :aria-label="isStarredSymbol(row.symbol) ? `Remove ${row.symbol} from starred stocks` : `Star ${row.symbol}`"
                @click="toggleStarredSymbol(row.symbol)"
              >
                {{ isStarredSymbol(row.symbol) ? '★' : '☆' }}
              </button>
            </div>
          </div>
        </article>

        <article v-if="exploreViewMode !== 'full'" class="table-surface explore-sidecard">
          <div class="table-header">
            <h2>Board Context</h2>
            <span class="section-chip">Snapshot</span>
          </div>
          <div class="dashboard-card-grid">
            <div class="dashboard-mini-card">
              <span>Current focus</span>
              <strong>{{ activeSymbol }}</strong>
              <small>Search any ticker, then star it into your dashboard.</small>
            </div>
            <div class="dashboard-mini-card">
              <span>Saved stars</span>
              <strong>{{ starredSymbols.length }}</strong>
              <small>Your dashboard watchlist updates from this board.</small>
            </div>
            <div class="dashboard-mini-card">
              <span>Best next step</span>
              <strong>Open full board</strong>
              <small>Use the full-board button when you want a long scrollable list instead of a short ranked panel.</small>
            </div>
          </div>
        </article>
      </section>
    </main>

    <main v-else-if="activePage === 'Portfolio'" class="product-page">
      <section class="hero-surface compact portfolio-hero">
        <div>
          <p class="eyebrow">Portfolio</p>
          <h1 class="page-title">Your holdings, pricing, and current position value.</h1>
          <p class="page-subtitle">
            A clean holdings page between Trade and Explore, focused on what you own now, what it is worth, and how the account has moved over the last six months.
          </p>
        </div>

        <div class="dashboard-mini-chart portfolio-mini-chart">
          <div class="dashboard-chart-grid"></div>
          <div class="dashboard-axis dashboard-axis-y">
            <span v-for="label in portfolioYAxis" :key="label">{{ label }}</span>
          </div>
          <div class="dashboard-axis dashboard-axis-x">
            <span v-for="label in dashboardXAxis" :key="label">{{ label }}</span>
          </div>
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <linearGradient id="portfolioFillTop" x1="0%" x2="0%" y1="0%" y2="100%">
                <stop offset="0%" stop-color="rgba(255, 138, 0, 0.28)" />
                <stop offset="100%" stop-color="rgba(255, 138, 0, 0.02)" />
              </linearGradient>
            </defs>
            <path class="dashboard-area" :d="portfolioAreaPath" fill="url(#portfolioFillTop)" />
            <path class="dashboard-line-shadow" :d="portfolioChartPath" />
            <path class="dashboard-line" :d="portfolioChartPath" />
          </svg>
        </div>
      </section>

      <section class="table-surface portfolio-entry-card">
        <div class="table-header">
          <h2>Save Holdings to Portfolio</h2>
          <span class="section-chip">Bookkeeping</span>
        </div>

        <div class="portfolio-entry-grid">
          <label class="trade-ticket-field">
            <span>Account Name</span>
            <input v-model="portfolioForm.accountName" type="text" placeholder="Family Account" />
          </label>
          <label class="trade-ticket-field">
            <span>Stock Symbol</span>
            <input v-model="portfolioForm.symbol" type="text" placeholder="AAPL" />
          </label>
          <label class="trade-ticket-field">
            <span>Shares</span>
            <input v-model="portfolioForm.shares" min="1" type="number" />
          </label>
        </div>

        <div class="trade-ticket-actions">
          <button class="topbar-button" @click="savePortfolioHolding">Add</button>
        </div>
        <p class="page-subtitle">
          Saved holdings are marked with the current linked stock price. The six-month curve stays flat at zero until a holding is created, then steps higher as positions are added.
        </p>
        <p v-if="portfolioMessage" class="status-message loading-message">{{ portfolioMessage }}</p>
      </section>

      <section class="stats-strip portfolio-summary-strip">
        <article class="stat-card">
          <p>Total Assets</p>
          <h2>{{ formatCurrency(totalAssetValue) }}</h2>
          <span>Synced with the dashboard total</span>
        </article>
        <article class="stat-card">
          <p>Total Cost Basis</p>
          <h2>{{ formatCurrency(portfolioSummary.totalCost) }}</h2>
          <span>Original recorded capital committed to holdings</span>
        </article>
        <article class="stat-card">
          <p>Largest Position</p>
          <h2>{{ portfolioSummary.biggestPosition?.symbol || 'N/A' }}</h2>
          <span>{{ portfolioSummary.biggestPosition ? `${portfolioSummary.biggestPosition.allocation.toFixed(0)}% allocation` : 'No allocation data' }}</span>
        </article>
        <article class="stat-card">
          <p>Top Winner</p>
          <h2>{{ portfolioSummary.topWinner?.symbol || 'N/A' }}</h2>
          <span>{{ portfolioSummary.topWinner ? formatSignedCurrency(portfolioSummary.topWinner.pnl) : 'No P/L yet' }}</span>
        </article>
      </section>

      <section class="portfolio-layout">
        <article class="table-surface portfolio-table-card">
          <div class="table-header">
            <h2>Open Positions</h2>
            <button class="chip" @click="navigateTo('Trade')">Open Trade</button>
          </div>
          <div class="data-table">
            <div class="data-row data-head portfolio-holdings-head">
              <span>Stock</span>
              <span>Price</span>
              <span>Position Value</span>
              <span>Trend</span>
              <span>Adjust</span>
            </div>
            <div v-for="holding in holdingsWithMetrics" :key="`${holding.accountName}-${holding.symbol}-${holding.addedMonth}`" class="data-row portfolio-holdings-row">
              <div class="portfolio-stock-cell">
                <strong>{{ holding.symbol }}</strong>
                <small>{{ holding.accountName }} · {{ holding.shares }} shares</small>
              </div>
              <span>{{ formatCurrency(holding.currentPrice) }}</span>
              <div class="portfolio-value-cell">
                <strong>{{ formatCurrency(holding.marketValue) }}</strong>
                <small :class="holding.pnl >= 0 ? 'positive' : 'negative'">{{ formatSignedCurrency(holding.pnl) }}</small>
              </div>
              <div class="portfolio-trend-cell">
                <div v-if="getPortfolioSparkline(holding.symbol)?.state === 'ready'" class="portfolio-sparkline-card">
                  <svg viewBox="0 0 100 100" preserveAspectRatio="none" class="portfolio-sparkline-svg" aria-hidden="true">
                    <line class="portfolio-sparkline-grid" x1="0" y1="0" x2="0" y2="100" />
                    <line class="portfolio-sparkline-grid" x1="0" y1="100" x2="100" y2="100" />
                    <polyline
                      class="portfolio-sparkline-line"
                      fill="none"
                      :points="getPortfolioSparkline(holding.symbol)?.points"
                    />
                  </svg>
                  <small>Live 5D</small>
                </div>
                <div v-else-if="getPortfolioSparkline(holding.symbol)?.state === 'loading'" class="portfolio-sparkline-card portfolio-sparkline-card--muted">
                  <small>Loading live...</small>
                </div>
                <div v-else class="portfolio-sparkline-card portfolio-sparkline-card--muted">
                  <small>Live API required</small>
                </div>
              </div>
              <div class="portfolio-adjust-cell">
                <input
                  :value="getPortfolioAdjustment(holding)"
                  class="portfolio-adjust-input"
                  min="1"
                  type="number"
                  @input="setPortfolioAdjustment(holding, $event.target.value)"
                />
                <div class="portfolio-adjust-actions">
                  <template v-if="getPendingPortfolioAction(holding)">
                    <button class="chip chip-confirm" @click="confirmPortfolioAction(holding)">Confirm</button>
                    <button class="chip chip-muted" @click="clearPortfolioAction(holding)">Cancel</button>
                  </template>
                  <template v-else>
                    <button class="chip" @click="startPortfolioAction(holding, 'reduce')">Reduce</button>
                    <button class="chip chip-danger" @click="startPortfolioAction(holding, 'remove')">Remove</button>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </article>

      </section>

      <section class="table-surface portfolio-detail-card">
        <div class="table-header">
          <h2>Position Detail</h2>
          <button class="chip" @click="navigateTo('Explore')">Open Explore</button>
        </div>
        <div class="data-table">
          <div class="data-row data-head portfolio-head">
            <span>Symbol</span>
            <span>Shares</span>
            <span>Cost Basis</span>
            <span>Current Price</span>
            <span>Market Value</span>
            <span>P/L</span>
            <span>Allocation</span>
          </div>
          <div v-for="holding in holdingsWithMetrics" :key="`${holding.accountName}-${holding.symbol}-${holding.addedMonth}-detail`" class="data-row portfolio-row">
            <span>{{ holding.symbol }}</span>
            <span>{{ holding.shares }}</span>
            <span>{{ formatCurrency(holding.costBasis) }}</span>
            <span>{{ formatCurrency(holding.currentPrice) }}</span>
            <span>{{ formatCurrency(holding.marketValue) }}</span>
            <span :class="holding.pnl >= 0 ? 'positive' : 'negative'">{{ formatSignedCurrency(holding.pnl) }}</span>
            <span>{{ holding.allocation.toFixed(1) }}%</span>
          </div>
        </div>
      </section>
    </main>

    <main v-else-if="activePage === 'History'" class="product-page">
      <section class="hero-surface compact">
        <div>
          <p class="eyebrow">Past Transactions</p>
          <h1 class="page-title">History of executed trade decisions</h1>
          <p class="page-subtitle">
            This screen shows prior buy and sell transactions so the user can review what has already happened.
          </p>
        </div>
      </section>

      <section class="stats-strip">
        <article v-for="stat in historySummary" :key="stat.label" class="stat-card">
          <p>{{ stat.label }}</p>
          <h2>{{ stat.value }}</h2>
          <span>{{ stat.note }}</span>
        </article>
      </section>

      <section class="table-surface">
        <div class="table-header">
          <h2>Transaction Ledger</h2>
          <button class="chip" @click="navigateTo('Reports')">Use in Reports</button>
        </div>
        <div class="data-table">
          <div class="data-row data-head transaction-head">
            <span>Date</span>
            <span>Symbol</span>
            <span>Side</span>
            <span>Quantity</span>
            <span>Price</span>
            <span>Total</span>
            <span>Status</span>
          </div>
          <div v-for="item in transactionHistory" :key="item.id" class="data-row transaction-row">
            <span>{{ item.date }}</span>
            <span>{{ item.symbol }}</span>
            <span :class="item.side === 'Buy' ? 'positive' : 'negative'">{{ item.side }}</span>
            <span>{{ item.quantity }}</span>
            <span>{{ formatCurrency(item.price) }}</span>
            <span>{{ formatCurrency(item.total) }}</span>
            <span>{{ item.status }}</span>
          </div>
        </div>
      </section>
    </main>

    <main v-else-if="activePage === 'Reports'" class="product-page">
      <section class="hero-surface compact">
        <div>
          <p class="eyebrow">Reporting</p>
          <h1 class="page-title">Class-ready reporting functionality</h1>
          <p class="page-subtitle">
            This page summarizes activity, portfolio state, and key takeaways so the user can report performance and decisions.
          </p>
        </div>
      </section>

      <section class="stats-strip">
        <article v-for="metric in reportMetrics" :key="metric.label" class="stat-card">
          <p>{{ metric.label }}</p>
          <h2>{{ metric.value }}</h2>
          <span>{{ metric.note }}</span>
        </article>
      </section>

      <section class="dashboard-grid report-grid">
        <article class="table-surface dashboard-card">
          <div class="table-header">
            <h2>Suggested Report Sections</h2>
            <span class="section-chip">Documentation</span>
          </div>
          <div class="task-list">
            <div v-for="section in reportSections" :key="section.name" class="task-row">
              <strong>{{ section.name }}</strong>
              <small>{{ section.detail }}</small>
            </div>
          </div>
        </article>

        <article class="table-surface dashboard-card">
          <div class="table-header">
            <h2>Performance Snapshot</h2>
            <span class="section-chip">Latest</span>
          </div>
          <div class="dashboard-card-grid">
            <div v-for="highlight in reportHighlights" :key="highlight.title" class="dashboard-mini-card">
              <span>{{ highlight.title }}</span>
              <strong>{{ highlight.value }}</strong>
              <small>{{ highlight.detail }}</small>
            </div>
          </div>
        </article>
      </section>
    </main>

    <main v-else-if="activePage === 'Markets'" class="product-page">
      <section class="hero-surface compact market-hero">
        <div>
          <p class="eyebrow">Markets</p>
          <h1 class="page-title">Signal, news, and social pulse</h1>
          <p class="page-subtitle">
            A market desk for monitoring the tape, reading the story, and tracking what traders are saying around your focus symbol.
          </p>
        </div>
      </section>

      <section class="stats-strip market-pulse-strip">
        <article
          v-for="card in marketOverviewCards"
          :key="card.name"
          class="stat-card market-pulse-card"
        >
          <p>{{ card.name }}</p>
          <h2>{{ card.level }}</h2>
          <span>{{ card.change }}</span>
        </article>
      </section>

      <section class="market-intelligence-grid">
        <article class="table-surface intelligence-card">
          <div class="table-header">
            <h2>{{ marketFocusLabel }} News</h2>
            <span class="section-chip">Latest</span>
          </div>

          <div class="news-ticker-window">
            <div class="news-ticker-track">
              <a
                v-for="(story, index) in scrollingNewsFeed"
                :key="`${story.title}-${index}`"
                class="news-item news-link"
                :href="story.href"
                target="_blank"
                rel="noreferrer"
              >
                <div class="news-meta-row">
                  <span class="news-source">{{ story.source }}</span>
                  <span class="news-time">{{ story.time }}</span>
                </div>
                <h3>{{ story.title }}</h3>
                <p>{{ story.summary }}</p>
              </a>
            </div>
          </div>
        </article>

        <article class="table-surface intelligence-card">
          <div class="table-header">
            <h2>X / Trader Posts</h2>
            <span class="section-chip">Symbol-aware</span>
          </div>

          <div class="post-list">
            <a
              v-for="post in socialFeed"
              :key="post.handle + post.post"
              class="post-item post-link"
              :href="post.href"
              target="_blank"
              rel="noreferrer"
            >
              <div class="post-header-row">
                <strong>{{ post.handle }}</strong>
                <span class="post-tone">{{ post.tone }}</span>
              </div>
              <p>{{ post.post }}</p>
            </a>
          </div>
        </article>

        <article class="table-surface intelligence-card spotlight-card">
          <div class="table-header">
            <h2>Market Spotlight</h2>
            <span class="section-chip">{{ activeSymbol }}</span>
          </div>

          <div class="spotlight-grid">
            <div class="spotlight-item">
              <span>Current Price</span>
              <strong>${{ stockResponse.stock.currentPrice }}</strong>
            </div>
            <div class="spotlight-item">
              <span>52W High</span>
              <strong>${{ stockResponse.stock.week52High }}</strong>
            </div>
            <div class="spotlight-item">
              <span>52W Low</span>
              <strong>${{ stockResponse.stock.week52Low }}</strong>
            </div>
            <div class="spotlight-item">
              <span>Probability</span>
              <strong>{{ stockResponse.patternAnalysis.probabilityOfIncrease }}%</strong>
            </div>
          </div>
        </article>
      </section>
    </main>

    <main v-else-if="activePage === 'Myself'" class="product-page">
      <section class="hero-surface compact">
        <div>
          <p class="eyebrow">Myself</p>
          <h1 class="page-title">Your account at a glance</h1>
          <p class="page-subtitle">
            Review your personal account ID, registered email, and basic account status in one place.
          </p>
        </div>
      </section>

      <section class="dashboard-grid myself-grid">
        <article class="table-surface dashboard-card">
          <div class="table-header">
            <h2>Account Details</h2>
            <span class="section-chip">{{ currentUser?.isAdmin ? 'Admin' : 'User' }}</span>
          </div>
          <div class="task-list myself-detail-list">
            <div class="task-row">
              <strong>Account ID</strong>
              <small>{{ currentUserCode }}</small>
            </div>
            <div class="task-row">
              <strong>Full Name</strong>
              <small>{{ currentUser?.fullName || currentUserName }}</small>
            </div>
            <div class="task-row">
              <strong>Email</strong>
              <small>{{ currentUser?.email || 'Not available' }}</small>
            </div>
            <div class="task-row">
              <strong>Membership</strong>
              <small>{{ currentUser?.membership || 'Regular User' }}</small>
            </div>
            <div class="task-row">
              <strong>Joined</strong>
              <small>{{ currentUser?.joinedAt || 'Recent' }}</small>
            </div>
          </div>
        </article>

        <article class="table-surface dashboard-card">
          <div class="table-header">
            <h2>Settings</h2>
            <span class="section-chip">Session</span>
          </div>
          <div class="dashboard-card-grid">
            <div class="dashboard-mini-card">
              <span>Current login</span>
              <strong>{{ currentUser?.emailVerified ? 'Verified' : 'Pending verification' }}</strong>
              <small>Your account stays stored locally even when the shared market seed database is updated.</small>
            </div>
          </div>
          <div class="myself-actions">
            <button class="topbar-button" @click="signOut">Logout</button>
          </div>
        </article>
      </section>
    </main>

    <main v-else-if="activePage === 'Admin'" class="product-page">
      <section class="hero-surface compact">
        <div>
          <p class="eyebrow">Admin</p>
          <h1 class="page-title">User administration panel</h1>
          <p class="page-subtitle">
            Review registered users, track their user IDs, and remove accounts when needed.
          </p>
        </div>
      </section>

      <section class="table-surface">
        <div class="table-header">
          <h2>Registered Users</h2>
          <button class="topbar-button secondary" @click="loadAdminUsers">Refresh</button>
        </div>

        <p v-if="adminMessage" class="status-message loading-message">{{ adminMessage }}</p>

        <div class="data-table">
          <div class="data-row data-head admin-users-head">
            <span>ID</span>
            <span>Name</span>
            <span>Email</span>
            <span>Role</span>
            <span>Status</span>
            <span>Joined</span>
            <span>Actions</span>
          </div>

          <div
            v-for="user in adminUsers"
            :key="user.id"
            class="data-row admin-users-row"
          >
            <span>{{ formatAdminUserCode(user.displayCode ?? user.id) }}</span>
            <span>{{ user.fullName }}</span>
            <span>{{ user.email }}</span>
            <span>{{ user.role }}</span>
            <span>
              <span :class="user.isDisabled ? 'section-chip section-chip-warning' : 'section-chip section-chip-positive'">
                {{ user.isDisabled ? 'Disabled' : 'Active' }}
              </span>
            </span>
            <span>{{ user.joinedAt }}</span>
            <div class="admin-action-cell">
              <template v-if="!user.isAdmin">
                <div class="admin-action-stack">
                  <div class="admin-action-row">
                    <button
                      class="chip"
                      :class="user.isDisabled ? 'chip-confirm' : 'chip-danger'"
                      :disabled="pendingAdminStatusUpdates[String(user.id)]"
                      @click="updateAdminUserStatus(user, !user.isDisabled)"
                    >
                      {{ pendingAdminStatusUpdates[String(user.id)] ? 'Saving...' : (user.isDisabled ? 'Enable' : 'Disable') }}
                    </button>
                    <button
                      class="chip chip-muted"
                      type="button"
                      @click="openAdminPasswordReset(user)"
                    >
                      Reset Password
                    </button>
                  </div>
                  <div v-if="Object.prototype.hasOwnProperty.call(adminPasswordResetDrafts, String(user.id))" class="admin-password-reset-row">
                    <input
                      v-model="adminPasswordResetDrafts[String(user.id)]"
                      type="password"
                      class="admin-password-reset-input"
                      placeholder="Enter new password"
                    />
                    <button
                      class="chip chip-confirm"
                      type="button"
                      :disabled="pendingAdminPasswordResets[String(user.id)]"
                      @click="resetAdminUserPassword(user)"
                    >
                      {{ pendingAdminPasswordResets[String(user.id)] ? 'Saving...' : 'Submit' }}
                    </button>
                    <button
                      class="chip chip-muted"
                      type="button"
                      :disabled="pendingAdminPasswordResets[String(user.id)]"
                      @click="cancelAdminPasswordReset(user)"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </template>
              <span v-else class="section-chip">Protected</span>
            </div>
          </div>
        </div>

        <div v-if="isAdminLoading" class="empty-state empty-state--compact">
          Loading registered users...
        </div>
        <div v-else-if="!adminUsers.length" class="empty-state empty-state--compact">
          No registered users are available yet.
        </div>
      </section>
    </main>

    <main v-else class="product-page">
      <section class="hero-surface compact">
        <div>
          <p class="eyebrow">More</p>
          <h1 class="page-title">What Noob Trade is building</h1>
          <p class="page-subtitle">
            A beginner-first stock analysis workspace designed to make pattern-based trading more understandable, structured, and less intimidating.
          </p>
        </div>
      </section>

      <section class="more-story-grid">
        <article class="more-card feature-story-card">
          <p class="eyebrow">About Noob Trade</p>
          <h2>Noob Trade</h2>
          <p>
            Noob Trade turns stock pattern analysis into a cleaner workflow: search a symbol, inspect price structure, compare historical matches, and plan exits before acting.
          </p>
        </article>

        <article class="more-card feature-story-card">
          <p class="eyebrow">Core Features</p>
          <h2>What the platform helps with</h2>
          <ul class="feature-list">
            <li v-for="feature in moreFeatures" :key="feature">{{ feature }}</li>
          </ul>
        </article>
      </section>

      <section class="more-story-grid feedback-grid">
        <article class="more-card feature-story-card">
          <p class="eyebrow">User Feedback</p>
          <h2>Write to the team</h2>
          <p>
            We want to hear where you get confused, what feels useful, and what should be easier for first-time traders to understand.
          </p>
          <div class="feedback-list">
            <div
              v-for="channel in feedbackChannels"
              :key="channel.label"
              class="feedback-row"
            >
              <span>{{ channel.label }}</span>
              <strong v-if="channel.href">
                <a :href="channel.href" class="feedback-link" rel="noreferrer" target="_blank">
                  {{ channel.value }}
                </a>
              </strong>
              <strong v-else>{{ channel.value }}</strong>
            </div>
          </div>
        </article>

        <article class="more-card feature-story-card">
          <p class="eyebrow">Roadmap</p>
          <h2>What comes next</h2>
          <p>
            The next step is turning Noob Trade into a polished mobile product ready for global release on the Apple App Store and Google Play, with a cleaner onboarding flow, stronger production infrastructure, and a launch-ready experience for first-time traders.
          </p>
        </article>
      </section>
    </main>

    <div
      v-if="replayPattern"
      class="replay-overlay"
      role="dialog"
      aria-modal="true"
    >
      <div class="replay-modal">
        <div class="panel-topbar replay-topbar">
          <div class="panel-heading-group">
            <h2>{{ replayPattern.symbol }} Historical Replay</h2>
            <span class="source-pill source-pill--live">Matched Setup</span>
          </div>
          <button class="topbar-button secondary" @click="closeHistoricalReplay">Close</button>
        </div>

        <div class="replay-meta-grid">
          <div class="spotlight-item">
            <span>Setup</span>
            <strong>{{ replayPattern.patternName }}</strong>
          </div>
          <div class="spotlight-item">
            <span>Match Score</span>
            <strong>{{ replayPattern.matchScore }}%</strong>
          </div>
          <div class="spotlight-item">
            <span>End Date</span>
            <strong>{{ replayPattern.date }}</strong>
          </div>
          <div class="spotlight-item">
            <span>5D Future High</span>
            <strong>{{ formatPercent(replayPattern.futureReturn5d) }}</strong>
          </div>
        </div>

        <ChartPanel
          :active-indicators="appliedIndicators"
          :active-symbol="replayPattern.symbol"
          :chart-data="replayChartData"
          :chart-intervals="[replayPattern.timeframe]"
          :company-name="`${replayPattern.symbol} historical replay`"
          :industry="'Matched setup'"
          :selected-interval="replayInterval"
          :sector="'Historical window'"
          @update:selected-interval="replayInterval = $event"
        />
      </div>
    </div>

    <div v-if="installMessage" class="install-toast">
      {{ installMessage }}
    </div>

    <div v-if="showInstallGuide" class="install-guide-backdrop" @click="showInstallGuide = false">
      <div class="install-guide-card" @click.stop>
        <span class="section-chip">iPhone / iPad</span>
        <h2>Add Noob Trade to Home Screen</h2>
        <p>
          In Safari, tap the Share button, then choose <strong>Add to Home Screen</strong>. After that, Noob Trade
          will launch like a standalone app from your device.
        </p>
        <div class="auth-actions">
          <button class="topbar-button" @click="showInstallGuide = false">Got it</button>
        </div>
      </div>
    </div>

    <nav class="mobile-tabbar" aria-label="Mobile navigation">
      <button
        v-for="page in mobileNavPages"
        :key="`mobile-${page}`"
        class="mobile-tab"
        :class="{ active: activePage === page }"
        @click="navigateTo(page)"
      >
        <span class="mobile-tab-label">{{ page }}</span>
      </button>
    </nav>
  </div>
</template>
