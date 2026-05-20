<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import ChartPanel from './components/ChartPanel.vue'
import IndicatorSelector from './components/IndicatorSelector.vue'
import MatchedPatterns from './components/MatchedPatterns.vue'
import PredictionSummary from './components/PredictionSummary.vue'
import SearchBar from './components/SearchBar.vue'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'
const ADMIN_USERS_CACHE_KEY = 'noobtrade_admin_users'
const chartIntervals = ['daily', '5day', 'weekly', '2week', 'monthly']
const publicPages = ['Home', 'Sign In', 'Register', 'Verify Email', 'Reset Password', 'Reset Password Confirm']
const publicNavPages = ['Home', 'Sign In', 'Register']
const authenticatedPages = ['Dashboard', 'Stock Trade', 'Crypto Trade', 'Portfolio', 'Explore', 'Markets', 'Myself', 'More']
const tradeWorkspacePages = ['Stock Trade', 'Crypto Trade']
const voiceCommandExamples = [
  'Open Stock Trade',
  'Enable MACD and Bollinger',
  'Generate AAPL',
  'Search BTC',
  'Go to Portfolio',
  'Confirm / Cancel'
]
const voiceCryptoSymbols = new Set(['BTC', 'ETH', 'OKB', 'SOL', 'BNB'])
const voiceSymbolAliases = {
  apple: 'AAPL',
  tesla: 'TSLA',
  nvidia: 'NVDA',
  microsoft: 'MSFT',
  amazon: 'AMZN',
  meta: 'META',
  google: 'GOOGL',
  alphabet: 'GOOGL',
  bitcoin: 'BTC',
  ethereum: 'ETH',
  solana: 'SOL',
  'o k b': 'OKB',
  okb: 'OKB',
  spy: 'SPY'
}
const voiceIndicatorAliases = [
  { name: 'MA', phrases: ['ma', 'm a', 'moving average', 'moving averages'] },
  { name: 'EMA', phrases: ['ema', 'e m a', 'exponential moving average'] },
  { name: 'MACD', phrases: ['macd', 'm a c d'] },
  { name: 'BOLL', phrases: ['boll', 'bollinger', 'bollinger band', 'bollinger bands'] },
  { name: 'RSI', phrases: ['rsi', 'r s i'] },
  { name: 'Vol', phrases: ['vol', 'volume'] },
  { name: 'KDJ', phrases: ['kdj', 'k d j'] },
  { name: 'OI', phrases: ['oi', 'o i', 'open interest'] },
  { name: 'OBV', phrases: ['obv', 'o b v', 'on balance volume'] }
]
const voicePageAliases = [
  { page: 'Crypto Trade', phrases: ['crypto trade', 'crypto', 'crypto analysis'] },
  { page: 'Stock Trade', phrases: ['stock trade', 'stock analysis', 'analysis', 'trade page', 'trade'] },
  { page: 'Dashboard', phrases: ['dashboard', 'home dashboard'] },
  { page: 'Portfolio', phrases: ['portfolio', 'holdings'] },
  { page: 'Explore', phrases: ['explore', 'watchlist'] },
  { page: 'Markets', phrases: ['markets', 'market'] },
  { page: 'Myself', phrases: ['myself', 'profile', 'account'] },
  { page: 'More', phrases: ['more', 'more page'] },
  { page: 'Admin', phrases: ['admin', 'admin page'] }
]
const voiceIntervalAliases = [
  { interval: 'daily', phrases: ['daily', 'day chart', 'one day'] },
  { interval: '5day', phrases: ['five day', '5 day', 'five days', '5 days'] },
  { interval: 'weekly', phrases: ['weekly', 'week chart', 'one week'] },
  { interval: '2week', phrases: ['two week', '2 week', 'two weeks', '2 weeks'] },
  { interval: 'monthly', phrases: ['monthly', 'month chart', 'one month'] }
]
const voiceConfirmPhrases = ['confirm', 'yes', 'proceed', 'do it', 'run it', 'continue']
const voiceCancelPhrases = ['cancel', 'stop', 'no', 'never mind', 'nevermind']
const voiceEnablePhrases = ['enable', 'select', 'turn on', 'check', 'add', 'use']
const voiceDisablePhrases = ['disable', 'unselect', 'turn off', 'uncheck', 'remove', 'drop']

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
const voiceAssistantOpen = ref(false)
const voiceAssistantEnabled = ref(false)
const voiceListening = ref(false)
const voiceSupported = ref(false)
const voiceStatus = ref('Voice assistant ready.')
const voiceTranscript = ref('')
const voicePendingAction = ref(null)
const voiceRecognition = ref(null)
const voiceCommandLog = ref([])
const voicePreferredVoiceName = ref('System voice')
const voiceIsSpeaking = ref(false)
const voiceInputDraft = ref('')

let feedRefreshTimer = null
let beforeInstallHandler = null
let voiceVoicesChangedHandler = null
let voiceRestartTimer = null

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
const cryptoResponse = ref(createCryptoWorkspaceResponse())
const currentUser = ref(null)
const cashBalance = ref(86420)
const adminUsers = ref([])
const adminMessage = ref('')
const isAdminLoading = ref(false)
const hasAdminUsersCache = ref(false)
const isTradeWorkspacePage = computed(() => tradeWorkspacePages.includes(activePage.value))
const activeTradeWorkspaceLabel = computed(() => (activePage.value === 'Crypto Trade' ? 'Crypto Trade' : 'Stock Trade'))
const activeTradeResponse = computed(() => (activePage.value === 'Crypto Trade' ? cryptoResponse.value : stockResponse.value))
const displayedTradeSymbol = computed(() => activeTradeResponse.value?.stock?.symbol || activeSymbol.value)
const tradeSearchPlaceholder = computed(() => (
  activePage.value === 'Crypto Trade' ? 'Enter Crypto Ticker (e.g. BTC)' : 'Enter Ticker (e.g. AAPL)'
))
const tradeSearchLoadingLabel = computed(() => (
  activePage.value === 'Crypto Trade' ? 'Loading crypto data for' : 'Loading stock data for'
))
const tradePopularSymbols = computed(() => (
  activePage.value === 'Crypto Trade' ? ['BTC', 'ETH', 'OKB', 'SOL'] : ['AAPL', 'TSLA', 'NVDA', 'SPY']
))
const adminUserCountLabel = computed(() => {
  if (isAdminLoading.value && !hasAdminUsersCache.value && adminUsers.value.length === 0) {
    return 'Loading...'
  }
  return `${adminUsers.value.length} total`
})
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

const cryptoExploreRows = [
  { symbol: 'BTC', name: 'Bitcoin', category: 'Store of Value', price: '$103,420.50', notional: '$2.04T', change: '+2.84%', tone: 'positive' },
  { symbol: 'ETH', name: 'Ethereum', category: 'Smart Contracts', price: '$4,920.40', notional: '$592.1B', change: '+2.18%', tone: 'positive' },
  { symbol: 'OKB', name: 'OKB', category: 'Exchange Token', price: '$68.42', notional: '$4.1B', change: '+3.07%', tone: 'positive' },
  { symbol: 'SOL', name: 'Solana', category: 'Layer 1', price: '$224.15', notional: '$106.8B', change: '+4.31%', tone: 'positive' },
  { symbol: 'BNB', name: 'BNB', category: 'Exchange Token', price: '$734.60', notional: '$102.9B', change: '+1.44%', tone: 'positive' }
]

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

const accessiblePages = computed(() => {
  if (!isAuthenticated.value) {
    return publicPages
  }

  if (currentUser.value?.isAdmin) {
    return [...authenticatedPages, 'Admin']
  }

  return authenticatedPages
})

const visiblePages = computed(() => {
  if (!isAuthenticated.value) {
    return publicNavPages
  }

  if (currentUser.value?.isAdmin) {
    return [...authenticatedPages, 'Admin']
  }

  return authenticatedPages
})
const selectedIndicators = computed(() => indicators.value.filter((indicator) => indicator.active))
const appliedIndicatorSet = computed(() => new Set(
  activeTradeResponse.value?.request?.indicators
  || activeTradeResponse.value?.patternAnalysis?.selectedIndicators
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
const filteredCryptoExploreRows = computed(() => {
  const query = exploreSearchQuery.value.trim().toUpperCase()

  if (!query) {
    return cryptoExploreRows
  }

  return cryptoExploreRows.filter((row) => {
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
  if (activeTradeResponse.value.dataSource === 'crypto-mock') {
    return {
      label: 'Crypto Preview',
      description: 'Crypto framework placeholder',
      tone: 'mock'
    }
  }

  if (activeTradeResponse.value.dataSource === 'live') {
    return {
      label: 'Live API',
      description: 'Connected market feed',
      tone: 'live'
    }
  }

  if (activeTradeResponse.value.dataSource === 'cached') {
    return {
      label: 'Live API',
      description: 'Connected market feed',
      tone: 'live'
    }
  }

  return {
    label: 'Mock Data',
    description: 'Fallback sample feed',
    tone: 'mock'
  }
})
const voiceActionLabel = computed(() => {
  if (isGenerating.value) {
    return 'Generating'
  }

  if (isSearching.value) {
    return 'Searching'
  }

  if (voiceIsSpeaking.value) {
    return 'Speaking'
  }

  if (voiceListening.value) {
    return 'Listening'
  }

  return voiceAssistantEnabled.value ? 'AI mode on' : 'AI mode off'
})
const voiceChatTimeline = computed(() => [...voiceCommandLog.value].reverse())

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
  initializeVoiceAssistant()
  refreshPreferredVoice()

  if (typeof window !== 'undefined' && window.speechSynthesis) {
    voiceVoicesChangedHandler = () => refreshPreferredVoice()
    window.speechSynthesis.addEventListener?.('voiceschanged', voiceVoicesChangedHandler)
  }

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

  if (beforeInstallHandler) {
    window.removeEventListener('beforeinstallprompt', beforeInstallHandler)
  }

  stopVoiceListening()
  clearVoiceRestartTimer()

  if (voiceVoicesChangedHandler && typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.removeEventListener?.('voiceschanged', voiceVoicesChangedHandler)
  }
})

function readAdminUsersCache() {
  if (typeof window === 'undefined') {
    return []
  }

  try {
    const rawValue = window.sessionStorage.getItem(ADMIN_USERS_CACHE_KEY)
    if (!rawValue) {
      return []
    }

    const parsed = JSON.parse(rawValue)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeAdminUsersCache(users) {
  if (typeof window === 'undefined') {
    return
  }

  try {
    window.sessionStorage.setItem(ADMIN_USERS_CACHE_KEY, JSON.stringify(Array.isArray(users) ? users : []))
  } catch {
    // Ignore storage failures in private browsing or restricted environments.
  }
}

function clearAdminUsersCache() {
  if (typeof window === 'undefined') {
    return
  }

  try {
    window.sessionStorage.removeItem(ADMIN_USERS_CACHE_KEY)
  } catch {
    // Ignore storage failures in private browsing or restricted environments.
  }
}

function restoreAdminUsersFromCache() {
  const cachedUsers = readAdminUsersCache()
  hasAdminUsersCache.value = cachedUsers.length > 0

  if (cachedUsers.length > 0) {
    adminUsers.value = cachedUsers
    adminMessage.value = ''
    isAdminLoading.value = false
    return true
  }

  return false
}

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

function createCryptoWorkspaceResponse(symbol = 'BTC') {
  const normalizedSymbol = String(symbol || 'BTC').trim().toUpperCase() || 'BTC'
  const cryptoLookup = {
    BTC: {
      companyName: 'Bitcoin',
      sector: 'Crypto',
      industry: 'Store of Value',
      currentPrice: 103420.5,
      previousClose: 101980.2,
      open: 102215.8,
      volume: 928450,
      week52High: 109880.0,
      week52Low: 58740.0
    },
    ETH: {
      companyName: 'Ethereum',
      sector: 'Crypto',
      industry: 'Smart Contracts',
      currentPrice: 4920.4,
      previousClose: 4848.8,
      open: 4866.1,
      volume: 1456200,
      week52High: 5362.0,
      week52Low: 2214.5
    },
    OKB: {
      companyName: 'OKB',
      sector: 'Crypto',
      industry: 'Exchange Token',
      currentPrice: 68.42,
      previousClose: 66.91,
      open: 67.15,
      volume: 382100,
      week52High: 74.8,
      week52Low: 38.2
    },
    SOL: {
      companyName: 'Solana',
      sector: 'Crypto',
      industry: 'Layer 1',
      currentPrice: 224.15,
      previousClose: 217.03,
      open: 218.7,
      volume: 1183600,
      week52High: 259.4,
      week52Low: 97.85
    }
  }
  const selected = cryptoLookup[normalizedSymbol] || {
    companyName: `${normalizedSymbol} Crypto`,
    sector: 'Crypto',
    industry: 'Digital Asset',
    currentPrice: 100.0,
    previousClose: 98.4,
    open: 99.1,
    volume: 250000,
    week52High: 132.0,
    week52Low: 42.0
  }

  return {
    dataSource: 'crypto-mock',
    request: {
      symbol: normalizedSymbol,
      interval: 'daily',
      indicators: ['MA', 'EMA', 'MACD', 'BOLL', 'Vol']
    },
    stock: {
      symbol: normalizedSymbol,
      ...selected
    },
    patternAnalysis: {
      selectedIndicators: ['MA', 'EMA', 'MACD', 'BOLL', 'Vol'],
      probabilityOfIncrease: 88,
      probabilityOfDecrease: 46,
      avgReturn: 8.4,
      maxDrawdown: -6.2,
      matchedPatternsCount: 18,
      quantConfidence: 0.84,
      signalClassification: 'Crypto Momentum Bias',
      futureFiveDayProbabilities: {
        up: [
          { threshold: 1, probability: 88 },
          { threshold: 5, probability: 71 },
          { threshold: 10, probability: 38 }
        ],
        down: [
          { threshold: 1, probability: 46 },
          { threshold: 5, probability: 24 },
          { threshold: 10, probability: 9 }
        ]
      },
      recommendedSellPrice: Number((selected.currentPrice * 1.061).toFixed(2)),
      recommendedSellDate: 'Within 5 trading days',
      stopLossPrice: Number((selected.currentPrice * 0.958).toFixed(2)),
      matchedHistoricalPatterns: [
        {
          patternName: 'CRYPTO 30-bar setup',
          matchScore: 90,
          date: '2026-04-18',
          symbol: normalizedSymbol,
          timeframe: 'daily',
          windowSize: 30,
          returnPct: 9.12,
          maxDrawdown: -5.4
        },
        {
          patternName: 'CRYPTO 30-bar setup',
          matchScore: 84,
          date: '2026-03-27',
          symbol: 'ETH',
          timeframe: 'daily',
          windowSize: 30,
          returnPct: 7.31,
          maxDrawdown: -6.1
        },
        {
          patternName: 'CRYPTO 30-bar setup',
          matchScore: 79,
          date: '2026-02-14',
          symbol: 'OKB',
          timeframe: 'daily',
          windowSize: 30,
          returnPct: 5.88,
          maxDrawdown: -4.7
        }
      ],
      highFitHistoricalPaths: [
        { label: `${normalizedSymbol} continuation path`, fitScore: 90, status: `${normalizedSymbol} ended on 2026-04-18` },
        { label: 'ETH breakout path', fitScore: 84, status: 'ETH ended on 2026-03-27' },
        { label: 'OKB exchange path', fitScore: 79, status: 'OKB ended on 2026-02-14' }
      ]
    },
    chartData: {
      series: {
        daily: [
          { date: '2026-04-28', open: selected.currentPrice * 0.95, high: selected.currentPrice * 0.98, low: selected.currentPrice * 0.93, close: selected.currentPrice * 0.97, volume: selected.volume * 0.92 },
          { date: '2026-04-29', open: selected.currentPrice * 0.97, high: selected.currentPrice * 0.99, low: selected.currentPrice * 0.95, close: selected.currentPrice * 0.98, volume: selected.volume * 0.95 },
          { date: '2026-04-30', open: selected.currentPrice * 0.98, high: selected.currentPrice * 1.0, low: selected.currentPrice * 0.96, close: selected.currentPrice * 0.99, volume: selected.volume * 0.97 },
          { date: '2026-05-01', open: selected.currentPrice * 0.99, high: selected.currentPrice * 1.01, low: selected.currentPrice * 0.98, close: selected.currentPrice, volume: selected.volume }
        ],
        '5day': [
          { date: '2026-04-25', open: selected.currentPrice * 0.92, high: selected.currentPrice * 0.99, low: selected.currentPrice * 0.9, close: selected.currentPrice * 0.97, volume: selected.volume * 4.2 },
          { date: '2026-05-01', open: selected.currentPrice * 0.97, high: selected.currentPrice * 1.01, low: selected.currentPrice * 0.95, close: selected.currentPrice, volume: selected.volume * 4.5 }
        ],
        weekly: [
          { date: '2026-W17', open: selected.currentPrice * 0.9, high: selected.currentPrice * 0.99, low: selected.currentPrice * 0.88, close: selected.currentPrice * 0.97, volume: selected.volume * 7.1 },
          { date: '2026-W18', open: selected.currentPrice * 0.97, high: selected.currentPrice * 1.01, low: selected.currentPrice * 0.95, close: selected.currentPrice, volume: selected.volume * 7.4 }
        ],
        '2week': [
          { date: '2026-H1', open: selected.currentPrice * 0.88, high: selected.currentPrice * 0.99, low: selected.currentPrice * 0.84, close: selected.currentPrice * 0.96, volume: selected.volume * 12.8 },
          { date: '2026-H2', open: selected.currentPrice * 0.96, high: selected.currentPrice * 1.01, low: selected.currentPrice * 0.93, close: selected.currentPrice, volume: selected.volume * 13.1 }
        ],
        monthly: [
          { date: '2026-01', open: selected.currentPrice * 0.74, high: selected.currentPrice * 0.81, low: selected.currentPrice * 0.7, close: selected.currentPrice * 0.78, volume: selected.volume * 22 },
          { date: '2026-02', open: selected.currentPrice * 0.78, high: selected.currentPrice * 0.89, low: selected.currentPrice * 0.75, close: selected.currentPrice * 0.86, volume: selected.volume * 24 },
          { date: '2026-03', open: selected.currentPrice * 0.86, high: selected.currentPrice * 0.95, low: selected.currentPrice * 0.82, close: selected.currentPrice * 0.91, volume: selected.volume * 26 },
          { date: '2026-04', open: selected.currentPrice * 0.91, high: selected.currentPrice, low: selected.currentPrice * 0.88, close: selected.currentPrice * 0.97, volume: selected.volume * 28 },
          { date: '2026-05', open: selected.currentPrice * 0.97, high: selected.currentPrice * 1.01, low: selected.currentPrice * 0.95, close: selected.currentPrice, volume: selected.volume * 19 }
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
    fullName: 'NoobTrade123',
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

function getSpeechRecognitionConstructor() {
  if (typeof window === 'undefined') {
    return null
  }

  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

function initializeVoiceAssistant() {
  if (typeof window === 'undefined') {
    return
  }

  const SpeechRecognitionConstructor = getSpeechRecognitionConstructor()
  voiceSupported.value = Boolean(SpeechRecognitionConstructor && window.speechSynthesis)

  if (!voiceSupported.value || voiceRecognition.value) {
    if (!voiceSupported.value) {
      voiceStatus.value = 'Voice control is not supported in this browser yet. Try Chrome or Edge over HTTPS.'
    }
    return
  }

  const recognition = new SpeechRecognitionConstructor()
  recognition.lang = 'en-US'
  recognition.continuous = true
  recognition.interimResults = false
  recognition.maxAlternatives = 1

  recognition.onstart = () => {
    voiceListening.value = true
    voiceStatus.value = 'AI Mode is listening. Speak naturally.'
  }

  recognition.onend = () => {
    voiceListening.value = false
    scheduleVoiceRestart()
  }

  recognition.onerror = (event) => {
    voiceListening.value = false
    const errorName = event?.error || 'voice error'
    if (errorName === 'not-allowed') {
      voiceAssistantEnabled.value = false
      setVoiceStatus('Microphone permission is blocked. Please allow microphone access for Noob Trade.', { speak: false })
      return
    }

    if (errorName !== 'no-speech' && errorName !== 'aborted') {
      setVoiceStatus(`Voice input paused: ${errorName}. I will keep trying while AI Mode is on.`, { speak: false })
    }

    scheduleVoiceRestart(900)
  }

  recognition.onresult = (event) => {
    const transcript = Array.from(event.results || [])
      .slice(event.resultIndex || 0)
      .map((result) => result?.[0]?.transcript || '')
      .join(' ')
      .trim()

    if (transcript) {
      handleVoiceCommand(transcript).catch((error) => {
        console.error(error)
        setVoiceStatus('I could not complete that command. Please try again.', { speak: true })
      })
    }
  }

  voiceRecognition.value = recognition
}

function refreshPreferredVoice() {
  const voice = getPreferredVoice()
  voicePreferredVoiceName.value = voice?.name || 'System voice'
}

function clearVoiceRestartTimer() {
  if (voiceRestartTimer) {
    window.clearTimeout(voiceRestartTimer)
    voiceRestartTimer = null
  }
}

function scheduleVoiceRestart(delayMs = 550) {
  if (
    typeof window === 'undefined'
    || !voiceAssistantEnabled.value
    || !voiceRecognition.value
    || voiceListening.value
    || voiceIsSpeaking.value
  ) {
    return
  }

  clearVoiceRestartTimer()
  voiceRestartTimer = window.setTimeout(() => {
    voiceRestartTimer = null

    if (!voiceAssistantEnabled.value || voiceListening.value || voiceIsSpeaking.value) {
      return
    }

    startVoiceListening({ silent: true })
  }, delayMs)
}

function getPreferredVoice() {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    return null
  }

  const voices = window.speechSynthesis.getVoices?.() || []
  const englishVoices = voices.filter((voice) => /^en([-_]|$)/i.test(voice.lang || ''))
  const preferredNames = [
    'Samantha',
    'Victoria',
    'Ava',
    'Allison',
    'Susan',
    'Karen',
    'Moira',
    'Tessa',
    'Fiona',
    'Google US English',
    'Microsoft Aria',
    'Microsoft Jenny',
    'Microsoft Zira'
  ]

  for (const preferredName of preferredNames) {
    const matchedVoice = englishVoices.find((voice) => voice.name.toLowerCase().includes(preferredName.toLowerCase()))
    if (matchedVoice) {
      return matchedVoice
    }
  }

  return englishVoices[0] || voices[0] || null
}

function speakVoice(text) {
  if (typeof window === 'undefined' || !window.speechSynthesis || !text) {
    return
  }

  if (voiceRecognition.value && voiceListening.value) {
    try {
      voiceRecognition.value.stop()
    } catch {
      // Recognition may already be stopped while the assistant is answering.
    }
  }

  const utterance = new SpeechSynthesisUtterance(text)
  const preferredVoice = getPreferredVoice()

  if (preferredVoice) {
    utterance.voice = preferredVoice
    utterance.lang = preferredVoice.lang || 'en-US'
    voicePreferredVoiceName.value = preferredVoice.name
  } else {
    utterance.lang = 'en-US'
  }

  utterance.rate = 0.94
  utterance.pitch = 1.08
  utterance.volume = 0.88
  utterance.onstart = () => {
    voiceIsSpeaking.value = true
  }
  utterance.onend = () => {
    voiceIsSpeaking.value = false
    scheduleVoiceRestart(420)
  }
  utterance.onerror = () => {
    voiceIsSpeaking.value = false
    scheduleVoiceRestart(420)
  }
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(utterance)
}

function setVoiceStatus(message, { speak = false, transcript = '' } = {}) {
  voiceStatus.value = message

  if (transcript || message) {
    voiceCommandLog.value = [
      {
        transcript: transcript || 'Noob AI',
        response: message,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      },
      ...voiceCommandLog.value
    ].slice(0, 4)
  }

  if (speak) {
    speakVoice(message)
  }
}

function toggleVoiceAssistant() {
  if (voiceAssistantEnabled.value) {
    disableVoiceAssistant()
    return
  }

  enableVoiceAssistant()
}

function openVoiceAssistantPanel() {
  voiceAssistantOpen.value = true
  initializeVoiceAssistant()
  refreshPreferredVoice()

  if (!voiceAssistantEnabled.value) {
    voiceStatus.value = 'AI Mode is off. Turn it on when you want hands-free help.'
  }
}

function minimizeVoiceAssistantPanel() {
  voiceAssistantOpen.value = false
}

function enableVoiceAssistant() {
  if (!isAuthenticated.value) {
    setVoiceStatus('Please sign in before using AI Mode.', { speak: true })
    return
  }

  voiceAssistantOpen.value = true
  voiceAssistantEnabled.value = true
  initializeVoiceAssistant()
  refreshPreferredVoice()

  if (!voiceSupported.value || !voiceRecognition.value) {
    voiceAssistantEnabled.value = false
    setVoiceStatus('Voice chat needs browser microphone support. Please try Chrome or Edge over HTTPS.', { speak: true })
    return
  }

  const greeting = 'AI Mode is on. You can talk naturally. Try: Generate AAPL, explain RSI, or open Portfolio.'
  setVoiceStatus(greeting, { speak: true })
  scheduleVoiceRestart(900)
}

function disableVoiceAssistant() {
  voiceAssistantEnabled.value = false
  voicePendingAction.value = null
  clearVoiceRestartTimer()
  stopVoiceListening()
  window.speechSynthesis?.cancel()
  voiceIsSpeaking.value = false
  voiceStatus.value = 'AI Mode is off. Manual controls stay available.'
}

function startVoiceListening({ silent = false } = {}) {
  if (!isAuthenticated.value) {
    setVoiceStatus('Please sign in before using voice control.', { speak: true })
    return
  }

  initializeVoiceAssistant()

  if (!voiceSupported.value || !voiceRecognition.value) {
    setVoiceStatus('Voice control is not supported in this browser yet. Try Chrome or Edge over HTTPS.', { speak: true })
    return
  }

  try {
    window.speechSynthesis?.cancel()
    voiceRecognition.value.start()
  } catch {
    if (!silent) {
      setVoiceStatus('I am already listening. Say a command now.', { speak: false })
    }
  }
}

function stopVoiceListening() {
  if (!voiceRecognition.value) {
    voiceListening.value = false
    return
  }

  try {
    voiceRecognition.value.stop()
  } catch {
    // The browser throws if recognition is already stopped.
  }

  voiceListening.value = false
}

function normalizeVoiceText(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/[^a-z0-9.\s-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function includesVoicePhrase(command, phrases) {
  return phrases.some((phrase) => command.includes(phrase))
}

function findVoicePage(command) {
  const sortedAliases = [...voicePageAliases].sort((left, right) => {
    const leftLength = Math.max(...left.phrases.map((phrase) => phrase.length))
    const rightLength = Math.max(...right.phrases.map((phrase) => phrase.length))
    return rightLength - leftLength
  })

  return sortedAliases.find(({ phrases }) => includesVoicePhrase(command, phrases))?.page || null
}

function findVoiceInterval(command) {
  return voiceIntervalAliases.find(({ phrases }) => includesVoicePhrase(command, phrases))?.interval || null
}

function findVoiceIndicators(command) {
  return voiceIndicatorAliases
    .filter(({ phrases }) => includesVoicePhrase(command, phrases))
    .map(({ name }) => name)
}

function setIndicatorActive(indicatorNames, active) {
  const selectedNames = new Set(indicatorNames)
  indicators.value = indicators.value.map((indicator) => {
    if (selectedNames.has(indicator.name)) {
      return { ...indicator, active }
    }

    return indicator
  })
}

function setOnlyVoiceIndicators(indicatorNames) {
  const selectedNames = new Set(indicatorNames)
  indicators.value = indicators.value.map((indicator) => ({
    ...indicator,
    active: selectedNames.has(indicator.name)
  }))
}

function resolveVoiceSymbol(rawValue) {
  const cleanedValue = normalizeVoiceText(rawValue)
  if (!cleanedValue) {
    return ''
  }

  if (voiceSymbolAliases[cleanedValue]) {
    return voiceSymbolAliases[cleanedValue]
  }

  const compactValue = cleanedValue.replace(/\s+/g, '')
  if (voiceSymbolAliases[compactValue]) {
    return voiceSymbolAliases[compactValue]
  }

  if (/^[a-z0-9]{1,10}$/.test(compactValue)) {
    return compactValue.toUpperCase()
  }

  return ''
}

function extractVoiceSymbol(command) {
  for (const [alias, symbol] of Object.entries(voiceSymbolAliases)) {
    if (command.includes(alias)) {
      return symbol
    }
  }

  const commandWords = new Set([
    'generate', 'search', 'analyze', 'analyse', 'run', 'for', 'stock', 'crypto', 'ticker', 'symbol',
    'quote', 'price', 'open', 'go', 'to', 'page', 'trade', 'look', 'up', 'show', 'the', 'a'
  ])
  const tokens = command.split(' ').filter(Boolean)

  for (let index = tokens.length - 1; index >= 0; index -= 1) {
    const token = tokens[index]
    if (!commandWords.has(token) && /^[a-z0-9]{1,10}$/.test(token)) {
      return resolveVoiceSymbol(token)
    }
  }

  return ''
}

function routeVoiceSymbol(symbol) {
  const normalizedSymbol = String(symbol || '').trim().toUpperCase()
  if (!normalizedSymbol) {
    return
  }

  if (voiceCryptoSymbols.has(normalizedSymbol)) {
    navigateTo('Crypto Trade')
  } else {
    navigateTo('Stock Trade')
  }

  symbolInput.value = normalizedSymbol
}

async function runVoiceAnalysis(source, symbol = '', transcript = '') {
  const normalizedSymbol = resolveVoiceSymbol(symbol) || String(symbolInput.value || activeSymbol.value).trim().toUpperCase()

  if (normalizedSymbol) {
    routeVoiceSymbol(normalizedSymbol)
  } else if (!isTradeWorkspacePage.value) {
    navigateTo('Stock Trade')
  }

  const actionLabel = source === 'generate' ? 'Generating' : 'Searching'
  const workingSymbol = symbolInput.value.trim().toUpperCase() || activeSymbol.value
  setVoiceStatus(`${actionLabel} ${workingSymbol}.`, { speak: true, transcript })
  await runSearch(source)

  if (errorMessage.value) {
    setVoiceStatus(errorMessage.value, { speak: true, transcript })
    return
  }

  const finishedSymbol = activeTradeResponse.value?.stock?.symbol || workingSymbol
  setVoiceStatus(`${finishedSymbol} is ready. I loaded the latest analysis workspace for you.`, { speak: true, transcript })
}

function queueVoiceAction(action) {
  voicePendingAction.value = action
  setVoiceStatus(action.prompt, { speak: true })
}

function confirmVoiceAction() {
  const action = voicePendingAction.value

  if (!action) {
    setVoiceStatus('There is no pending action to confirm.', { speak: true })
    return
  }

  voicePendingAction.value = null

  if (action.type === 'signOut') {
    signOut()
    setVoiceStatus('Signed out safely.', { speak: true })
  }
}

function cancelVoiceAction() {
  voicePendingAction.value = null
  setVoiceStatus('Cancelled.', { speak: true })
}

function getIndicatorExplanation(command) {
  const explanations = {
    MA: 'MA is a moving average. It smooths price so you can see trend direction more clearly.',
    EMA: 'EMA is an exponential moving average. It reacts faster than a simple moving average.',
    MACD: 'MACD compares fast and slow moving averages. It helps spot momentum shifts.',
    BOLL: 'Bollinger Bands show whether price is stretched compared with recent volatility.',
    RSI: 'RSI measures overbought or oversold pressure on a zero to one hundred scale.',
    Vol: 'Volume shows trading activity. It helps confirm whether a move has real participation.',
    KDJ: 'KDJ is a momentum oscillator. It is useful for short-term turning point context.',
    OI: 'Open interest tracks active derivative contracts. It can show whether participation is expanding.',
    OBV: 'OBV is on balance volume. It estimates whether volume is flowing with buyers or sellers.'
  }
  const indicatorName = findVoiceIndicators(command)[0]
  return indicatorName ? explanations[indicatorName] : ''
}

function getAssistantContextSummary() {
  const selected = getSelectedIndicators()
  const symbol = activeTradeResponse.value?.stock?.symbol || activeSymbol.value
  return `You are on ${activePage.value}. Current symbol is ${symbol}. Selected indicators are ${selected.length ? selected.join(', ') : 'none'}.`
}

function buildConversationalReply(command) {
  const indicatorExplanation = getIndicatorExplanation(command)

  if (indicatorExplanation && includesVoicePhrase(command, ['what is', 'explain', 'tell me about', 'how does'])) {
    return indicatorExplanation
  }

  if (includesVoicePhrase(command, ['hello', 'hi', 'hey', 'good morning', 'good afternoon'])) {
    return 'Hi, I am here. You can talk normally, and I will either answer or operate the page for you.'
  }

  if (includesVoicePhrase(command, ['thank you', 'thanks', 'nice', 'great'])) {
    return 'Anytime. I am staying in AI Mode, so you can keep talking or use the page manually.'
  }

  if (includesVoicePhrase(command, ['where am i', 'what page', 'current page', 'where are we'])) {
    return getAssistantContextSummary()
  }

  if (includesVoicePhrase(command, ['what symbol', 'current symbol', 'which ticker', 'what ticker'])) {
    const symbol = activeTradeResponse.value?.stock?.symbol || activeSymbol.value
    return `The current ticker is ${symbol}. Say Generate ${symbol} if you want me to run the full analysis.`
  }

  if (includesVoicePhrase(command, ['which indicators', 'selected indicators', 'what indicators', 'indicators are on'])) {
    const selected = getSelectedIndicators()
    return selected.length
      ? `Selected indicators are ${selected.join(', ')}. You can say enable RSI, disable EMA, or only MACD and Bollinger.`
      : 'No indicators are selected. You can say enable all indicators, or enable MACD and Bollinger.'
  }

  if (includesVoicePhrase(command, ['how to generate', 'how do i generate', 'how can i generate'])) {
    return 'Say Generate followed by a ticker, like Generate AAPL. I will switch to the right workspace and run it.'
  }

  if (includesVoicePhrase(command, ['what can you do', 'help', 'commands'])) {
    return 'I can chat, open pages, select indicators, switch intervals, search tickers, and run Generate. I cannot place trades or give investment advice.'
  }

  if (includesVoicePhrase(command, ['financial advice', 'should i buy', 'should i sell', 'recommend', 'advice'])) {
    return 'I cannot give investment advice. I can help you open the analysis, explain indicators, and show the model output so you can review it.'
  }

  const maybeSymbol = extractVoiceSymbol(command)
  if (maybeSymbol) {
    return `I heard ${maybeSymbol}. If you want action, say Search ${maybeSymbol} or Generate ${maybeSymbol}.`
  }

  return 'I am listening, but I am not sure what action you want. You can ask a question, or say something like Generate AAPL, open Crypto Trade, or enable MACD.'
}

async function submitVoiceTextCommand() {
  const draft = voiceInputDraft.value.trim()

  if (!draft) {
    return
  }

  voiceInputDraft.value = ''
  await handleVoiceCommand(draft)
}

async function handleVoiceCommand(rawTranscript) {
  const command = normalizeVoiceText(rawTranscript)
  voiceTranscript.value = rawTranscript

  if (!command) {
    setVoiceStatus('I did not catch that. Please try again.', { speak: true, transcript: rawTranscript })
    return
  }

  if (voicePendingAction.value) {
    if (includesVoicePhrase(command, voiceConfirmPhrases)) {
      confirmVoiceAction()
      return
    }

    if (includesVoicePhrase(command, voiceCancelPhrases)) {
      cancelVoiceAction()
      return
    }
  }

  if (includesVoicePhrase(command, ['help', 'what can you do', 'commands'])) {
    setVoiceStatus(buildConversationalReply(command), {
      speak: true,
      transcript: rawTranscript
    })
    return
  }

  if (includesVoicePhrase(command, ['buy ', 'sell ', 'place order', 'submit order', 'market order', 'limit order', 'short ', 'go long', 'go short'])) {
    setVoiceStatus('Voice trading orders are disabled. I can control analysis and navigation only.', {
      speak: true,
      transcript: rawTranscript
    })
    return
  }

  if (includesVoicePhrase(command, ['sign out', 'log out', 'logout'])) {
    queueVoiceAction({
      type: 'signOut',
      prompt: 'Confirm sign out? Say confirm to leave your account, or cancel to stay signed in.'
    })
    return
  }

  if (includesVoicePhrase(command, ['clear indicators', 'turn off all indicators', 'disable all indicators'])) {
    indicators.value = indicators.value.map((indicator) => ({ ...indicator, active: false }))
    setVoiceStatus('All indicators are off.', { speak: true, transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['select all indicators', 'enable all indicators', 'turn on all indicators'])) {
    indicators.value = indicators.value.map((indicator) => ({ ...indicator, active: true }))
    setVoiceStatus('All indicators are on.', { speak: true, transcript: rawTranscript })
    return
  }

  const mentionedIndicators = findVoiceIndicators(command)
  if (mentionedIndicators.length) {
    if (command.includes('only')) {
      setOnlyVoiceIndicators(mentionedIndicators)
      setVoiceStatus(`Only ${mentionedIndicators.join(', ')} are selected.`, { speak: true, transcript: rawTranscript })
      return
    }

    if (includesVoicePhrase(command, voiceDisablePhrases)) {
      setIndicatorActive(mentionedIndicators, false)
      setVoiceStatus(`${mentionedIndicators.join(', ')} turned off.`, { speak: true, transcript: rawTranscript })
      return
    }

    if (includesVoicePhrase(command, voiceEnablePhrases)) {
      setIndicatorActive(mentionedIndicators, true)
      setVoiceStatus(`${mentionedIndicators.join(', ')} turned on.`, { speak: true, transcript: rawTranscript })
      return
    }
  }

  const requestedInterval = findVoiceInterval(command)
  if (requestedInterval && includesVoicePhrase(command, ['interval', 'chart', 'time frame', 'timeframe', 'switch'])) {
    selectedChartInterval.value = requestedInterval
    setVoiceStatus(`Chart interval set to ${requestedInterval}.`, { speak: true, transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['generate', 'run analysis', 'analyze', 'analyse'])) {
    await runVoiceAnalysis('generate', extractVoiceSymbol(command), rawTranscript)
    return
  }

  if (includesVoicePhrase(command, ['search', 'look up', 'quote', 'price'])) {
    await runVoiceAnalysis('search', extractVoiceSymbol(command), rawTranscript)
    return
  }

  const naturalSymbol = extractVoiceSymbol(command)
  if (naturalSymbol && includesVoicePhrase(command, ['show', 'check', 'open', 'load', 'what about'])) {
    await runVoiceAnalysis('search', naturalSymbol, rawTranscript)
    return
  }

  const requestedPage = findVoicePage(command)
  if (requestedPage && includesVoicePhrase(command, ['open', 'go to', 'show', 'switch to', 'navigate'])) {
    navigateTo(requestedPage)
    setVoiceStatus(`Opened ${requestedPage}.`, { speak: true, transcript: rawTranscript })
    return
  }

  setVoiceStatus(buildConversationalReply(command), {
    speak: true,
    transcript: rawTranscript
  })
}

function navigateTo(page) {
  const normalizedPage = page === 'Analysis' ? 'Stock Trade' : page

  if (accessiblePages.value.includes(normalizedPage)) {
    activePage.value = normalizedPage
    authMessage.value = ''
    errorMessage.value = ''

    if (normalizedPage === 'Crypto Trade') {
      symbolInput.value = cryptoResponse.value.stock.symbol
    } else if (normalizedPage === 'Stock Trade') {
      symbolInput.value = activeSymbol.value
    }

    if (normalizedPage === 'Reset Password') {
      resetPasswordRequestForm.value.email = resetPasswordForm.value.email || resetPasswordRequestForm.value.email
    }

    if (normalizedPage === 'Admin' && currentUser.value?.isAdmin) {
      loadAdminUsers({ silent: hasAdminUsersCache.value })
    }
  }
}

function selectPopularSymbol(symbol) {
  symbolInput.value = symbol
  if (activePage.value === 'Crypto Trade') {
    cryptoResponse.value = createCryptoWorkspaceResponse(symbol)
    errorMessage.value = ''
    return
  }
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
  activePage.value = 'Stock Trade'

  if (symbol !== activeSymbol.value) {
    runSearch()
  }
}

function openCryptoAnalysis(symbol = cryptoResponse.value.stock.symbol) {
  if (!isAuthenticated.value) {
    activePage.value = 'Sign In'
    authMessage.value = 'Please sign in first to access the crypto trade workspace.'
    return
  }

  const cleanedSymbol = String(symbol || 'BTC').trim().toUpperCase() || 'BTC'
  cryptoResponse.value = createCryptoWorkspaceResponse(cleanedSymbol)
  symbolInput.value = cleanedSymbol
  activePage.value = 'Crypto Trade'
}

function buildAnalysisCacheKey(symbol, analysisMode = 'full') {
  return [
    String(symbol || '').trim().toUpperCase(),
    selectedChartInterval.value,
    getSelectedIndicators().join(','),
    analysisMode
  ].join('|')
}

async function fetchStockAnalysis(symbol, { analysisMode = 'full' } = {}) {
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

  const requestUrl = `${API_BASE_URL}/stock/${cleanedSymbol}?${query.toString()}`
  const response = await secureFetch(requestUrl, {
    timeoutMs: analysisMode === 'search' ? 12000 : 35000
  })

  if (!response.ok) {
    const payload = await parseErrorResponse(
      response,
      `${cleanedSymbol} data is not accessible right now.`
    )
    throw new Error(payload.message || `${cleanedSymbol} data is not accessible right now.`)
  }

  const data = await response.json()
  analysisCache.value = {
    ...analysisCache.value,
    [cacheKey]: data
  }

  return data
}

async function runSearch(source = 'search') {
  const cleanedSymbol = symbolInput.value.trim().toUpperCase()

  if (!cleanedSymbol) {
    errorMessage.value = activePage.value === 'Crypto Trade'
      ? 'Please enter a crypto ticker before searching.'
      : 'Please enter a stock symbol before searching.'
    return
  }

  if (!/^[A-Z0-9]{1,10}$/.test(cleanedSymbol)) {
    errorMessage.value = activePage.value === 'Crypto Trade'
      ? 'Please enter a valid crypto ticker using letters or numbers, such as BTC or OKB.'
      : 'Please enter a valid symbol using letters only, such as AAPL.'
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

  if (activePage.value === 'Crypto Trade') {
    cryptoResponse.value = createCryptoWorkspaceResponse(cleanedSymbol)
    symbolInput.value = cleanedSymbol
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        window.scrollTo({ top: 0, behavior: 'smooth' })
      })
    })
    if (isGenerateAction) {
      isGenerating.value = false
    } else {
      isSearching.value = false
    }
    return
  }

  try {
    const data = await fetchStockAnalysis(cleanedSymbol, {
      analysisMode: isGenerateAction ? 'full' : 'search'
    })

    stockResponse.value = data
    activeSymbol.value = data.stock.symbol
    symbolInput.value = data.stock.symbol
    activePage.value = 'Stock Trade'
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        window.scrollTo({ top: 0, behavior: 'smooth' })
      })
    })
  } catch (error) {
    errorMessage.value =
      error?.message || 'This data is not accessible right now.'
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
  () => [isAuthenticated.value, portfolioSymbols.value.join('|')],
  ([authenticated]) => {
    if (!authenticated || !portfolioSymbols.value.length) {
      return
    }

    syncPortfolioSparklines(portfolioSymbols.value)
  },
  { immediate: true }
)

watch(isAuthenticated, (authenticated) => {
  if (authenticated) {
    return
  }

  stopVoiceListening()
  clearVoiceRestartTimer()
  voiceAssistantOpen.value = false
  voiceAssistantEnabled.value = false
  voicePendingAction.value = null
})

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

async function parseErrorResponse(response, fallbackMessage) {
  const rawText = await response.text()
  const statusMessage = response?.status
    ? `${fallbackMessage} (HTTP ${response.status})`
    : fallbackMessage

  if (!rawText) {
    return { message: statusMessage }
  }

  try {
    return JSON.parse(rawText)
  } catch {
    const textPreview = String(rawText)
      .replace(/<[^>]*>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 180)

    return {
      message: textPreview ? `${statusMessage}: ${textPreview}` : statusMessage
    }
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

async function fetchFreshCsrfToken() {
  csrfToken.value = ''
  return ensureCsrfToken()
}

async function secureFetch(url, options = {}) {
  const method = String(options.method || 'GET').toUpperCase()
  const needsCsrf = !options.skipCsrf && method !== 'GET' && method !== 'HEAD'
  const timeoutMs = Number(options.timeoutMs || 0) > 0 ? Number(options.timeoutMs) : 12000

  async function performRequest(forceFreshToken = false) {
    const headers = {
      ...(options.headers || {})
    }

    if (needsCsrf) {
      headers['X-CSRF-Token'] = forceFreshToken
        ? await fetchFreshCsrfToken()
        : await ensureCsrfToken()
    }

    const controller = new AbortController()
    const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)

    try {
      return await fetch(url, {
        ...options,
        headers,
        credentials: 'same-origin',
        signal: controller.signal,
      })
    } finally {
      window.clearTimeout(timeoutId)
    }
  }

  let response

  try {
    response = await performRequest(false)
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new Error('The request took too long. Please try again.')
    }
    throw error
  }

  if (needsCsrf && response.status === 403) {
    let payload = null
    try {
      payload = await response.clone().json()
    } catch {
      payload = null
    }

    if (payload?.message === 'CSRF validation failed.') {
      try {
        response = await performRequest(true)
      } catch (error) {
        if (error?.name === 'AbortError') {
          throw new Error('The request took too long. Please try again.')
        }
        throw error
      }
    }
  }

  return response
}

function applyAuthenticatedState(user, message = '') {
  currentUser.value = user
  isAuthenticated.value = true
  activePage.value = 'Dashboard'
  authMessage.value = message
}

function applyAdminUsers(users) {
  if (!Array.isArray(users)) {
    return
  }

  adminUsers.value = users
  hasAdminUsersCache.value = users.length > 0
  writeAdminUsersCache(users)
  adminMessage.value = ''
  isAdminLoading.value = false
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
    if (payload.user?.isAdmin) {
      restoreAdminUsersFromCache()
      loadAdminUsers({ silent: hasAdminUsersCache.value }).catch(() => {})
    } else {
      applyAdminUsers([])
    }
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
      skipCsrf: true,
      timeoutMs: 20000,
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
    if (payload.user?.isAdmin) {
      restoreAdminUsersFromCache()
      loadAdminUsers({ silent: hasAdminUsersCache.value }).catch(() => {})
    } else {
      applyAdminUsers([])
    }
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
    authMessage.value = 'Please complete username, email, and password to create the account.'
    return
  }

  const normalizedUsername = registrationForm.value.fullName.trim()
  if (!/^[A-Za-z0-9]+$/.test(normalizedUsername)) {
    authMessage.value = 'Username must use only English letters and numbers.'
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
        fullName: normalizedUsername,
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

async function loadAdminUsers(options = {}) {
  if (!currentUser.value?.isAdmin) {
    adminMessage.value = 'Admin access is required.'
    return
  }

  const silent = Boolean(options.silent)

  if (!silent) {
    isAdminLoading.value = true
    adminMessage.value = ''
  }

  try {
    const response = await secureFetch(`${API_BASE_URL}/auth/users`, {
      timeoutMs: 20000
    })
    const payload = await parseJsonResponse(
      response,
      'Could not load registered users right now.'
    )

    if (!response.ok) {
      throw new Error(payload.message || 'Could not load registered users.')
    }

    applyAdminUsers(payload.users || [])
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

  const confirmed = window.confirm(
    isDisabled
      ? `Disable ${user.email}? They will not be able to sign in until you enable the account again.`
      : `Enable ${user.email}? This user will be allowed to sign in again.`
  )

  if (!confirmed) {
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

async function removeAdminUser(user) {
  if (!currentUser.value?.isAdmin) {
    adminMessage.value = 'Admin access is required.'
    return
  }

  const confirmed = window.confirm(
    `Remove ${user.email}? This will permanently delete the user account.`
  )

  if (!confirmed) {
    return
  }

  const key = String(user?.id ?? '')
  adminMessage.value = `Removing ${user.email}...`
  pendingAdminStatusUpdates.value = {
    ...pendingAdminStatusUpdates.value,
    [key]: true
  }

  try {
    const response = await secureFetch(`${API_BASE_URL}/auth/users/${user.id}`, {
      method: 'DELETE'
    })
    const payload = await response.json()

    if (!response.ok) {
      throw new Error(payload.message || 'Could not remove this user.')
    }

    adminUsers.value = adminUsers.value.filter((item) => item.id !== user.id)
    adminMessage.value = payload.message || `Removed ${user.email}.`
  } catch (error) {
    adminMessage.value = error.message || 'Could not remove this user right now.'
  } finally {
    const nextPending = { ...pendingAdminStatusUpdates.value }
    delete nextPending[key]
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
  hasAdminUsersCache.value = false
  adminMessage.value = ''
  pendingAdminStatusUpdates.value = {}
  pendingAdminPasswordResets.value = {}
  adminPasswordResetDrafts.value = {}
  csrfToken.value = ''
  clearAdminUsersCache()
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
      const normalizedPage = page === 'Analysis' ? 'Stock Trade' : page
      if (accessiblePages.value.includes(normalizedPage)) {
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

      <div v-if="canInstallApp || isAuthenticated" class="topbar-actions">
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
            <button class="topbar-button" @click="navigateTo('Register')">Register</button>
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
              <button class="topbar-button secondary" type="button" @click="navigateTo('Register')">Register</button>
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
          <h1>Register for Noob Trade</h1>
          <p class="page-subtitle">
            Register with your email and password. Regular users must verify by email, while the preconfigured admin accounts can sign in directly.
          </p>

          <form @submit.prevent="submitRegistration">
            <div v-if="authMessage" class="status-message loading-message">
              {{ authMessage }}
            </div>

            <div class="auth-form-grid two-columns">
              <label class="auth-field">
                <span>Username</span>
                <input
                  v-model="registrationForm.fullName"
                  type="text"
                  placeholder="NoobTrade123"
                  inputmode="latin"
                  autocomplete="username"
                />
                <small class="auth-field-hint">Use only English letters and numbers.</small>
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
              <button class="topbar-button" type="submit">Register</button>
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

    <main v-else-if="isTradeWorkspacePage" class="dashboard-layout">
      <section class="column panel left-panel">
        <div class="panel-topbar brand-bar">
          <div class="brand-mark">
            <span class="brand-title trade-title">{{ activeTradeWorkspaceLabel }}</span>
          </div>
          <button class="menu-button" type="button">≡</button>
        </div>

        <div class="search-block">
          <h1>{{ activeTradeWorkspaceLabel }} Desk</h1>
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
            :placeholder="tradeSearchPlaceholder"
            :loading-label="tradeSearchLoadingLabel"
            :popular-symbols="tradePopularSymbols"
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
            <h2>{{ displayedTradeSymbol }} {{ activeTradeWorkspaceLabel }} Setup</h2>
            <span class="source-pill" :class="`source-pill--${dataSourceMeta.tone}`">
              {{ dataSourceMeta.label }}
            </span>
          </div>
        </div>

        <ChartPanel
          :active-indicators="appliedIndicators"
          :active-symbol="displayedTradeSymbol"
          :chart-data="activeTradeResponse.chartData"
          :chart-intervals="chartIntervals"
          :company-name="activeTradeResponse.stock.companyName"
          :industry="activeTradeResponse.stock.industry"
          :selected-interval="selectedChartInterval"
          :sector="activeTradeResponse.stock.sector"
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
            <h2>{{ displayedTradeSymbol }} Forecast</h2>
            <span class="source-pill" :class="`source-pill--${dataSourceMeta.tone}`">
              {{ dataSourceMeta.label }}
            </span>
          </div>
        </div>

        <PredictionSummary
          :format-percent="formatPercent"
          :request-data="activeTradeResponse.request"
          :stock-data="activeTradeResponse.stock"
          :analysis-data="activeTradeResponse.patternAnalysis"
        />

        <MatchedPatterns
          :matched-patterns="activeTradeResponse.patternAnalysis.matchedHistoricalPatterns"
          :high-fit-paths="activeTradeResponse.patternAnalysis.highFitHistoricalPaths"
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
        <article class="table-surface explore-market-panel">
          <div class="table-header">
            <h2>Stock</h2>
            <span class="section-chip">{{ exploreSearchQuery ? 'Search Results' : exploreViewMode === 'full' ? 'Full Market Board' : currentExploreTab }}</span>
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

        <article v-if="exploreViewMode !== 'full'" class="table-surface explore-market-panel crypto-explore-panel">
          <div class="table-header">
            <h2>Crypto</h2>
            <span class="section-chip">Ranked</span>
          </div>

          <div class="data-table">
            <div class="data-row data-head explore-head crypto-explore-head">
              <span>Symbol</span>
              <span>Name</span>
              <span>Category</span>
              <span>Price</span>
              <span>Market Value</span>
              <span>1D</span>
            </div>
            <div
              v-for="row in filteredCryptoExploreRows"
              :key="`crypto-${row.symbol}`"
              class="data-row explore-row crypto-explore-row"
            >
              <button
                class="watchlist-link explore-symbol-link"
                @click="openCryptoAnalysis(row.symbol)"
              >
                {{ row.symbol }}
              </button>
              <span>{{ row.name }}</span>
              <span>{{ row.category }}</span>
              <span>{{ row.price }}</span>
              <span>{{ row.notional }}</span>
              <strong :class="row.tone">{{ row.change }}</strong>
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
            <button class="chip" @click="navigateTo('Stock Trade')">Open Stock Trade</button>
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
          <h2>Registered Users ({{ adminUserCountLabel }})</h2>
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
                      :disabled="pendingAdminStatusUpdates[String(user.id)]"
                      @click="openAdminPasswordReset(user)"
                    >
                      Reset Password
                    </button>
                    <button
                      class="chip chip-danger"
                      type="button"
                      :disabled="pendingAdminStatusUpdates[String(user.id)]"
                      @click="removeAdminUser(user)"
                    >
                      {{ pendingAdminStatusUpdates[String(user.id)] ? 'Saving...' : 'Remove' }}
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

    <aside v-if="isAuthenticated" class="voice-assistant" :class="{ open: voiceAssistantOpen, enabled: voiceAssistantEnabled }">
      <button
        v-if="!voiceAssistantOpen"
        class="voice-fab"
        type="button"
        :aria-expanded="voiceAssistantOpen"
        aria-controls="voice-assistant-panel"
        @click="openVoiceAssistantPanel"
      >
        <span class="voice-fab-orb" :class="{ listening: voiceListening, enabled: voiceAssistantEnabled }"></span>
        <span>AI</span>
      </button>

      <section
        v-if="voiceAssistantOpen"
        id="voice-assistant-panel"
        class="voice-panel"
        aria-label="Noob Trade voice assistant"
      >
        <div class="voice-panel-header">
          <div>
            <span class="section-chip">AI Voice Mode</span>
            <h2>Noob AI Assistant</h2>
          </div>
          <div class="voice-header-actions">
            <span class="voice-state" :class="{ active: voiceListening }">{{ voiceActionLabel }}</span>
            <button class="voice-minimize-button" type="button" @click="minimizeVoiceAssistantPanel">Shrink</button>
          </div>
        </div>

        <p class="voice-disclaimer">
          AI Mode listens continuously while on. You can still use every manual control. No voice trading orders or investment advice.
        </p>

        <button
          class="voice-mode-toggle"
          type="button"
          :class="{ enabled: voiceAssistantEnabled }"
          @click="toggleVoiceAssistant"
        >
          <span class="voice-switch-track">
            <span class="voice-switch-thumb"></span>
          </span>
          <span>
            <strong>{{ voiceAssistantEnabled ? 'AI Mode On' : 'AI Mode Off' }}</strong>
            <small>{{ voiceAssistantEnabled ? 'Listening and chatting automatically' : 'Manual mode only' }}</small>
          </span>
        </button>

        <div class="voice-command-box" aria-live="polite">
          <small>Assistant status</small>
          <strong>{{ voiceStatus }}</strong>
          <p>{{ voiceTranscript ? `Heard: ${voiceTranscript}` : 'Say a question or command in English.' }}</p>
        </div>

        <div class="voice-text-input">
          <input
            v-model="voiceInputDraft"
            type="text"
            placeholder="Type a question or command..."
            @keyup.enter="submitVoiceTextCommand"
          />
          <button class="topbar-button secondary" type="button" @click="submitVoiceTextCommand">Send</button>
        </div>

        <div v-if="voicePendingAction" class="voice-confirm-card">
          <strong>Confirmation required</strong>
          <p>{{ voicePendingAction.prompt }}</p>
          <div class="voice-actions">
            <button class="topbar-button" type="button" @click="confirmVoiceAction">Confirm</button>
            <button class="topbar-button secondary" type="button" @click="cancelVoiceAction">Cancel</button>
          </div>
        </div>

        <div class="voice-hints">
          <span v-for="example in voiceCommandExamples" :key="example">{{ example }}</span>
        </div>

        <div class="voice-footer">
          <span>Voice: {{ voicePreferredVoiceName }}</span>
          <span>{{ voiceSupported ? 'Browser voice enabled' : 'Use Chrome or Edge for mic control' }}</span>
        </div>

        <div class="voice-log">
          <div v-if="!voiceChatTimeline.length" class="voice-log-empty">
            <strong>Noob AI</strong>
            <small>Turn AI Mode on and talk naturally. I can answer questions or operate the page.</small>
          </div>
          <div v-for="item in voiceChatTimeline" :key="`${item.time}-${item.transcript}-${item.response}`" class="voice-chat-turn">
            <div class="voice-bubble user">
              <span>You · {{ item.time }}</span>
              <strong>{{ item.transcript }}</strong>
            </div>
            <div class="voice-bubble assistant">
              <span>Noob AI</span>
              <strong>{{ item.response }}</strong>
            </div>
          </div>
        </div>
      </section>
    </aside>

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
