
<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Fuse from 'fuse.js'

import ChartPanel from './components/ChartPanel.vue'
import IndicatorSelector from './components/IndicatorSelector.vue'
import MatchedPatterns from './components/MatchedPatterns.vue'
import PredictionSummary from './components/PredictionSummary.vue'
import SearchBar from './components/SearchBar.vue'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'
const ADMIN_USERS_CACHE_KEY = 'noobtrade_admin_users'
const UI_LANGUAGE_KEY = 'noobtrade_ui_language'
const APP_MODE_KEY = 'noobtrade_app_mode'
const DEFAULT_STOCK_SYMBOL = 'AAPL'
const DEFAULT_CRYPTO_SYMBOL = 'BTC'
const STOCK_GENERATE_INTERVAL = 'daily'
const CRYPTO_GENERATE_INTERVAL = 'daily'
const GENERATE_WARM_RETRY_ATTEMPTS = 8
const STOCK_CHART_PREFETCH_INTERVALS = ['1min', '5min', '15min', '30min', '1hour', 'monthly']
const CHART_SERIES_MINIMUM_BARS = {
  '1min': 30,
  '5min': 30,
  '15min': 24,
  '30min': 20,
  '1hour': 16,
  daily: 30,
  '5day': 20,
  weekly: 20,
  '2week': 12,
  monthly: 12
}
const STOCK_MARKET_PAGE_SIZE = 30
const CRYPTO_EXPLORE_UNIVERSE_SIZE = 250
const STOCK_EXPLORE_LIVE_SEARCH_DELAY_MS = 350
const chartIntervals = ['1min', '5min', '15min', '30min', '1hour', 'daily', '5day', 'weekly', '2week', 'monthly']
const publicPages = ['Home', 'Sign In', 'Register', 'Verify Email', 'Reset Password', 'Reset Password Confirm']
const publicNavPages = ['Home', 'Sign In', 'Register']
const authenticatedPages = ['Dashboard', 'Stock Trade', 'Crypto Trade', 'Explore', 'Markets', 'Settings', 'More']
const tradeWorkspacePages = ['Stock Trade', 'Crypto Trade']
const languageOptions = [
  { code: 'en', label: 'English', voiceLang: 'en-US' },
  { code: 'zh', label: '中文', voiceLang: 'zh-CN' },
  { code: 'es', label: 'Español', voiceLang: 'es-ES' },
  { code: 'fr', label: 'Français', voiceLang: 'fr-FR' }
]
const uiCopy = {
  en: {
    selectLanguage: 'Select your language',
    signOut: 'Sign out',
    switchToCrypto: 'Switch to Crypto',
    switchToStock: 'Switch to Stock',
    installApp: 'Install App',
    pageLabels: {
      Home: 'Home',
      'Sign In': 'Sign In',
      Register: 'Register',
      Dashboard: 'Dashboard',
      'Stock Trade': 'Stock Trade',
      'Crypto Trade': 'Crypto Trade',
      Portfolio: 'Portfolio',
      Explore: 'Explore',
      Markets: 'Markets',
      Settings: 'Settings',
      More: 'More',
      Admin: 'Admin'
    },
    settingsEyebrow: 'Settings',
    settingsTitle: 'Your account at a glance',
    settingsSubtitle: 'Review your personal account ID, registered email, language preference, and basic account status in one place.',
    accountDetails: 'Account Details',
    accountId: 'Account ID',
    fullName: 'Full Name',
    email: 'Email',
    membership: 'Membership',
    joined: 'Joined',
    adminRole: 'Admin',
    userRole: 'User',
    notAvailable: 'Not available',
    regularUser: 'Regular User',
    recent: 'Recent',
    session: 'Session',
    currentLogin: 'Current login',
    verified: 'Verified',
    pendingVerification: 'Pending verification',
    aiMode: 'AI Voice Mode',
    aiTitle: 'Noob AI Assistant',
    shrink: 'Shrink',
    aiDisclaimer: 'AI Mode listens continuously while on. You can still use every manual control. No voice trading orders or investment advice.',
    aiModeOn: 'AI Mode On',
    aiModeOff: 'AI Mode Off',
    aiListening: 'Listening and chatting automatically',
    aiManual: 'Manual mode only',
    assistantStatus: 'Assistant status',
    heardPrefix: 'Heard',
    sayCommand: 'Say a question or command.',
    typeCommand: 'Type a question or command...',
    send: 'Send',
    confirmationRequired: 'Confirmation required',
    confirm: 'Confirm',
    cancel: 'Cancel',
    voiceLabel: 'Voice',
    voiceEnabled: 'Browser voice enabled',
    voiceUnsupported: 'Use Chrome or Edge for mic control',
    noobAiIntro: 'Turn AI Mode on and talk naturally. I can answer questions or operate the page.',
    you: 'You',
    generating: 'Generating',
    searching: 'Searching',
    speaking: 'Speaking',
    listening: 'Listening',
    aiModeOnShort: 'AI mode on',
    aiModeOffShort: 'AI mode off',
  },
  zh: {
    selectLanguage: '选择语言',
    signOut: '退出登录',
    switchToCrypto: '切换到 Crypto',
    switchToStock: '切换到 Stock',
    installApp: '安装应用',
    pageLabels: {
      Home: '首页',
      'Sign In': '登录',
      Register: '注册',
      Dashboard: '仪表盘',
      'Stock Trade': '股票分析',
      'Crypto Trade': '加密分析',
      Portfolio: '投资组合',
      Explore: '探索',
      Markets: '市场',
      Settings: '设置',
      More: '更多',
      Admin: '后台'
    },
    settingsEyebrow: '设置',
    settingsTitle: '你的账户信息',
    settingsSubtitle: '在这里查看账户 ID、注册邮箱、语言偏好和基础账户状态。',
    accountDetails: '账户详情',
    accountId: '账户 ID',
    fullName: '用户名',
    email: '邮箱',
    membership: '会员类型',
    joined: '加入时间',
    adminRole: '管理员',
    userRole: '用户',
    notAvailable: '暂无',
    regularUser: '普通用户',
    recent: '最近',
    session: '会话',
    currentLogin: '当前登录',
    verified: '已验证',
    pendingVerification: '等待验证',
    aiMode: 'AI 语音模式',
    aiTitle: 'Noob AI 助手',
    shrink: '缩小',
    aiDisclaimer: 'AI 模式开启后会持续听取指令。你仍然可以手动操作。不会语音下单，也不构成投资建议。',
    aiModeOn: 'AI 模式开启',
    aiModeOff: 'AI 模式关闭',
    aiListening: '正在自动听取和回复',
    aiManual: '仅手动操作',
    assistantStatus: '助手状态',
    heardPrefix: '听到',
    sayCommand: '说一个问题或指令。',
    typeCommand: '输入问题或指令...',
    send: '发送',
    confirmationRequired: '需要确认',
    confirm: '确认',
    cancel: '取消',
    voiceLabel: '声音',
    voiceEnabled: '浏览器语音已启用',
    voiceUnsupported: '建议使用 Chrome 或 Edge 开启麦克风',
    noobAiIntro: '打开 AI 模式后可以自然说话。我可以回答问题，也可以帮你操作页面。',
    you: '你',
    generating: '生成中',
    searching: '搜索中',
    speaking: '正在回答',
    listening: '正在聆听',
    aiModeOnShort: 'AI 已开启',
    aiModeOffShort: 'AI 已关闭',
  },
  es: {
    selectLanguage: 'Selecciona tu idioma',
    signOut: 'Cerrar sesión',
    switchToCrypto: 'Cambiar a Crypto',
    switchToStock: 'Cambiar a Stock',
    installApp: 'Instalar app',
    pageLabels: {
      Home: 'Inicio',
      'Sign In': 'Iniciar sesión',
      Register: 'Registro',
      Dashboard: 'Panel',
      'Stock Trade': 'Acciones',
      'Crypto Trade': 'Cripto',
      Portfolio: 'Portafolio',
      Explore: 'Explorar',
      Markets: 'Mercados',
      Settings: 'Configuración',
      More: 'Más',
      Admin: 'Admin'
    },
    settingsEyebrow: 'Configuración',
    settingsTitle: 'Tu cuenta de un vistazo',
    settingsSubtitle: 'Revisa tu ID, correo registrado, idioma y estado básico de cuenta.',
    accountDetails: 'Detalles de cuenta',
    accountId: 'ID de cuenta',
    fullName: 'Nombre',
    email: 'Correo',
    membership: 'Membresía',
    joined: 'Fecha de registro',
    adminRole: 'Admin',
    userRole: 'Usuario',
    notAvailable: 'No disponible',
    regularUser: 'Usuario regular',
    recent: 'Reciente',
    session: 'Sesión',
    currentLogin: 'Inicio actual',
    verified: 'Verificado',
    pendingVerification: 'Verificación pendiente',
    aiMode: 'Modo de voz AI',
    aiTitle: 'Asistente Noob AI',
    shrink: 'Reducir',
    aiDisclaimer: 'AI Mode escucha continuamente cuando está activado. También puedes usar controles manuales. Sin órdenes de trading ni asesoría financiera.',
    aiModeOn: 'AI Mode activado',
    aiModeOff: 'AI Mode desactivado',
    aiListening: 'Escuchando y respondiendo automáticamente',
    aiManual: 'Solo modo manual',
    assistantStatus: 'Estado del asistente',
    heardPrefix: 'Escuché',
    sayCommand: 'Di una pregunta o comando.',
    typeCommand: 'Escribe una pregunta o comando...',
    send: 'Enviar',
    confirmationRequired: 'Confirmación requerida',
    confirm: 'Confirmar',
    cancel: 'Cancelar',
    voiceLabel: 'Voz',
    voiceEnabled: 'Voz del navegador activada',
    voiceUnsupported: 'Usa Chrome o Edge para el micrófono',
    noobAiIntro: 'Activa AI Mode y habla naturalmente. Puedo responder o controlar la página.',
    you: 'Tú',
    generating: 'Generando',
    searching: 'Buscando',
    speaking: 'Hablando',
    listening: 'Escuchando',
    aiModeOnShort: 'AI activado',
    aiModeOffShort: 'AI desactivado',
  },
  fr: {
    selectLanguage: 'Choisir la langue',
    signOut: 'Se déconnecter',
    switchToCrypto: 'Passer à Crypto',
    switchToStock: 'Passer à Stock',
    installApp: 'Installer',
    pageLabels: {
      Home: 'Accueil',
      'Sign In': 'Connexion',
      Register: 'Inscription',
      Dashboard: 'Tableau',
      'Stock Trade': 'Actions',
      'Crypto Trade': 'Crypto',
      Portfolio: 'Portefeuille',
      Explore: 'Explorer',
      Markets: 'Marchés',
      Settings: 'Paramètres',
      More: 'Plus',
      Admin: 'Admin'
    },
    settingsEyebrow: 'Paramètres',
    settingsTitle: 'Votre compte en un coup d’oeil',
    settingsSubtitle: 'Consultez votre ID, votre e-mail, votre langue et le statut du compte.',
    accountDetails: 'Détails du compte',
    accountId: 'ID du compte',
    fullName: 'Nom complet',
    email: 'E-mail',
    membership: 'Abonnement',
    joined: 'Inscription',
    adminRole: 'Admin',
    userRole: 'Utilisateur',
    notAvailable: 'Non disponible',
    regularUser: 'Utilisateur standard',
    recent: 'Récent',
    session: 'Session',
    currentLogin: 'Connexion actuelle',
    verified: 'Vérifié',
    pendingVerification: 'Vérification en attente',
    aiMode: 'Mode vocal IA',
    aiTitle: 'Assistant Noob AI',
    shrink: 'Réduire',
    aiDisclaimer: 'Le mode IA écoute en continu lorsqu’il est activé. Les contrôles manuels restent disponibles. Pas d’ordres de trading ni de conseil financier.',
    aiModeOn: 'Mode IA activé',
    aiModeOff: 'Mode IA désactivé',
    aiListening: 'Écoute et réponse automatiques',
    aiManual: 'Mode manuel uniquement',
    assistantStatus: 'État de l’assistant',
    heardPrefix: 'Entendu',
    sayCommand: 'Posez une question ou donnez une commande.',
    typeCommand: 'Écrire une question ou commande...',
    send: 'Envoyer',
    confirmationRequired: 'Confirmation requise',
    confirm: 'Confirmer',
    cancel: 'Annuler',
    voiceLabel: 'Voix',
    voiceEnabled: 'Voix du navigateur activée',
    voiceUnsupported: 'Utilisez Chrome ou Edge pour le micro',
    noobAiIntro: 'Activez le mode IA et parlez naturellement. Je peux répondre ou contrôler la page.',
    you: 'Vous',
    generating: 'Génération',
    searching: 'Recherche',
    speaking: 'Réponse',
    listening: 'Écoute',
    aiModeOnShort: 'IA activée',
    aiModeOffShort: 'IA désactivée',
  }
}
const voiceCommandExamples = [
  'Scan watchlist',
  'Generate AAPL',
  'Generate BTC',
  'Open Full Market',
  'Open User Guide'
]
const voiceShortReplies = {
  en: {
    ready: 'Ready.',
    listen: 'Listening.',
    scanStart: 'OK, scanning now.',
    scanDone: 'Scan complete.',
    generateStart: 'OK, generating now.',
    generateDone: 'Generate complete.',
    searchStart: 'OK, searching now.',
    searchDone: 'Search complete.',
    starAdded: 'Star added.',
    starRemoved: 'Star removed.',
    dashboard: 'Back to Dashboard.',
    news: 'News opened.',
    done: 'Done.',
    pageOpened: 'Page opened.',
    indicators: 'Indicators updated.',
    interval: 'Interval changed.',
    probability: 'Probability updated.',
    history: 'History opened.',
    more: 'Loaded more.',
    stopped: 'Stopped.',
    blockedTrading: 'Manual trading only.',
    signIn: 'Please sign in.',
    unsupported: 'Voice unsupported.',
    misunderstood: 'I could not understand. Please say it again.',
    manualFallback: 'Please use manual controls. AI is improving.',
  },
  zh: {
    ready: '我在。',
    listen: '正在听。',
    scanStart: '好的，我这就scan。',
    scanDone: 'scan完成。',
    generateStart: '好的，我这就generate。',
    generateDone: 'generate完成。',
    searchStart: '好的，我这就search。',
    searchDone: 'search完成。',
    starAdded: '已添加星标。',
    starRemoved: '已取消星标。',
    dashboard: '已回到dashboard。',
    news: '我已经打开新闻。',
    done: '已完成。',
    pageOpened: '页面已打开。',
    indicators: '指标已更新。',
    interval: '周期已切换。',
    probability: '概率已更新。',
    history: '历史窗口已打开。',
    more: '已加载更多。',
    stopped: '已停止。',
    blockedTrading: '请手动操作。',
    signIn: '请先登录。',
    unsupported: '语音暂不支持。',
    misunderstood: '无法理解您说的，请再说一遍。',
    manualFallback: '请手动操作，AI智能提升中。',
  },
  es: {
    ready: 'Listo.',
    listen: 'Escuchando.',
    scanStart: 'Bien, escaneando.',
    scanDone: 'Scan completo.',
    generateStart: 'Bien, generando.',
    generateDone: 'Generate completo.',
    searchStart: 'Bien, buscando.',
    searchDone: 'Búsqueda completa.',
    starAdded: 'Favorito añadido.',
    starRemoved: 'Favorito quitado.',
    dashboard: 'Volví al Dashboard.',
    news: 'Noticias abiertas.',
    done: 'Hecho.',
    pageOpened: 'Página abierta.',
    indicators: 'Indicadores actualizados.',
    interval: 'Intervalo cambiado.',
    probability: 'Probabilidad actualizada.',
    history: 'Historial abierto.',
    more: 'Más cargado.',
    stopped: 'Detenido.',
    blockedTrading: 'Operación manual solamente.',
    signIn: 'Inicie sesión.',
    unsupported: 'Voz no soportada.',
    misunderstood: 'No entendí. Repítalo, por favor.',
    manualFallback: 'Use controles manuales. La IA está mejorando.',
  },
  fr: {
    ready: 'Prêt.',
    listen: 'Écoute.',
    scanStart: 'D’accord, je scan.',
    scanDone: 'Scan terminé.',
    generateStart: 'D’accord, je generate.',
    generateDone: 'Generate terminé.',
    searchStart: 'D’accord, je cherche.',
    searchDone: 'Recherche terminée.',
    starAdded: 'Favori ajouté.',
    starRemoved: 'Favori retiré.',
    dashboard: 'Retour Dashboard.',
    news: 'Nouvelles ouvertes.',
    done: 'Terminé.',
    pageOpened: 'Page ouverte.',
    indicators: 'Indicateurs mis à jour.',
    interval: 'Intervalle changé.',
    probability: 'Probabilité mise à jour.',
    history: 'Historique ouvert.',
    more: 'Plus chargé.',
    stopped: 'Arrêté.',
    blockedTrading: 'Trading manuel uniquement.',
    signIn: 'Connectez-vous.',
    unsupported: 'Voix non prise en charge.',
    misunderstood: "Je n'ai pas compris. Répétez, s'il vous plaît.",
    manualFallback: "Utilisez les contrôles manuels. L'IA s'améliore.",
  }
}
const voiceCryptoSymbols = new Set([
  'BTC', 'ETH', 'OKB', 'SOL', 'BNB', 'XRP', 'DOGE', 'ADA', 'TRX', 'AVAX',
  'LINK', 'TON', 'SHIB', 'DOT', 'BCH', 'NEAR', 'LTC', 'UNI', 'ICP', 'APT',
  'ETC', 'HBAR', 'ATOM', 'FIL', 'ARB', 'OP', 'SUI', 'INJ', 'SUSHI'
])
const voiceSymbolAliases = {
  aapl: 'AAPL',
  apl: 'AAPL',
  appl: 'AAPL',
  'a p l': 'AAPL',
  'a p p l': 'AAPL',
  apple: 'AAPL',
  iphone: 'AAPL',
  msft: 'MSFT',
  'm s f t': 'MSFT',
  tesla: 'TSLA',
  tsla: 'TSLA',
  't s l a': 'TSLA',
  nvidia: 'NVDA',
  nvda: 'NVDA',
  'n v d a': 'NVDA',
  microsoft: 'MSFT',
  amzn: 'AMZN',
  'a m z n': 'AMZN',
  amazon: 'AMZN',
  meta: 'META',
  facebook: 'META',
  googl: 'GOOGL',
  'g o o g l': 'GOOGL',
  google: 'GOOGL',
  alphabet: 'GOOGL',
  berkshire: 'BRK.B',
  'berkshire hathaway': 'BRK.B',
  brkb: 'BRK.B',
  'brk b': 'BRK.B',
  lilly: 'LLY',
  'eli lilly': 'LLY',
  broadcom: 'AVGO',
  jpmorgan: 'JPM',
  'jp morgan': 'JPM',
  chase: 'JPM',
  visa: 'V',
  exxon: 'XOM',
  'exxon mobil': 'XOM',
  unitedhealth: 'UNH',
  'united health': 'UNH',
  mastercard: 'MA',
  costco: 'COST',
  'johnson and johnson': 'JNJ',
  'home depot': 'HD',
  oracle: 'ORCL',
  'procter gamble': 'PG',
  merck: 'MRK',
  netflix: 'NFLX',
  abbvie: 'ABBV',
  'bank of america': 'BAC',
  'coca cola': 'KO',
  coke: 'KO',
  'advanced micro devices': 'AMD',
  chevron: 'CVX',
  pepsi: 'PEP',
  pepsico: 'PEP',
  salesforce: 'CRM',
  walmart: 'WMT',
  'thermo fisher': 'TMO',
  accenture: 'ACN',
  cisco: 'CSCO',
  mcdonalds: 'MCD',
  'mcdonald s': 'MCD',
  abbott: 'ABT',
  ibm: 'IBM',
  'international business machines': 'IBM',
  'general electric': 'GE',
  'ge aerospace': 'GE',
  linde: 'LIN',
  disney: 'DIS',
  adobe: 'ADBE',
  servicenow: 'NOW',
  'service now': 'NOW',
  intuit: 'INTU',
  qualcomm: 'QCOM',
  caterpillar: 'CAT',
  'texas instruments': 'TXN',
  'american express': 'AXP',
  amex: 'AXP',
  'applied materials': 'AMAT',
  booking: 'BKNG',
  'booking holdings': 'BKNG',
  uber: 'UBER',
  'uber technologies': 'UBER',
  goldman: 'GS',
  'goldman sachs': 'GS',
  bitcoin: 'BTC',
  btc: 'BTC',
  ethereum: 'ETH',
  eth: 'ETH',
  solana: 'SOL',
  sol: 'SOL',
  bnb: 'BNB',
  binance: 'BNB',
  xrp: 'XRP',
  ripple: 'XRP',
  doge: 'DOGE',
  dogecoin: 'DOGE',
  ada: 'ADA',
  cardano: 'ADA',
  trx: 'TRX',
  tron: 'TRX',
  avax: 'AVAX',
  avalanche: 'AVAX',
  link: 'LINK',
  chainlink: 'LINK',
  ton: 'TON',
  toncoin: 'TON',
  shib: 'SHIB',
  'shiba inu': 'SHIB',
  dot: 'DOT',
  polkadot: 'DOT',
  bch: 'BCH',
  'bitcoin cash': 'BCH',
  near: 'NEAR',
  litecoin: 'LTC',
  ltc: 'LTC',
  uni: 'UNI',
  uniswap: 'UNI',
  icp: 'ICP',
  apt: 'APT',
  aptos: 'APT',
  etc: 'ETC',
  'ethereum classic': 'ETC',
  hbar: 'HBAR',
  hedera: 'HBAR',
  atom: 'ATOM',
  cosmos: 'ATOM',
  fil: 'FIL',
  filecoin: 'FIL',
  arb: 'ARB',
  arbitrum: 'ARB',
  op: 'OP',
  optimism: 'OP',
  sui: 'SUI',
  inj: 'INJ',
  injective: 'INJ',
  sushi: 'SUSHI',
  sushiswap: 'SUSHI',
  'o k b': 'OKB',
  okb: 'OKB',
  's p y': 'SPY',
  spy: 'SPY'
}
const voiceIndicatorAliases = [
  { name: 'MA', phrases: ['ma', 'm a', 'moving average', 'moving averages', '均线', '移动平均', 'media movil', 'moyenne mobile'] },
  { name: 'EMA', phrases: ['ema', 'e m a', 'exponential moving average', '指数均线', '指数移动平均', 'media exponencial', 'moyenne exponentielle'] },
  { name: 'MACD', phrases: ['macd', 'm a c d'] },
  { name: 'BOLL', phrases: ['boll', 'bollinger', 'bollinger band', 'bollinger bands', '布林', '布林带', 'bandas de bollinger', 'bandes de bollinger'] },
  { name: 'RSI', phrases: ['rsi', 'r s i', '相对强弱', 'fuerza relativa', 'force relative'] },
  { name: 'Vol', phrases: ['vol', 'volume', '成交量', '量能', 'volumen'] },
  { name: 'KDJ', phrases: ['kdj', 'k d j'] },
  { name: 'OI', phrases: ['oi', 'o i', 'open interest', '未平仓量', 'interes abierto', 'intérêt ouvert'] },
  { name: 'OBV', phrases: ['obv', 'o b v', 'on balance volume', '能量潮', 'balance volume'] }
]
const voicePageAliases = [
  { page: 'Crypto Trade', phrases: ['crypto trade', 'crypto', 'crypto analysis', '加密', '加密分析', '虚拟货币', 'cripto', 'criptomonedas', 'crypto monnaie', 'cryptomonnaie'] },
  { page: 'Stock Trade', phrases: ['stock trade', 'stock analysis', 'analysis', 'trade page', 'trade', '股票分析', '股票', 'acciones', 'accion', 'análisis de acciones', 'analyse actions', 'actions'] },
  { page: 'Dashboard', phrases: ['dashboard', 'home dashboard', '仪表盘', '面板', 'panel', 'tableau'] },
  { page: 'Explore', phrases: ['explore', 'watchlist', 'explorar', 'explorer', '探索', '自选'] },
  { page: 'User Guide', phrases: ['user guide', 'how noobtrade works', 'how noob trade works', 'how it works', 'learn more', 'manual', 'guide', 'help page', '使用说明', '用户手册', '操作手册', '怎么用', '如何使用', '工作原理', 'guia', 'guía', 'manual de usuario', 'mode d emploi', 'guide utilisateur'] },
  { page: 'Markets', phrases: ['markets', 'market', '市场', 'mercados', 'mercado', 'marches', 'marchés'] },
  { page: 'Settings', phrases: ['settings', 'setting', 'myself', 'profile', 'account', 'configuration', 'configuracion', 'ajustes', 'parametres', 'paramètres', 'reglages', 'réglages', '设置', '账户', '账号', '个人信息'] },
  { page: 'More', phrases: ['more', 'more page', '更多', 'mas', 'más', 'plus'] },
  { page: 'Admin', phrases: ['admin', 'admin page', '后台', '管理员'] }
]
const voiceIntervalAliases = [
  { interval: '1min', phrases: ['1 minute', 'one minute', 'one min', '1 min', '1分钟', '一分钟'] },
  { interval: '5min', phrases: ['5 minute', 'five minute', '5 min', 'five min', '5分钟', '五分钟'] },
  { interval: '15min', phrases: ['15 minute', 'fifteen minute', '15 min', 'fifteen min', '15分钟', '十五分钟'] },
  { interval: '30min', phrases: ['30 minute', 'thirty minute', '30 min', 'thirty min', '30分钟', '三十分钟', '半小时'] },
  { interval: '1hour', phrases: ['hourly', 'one hour', '1 hour', '60 minute', '1小时', '一小时', '小时线'] },
  { interval: 'daily', phrases: ['daily', 'day chart', 'one day', '日线', '每日', '天线'] },
  { interval: '5day', phrases: ['five day', '5 day', 'five days', '5 days', '5日', '五日', '五天'] },
  { interval: 'weekly', phrases: ['weekly', 'week chart', 'one week', '周线', '一周'] },
  { interval: '2week', phrases: ['two week', '2 week', 'two weeks', '2 weeks', '两周', '2周'] },
  { interval: 'monthly', phrases: ['monthly', 'month chart', 'one month', '月线', '一月'] }
]
const voiceConfirmPhrases = ['confirm', 'yes', 'proceed', 'do it', 'run it', 'continue', '确认', '是的', '继续', 'sí', 'si', 'confirmar', 'oui', 'confirmer']
const voiceCancelPhrases = ['cancel', 'stop', 'no', 'never mind', 'nevermind', '取消', '停止', '不要', 'no', 'cancelar', 'parar', 'non', 'annuler', 'arreter', 'arrêter']
const voiceStopSpeechPhrases = ['stop talking', 'stop speaking', 'stop reading', 'be quiet', 'quiet', 'shut up', 'cancel speech', 'cancel voice', 'do not read', "don't read", 'pause voice', '停止朗读', '别念', '不要念', '不要读', '停一下', '安静', '闭嘴', 'parar voz', 'silencio', 'arrete de parler', 'arrête de parler']
const voiceEnablePhrases = ['enable', 'select', 'choose', 'pick', 'turn on', 'switch on', 'check', 'tick', 'add', 'use', 'include', '选择', '勾选', '打开', '启用', '加入', '使用', 'seleccionar', 'elige', 'elegir', 'activar', 'agregar', 'usar', 'incluye', 'incluire', 'selectionner', 'sélectionner', 'choisir', 'activer', 'ajouter', 'utiliser', 'inclure']
const voiceDisablePhrases = ['disable', 'unselect', 'deselect', 'cancel', 'turn off', 'switch off', 'uncheck', 'untick', 'remove', 'drop', 'exclude', '取消', '取消勾选', '关闭', '移除', '不要', 'quitar', 'desactivar', 'remover', 'excluir', 'retirer', 'desactiver', 'désactiver', 'enlever', 'exclure']
const voiceOnlyPhrases = ['only', 'only use', '只', '只选', '只用', '仅选择', 'solo', 'solamente', 'seulement', 'uniquement']
const voiceFollowUpPhrases = ['more', 'again', 'keep going', 'continue', 'a little bit more', 'little bit more', 'little more', 'bit more', 'further', 'more please', '再来', '继续', '再来一点', '再一点', '多一点', '再往下', '再往上', 'un poco mas', 'un poco más', 'otra vez', 'continua', 'continúa', 'encore', 'continuez', 'un peu plus']
const voiceFullMarketPhrases = [
  'full market', 'full market board', 'open full market', 'stock pool', 'stock universe',
  'all stocks', 'show all stocks', 'market board', 'full stock board',
  '全市场', '打开全市场', '股票池', '打开股票池', '全部股票', '所有股票', '完整股票列表',
  'mercado completo', 'todas las acciones', 'liste complete actions', 'liste complète actions'
]
const voiceViewMoreMarketPhrases = [
  'view more stocks', 'show more stocks', 'load more stocks', 'more stocks',
  'view more market', 'show more market', 'load more market',
  '查看更多股票', '加载更多股票', '显示更多股票', '更多股票', '查看更多市场',
  'ver mas acciones', 'ver más acciones', 'mostrar mas acciones', 'mostrar más acciones',
  'voir plus actions', 'afficher plus actions'
]
const voiceScrollIntentPhrases = [
  {
    intent: 'scrollDown',
    phrases: [
      'scroll down', 'scrolling down', 'scorll down', 'scorlling down', 'scrool down', 'scroolling down',
      'move down', 'page down', 'go down', 'down the page', 'lower', 'go lower', 'move lower',
      'keep going down', 'continue down', 'down more', 'more down', 'scroll more down', 'scrolling down more',
      '向下滚动', '下滑', '往下', '往下滚', '滚动到下面', '继续往下',
      'desplazar abajo', 'desplaza abajo', 'bajar', 'baja', 'mas abajo', 'más abajo',
      'faire defiler vers le bas', 'défiler vers le bas', 'descendre', 'plus bas'
    ]
  },
  {
    intent: 'scrollUp',
    phrases: [
      'scroll up', 'scrolling up', 'scorll up', 'scorlling up', 'scrool up', 'scroolling up',
      'move up', 'page up', 'go up', 'up the page', 'higher', 'go higher', 'move higher',
      'keep going up', 'continue up', 'up more', 'more up', 'scroll more up', 'scrolling up more',
      '向上滚动', '上滑', '往上', '往上滚', '滚动到上面', '继续往上',
      'desplazar arriba', 'desplaza arriba', 'subir', 'sube', 'mas arriba', 'más arriba',
      'faire defiler vers le haut', 'défiler vers le haut', 'monter', 'plus haut'
    ]
  },
  {
    intent: 'scrollTop',
    phrases: [
      'scroll to top', 'go to top', 'back to top', 'top of page', 'top of the page',
      '回到顶部', '到顶部', '顶部',
      'ir arriba', 'arriba del todo', 'haut de page', 'aller en haut'
    ]
  },
  {
    intent: 'scrollBottom',
    phrases: [
      'scroll to bottom', 'go to bottom', 'bottom of page', 'bottom of the page',
      '到底部', '底部',
      'ir abajo', 'abajo del todo', 'bas de page', 'aller en bas'
    ]
  }
]
const voiceScrollIntentDocuments = voiceScrollIntentPhrases.flatMap(({ intent, phrases }) => (
  phrases.map((phrase) => ({ intent, phrase: normalizeVoiceText(phrase) }))
))
const voiceScrollIntentFuse = new Fuse(voiceScrollIntentDocuments, {
  keys: ['phrase'],
  includeScore: true,
  ignoreLocation: true,
  threshold: 0.42,
  distance: 120,
  minMatchCharLength: 3
})
const voiceTechnicalErrorPatterns = [
  'httpsconnectionpool',
  'connectionpool',
  'connecttimeouterror',
  'readtimeout',
  'timeout',
  'timed out',
  'max retries exceeded',
  'http 502',
  'http 503',
  'marketdata.colab.duke.edu',
  'connection to',
  'connect timeout',
  'temporarily disabled after a recent connection failure',
  'non-json response',
  'traceback',
  'requests.exceptions'
]
const voiceSpeechMaxCharacters = 96

const activePage = ref('Home')
const appMode = ref('stock')
const uiLanguage = ref('en')
const isAuthenticated = ref(false)
const symbolInput = ref('')
const activeSymbol = ref('')
const selectedChartInterval = ref('daily')
const currentExploreTab = ref('Watchlist')
const exploreViewMode = ref('ranked')
const exploreSearchQuery = ref('')
const stockMarketVisibleCount = ref(STOCK_MARKET_PAGE_SIZE)
const isSearching = ref(false)
const isGenerating = ref(false)
const isPredictionLoading = ref(false)
const isMatchDetailsLoading = ref(false)
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
const liveStockQuoteLookup = ref({})
const exploreLiveSearchRows = ref([])
const portfolioSparklineSeries = ref({})
const watchlistScanThreshold = ref(60)
const isWatchlistScanning = ref(false)
const watchlistScanResults = ref([])
const watchlistScanMessage = ref('')
const watchlistScanScannedAt = ref('')
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
const voiceLastIntent = ref({ type: '', direction: '', at: 0 })
const voiceLastAssistantPrediction = ref(null)
const voiceMisunderstandingCount = ref(0)
const predictionSummaryRef = ref(null)
const matchedPatternsRef = ref(null)
const usagePaywall = ref({
  open: false,
  title: 'Request limit reached',
  message: 'You have reached the free request limit for this feature. Upgrade for unlimited requests.',
  usageLabel: 'NoobTrade requests',
  limitLabel: '',
  retryAfterSeconds: 0,
  planName: 'NoobTrade Pro',
  displayPrice: '$29.99/month',
  benefit: 'Unlimited Generate, Dashboard Scan, live chart, and matched-history requests.'
})
const usagePaywallUpgradeHref = computed(() => {
  const subject = encodeURIComponent('NoobTrade Pro unlimited requests')
  const body = encodeURIComponent('Hi, I want to upgrade to NoobTrade Pro at $29.99/month for unlimited requests.')
  return `mailto:benedictzhang01@gmail.com?subject=${subject}&body=${body}`
})

let feedRefreshTimer = null
let beforeInstallHandler = null
let voiceVoicesChangedHandler = null
let voiceRestartTimer = null
let analysisRequestVersion = 0
let chartIntervalRequestVersion = 0
let voiceSpeechToken = 0
let voiceLastSpeechSignature = ''
let voiceLastSpeechAt = 0
let exploreLiveSearchTimer = null
let exploreLiveSearchRequestVersion = 0
const stockChartRequestPromises = new Map()
const loadedChartSeriesKeys = new Set()
const cryptoWorkspaceLoadPromises = new Map()
const defaultLiveLoadPromises = {
  stock: null,
  crypto: null
}
const loginGenerateWarmKeys = new Set()
let stockChartWarmTimer = null
let stockMatchDetailRevealTimer = null

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
const isCryptoMode = computed(() => appMode.value === 'crypto')
const modeSwitchLabel = computed(() => (isCryptoMode.value ? t('switchToStock') : t('switchToCrypto')))
const modeLabel = computed(() => (isCryptoMode.value ? 'Crypto' : 'Stock'))
const isTradeWorkspacePage = computed(() => tradeWorkspacePages.includes(activePage.value))
const activeTradeWorkspaceLabel = computed(() => (activePage.value === 'Crypto Trade' ? 'Crypto Trade' : 'Stock Trade'))
const activeTradeResponse = computed(() => (
  activePage.value === 'Crypto Trade' || (isCryptoMode.value && activePage.value !== 'Stock Trade')
    ? cryptoResponse.value
    : stockResponse.value
))
const activeMarketSymbol = computed(() => (isCryptoMode.value ? cryptoResponse.value?.stock?.symbol || '' : activeSymbol.value))
const displayedTradeSymbol = computed(() => activeTradeResponse.value?.stock?.symbol || activeSymbol.value || 'Search')
const tradeSearchPlaceholder = computed(() => (
  activePage.value === 'Crypto Trade' ? 'Enter Crypto Ticker (e.g. BTC)' : 'Enter Ticker (e.g. AAPL)'
))
const tradeSearchLoadingLabel = computed(() => (
  activePage.value === 'Crypto Trade' ? 'Loading crypto data for' : 'Loading stock data for'
))
const predictionLoadingTitle = computed(() => (
  activePage.value === 'Crypto Trade' ? 'Generating crypto probabilities' : 'Generating stock probabilities'
))
const predictionLoadingMessage = computed(() => (
  activePage.value === 'Crypto Trade'
    ? 'Loading matched history and probability ranges.'
    : 'The historical database cache is warming up. The first Generate after opening the app may take a little longer, please wait.'
))
const tradePopularSymbols = computed(() => (
  activePage.value === 'Crypto Trade' ? ['BTC', 'ETH', 'OKB', 'SOL'] : ['AAPL', 'TSLA', 'NVDA', 'MSFT']
))
const activeCopy = computed(() => uiCopy[uiLanguage.value] || uiCopy.en)
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

const stockMarketOverviewCards = [
  { name: 'Market Feed', level: 'Live', change: 'Connected', tone: 'positive' },
  { name: 'Chart Data', level: 'Live', change: 'Search Ready', tone: 'positive' },
  { name: 'Indicators', level: 'Ready', change: 'Selectable', tone: 'neutral' },
  { name: 'History', level: 'Ready', change: 'Generate', tone: 'neutral' }
]

const cryptoMarketOverviewCards = [
  { name: 'OKX Feed', level: 'Live', change: 'Connected', tone: 'positive' },
  { name: 'Chart Data', level: 'Live', change: 'Search Ready', tone: 'positive' },
  { name: 'Indicators', level: 'Ready', change: 'Selectable', tone: 'neutral' },
  { name: 'History', level: 'Ready', change: 'Generate', tone: 'neutral' }
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

const starredSymbols = ref(['AAPL', 'NVDA', 'TSLA'])
const cryptoStarredSymbols = ref(['BTC', 'ETH', 'SOL', 'OKB'])

const stockDashboardAnnouncements = [
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

const cryptoDashboardAnnouncements = [
  {
    label: 'Crypto desk note',
    detail: 'Your crypto board is focused on liquidity leaders, exchange tokens, and Layer 1 momentum.',
    tag: '24 / 7'
  },
  {
    label: 'Risk prompt',
    detail: 'Crypto runs continuously, so size and volatility checks matter before chasing fast candles.',
    tag: 'Live'
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
    { symbol: 'BAC', name: 'Bank of America', category: 'Financials', price: '--', notional: '--', change: '--', tone: 'neutral' },
    { symbol: 'F', name: 'Ford Motor Company', category: 'Auto', price: '--', notional: '--', change: '--', tone: 'neutral' },
    { symbol: 'TSLA', name: 'Tesla Inc.', category: 'Auto', price: '$380.30', notional: '$176.5M', change: '-1.07%', tone: 'negative' },
    { symbol: 'AAPL', name: 'Apple Inc.', category: 'Large Cap', price: '$184.25', notional: '$142.8M', change: '+1.28%', tone: 'positive' },
    { symbol: 'AMD', name: 'AMD', category: 'Semis', price: '$197.43', notional: '$118.7M', change: '+1.09%', tone: 'positive' }
  ]
}

const cryptoExploreRows = [
  { symbol: 'BTC', name: 'Bitcoin', category: 'Store of Value', price: '--', notional: '--', change: '--', tone: 'neutral' },
  { symbol: 'ETH', name: 'Ethereum', category: 'Smart Contracts', price: '--', notional: '--', change: '--', tone: 'neutral' },
  { symbol: 'OKB', name: 'OKB', category: 'Exchange Token', price: '--', notional: '--', change: '--', tone: 'neutral' },
  { symbol: 'SOL', name: 'Solana', category: 'Layer 1', price: '--', notional: '--', change: '--', tone: 'neutral' },
  { symbol: 'BNB', name: 'BNB', category: 'Exchange Token', price: '--', notional: '--', change: '--', tone: 'neutral' }
]
const cryptoExploreLiveRows = ref([])
const cryptoExploreUniverseLoaded = ref(false)
let cryptoExploreUniverseLoadPromise = null

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

const stockMoreFeatures = [
  'Public entry pages for unauthenticated users, including registration and sign-in flow.',
  'Authenticated dashboard with total assets, a six-month curve, and self-selected stock monitoring.',
  'Trade workspace that supports buy or sell decisions with a connected trade ticket.',
  'Explore board for ranked stock scanning before drilling into Trade.',
  'Markets and More pages for market context, product story, and feedback channels.'
]

const cryptoMoreFeatures = [
  'Crypto mode keeps the same NoobTrade workflow but frames it around digital assets and 24/7 market structure.',
  'Dashboard favorites, Explore boards, Markets pulse, and Trade search all switch into crypto context together.',
  'The current crypto workspace is a product-preview shell for future crypto probability research.',
  'Black-and-white mode separates crypto research from the orange stock workflow visually.',
  'Settings, Admin, authentication, and account controls stay shared across both modes.'
]

const feedbackChannels = [
  { label: 'Feedback Email', value: 'benedictzhang01@gmail.com', href: 'mailto:benedictzhang01@gmail.com' },
  { label: 'Research Requests', value: 'benedictzhang01@gmail.com', href: 'mailto:benedictzhang01@gmail.com' },
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
  'INTU', 'QCOM', 'CAT', 'TXN', 'AXP', 'AMAT', 'BKNG', 'UBER', 'GS', 'CL'
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
  CL: { name: 'Colgate-Palmolive Company', category: 'Consumer Staples', price: '--', notional: '--', change: '--', tone: 'neutral' },
}

const stockMarketUniverseRows = [
  ['CHTR', 'Charter Communications', 'Communication Services'],
  ['CMCSA', 'Comcast', 'Communication Services'],
  ['DIS', 'Disney', 'Communication Services'],
  ['EA', 'Electronic Arts', 'Communication Services'],
  ['FOX', 'Fox Corporation (Class B)', 'Communication Services'],
  ['FOXA', 'Fox Corporation (Class A)', 'Communication Services'],
  ['GOOG', 'Alphabet Inc. (Class C)', 'Communication Services'],
  ['GOOGL', 'Alphabet Inc. (Class A)', 'Communication Services'],
  ['LYV', 'Live Nation Entertainment', 'Communication Services'],
  ['META', 'Meta Platforms', 'Communication Services'],
  ['NFLX', 'Netflix', 'Communication Services'],
  ['NWS', 'News Corp (Class B)', 'Communication Services'],
  ['NWSA', 'News Corp (Class A)', 'Communication Services'],
  ['OMC', 'Omnicom Group', 'Communication Services'],
  ['PSKY', 'Paramount Skydance Corporation', 'Communication Services'],
  ['SATS', 'EchoStar', 'Communication Services'],
  ['T', 'AT&T', 'Communication Services'],
  ['TKO', 'TKO Group Holdings', 'Communication Services'],
  ['TMUS', 'T-Mobile US', 'Communication Services'],
  ['TTD', 'Trade Desk (The)', 'Communication Services'],
  ['TTWO', 'Take-Two Interactive', 'Communication Services'],
  ['VZ', 'Verizon', 'Communication Services'],
  ['WBD', 'Warner Bros. Discovery', 'Communication Services'],
  ['ABNB', 'Airbnb', 'Consumer Discretionary'],
  ['AMZN', 'Amazon', 'Consumer Discretionary'],
  ['APTV', 'Aptiv', 'Consumer Discretionary'],
  ['AZO', 'AutoZone', 'Consumer Discretionary'],
  ['BBY', 'Best Buy', 'Consumer Discretionary'],
  ['BKNG', 'Booking Holdings', 'Consumer Discretionary'],
  ['CCL', 'Carnival Corporation', 'Consumer Discretionary'],
  ['CMG', 'Chipotle Mexican Grill', 'Consumer Discretionary'],
  ['CVNA', 'Carvana', 'Consumer Discretionary'],
  ['DASH', 'DoorDash', 'Consumer Discretionary'],
  ['DECK', 'Deckers Brands', 'Consumer Discretionary'],
  ['DHI', 'D. R. Horton', 'Consumer Discretionary'],
  ['DPZ', 'Domino\'s', 'Consumer Discretionary'],
  ['DRI', 'Darden Restaurants', 'Consumer Discretionary'],
  ['EBAY', 'eBay Inc.', 'Consumer Discretionary'],
  ['EXPE', 'Expedia Group', 'Consumer Discretionary'],
  ['F', 'Ford Motor Company', 'Consumer Discretionary'],
  ['GM', 'General Motors', 'Consumer Discretionary'],
  ['GPC', 'Genuine Parts Company', 'Consumer Discretionary'],
  ['GRMN', 'Garmin', 'Consumer Discretionary'],
  ['HAS', 'Hasbro', 'Consumer Discretionary'],
  ['HD', 'Home Depot', 'Consumer Discretionary'],
  ['HLT', 'Hilton Worldwide', 'Consumer Discretionary'],
  ['LEN', 'Lennar', 'Consumer Discretionary'],
  ['LOW', 'Lowe\'s', 'Consumer Discretionary'],
  ['LULU', 'Lululemon Athletica', 'Consumer Discretionary'],
  ['LVS', 'Las Vegas Sands', 'Consumer Discretionary'],
  ['MAR', 'Marriott International', 'Consumer Discretionary'],
  ['MCD', 'McDonald\'s', 'Consumer Discretionary'],
  ['MELI', 'Mercado Libre', 'Consumer Discretionary'],
  ['MGM', 'MGM Resorts', 'Consumer Discretionary'],
  ['NCLH', 'Norwegian Cruise Line Holdings', 'Consumer Discretionary'],
  ['NKE', 'Nike', 'Consumer Discretionary'],
  ['NVR', 'NVR, Inc.', 'Consumer Discretionary'],
  ['ORLY', 'O\'Reilly Automotive', 'Consumer Discretionary'],
  ['PHM', 'PulteGroup', 'Consumer Discretionary'],
  ['RCL', 'Royal Caribbean Group', 'Consumer Discretionary'],
  ['RL', 'Ralph Lauren Corporation', 'Consumer Discretionary'],
  ['ROST', 'Ross Stores', 'Consumer Discretionary'],
  ['SBUX', 'Starbucks', 'Consumer Discretionary'],
  ['TJX', 'TJX Companies', 'Consumer Discretionary'],
  ['TPR', 'Tapestry, Inc.', 'Consumer Discretionary'],
  ['TSCO', 'Tractor Supply', 'Consumer Discretionary'],
  ['TSLA', 'Tesla, Inc.', 'Consumer Discretionary'],
  ['ULTA', 'Ulta Beauty', 'Consumer Discretionary'],
  ['WSM', 'Williams-Sonoma, Inc.', 'Consumer Discretionary'],
  ['WYNN', 'Wynn Resorts', 'Consumer Discretionary'],
  ['YUM', 'Yum! Brands', 'Consumer Discretionary'],
  ['ADM', 'Archer Daniels Midland', 'Consumer Staples'],
  ['BF.B', 'Brown-Forman', 'Consumer Staples'],
  ['BG', 'Bunge Global', 'Consumer Staples'],
  ['CAG', 'Conagra Brands', 'Consumer Staples'],
  ['CASY', 'Casey\'s', 'Consumer Staples'],
  ['CCEP', 'Coca-Cola Europacific Partners', 'Consumer Staples'],
  ['CHD', 'Church & Dwight', 'Consumer Staples'],
  ['CL', 'Colgate-Palmolive', 'Consumer Staples'],
  ['CLX', 'Clorox', 'Consumer Staples'],
  ['COST', 'Costco', 'Consumer Staples'],
  ['DG', 'Dollar General', 'Consumer Staples'],
  ['DLTR', 'Dollar Tree', 'Consumer Staples'],
  ['EL', 'Estée Lauder Companies (The)', 'Consumer Staples'],
  ['GIS', 'General Mills', 'Consumer Staples'],
  ['HRL', 'Hormel Foods', 'Consumer Staples'],
  ['HSY', 'Hershey Company (The)', 'Consumer Staples'],
  ['KDP', 'Keurig Dr Pepper', 'Consumer Staples'],
  ['KHC', 'Kraft Heinz', 'Consumer Staples'],
  ['KMB', 'Kimberly-Clark', 'Consumer Staples'],
  ['KO', 'Coca-Cola', 'Consumer Staples'],
  ['KR', 'Kroger', 'Consumer Staples'],
  ['KVUE', 'Kenvue', 'Consumer Staples'],
  ['MDLZ', 'Mondelez International', 'Consumer Staples'],
  ['MKC', 'McCormick & Company', 'Consumer Staples'],
  ['MNST', 'Monster Beverage', 'Consumer Staples'],
  ['MO', 'Altria', 'Consumer Staples'],
  ['PEP', 'PepsiCo', 'Consumer Staples'],
  ['PG', 'Procter & Gamble', 'Consumer Staples'],
  ['PM', 'Philip Morris International', 'Consumer Staples'],
  ['SJM', 'J.M. Smucker Company (The)', 'Consumer Staples'],
  ['STZ', 'Constellation Brands', 'Consumer Staples'],
  ['SYY', 'Sysco', 'Consumer Staples'],
  ['TAP', 'Molson Coors Beverage Company', 'Consumer Staples'],
  ['TGT', 'Target Corporation', 'Consumer Staples'],
  ['TSN', 'Tyson Foods', 'Consumer Staples'],
  ['WMT', 'Walmart', 'Consumer Staples'],
  ['APA', 'APA Corporation', 'Energy'],
  ['BKR', 'Baker Hughes', 'Energy'],
  ['COP', 'ConocoPhillips', 'Energy'],
  ['CVX', 'Chevron', 'Energy'],
  ['DVN', 'Devon Energy', 'Energy'],
  ['EOG', 'EOG Resources', 'Energy'],
  ['EQT', 'EQT Corporation', 'Energy'],
  ['EXE', 'Expand Energy', 'Energy'],
  ['FANG', 'Diamondback Energy', 'Energy'],
  ['HAL', 'Halliburton', 'Energy'],
  ['KMI', 'Kinder Morgan', 'Energy'],
  ['MPC', 'Marathon Petroleum', 'Energy'],
  ['OKE', 'Oneok', 'Energy'],
  ['OXY', 'Occidental Petroleum', 'Energy'],
  ['PSX', 'Phillips 66', 'Energy'],
  ['SLB', 'Schlumberger', 'Energy'],
  ['TPL', 'Texas Pacific Land Corporation', 'Energy'],
  ['TRGP', 'Targa Resources', 'Energy'],
  ['VLO', 'Valero Energy', 'Energy'],
  ['WMB', 'Williams Companies', 'Energy'],
  ['XOM', 'ExxonMobil', 'Energy'],
  ['ACGL', 'Arch Capital Group', 'Financials'],
  ['AFL', 'Aflac', 'Financials'],
  ['AIG', 'American International Group', 'Financials'],
  ['AIZ', 'Assurant', 'Financials'],
  ['AJG', 'Arthur J. Gallagher & Co.', 'Financials'],
  ['ALL', 'Allstate', 'Financials'],
  ['AMP', 'Ameriprise Financial', 'Financials'],
  ['AON', 'Aon plc', 'Financials'],
  ['APO', 'Apollo Global Management', 'Financials'],
  ['ARES', 'Ares Management', 'Financials'],
  ['AXP', 'American Express', 'Financials'],
  ['BAC', 'Bank of America', 'Financials'],
  ['BEN', 'Franklin Resources', 'Financials'],
  ['BLK', 'BlackRock', 'Financials'],
  ['BNY', 'BNY Mellon', 'Financials'],
  ['BRK.B', 'Berkshire Hathaway', 'Financials'],
  ['BRO', 'Brown & Brown', 'Financials'],
  ['BX', 'Blackstone Inc.', 'Financials'],
  ['C', 'Citigroup', 'Financials'],
  ['CB', 'Chubb Limited', 'Financials'],
  ['CBOE', 'Cboe Global Markets', 'Financials'],
  ['CFG', 'Citizens Financial Group', 'Financials'],
  ['CINF', 'Cincinnati Financial', 'Financials'],
  ['CME', 'CME Group', 'Financials'],
  ['COF', 'Capital One', 'Financials'],
  ['COIN', 'Coinbase', 'Financials'],
  ['CPAY', 'Corpay', 'Financials'],
  ['EG', 'Everest Group', 'Financials'],
  ['ERIE', 'Erie Indemnity', 'Financials'],
  ['FDS', 'FactSet', 'Financials'],
  ['FIS', 'Fidelity National Information Services', 'Financials'],
  ['FISV', 'Fiserv', 'Financials'],
  ['FITB', 'Fifth Third Bancorp', 'Financials'],
  ['GL', 'Globe Life', 'Financials'],
  ['GPN', 'Global Payments', 'Financials'],
  ['GS', 'Goldman Sachs', 'Financials'],
  ['HBAN', 'Huntington Bancshares', 'Financials'],
  ['HIG', 'Hartford (The)', 'Financials'],
  ['HOOD', 'Robinhood Markets', 'Financials'],
  ['IBKR', 'Interactive Brokers', 'Financials'],
  ['ICE', 'Intercontinental Exchange', 'Financials'],
  ['IVZ', 'Invesco', 'Financials'],
  ['JKHY', 'Jack Henry & Associates', 'Financials'],
  ['JPM', 'JPMorgan Chase', 'Financials'],
  ['KEY', 'KeyCorp', 'Financials'],
  ['KKR', 'KKR & Co.', 'Financials'],
  ['L', 'Loews Corporation', 'Financials'],
  ['MA', 'Mastercard', 'Financials'],
  ['MCO', 'Moody\'s Corporation', 'Financials'],
  ['MET', 'MetLife', 'Financials'],
  ['MRSH', 'Marsh McLennan', 'Financials'],
  ['MS', 'Morgan Stanley', 'Financials'],
  ['MSCI', 'MSCI Inc.', 'Financials'],
  ['MTB', 'M&T Bank', 'Financials'],
  ['NDAQ', 'Nasdaq, Inc.', 'Financials'],
  ['NTRS', 'Northern Trust', 'Financials'],
  ['PFG', 'Principal Financial Group', 'Financials'],
  ['PGR', 'Progressive Corporation', 'Financials'],
  ['PNC', 'PNC Financial Services', 'Financials'],
  ['PRU', 'Prudential Financial', 'Financials'],
  ['PYPL', 'PayPal', 'Financials'],
  ['RF', 'Regions Financial Corporation', 'Financials'],
  ['RJF', 'Raymond James Financial', 'Financials'],
  ['SCHW', 'Charles Schwab Corporation', 'Financials'],
  ['SPGI', 'S&P Global', 'Financials'],
  ['STT', 'State Street Corporation', 'Financials'],
  ['SYF', 'Synchrony Financial', 'Financials'],
  ['TFC', 'Truist Financial', 'Financials'],
  ['TROW', 'T. Rowe Price', 'Financials'],
  ['TRV', 'Travelers Companies, Inc.', 'Financials'],
  ['USB', 'U.S. Bancorp', 'Financials'],
  ['V', 'Visa', 'Financials'],
  ['WFC', 'Wells Fargo', 'Financials'],
  ['WRB', 'W. R. Berkley Corporation', 'Financials'],
  ['WTW', 'Willis Towers Watson', 'Financials'],
  ['XYZ', 'Block, Inc.', 'Financials'],
  ['A', 'Agilent Technologies', 'Health Care'],
  ['ABBV', 'AbbVie', 'Health Care'],
  ['ABT', 'Abbott Laboratories', 'Health Care'],
  ['ALGN', 'Align Technology', 'Health Care'],
  ['ALNY', 'Alnylam Pharmaceuticals', 'Health Care'],
  ['AMGN', 'Amgen', 'Health Care'],
  ['BAX', 'Baxter International', 'Health Care'],
  ['BDX', 'Becton Dickinson', 'Health Care'],
  ['BIIB', 'Biogen', 'Health Care'],
  ['BMY', 'Bristol Myers Squibb', 'Health Care'],
  ['BSX', 'Boston Scientific', 'Health Care'],
  ['CAH', 'Cardinal Health', 'Health Care'],
  ['CI', 'Cigna', 'Health Care'],
  ['CNC', 'Centene Corporation', 'Health Care'],
  ['COO', 'Cooper Companies (The)', 'Health Care'],
  ['COR', 'Cencora', 'Health Care'],
  ['CRL', 'Charles River Laboratories', 'Health Care'],
  ['CVS', 'CVS Health', 'Health Care'],
  ['DGX', 'Quest Diagnostics', 'Health Care'],
  ['DHR', 'Danaher Corporation', 'Health Care'],
  ['DVA', 'DaVita', 'Health Care'],
  ['DXCM', 'Dexcom', 'Health Care'],
  ['ELV', 'Elevance Health', 'Health Care'],
  ['EW', 'Edwards Lifesciences', 'Health Care'],
  ['GEHC', 'GE HealthCare', 'Health Care'],
  ['GILD', 'Gilead Sciences', 'Health Care'],
  ['HCA', 'HCA Healthcare', 'Health Care'],
  ['HSIC', 'Henry Schein', 'Health Care'],
  ['HUM', 'Humana', 'Health Care'],
  ['IDXX', 'Idexx Laboratories', 'Health Care'],
  ['INCY', 'Incyte', 'Health Care'],
  ['INSM', 'Insmed Incorporated', 'Health Care'],
  ['IQV', 'IQVIA', 'Health Care'],
  ['ISRG', 'Intuitive Surgical', 'Health Care'],
  ['JNJ', 'Johnson & Johnson', 'Health Care'],
  ['LH', 'Labcorp', 'Health Care'],
  ['LLY', 'Lilly (Eli)', 'Health Care'],
  ['MCK', 'McKesson Corporation', 'Health Care'],
  ['MDT', 'Medtronic', 'Health Care'],
  ['MRK', 'Merck', 'Health Care'],
  ['MRNA', 'Moderna', 'Health Care'],
  ['MTD', 'Mettler Toledo', 'Health Care'],
  ['PFE', 'Pfizer', 'Health Care'],
  ['PODD', 'Insulet Corporation', 'Health Care'],
  ['REGN', 'Regeneron Pharmaceuticals', 'Health Care'],
  ['RMD', 'ResMed', 'Health Care'],
  ['RVTY', 'Revvity', 'Health Care'],
  ['SOLV', 'Solventum', 'Health Care'],
  ['STE', 'Steris', 'Health Care'],
  ['SYK', 'Stryker Corporation', 'Health Care'],
  ['TECH', 'Bio-Techne', 'Health Care'],
  ['TMO', 'Thermo Fisher Scientific', 'Health Care'],
  ['UHS', 'Universal Health Services', 'Health Care'],
  ['UNH', 'UnitedHealth Group', 'Health Care'],
  ['VEEV', 'Veeva Systems', 'Health Care'],
  ['VRTX', 'Vertex Pharmaceuticals', 'Health Care'],
  ['VTRS', 'Viatris', 'Health Care'],
  ['WAT', 'Waters Corporation', 'Health Care'],
  ['WST', 'West Pharmaceutical Services', 'Health Care'],
  ['ZBH', 'Zimmer Biomet', 'Health Care'],
  ['ZTS', 'Zoetis', 'Health Care'],
  ['ADP', 'Automatic Data Processing', 'Industrials'],
  ['ALLE', 'Allegion', 'Industrials'],
  ['AME', 'Ametek', 'Industrials'],
  ['AOS', 'A. O. Smith', 'Industrials'],
  ['AXON', 'Axon Enterprise', 'Industrials'],
  ['BA', 'Boeing', 'Industrials'],
  ['BLDR', 'Builders FirstSource', 'Industrials'],
  ['BR', 'Broadridge Financial Solutions', 'Industrials'],
  ['CARR', 'Carrier Global', 'Industrials'],
  ['CAT', 'Caterpillar', 'Industrials'],
  ['CHRW', 'C.H. Robinson', 'Industrials'],
  ['CMI', 'Cummins', 'Industrials'],
  ['CPRT', 'Copart', 'Industrials'],
  ['CSX', 'CSX Corporation', 'Industrials'],
  ['CTAS', 'Cintas', 'Industrials'],
  ['DAL', 'Delta Air Lines', 'Industrials'],
  ['DE', 'Deere & Company', 'Industrials'],
  ['DOV', 'Dover Corporation', 'Industrials'],
  ['EFX', 'Equifax', 'Industrials'],
  ['EME', 'Emcor', 'Industrials'],
  ['EMR', 'Emerson Electric', 'Industrials'],
  ['ETN', 'Eaton Corporation', 'Industrials'],
  ['EXPD', 'Expeditors International', 'Industrials'],
  ['FAST', 'Fastenal', 'Industrials'],
  ['FDX', 'FedEx', 'Industrials'],
  ['FDXF', 'FedEx Freight', 'Industrials'],
  ['FER', 'Ferrovial', 'Industrials'],
  ['FIX', 'Comfort Systems USA', 'Industrials'],
  ['FTV', 'Fortive', 'Industrials'],
  ['GD', 'General Dynamics', 'Industrials'],
  ['GE', 'GE Aerospace', 'Industrials'],
  ['GEV', 'GE Vernova', 'Industrials'],
  ['GNRC', 'Generac', 'Industrials'],
  ['GWW', 'W. W. Grainger', 'Industrials'],
  ['HII', 'Huntington Ingalls Industries', 'Industrials'],
  ['HON', 'Honeywell', 'Industrials'],
  ['HUBB', 'Hubbell Incorporated', 'Industrials'],
  ['HWM', 'Howmet Aerospace', 'Industrials'],
  ['IEX', 'IDEX Corporation', 'Industrials'],
  ['IR', 'Ingersoll Rand', 'Industrials'],
  ['ITW', 'Illinois Tool Works', 'Industrials'],
  ['J', 'Jacobs Solutions', 'Industrials'],
  ['JBHT', 'J.B. Hunt', 'Industrials'],
  ['JCI', 'Johnson Controls', 'Industrials'],
  ['LDOS', 'Leidos', 'Industrials'],
  ['LHX', 'L3Harris', 'Industrials'],
  ['LII', 'Lennox International', 'Industrials'],
  ['LMT', 'Lockheed Martin', 'Industrials'],
  ['LUV', 'Southwest Airlines', 'Industrials'],
  ['MAS', 'Masco', 'Industrials'],
  ['MMM', '3M', 'Industrials'],
  ['NDSN', 'Nordson Corporation', 'Industrials'],
  ['NOC', 'Northrop Grumman', 'Industrials'],
  ['NSC', 'Norfolk Southern', 'Industrials'],
  ['ODFL', 'Old Dominion', 'Industrials'],
  ['OTIS', 'Otis Worldwide', 'Industrials'],
  ['PAYX', 'Paychex', 'Industrials'],
  ['PCAR', 'Paccar', 'Industrials'],
  ['PH', 'Parker Hannifin', 'Industrials'],
  ['PNR', 'Pentair', 'Industrials'],
  ['PWR', 'Quanta Services', 'Industrials'],
  ['ROK', 'Rockwell Automation', 'Industrials'],
  ['ROL', 'Rollins, Inc.', 'Industrials'],
  ['RSG', 'Republic Services', 'Industrials'],
  ['RTX', 'RTX Corporation', 'Industrials'],
  ['SNA', 'Snap-on', 'Industrials'],
  ['SWK', 'Stanley Black & Decker', 'Industrials'],
  ['TDG', 'TransDigm Group', 'Industrials'],
  ['TT', 'Trane Technologies', 'Industrials'],
  ['TXT', 'Textron', 'Industrials'],
  ['UAL', 'United Airlines Holdings', 'Industrials'],
  ['UBER', 'Uber', 'Industrials'],
  ['UNP', 'Union Pacific Corporation', 'Industrials'],
  ['UPS', 'United Parcel Service', 'Industrials'],
  ['URI', 'United Rentals', 'Industrials'],
  ['VLTO', 'Veralto', 'Industrials'],
  ['VRSK', 'Verisk Analytics', 'Industrials'],
  ['VRT', 'Vertiv', 'Industrials'],
  ['WAB', 'Wabtec', 'Industrials'],
  ['WM', 'Waste Management', 'Industrials'],
  ['XYL', 'Xylem Inc.', 'Industrials'],
  ['AAPL', 'Apple', 'Information Technology'],
  ['ACN', 'Accenture', 'Information Technology'],
  ['ADBE', 'Adobe Inc.', 'Information Technology'],
  ['ADI', 'Analog Devices', 'Information Technology'],
  ['ADSK', 'Autodesk', 'Information Technology'],
  ['AKAM', 'Akamai Technologies', 'Information Technology'],
  ['AMAT', 'Applied Materials', 'Information Technology'],
  ['AMD', 'Advanced Micro Devices', 'Information Technology'],
  ['ANET', 'Arista Networks', 'Information Technology'],
  ['APH', 'Amphenol', 'Information Technology'],
  ['APP', 'AppLovin', 'Information Technology'],
  ['AVGO', 'Broadcom', 'Information Technology'],
  ['CDNS', 'Cadence Design Systems', 'Information Technology'],
  ['CDW', 'CDW Corporation', 'Information Technology'],
  ['CIEN', 'Ciena', 'Information Technology'],
  ['COHR', 'Coherent Corp.', 'Information Technology'],
  ['CRM', 'Salesforce', 'Information Technology'],
  ['CRWD', 'CrowdStrike', 'Information Technology'],
  ['CSCO', 'Cisco', 'Information Technology'],
  ['CTSH', 'Cognizant', 'Information Technology'],
  ['DDOG', 'Datadog', 'Information Technology'],
  ['DELL', 'Dell Technologies', 'Information Technology'],
  ['FFIV', 'F5, Inc.', 'Information Technology'],
  ['FICO', 'Fair Isaac', 'Information Technology'],
  ['FLEX', 'Flex Ltd.', 'Information Technology'],
  ['FSLR', 'First Solar', 'Information Technology'],
  ['FTNT', 'Fortinet', 'Information Technology'],
  ['GDDY', 'GoDaddy', 'Information Technology'],
  ['GEN', 'Gen Digital', 'Information Technology'],
  ['GLW', 'Corning Inc.', 'Information Technology'],
  ['HPE', 'Hewlett Packard Enterprise', 'Information Technology'],
  ['HPQ', 'HP Inc.', 'Information Technology'],
  ['IBM', 'IBM', 'Information Technology'],
  ['INTC', 'Intel', 'Information Technology'],
  ['INTU', 'Intuit', 'Information Technology'],
  ['IT', 'Gartner', 'Information Technology'],
  ['JBL', 'Jabil', 'Information Technology'],
  ['KEYS', 'Keysight Technologies', 'Information Technology'],
  ['KLAC', 'KLA Corporation', 'Information Technology'],
  ['LITE', 'Lumentum', 'Information Technology'],
  ['LRCX', 'Lam Research', 'Information Technology'],
  ['MCHP', 'Microchip Technology', 'Information Technology'],
  ['MPWR', 'Monolithic Power Systems', 'Information Technology'],
  ['MRVL', 'Marvell Technology', 'Information Technology'],
  ['MSFT', 'Microsoft', 'Information Technology'],
  ['MSI', 'Motorola Solutions', 'Information Technology'],
  ['MU', 'Micron Technology', 'Information Technology'],
  ['NOW', 'ServiceNow', 'Information Technology'],
  ['NTAP', 'NetApp', 'Information Technology'],
  ['NVDA', 'Nvidia', 'Information Technology'],
  ['NXPI', 'NXP Semiconductors', 'Information Technology'],
  ['ON', 'ON Semiconductor', 'Information Technology'],
  ['ORCL', 'Oracle Corporation', 'Information Technology'],
  ['PANW', 'Palo Alto Networks', 'Information Technology'],
  ['PLTR', 'Palantir Technologies', 'Information Technology'],
  ['PTC', 'PTC Inc.', 'Information Technology'],
  ['Q', 'Qnity Electronics', 'Information Technology'],
  ['QCOM', 'Qualcomm', 'Information Technology'],
  ['ROP', 'Roper Technologies', 'Information Technology'],
  ['SMCI', 'Supermicro', 'Information Technology'],
  ['SNDK', 'Sandisk', 'Information Technology'],
  ['SNPS', 'Synopsys', 'Information Technology'],
  ['STX', 'Seagate Technology', 'Information Technology'],
  ['SWKS', 'Skyworks Solutions', 'Information Technology'],
  ['TDY', 'Teledyne Technologies', 'Information Technology'],
  ['TEL', 'TE Connectivity', 'Information Technology'],
  ['TER', 'Teradyne', 'Information Technology'],
  ['TRMB', 'Trimble Inc.', 'Information Technology'],
  ['TXN', 'Texas Instruments', 'Information Technology'],
  ['TYL', 'Tyler Technologies', 'Information Technology'],
  ['VRSN', 'Verisign', 'Information Technology'],
  ['WDAY', 'Workday, Inc.', 'Information Technology'],
  ['WDC', 'Western Digital', 'Information Technology'],
  ['ZBRA', 'Zebra Technologies', 'Information Technology'],
  ['ALB', 'Albemarle Corporation', 'Materials'],
  ['AMCR', 'Amcor', 'Materials'],
  ['APD', 'Air Products', 'Materials'],
  ['AVY', 'Avery Dennison', 'Materials'],
  ['BALL', 'Ball Corporation', 'Materials'],
  ['CF', 'CF Industries', 'Materials'],
  ['CRH', 'CRH plc', 'Materials'],
  ['CTVA', 'Corteva', 'Materials'],
  ['DD', 'DuPont', 'Materials'],
  ['DOW', 'Dow Inc.', 'Materials'],
  ['ECL', 'Ecolab', 'Materials'],
  ['FCX', 'Freeport-McMoRan', 'Materials'],
  ['IFF', 'International Flavors & Fragrances', 'Materials'],
  ['IP', 'International Paper', 'Materials'],
  ['LIN', 'Linde plc', 'Materials'],
  ['LYB', 'LyondellBasell', 'Materials'],
  ['MLM', 'Martin Marietta Materials', 'Materials'],
  ['MOS', 'Mosaic Company (The)', 'Materials'],
  ['NEM', 'Newmont', 'Materials'],
  ['NUE', 'Nucor', 'Materials'],
  ['PKG', 'Packaging Corporation of America', 'Materials'],
  ['PPG', 'PPG Industries', 'Materials'],
  ['SHW', 'Sherwin-Williams', 'Materials'],
  ['STLD', 'Steel Dynamics', 'Materials'],
  ['SW', 'Smurfit Westrock', 'Materials'],
  ['VMC', 'Vulcan Materials Company', 'Materials'],
  ['AACB', 'Artius II Acquisition Inc.', 'Nasdaq Listed'],
  ['AACG', 'ATA Creativity Global', 'Nasdaq Listed'],
  ['AACI', 'Armada Acquisition Corp. III', 'Nasdaq Listed'],
  ['AACO', 'Abony Acquisition Corp. I', 'Nasdaq Listed'],
  ['AACP', 'Apogee Acquisition Corp', 'Nasdaq Listed'],
  ['AAL', 'American Airlines Group, Inc.', 'Nasdaq Listed'],
  ['AAME', 'Atlantic American Corporation', 'Nasdaq Listed'],
  ['AAOI', 'Applied Optoelectronics, Inc.', 'Nasdaq Listed'],
  ['AAON', 'AAON, Inc.', 'Nasdaq Listed'],
  ['AARD', 'Aardvark Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ABAT', 'American Battery Technology Company', 'Nasdaq Listed'],
  ['ABCL', 'AbCellera Biologics Inc.', 'Nasdaq Listed'],
  ['ABEO', 'Abeona Therapeutics Inc.', 'Nasdaq Listed'],
  ['ABLV', 'Able View Global Inc.', 'Nasdaq Listed'],
  ['ABOS', 'Acumen Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['ABSI', 'Absci Corporation', 'Nasdaq Listed'],
  ['ABTC', 'American Bitcoin Corp.', 'Nasdaq Listed'],
  ['ABTS', 'Abits Group Inc', 'Nasdaq Listed'],
  ['ABUS', 'Arbutus Biopharma Corporation', 'Nasdaq Listed'],
  ['ABVC', 'ABVC BioPharma, Inc.', 'Nasdaq Listed'],
  ['ABVE', 'Above Food Ingredients Inc.', 'Nasdaq Listed'],
  ['ABVX', 'Abivax SA', 'Nasdaq Listed'],
  ['ACAA', 'Averin Capital Acquisition Corp.', 'Nasdaq Listed'],
  ['ACAD', 'ACADIA Pharmaceuticals Inc.', 'Nasdaq Listed'],
  ['ACB', 'Aurora Cannabis Inc.', 'Nasdaq Listed'],
  ['ACCL', 'Acco Group Holdings Limited', 'Nasdaq Listed'],
  ['ACDC', 'ProFrac Holding Corp.', 'Nasdaq Listed'],
  ['ACET', 'Adicet Bio, Inc.', 'Nasdaq Listed'],
  ['ACFN', 'Acorn Energy, Inc.', 'Nasdaq Listed'],
  ['ACGC', 'ACP Holdings Acquisition Corp.', 'Nasdaq Listed'],
  ['ACHC', 'Acadia Healthcare Company, Inc.', 'Nasdaq Listed'],
  ['ACHV', 'Achieve Life Sciences, Inc.', 'Nasdaq Listed'],
  ['ACIC', 'American Coastal Insurance Corporation', 'Nasdaq Listed'],
  ['ACIU', 'AC Immune SA', 'Nasdaq Listed'],
  ['ACIW', 'ACI Worldwide, Inc.', 'Nasdaq Listed'],
  ['ACLS', 'Axcelis Technologies, Inc.', 'Nasdaq Listed'],
  ['ACMR', 'ACM Research, Inc.', 'Nasdaq Listed'],
  ['ACNB', 'ACNB Corporation', 'Nasdaq Listed'],
  ['ACNT', 'Ascent Industries Co.', 'Nasdaq Listed'],
  ['ACOG', 'Alpha Cognition Inc.', 'Nasdaq Listed'],
  ['ACON', 'Aclarion, Inc.', 'Nasdaq Listed'],
  ['ACRS', 'Aclaris Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ACRV', 'Acrivon Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ACT', 'Enact Holdings, Inc.', 'Nasdaq Listed'],
  ['ACTG', 'Acacia Research Corporation', 'Nasdaq Listed'],
  ['ACTU', 'Actuate Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ACXP', 'Acurx Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['ADAC', 'American Drive Acquisition Company', 'Nasdaq Listed'],
  ['ADAG', 'Adagene Inc.', 'Nasdaq Listed'],
  ['ADEA', 'Adeia Inc.', 'Nasdaq Listed'],
  ['ADGM', 'Adagio Medical Holdings, Inc', 'Nasdaq Listed'],
  ['ADIL', 'Adial Pharmaceuticals, Inc', 'Nasdaq Listed'],
  ['ADMA', 'ADMA Biologics Inc', 'Nasdaq Listed'],
  ['ADPT', 'Adaptive Biotechnologies Corporation', 'Nasdaq Listed'],
  ['ADSE', 'ADS-TEC ENERGY PLC', 'Nasdaq Listed'],
  ['ADTN', 'ADTRAN Holdings, Inc.', 'Nasdaq Listed'],
  ['ADTX', 'Aditxt, Inc.', 'Nasdaq Listed'],
  ['ADUR', 'Aduro Clean Technologies Inc.', 'Nasdaq Listed'],
  ['ADUS', 'Addus HomeCare Corporation', 'Nasdaq Listed'],
  ['ADV', 'Advantage Solutions Inc.', 'Nasdaq Listed'],
  ['ADVB', 'Advanced Biomed Inc.', 'Nasdaq Listed'],
  ['ADXN', 'Addex Therapeutics Ltd', 'Nasdaq Listed'],
  ['AEAQ', 'Activate Energy Acquisition Corp.', 'Nasdaq Listed'],
  ['AEBI', 'Aebi Schmidt Holding AG', 'Nasdaq Listed'],
  ['AEC', 'Anfield Energy Inc.', 'Nasdaq Listed'],
  ['AEHL', 'Antelope Enterprise Holdings Limited', 'Nasdaq Listed'],
  ['AEHR', 'Aehr Test Systems', 'Nasdaq Listed'],
  ['AEI', 'Alset Inc.', 'Nasdaq Listed'],
  ['AEIS', 'Advanced Energy Industries, Inc.', 'Nasdaq Listed'],
  ['AEMD', 'Aethlon Medical, Inc.', 'Nasdaq Listed'],
  ['AENT', 'Alliance Entertainment Holding Corporation', 'Nasdaq Listed'],
  ['AERT', 'Aeries Technology, Inc.', 'Nasdaq Listed'],
  ['AEVA', 'Aeva Technologies, Inc.', 'Nasdaq Listed'],
  ['AEYE', 'AudioEye, Inc.', 'Nasdaq Listed'],
  ['AFBI', 'Affinity Bancshares, Inc.', 'Nasdaq Listed'],
  ['AFCG', 'Advanced Flower Capital Inc.', 'Nasdaq Listed'],
  ['AFJK', 'Aimei Health Technology Co., Ltd - Ordinary Share', 'Nasdaq Listed'],
  ['AFRI', 'Forafric Global PLC', 'Nasdaq Listed'],
  ['AFRM', 'Affirm Holdings, Inc.', 'Nasdaq Listed'],
  ['AFYA', 'Afya Limited - Class A Common Shares', 'Nasdaq Listed'],
  ['AGCC', 'Agencia Comercial Spirits Ltd', 'Nasdaq Listed'],
  ['AGEN', 'Agenus Inc.', 'Nasdaq Listed'],
  ['AGIO', 'Agios Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['AGMH', 'AGM Group Holdings Inc.', 'Nasdaq Listed'],
  ['AGNC', 'AGNC Investment Corp.', 'Nasdaq Listed'],
  ['AGNT', 'eXp World Holdings, Inc.', 'Nasdaq Listed'],
  ['AGPU', 'Axe Compute Inc.', 'Nasdaq Listed'],
  ['AGRZ', 'Agroz Inc.', 'Nasdaq Listed'],
  ['AGYS', 'Agilysys, Inc.', 'Nasdaq Listed'],
  ['AHCO', 'AdaptHealth Corp.', 'Nasdaq Listed'],
  ['AHG', 'Akso Health Group', 'Nasdaq Listed'],
  ['AHMA', 'Ambitions Enterprise Management Co. L.L.C', 'Nasdaq Listed'],
  ['AIAI', 'AIAI Holdings Corporation', 'Nasdaq Listed'],
  ['AIDX', '20/20 Biolabs, Inc.', 'Nasdaq Listed'],
  ['AIFA', 'All In FutureTech Alliance, Inc.', 'Nasdaq Listed'],
  ['AIFC', 'AI Financial Corporation', 'Nasdaq Listed'],
  ['AIFF', 'Firefly Neuroscience, Inc.', 'Nasdaq Listed'],
  ['AIFU', 'AIFU Inc.', 'Nasdaq Listed'],
  ['AIHS', 'Senmiao Technology Limited', 'Nasdaq Listed'],
  ['AIIO', 'Robo.ai Inc.', 'Nasdaq Listed'],
  ['AIIR', 'Air Global PLC', 'Nasdaq Listed'],
  ['AIMD', 'Ainos, Inc.', 'Nasdaq Listed'],
  ['AIOS', 'AIOS Tech Inc. - Class A Common Shares', 'Nasdaq Listed'],
  ['AIOT', 'PowerFleet, Inc.', 'Nasdaq Listed'],
  ['AIP', 'Arteris, Inc.', 'Nasdaq Listed'],
  ['AIRE', 'reAlpha Tech Corp.', 'Nasdaq Listed'],
  ['AIRG', 'Airgain, Inc.', 'Nasdaq Listed'],
  ['AIRJ', 'AirJoule Technologies Corporation', 'Nasdaq Listed'],
  ['AIRO', 'AIRO Group Holdings, Inc.', 'Nasdaq Listed'],
  ['AIRS', 'AirSculpt Technologies, Inc.', 'Nasdaq Listed'],
  ['AIRT', 'Air T, Inc.', 'Nasdaq Listed'],
  ['AISP', 'Airship AI Holdings, Inc', 'Nasdaq Listed'],
  ['AIXC', 'AIxCrypto Holdings, Inc.', 'Nasdaq Listed'],
  ['AIXI', 'XIAO-I Corporation', 'Nasdaq Listed'],
  ['AKAN', 'Akanda Corp.', 'Nasdaq Listed'],
  ['AKBA', 'Akebia Therapeutics, Inc.', 'Nasdaq Listed'],
  ['AKTS', 'Aktis Oncology, Inc.', 'Nasdaq Listed'],
  ['AKTX', 'Akari Therapeutics Plc', 'Nasdaq Listed'],
  ['ALAB', 'Astera Labs, Inc.', 'Nasdaq Listed'],
  ['ALAR', 'Alarum Technologies Ltd.', 'Nasdaq Listed'],
  ['ALBT', 'Avalon GloboCare Corp.', 'Nasdaq Listed'],
  ['ALCO', 'Alico, Inc.', 'Nasdaq Listed'],
  ['ALDF', 'Aldel Financial II Inc.', 'Nasdaq Listed'],
  ['ALDX', 'Aldeyra Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ALEC', 'Alector, Inc.', 'Nasdaq Listed'],
  ['ALF', 'Centurion Acquisition Corp.', 'Nasdaq Listed'],
  ['ALGM', 'Allegro MicroSystems, Inc.', 'Nasdaq Listed'],
  ['ALGS', 'Aligos Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ALGT', 'Allegiant Travel Company', 'Nasdaq Listed'],
  ['ALHC', 'Alignment Healthcare, Inc.', 'Nasdaq Listed'],
  ['ALIS', 'Calisa Acquisition Corp', 'Nasdaq Listed'],
  ['ALKS', 'Alkermes plc', 'Nasdaq Listed'],
  ['ALKT', 'Alkami Technology, Inc.', 'Nasdaq Listed'],
  ['ALLO', 'Allogene Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ALLR', 'Allarity Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ALLT', 'Allot Ltd.', 'Nasdaq Listed'],
  ['ALM', 'Almonty Industries Inc.', 'Nasdaq Listed'],
  ['ALMR', 'Alamar Biosciences, Inc.', 'Nasdaq Listed'],
  ['ALMS', 'Alumis Inc.', 'Nasdaq Listed'],
  ['ALMU', 'Aeluma, Inc.', 'Nasdaq Listed'],
  ['ALNT', 'Allient Inc.', 'Nasdaq Listed'],
  ['ALOT', 'AstroNova, Inc.', 'Nasdaq Listed'],
  ['ALOV', 'Aldabra 4 Liquidity Opportunity Vehicle, Inc.', 'Nasdaq Listed'],
  ['ALOY', 'REalloys Inc.', 'Nasdaq Listed'],
  ['ALP', 'Alpha Compute Corp', 'Nasdaq Listed'],
  ['ALPS', 'ALPS Group Inc - Ordinary Share', 'Nasdaq Listed'],
  ['ALRM', 'Alarm.com Holdings, Inc.', 'Nasdaq Listed'],
  ['ALRS', 'Alerus Financial Corporation', 'Nasdaq Listed'],
  ['ALT', 'Altimmune, Inc.', 'Nasdaq Listed'],
  ['ALTI', 'AlTi Global, Inc.', 'Nasdaq Listed'],
  ['ALTO', 'Alto Ingredients, Inc.', 'Nasdaq Listed'],
  ['ALVO', 'Alvotech', 'Nasdaq Listed'],
  ['ALXO', 'ALX Oncology Holdings Inc.', 'Nasdaq Listed'],
  ['ALZN', 'Alzamend Neuro, Inc.', 'Nasdaq Listed'],
  ['AMAL', 'Amalgamated Financial Corp.', 'Nasdaq Listed'],
  ['AMAN', 'Amanat Acquisition Corp', 'Nasdaq Listed'],
  ['AMBA', 'Ambarella, Inc.', 'Nasdaq Listed'],
  ['AMBR', 'Amber International Holding Limited', 'Nasdaq Listed'],
  ['AMCI', 'AMC Robotics Corporation', 'Nasdaq Listed'],
  ['AMCX', 'AMC Global Media Inc.', 'Nasdaq Listed'],
  ['AMIX', 'Autonomix Medical, Inc.', 'Nasdaq Listed'],
  ['AMKR', 'Amkor Technology, Inc.', 'Nasdaq Listed'],
  ['AMLX', 'Amylyx Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['AMOD', 'Alpha Modus Holdings, Inc.', 'Nasdaq Listed'],
  ['AMPG', 'Amplitech Group, Inc.', 'Nasdaq Listed'],
  ['AMPH', 'Amphastar Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['AMPL', 'Amplitude, Inc.', 'Nasdaq Listed'],
  ['AMRN', 'Amarin Corporation plc', 'Nasdaq Listed'],
  ['AMRX', 'Amneal Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['AMSC', 'American Superconductor Corporation', 'Nasdaq Listed'],
  ['AMSF', 'AMERISAFE, Inc.', 'Nasdaq Listed'],
  ['AMSS', 'AMASS Brands Inc.', 'Nasdaq Listed'],
  ['AMST', 'Amesite Inc.', 'Nasdaq Listed'],
  ['AMTX', 'Aemetis, Inc', 'Nasdaq Listed'],
  ['ANAB', 'AnaptysBio, Inc.', 'Nasdaq Listed'],
  ['ANDE', 'The Andersons, Inc.', 'Nasdaq Listed'],
  ['ANGH', 'Anghami Inc.', 'Nasdaq Listed'],
  ['ANGI', 'Angi Inc.', 'Nasdaq Listed'],
  ['ANGO', 'AngioDynamics, Inc.', 'Nasdaq Listed'],
  ['ANIK', 'Anika Therapeutics Inc.', 'Nasdaq Listed'],
  ['ANIP', 'ANI Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['ANIX', 'Anixa Biosciences, Inc.', 'Nasdaq Listed'],
  ['ANL', 'Adlai Nortye Ltd.', 'Nasdaq Listed'],
  ['ANNA', 'AleAnna, Inc.', 'Nasdaq Listed'],
  ['ANNX', 'Annexon, Inc.', 'Nasdaq Listed'],
  ['ANPA', 'Rich Sparkle Holdings Limited', 'Nasdaq Listed'],
  ['ANSC', 'Agriculture & Natural Solutions Acquisition Corporation', 'Nasdaq Listed'],
  ['ANTA', 'Antalpha Platform Holding Company', 'Nasdaq Listed'],
  ['ANTX', 'AN2 Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ANY', 'Sphere 3D Corp.', 'Nasdaq Listed'],
  ['AOSL', 'Alpha and Omega Semiconductor Limited', 'Nasdaq Listed'],
  ['AOUT', 'American Outdoor Brands, Inc.', 'Nasdaq Listed'],
  ['APAC', 'StoneBridge Acquisition II Corporation', 'Nasdaq Listed'],
  ['APC', 'ARKO Petroleum Corp.', 'Nasdaq Listed'],
  ['APEI', 'American Public Education, Inc.', 'Nasdaq Listed'],
  ['APGE', 'Apogee Therapeutics, Inc.', 'Nasdaq Listed'],
  ['API', 'Agora, Inc.', 'Nasdaq Listed'],
  ['APLD', 'Applied Digital Corporation', 'Nasdaq Listed'],
  ['APLM', 'Apollomics Inc.', 'Nasdaq Listed'],
  ['APM', 'Aptorum Group Limited', 'Nasdaq Listed'],
  ['APOG', 'Apogee Enterprises, Inc.', 'Nasdaq Listed'],
  ['APPF', 'AppFolio, Inc.', 'Nasdaq Listed'],
  ['APPN', 'Appian Corporation', 'Nasdaq Listed'],
  ['APPS', 'Digital Turbine, Inc.', 'Nasdaq Listed'],
  ['APRE', 'Aprea Therapeutics, Inc.', 'Nasdaq Listed'],
  ['APVO', 'Aptevo Therapeutics Inc.', 'Nasdaq Listed'],
  ['APWC', 'Asia Pacific Wire & Cable Corporation Limited - Common shares, Par value .01 per share', 'Nasdaq Listed'],
  ['APXT', 'Apex Treasury Corporation', 'Nasdaq Listed'],
  ['APYX', 'Apyx Medical Corporation', 'Nasdaq Listed'],
  ['AQB', 'AquaBounty Technologies, Inc.', 'Nasdaq Listed'],
  ['AQMS', 'Aqua Metals, Inc.', 'Nasdaq Listed'],
  ['AQST', 'Aquestive Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ARAI', 'Arrive AI Inc.', 'Nasdaq Listed'],
  ['ARAY', 'Accuray Incorporated', 'Nasdaq Listed'],
  ['ARBB', 'ARB IOT Group Limited', 'Nasdaq Listed'],
  ['ARBE', 'Arbe Robotics Ltd.', 'Nasdaq Listed'],
  ['ARBK', 'Argo Blockchain plc', 'Nasdaq Listed'],
  ['ARCB', 'ArcBest Corporation', 'Nasdaq Listed'],
  ['ARCI', 'Archimedes Tech SPAC Partners III Co. - Ordinary Share', 'Nasdaq Listed'],
  ['ARCL', 'ARC Group Acquisition I Corp', 'Nasdaq Listed'],
  ['ARCT', 'Arcturus Therapeutics Holdings Inc.', 'Nasdaq Listed'],
  ['ARDX', 'Ardelyx, Inc.', 'Nasdaq Listed'],
  ['AREC', 'American Resources Corporation', 'Nasdaq Listed'],
  ['ARGX', 'argenx SE', 'Nasdaq Listed'],
  ['ARHS', 'Arhaus, Inc.', 'Nasdaq Listed'],
  ['ARKO', 'ARKO Corp.', 'Nasdaq Listed'],
  ['ARKR', 'Ark Restaurants Corp.', 'Nasdaq Listed'],
  ['AROW', 'Arrow Financial Corporation', 'Nasdaq Listed'],
  ['ARQ', 'Arq, Inc.', 'Nasdaq Listed'],
  ['ARQQ', 'Arqit Quantum Inc.', 'Nasdaq Listed'],
  ['ARQT', 'Arcutis Biotherapeutics, Inc.', 'Nasdaq Listed'],
  ['ARRY', 'Array Technologies, Inc.', 'Nasdaq Listed'],
  ['ARTC', 'Art Technology Acquisition Corp.', 'Nasdaq Listed'],
  ['ARTL', 'Artelo Biosciences, Inc.', 'Nasdaq Listed'],
  ['ARTNA', 'Artesian Resources Corporation - Class A Non-Voting Common Stock', 'Nasdaq Listed'],
  ['ARTV', 'Artiva Biotherapeutics, Inc.', 'Nasdaq Listed'],
  ['ARTW', 'Art\'s-Way Manufacturing Co., Inc.', 'Nasdaq Listed'],
  ['ARVN', 'Arvinas, Inc.', 'Nasdaq Listed'],
  ['ARWR', 'Arrowhead Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['ARXS', 'Arxis, Inc.', 'Nasdaq Listed'],
  ['ASBP', 'Aspire Biopharma Holdings, Inc.', 'Nasdaq Listed'],
  ['ASLE', 'AerSale Corporation', 'Nasdaq Listed'],
  ['ASMB', 'Assembly Biosciences, Inc.', 'Nasdaq Listed'],
  ['ASND', 'Ascendis Pharma A/S - Ordinary Share', 'Nasdaq Listed'],
  ['ASO', 'Academy Sports and Outdoors, Inc.', 'Nasdaq Listed'],
  ['ASPC', 'A SPAC III Acquisition Corp.', 'Nasdaq Listed'],
  ['ASPI', 'ASP Isotopes Inc.', 'Nasdaq Listed'],
  ['ASPS', 'Altisource Portfolio Solutions S.A.', 'Nasdaq Listed'],
  ['ASRT', 'Assertio Holdings, Inc.', 'Nasdaq Listed'],
  ['ASRV', 'AmeriServ Financial Inc.', 'Nasdaq Listed'],
  ['ASST', 'Strive, Inc.', 'Nasdaq Listed'],
  ['ASTC', 'Astrotech Corporation', 'Nasdaq Listed'],
  ['ASTE', 'Astec Industries, Inc.', 'Nasdaq Listed'],
  ['ASTH', 'Astrana Health Inc.', 'Nasdaq Listed'],
  ['ASTI', 'Ascent Solar Technologies, Inc', 'Nasdaq Listed'],
  ['ASTL', 'Algoma Steel Group Inc.', 'Nasdaq Listed'],
  ['ASTS', 'AST SpaceMobile, Inc.', 'Nasdaq Listed'],
  ['ASUR', 'Asure Software Inc', 'Nasdaq Listed'],
  ['ASYS', 'Amtech Systems, Inc.', 'Nasdaq Listed'],
  ['ATAI', 'AtaiBeckley Inc.', 'Nasdaq Listed'],
  ['ATAT', 'Atour Lifestyle Holdings Limited', 'Nasdaq Listed'],
  ['ATCX', 'Atlas Critical Minerals Corporation', 'Nasdaq Listed'],
  ['ATEC', 'Alphatec Holdings, Inc.', 'Nasdaq Listed'],
  ['ATER', 'Aterian, Inc.', 'Nasdaq Listed'],
  ['ATEX', 'Anterix Inc.', 'Nasdaq Listed'],
  ['ATGL', 'Alpha Technology Group Limited', 'Nasdaq Listed'],
  ['ATHE', 'Alterity Therapeutics Limited', 'Nasdaq Listed'],
  ['ATHR', 'Aether Holdings, Inc.', 'Nasdaq Listed'],
  ['ATII', 'Archimedes Tech SPAC Partners II Co.', 'Nasdaq Listed'],
  ['ATLC', 'Atlanticus Holdings Corporation', 'Nasdaq Listed'],
  ['ATLN', 'Atlantic International Corp.', 'Nasdaq Listed'],
  ['ATLO', 'Ames National Corporation', 'Nasdaq Listed'],
  ['ATLX', 'Atlas Lithium Corporation', 'Nasdaq Listed'],
  ['ATNI', 'ATN International, Inc.', 'Nasdaq Listed'],
  ['ATOM', 'Atomera Incorporated', 'Nasdaq Listed'],
  ['ATOS', 'Atossa Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ATPC', 'Agape ATP Corporation', 'Nasdaq Listed'],
  ['ATRA', 'Atara Biotherapeutics, Inc.', 'Nasdaq Listed'],
  ['ATRC', 'AtriCure, Inc.', 'Nasdaq Listed'],
  ['ATRO', 'Astronics Corporation', 'Nasdaq Listed'],
  ['ATXG', 'Addentax Group Corp.', 'Nasdaq Listed'],
  ['ATYR', 'aTyr Pharma, Inc.', 'Nasdaq Listed'],
  ['AUBN', 'Auburn National Bancorporation, Inc.', 'Nasdaq Listed'],
  ['AUC', 'ATIF Holdings Limited', 'Nasdaq Listed'],
  ['AUDC', 'AudioCodes Ltd.', 'Nasdaq Listed'],
  ['AUGO', 'Aura Minerals Inc.', 'Nasdaq Listed'],
  ['AUID', 'authID Inc.', 'Nasdaq Listed'],
  ['AUPH', 'Aurinia Pharmaceuticals Inc', 'Nasdaq Listed'],
  ['AUR', 'Aurora Innovation, Inc.', 'Nasdaq Listed'],
  ['AURA', 'Aura Biosciences, Inc.', 'Nasdaq Listed'],
  ['AURE', 'Aurelion Inc.', 'Nasdaq Listed'],
  ['AUTL', 'Autolus Therapeutics plc', 'Nasdaq Listed'],
  ['AUUD', 'Auddia Inc.', 'Nasdaq Listed'],
  ['AVAH', 'Aveanna Healthcare Holdings Inc.', 'Nasdaq Listed'],
  ['AVAV', 'AeroVironment, Inc.', 'Nasdaq Listed'],
  ['AVBH', 'Avidbank Holdings, Inc.', 'Nasdaq Listed'],
  ['AVBP', 'ArriVent BioPharma, Inc.', 'Nasdaq Listed'],
  ['AVIR', 'Atea Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['AVLN', 'Avalyn Pharma Inc.', 'Nasdaq Listed'],
  ['AVNW', 'Aviat Networks, Inc.', 'Nasdaq Listed'],
  ['AVO', 'Mission Produce, Inc.', 'Nasdaq Listed'],
  ['AVPT', 'AvePoint, Inc.', 'Nasdaq Listed'],
  ['AVR', 'Anteris Technologies Global Corp.', 'Nasdaq Listed'],
  ['AVT', 'Avnet, Inc.', 'Nasdaq Listed'],
  ['AVTX', 'Avalo Therapeutics, Inc.', 'Nasdaq Listed'],
  ['AVX', 'Avax One Technology Ltd.', 'Nasdaq Listed'],
  ['AVXL', 'Anavex Life Sciences Corp.', 'Nasdaq Listed'],
  ['AWRE', 'Aware, Inc.', 'Nasdaq Listed'],
  ['AXG', 'Solowin Holdings', 'Nasdaq Listed'],
  ['AXGN', 'Axogen, Inc.', 'Nasdaq Listed'],
  ['AXIN', 'Axiom Intelligence Acquisition Corp 1', 'Nasdaq Listed'],
  ['AXSM', 'Axsome Therapeutics, Inc.', 'Nasdaq Listed'],
  ['AXTI', 'AXT Inc', 'Nasdaq Listed'],
  ['AYA', 'Aya Gold & Silver Inc.', 'Nasdaq Listed'],
  ['AYTU', 'Aytu BioPharma, Inc.', 'Nasdaq Listed'],
  ['AZ', 'A2Z Cust2Mate Solutions Corp.', 'Nasdaq Listed'],
  ['AZI', 'Autozi Internet Technology (Global) Ltd.', 'Nasdaq Listed'],
  ['AZTA', 'Azenta, Inc.', 'Nasdaq Listed'],
  ['BACC', 'Blue Acquisition Corp.', 'Nasdaq Listed'],
  ['BAER', 'Bridger Aerospace Group Holdings, Inc.', 'Nasdaq Listed'],
  ['BAFN', 'BayFirst Financial Corp.', 'Nasdaq Listed'],
  ['BAND', 'Bandwidth Inc.', 'Nasdaq Listed'],
  ['BANF', 'BancFirst Corporation', 'Nasdaq Listed'],
  ['BANL', 'CBL International Limited', 'Nasdaq Listed'],
  ['BANR', 'Banner Corporation', 'Nasdaq Listed'],
  ['BAOS', 'Baosheng Media Group Holdings Limited', 'Nasdaq Listed'],
  ['BATRA', 'Atlanta Braves Holdings, Inc. - Series A Common Stock', 'Nasdaq Listed'],
  ['BATRK', 'Atlanta Braves Holdings, Inc. - Series C Common Stock', 'Nasdaq Listed'],
  ['BAYA', 'Bayview Acquisition Corp - Ordinary Share', 'Nasdaq Listed'],
  ['BBCP', 'Concrete Pumping Holdings, Inc.', 'Nasdaq Listed'],
  ['BBCQ', 'Bleichroeder Acquisition Corp. II', 'Nasdaq Listed'],
  ['BBGI', 'Beasley Broadcast Group, Inc.', 'Nasdaq Listed'],
  ['BBIO', 'BridgeBio Pharma, Inc.', 'Nasdaq Listed'],
  ['BBLG', 'Bone Biologics Corp', 'Nasdaq Listed'],
  ['BBNX', 'Beta Bionics, Inc.', 'Nasdaq Listed'],
  ['BBOT', 'BridgeBio Oncology Therapeutics, Inc.', 'Nasdaq Listed'],
  ['BBSI', 'Barrett Business Services, Inc.', 'Nasdaq Listed'],
  ['BCAB', 'BioAtla, Inc.', 'Nasdaq Listed'],
  ['BCAL', 'California BanCorp', 'Nasdaq Listed'],
  ['BCAR', 'D. Boral ARC Acquisition I Corp.', 'Nasdaq Listed'],
  ['BCAX', 'Bicara Therapeutics Inc.', 'Nasdaq Listed'],
  ['BCBP', 'BCB Bancorp, Inc. (NJ)', 'Nasdaq Listed'],
  ['BCDA', 'BioCardia, Inc.', 'Nasdaq Listed'],
  ['BCG', 'Binah Capital Group, Inc.', 'Nasdaq Listed'],
  ['BCML', 'BayCom Corp', 'Nasdaq Listed'],
  ['BCPC', 'Balchem Corporation', 'Nasdaq Listed'],
  ['BCRX', 'BioCryst Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['BCTX', 'BriaCell Therapeutics Corp.', 'Nasdaq Listed'],
  ['BCYC', 'Bicycle Therapeutics plc', 'Nasdaq Listed'],
  ['BDCI', 'BTC Development Corp.', 'Nasdaq Listed'],
  ['BDMD', 'Baird Medical Investment Holdings Ltd - Ordinary Share', 'Nasdaq Listed'],
  ['BDRX', 'Biodexa Pharmaceuticals plc', 'Nasdaq Listed'],
  ['BDSX', 'Biodesix, Inc.', 'Nasdaq Listed'],
  ['BDTX', 'Black Diamond Therapeutics, Inc.', 'Nasdaq Listed'],
  ['BEAG', 'Bold Eagle Acquisition Corp.', 'Nasdaq Listed'],
  ['BEAM', 'Beam Therapeutics Inc.', 'Nasdaq Listed'],
  ['BEAT', 'Heartbeam, Inc.', 'Nasdaq Listed'],
  ['BEEM', 'Beam Global', 'Nasdaq Listed'],
  ['BEEP', 'Mobile Infrastructure Corporation', 'Nasdaq Listed'],
  ['BELFA', 'Bel Fuse Inc.', 'Nasdaq Listed'],
  ['BELFB', 'Bel Fuse Inc.', 'Nasdaq Listed'],
  ['BENF', 'Beneficient', 'Nasdaq Listed'],
  ['BETR', 'Better Home & Finance Holding Company', 'Nasdaq Listed'],
  ['BFC', 'Bank First Corporation', 'Nasdaq Listed'],
  ['BFRG', 'Bullfrog AI Holdings, Inc.', 'Nasdaq Listed'],
  ['BFRI', 'Biofrontera Inc.', 'Nasdaq Listed'],
  ['BFST', 'Business First Bancshares, Inc.', 'Nasdaq Listed'],
  ['BGC', 'BGC Group, Inc.', 'Nasdaq Listed'],
  ['BGDE', 'Big Digital Energy, Inc.', 'Nasdaq Listed'],
  ['BGIN', 'Bgin Blockchain Limited', 'Nasdaq Listed'],
  ['BGL', 'Blue Gold Limited', 'Nasdaq Listed'],
  ['BGLC', 'BioNexus Gene Lab Corp', 'Nasdaq Listed'],
  ['BGM', 'BGM Group Ltd.', 'Nasdaq Listed'],
  ['BGMS', 'Bio Green Med Solution, Inc.', 'Nasdaq Listed'],
  ['BHAV', 'BHAV Acquisition Corp', 'Nasdaq Listed'],
  ['BHF', 'Brighthouse Financial, Inc.', 'Nasdaq Listed'],
  ['BHRB', 'Burke & Herbert Financial Services Corp.', 'Nasdaq Listed'],
  ['BHST', 'BioHarvest Sciences Inc.', 'Nasdaq Listed'],
  ['BIAF', 'bioAffinity Technologies, Inc.', 'Nasdaq Listed'],
  ['BIDU', 'Baidu, Inc.', 'Nasdaq Listed'],
  ['BILI', 'Bilibili Inc.', 'Nasdaq Listed'],
  ['BIOA', 'BioAge Labs, Inc.', 'Nasdaq Listed'],
  ['BIOX', 'Bioceres Crop Solutions Corp.', 'Nasdaq Listed'],
  ['BIRD', 'Allbirds, Inc.', 'Nasdaq Listed'],
  ['BIVI', 'BioVie Inc.', 'Nasdaq Listed'],
  ['BIXI', 'Bitcoin Infrastructure Acquisition Corp Ltd.', 'Nasdaq Listed'],
  ['BIYA', 'Baiya International Group Inc.', 'Nasdaq Listed'],
  ['BJDX', 'Bluejay Diagnostics, Inc.', 'Nasdaq Listed'],
  ['BJRI', 'BJ\'s Restaurants, Inc.', 'Nasdaq Listed'],
  ['BKHA', 'Black Hawk Acquisition Corporation', 'Nasdaq Listed'],
  ['BL', 'BlackLine, Inc.', 'Nasdaq Listed'],
  ['BLBD', 'Blue Bird Corporation', 'Nasdaq Listed'],
  ['BLDP', 'Ballard Power Systems, Inc.', 'Nasdaq Listed'],
  ['BLFS', 'BioLife Solutions, Inc.', 'Nasdaq Listed'],
  ['BLIN', 'Bridgeline Digital, Inc.', 'Nasdaq Listed'],
  ['BLIV', 'BeLive Holdings', 'Nasdaq Listed'],
  ['BLKB', 'Blackbaud, Inc.', 'Nasdaq Listed'],
  ['BLLN', 'BillionToOne, Inc.', 'Nasdaq Listed'],
  ['BLMN', 'Bloomin\' Brands, Inc.', 'Nasdaq Listed'],
  ['BLNE', 'Beeline Holdings, Inc.', 'Nasdaq Listed'],
  ['BLNK', 'Blink Charging Co.', 'Nasdaq Listed'],
  ['BLRK', 'Bluerock Acquisition Corp.', 'Nasdaq Listed'],
  ['BLRX', 'BioLineRx Ltd.', 'Nasdaq Listed'],
  ['BLTE', 'Belite Bio, Inc', 'Nasdaq Listed'],
  ['BLUW', 'Blue Water Acquisition Corp. III', 'Nasdaq Listed'],
  ['BLZE', 'Backblaze, Inc.', 'Nasdaq Listed'],
  ['BLZR', 'Trailblazer Acquisition Corp.', 'Nasdaq Listed'],
  ['BMBL', 'Bumble Inc.', 'Nasdaq Listed'],
  ['BMEA', 'Biomea Fusion, Inc.', 'Nasdaq Listed'],
  ['BMGL', 'Basel Medical Group Ltd', 'Nasdaq Listed'],
  ['BMHL', 'Bluemount Holdings Limited', 'Nasdaq Listed'],
  ['BMM', 'Blue Moon Metals Inc.', 'Nasdaq Listed'],
  ['BMR', 'Beamr Imaging Ltd. - Ordinary Share', 'Nasdaq Listed'],
  ['BMRA', 'Biomerica, Inc.', 'Nasdaq Listed'],
  ['BMRC', 'Bank of Marin Bancorp', 'Nasdaq Listed'],
  ['BMRN', 'BioMarin Pharmaceutical Inc.', 'Nasdaq Listed'],
  ['BNAI', 'Brand Engagement Network Inc.', 'Nasdaq Listed'],
  ['BNBX', 'BNB Plus Corp.', 'Nasdaq Listed'],
  ['BNC', 'CEA Industries Inc.', 'Nasdaq Listed'],
  ['BNGO', 'Bionano Genomics, Inc.', 'Nasdaq Listed'],
  ['BNKK', 'Bonk, Inc.', 'Nasdaq Listed'],
  ['BNR', 'Burning Rock Biotech Limited', 'Nasdaq Listed'],
  ['BNRG', 'Brenmiller Energy Ltd', 'Nasdaq Listed'],
  ['BNTC', 'Benitec Biopharma Inc.', 'Nasdaq Listed'],
  ['BNTX', 'BioNTech SE', 'Nasdaq Listed'],
  ['BNZI', 'Banzai International, Inc.', 'Nasdaq Listed'],
  ['BODI', 'The Beachbody Company, Inc.', 'Nasdaq Listed'],
  ['BOF', 'BranchOut Food Inc.', 'Nasdaq Listed'],
  ['BOKF', 'BOK Financial Corporation', 'Nasdaq Listed'],
  ['BOLD', 'Boundless Bio, Inc.', 'Nasdaq Listed'],
  ['BOLT', 'Bolt Biotherapeutics, Inc.', 'Nasdaq Listed'],
  ['BON', 'Bon Natural Life Limited', 'Nasdaq Listed'],
  ['BOOM', 'DMC Global Inc.', 'Nasdaq Listed'],
  ['BOSC', 'B.O.S. Better Online Solutions', 'Nasdaq Listed'],
  ['BOT', 'RoboStrategy, Inc.', 'Nasdaq Listed'],
  ['BOTJ', 'Bank of the James Financial Group, Inc.', 'Nasdaq Listed'],
  ['BOXL', 'Boxlight Corporation', 'Nasdaq Listed'],
  ['BPAC', 'Blueport Acquisition Ltd', 'Nasdaq Listed'],
  ['BPOP', 'Popular, Inc.', 'Nasdaq Listed'],
  ['BPRN', 'Princeton Bancorp, Inc.', 'Nasdaq Listed'],
  ['BRAG', 'Bragg Gaming Group Inc.', 'Nasdaq Listed'],
  ['BRAI', 'Braiin Limited', 'Nasdaq Listed'],
  ['BRBI', 'BRBI BR Partners S.A.', 'Nasdaq Listed'],
  ['BRCB', 'Black Rock Coffee Bar, Inc.', 'Nasdaq Listed'],
  ['BRFH', 'Barfresh Food Group Inc.', 'Nasdaq Listed'],
  ['BRID', 'Bridgford Foods Corporation', 'Nasdaq Listed'],
  ['BRKR', 'Bruker Corporation', 'Nasdaq Listed'],
  ['BRLS', 'Borealis Foods Inc. - Class A Common Shares', 'Nasdaq Listed'],
  ['BRLT', 'Brilliant Earth Group, Inc.', 'Nasdaq Listed'],
  ['BRNS', 'Barinthus Biotherapeutics plc', 'Nasdaq Listed'],
  ['BRR', 'ProCap Financial, Inc.', 'Nasdaq Listed'],
  ['BRTX', 'BioRestorative Therapies, Inc.', 'Nasdaq Listed'],
  ['BRUN', 'Boost Run Inc.', 'Nasdaq Listed'],
  ['BRZE', 'Braze, Inc.', 'Nasdaq Listed'],
  ['BSAA', 'BEST SPAC I Acquisition Corp.', 'Nasdaq Listed'],
  ['BSBK', 'Bogota Financial Corp.', 'Nasdaq Listed'],
  ['BSET', 'Bassett Furniture Industries, Incorporated', 'Nasdaq Listed'],
  ['BSRR', 'Sierra Bancorp', 'Nasdaq Listed'],
  ['BSVN', 'Bank7 Corp.', 'Nasdaq Listed'],
  ['BSY', 'Bentley Systems, Incorporated', 'Nasdaq Listed'],
  ['BTAI', 'BioXcel Therapeutics, Inc.', 'Nasdaq Listed'],
  ['BTBD', 'BT Brands, Inc.', 'Nasdaq Listed'],
  ['BTBT', 'Bit Digital, Inc. - Ordinary Share', 'Nasdaq Listed'],
  ['BTCS', 'BTCS Inc.', 'Nasdaq Listed'],
  ['BTCT', 'BTC Digital Ltd.', 'Nasdaq Listed'],
  ['BTDR', 'Bitdeer Technologies Group', 'Nasdaq Listed'],
  ['BTMD', 'Biote Corp.', 'Nasdaq Listed'],
  ['BTOC', 'Armlogi Holding Corp.', 'Nasdaq Listed'],
  ['BTOG', 'Bit Origin Limited', 'Nasdaq Listed'],
  ['BTQ', 'BTQ Technologies Corp.', 'Nasdaq Listed'],
  ['BTSG', 'BrightSpring Health Services, Inc.', 'Nasdaq Listed'],
  ['BTTC', 'Black Titan Corp', 'Nasdaq Listed'],
  ['BULL', 'Webull Corporation', 'Nasdaq Listed'],
  ['BUSE', 'First Busey Corporation', 'Nasdaq Listed'],
  ['BUUU', 'BUUU Group Limited', 'Nasdaq Listed'],
  ['BVC', 'BitVentures Limited - Ordinary Share', 'Nasdaq Listed'],
  ['BVFL', 'BV Financial, Inc.', 'Nasdaq Listed'],
  ['BVS', 'Bioventus Inc.', 'Nasdaq Listed'],
  ['BWAY', 'BrainsWay Ltd.', 'Nasdaq Listed'],
  ['BWB', 'Bridgewater Bancshares, Inc.', 'Nasdaq Listed'],
  ['BWEN', 'Broadwind, Inc.', 'Nasdaq Listed'],
  ['BWFG', 'Bankwell Financial Group, Inc.', 'Nasdaq Listed'],
  ['BWIN', 'The Baldwin Insurance Group, Inc.', 'Nasdaq Listed'],
  ['BWMN', 'Bowman Consulting Group Ltd.', 'Nasdaq Listed'],
  ['BYAH', 'Park Ha Biological Technology Co., Ltd.', 'Nasdaq Listed'],
  ['BYFC', 'Broadway Financial Corporation', 'Nasdaq Listed'],
  ['BYND', 'Beyond Meat, Inc.', 'Nasdaq Listed'],
  ['BYRN', 'Byrna Technologies, Inc.', 'Nasdaq Listed'],
  ['BYSI', 'BeyondSpring, Inc.', 'Nasdaq Listed'],
  ['BZAI', 'Blaize Holdings, Inc.', 'Nasdaq Listed'],
  ['BZFD', 'BuzzFeed, Inc.', 'Nasdaq Listed'],
  ['BZUN', 'Baozun Inc.', 'Nasdaq Listed'],
  ['CAAS', 'China Automotive Systems, Inc. - Ordinary Share', 'Nasdaq Listed'],
  ['CABA', 'Cabaletta Bio, Inc.', 'Nasdaq Listed'],
  ['CABR', 'Caring Brands, Inc.', 'Nasdaq Listed'],
  ['CAC', 'Camden National Corporation', 'Nasdaq Listed'],
  ['CACC', 'Credit Acceptance Corporation', 'Nasdaq Listed'],
  ['CADL', 'Candel Therapeutics, Inc.', 'Nasdaq Listed'],
  ['CAI', 'Caris Life Sciences, Inc.', 'Nasdaq Listed'],
  ['CAKE', 'The Cheesecake Factory Incorporated', 'Nasdaq Listed'],
  ['CALC', 'CalciMedica, Inc.', 'Nasdaq Listed'],
  ['CALM', 'Cal-Maine Foods, Inc.', 'Nasdaq Listed'],
  ['CAMP', 'CAMP4 Therapeutics Corporation', 'Nasdaq Listed'],
  ['CAMT', 'Camtek Ltd.', 'Nasdaq Listed'],
  ['CAN', 'Canaan Inc.', 'Nasdaq Listed'],
  ['CAPN', 'Cayson Acquisition Corp', 'Nasdaq Listed'],
  ['CAPR', 'Capricor Therapeutics, Inc.', 'Nasdaq Listed'],
  ['CAPS', 'Capstone Holding Corp.', 'Nasdaq Listed'],
  ['CAQ', 'Cambridge Acquisition Corp.', 'Nasdaq Listed'],
  ['CAR', 'Avis Budget Group, Inc.', 'Nasdaq Listed'],
  ['CARE', 'Carter Bankshares, Inc.', 'Nasdaq Listed'],
  ['CARG', 'CarGurus, Inc.', 'Nasdaq Listed'],
  ['CARL', 'Carlsmed, Inc.', 'Nasdaq Listed'],
  ['CART', 'Maplebear Inc.', 'Nasdaq Listed'],
  ['CASH', 'Pathward Financial, Inc.', 'Nasdaq Listed'],
  ['CASS', 'Cass Information Systems, Inc', 'Nasdaq Listed'],
  ['CAST', 'FreeCast, Inc.', 'Nasdaq Listed'],
  ['CATY', 'Cathay General Bancorp', 'Nasdaq Listed'],
  ['CBAT', 'CBAK Energy Technology, Inc.', 'Nasdaq Listed'],
  ['CBC', 'Central Bancompany, Inc.', 'Nasdaq Listed'],
  ['CBFV', 'CB Financial Services, Inc.', 'Nasdaq Listed'],
  ['CBIO', 'Crescent Biopharma, Inc.', 'Nasdaq Listed'],
  ['CBK', 'Commercial Bancgroup, Inc.', 'Nasdaq Listed'],
  ['CBLL', 'CeriBell, Inc.', 'Nasdaq Listed'],
  ['CBNK', 'Capital Bancorp, Inc.', 'Nasdaq Listed'],
  ['CBRL', 'Cracker Barrel Old Country Store, Inc.', 'Nasdaq Listed'],
  ['CBRS', 'Cerebras Systems Inc.', 'Nasdaq Listed'],
  ['CBSH', 'Commerce Bancshares, Inc.', 'Nasdaq Listed'],
  ['CBUS', 'Cibus, Inc.', 'Nasdaq Listed'],
  ['CCAP', 'Crescent Capital BDC, Inc.', 'Nasdaq Listed'],
  ['CCAQ', 'Collective Acquisition Corp.', 'Nasdaq Listed'],
  ['CCB', 'Coastal Financial Corporation', 'Nasdaq Listed'],
  ['CCBG', 'Capital City Bank Group', 'Nasdaq Listed'],
  ['CCC', 'CCC Intelligent Solutions Holdings Inc.', 'Nasdaq Listed'],
  ['CCCC', 'C4 Therapeutics, Inc.', 'Nasdaq Listed'],
  ['CCG', 'Cheche Group Inc.', 'Nasdaq Listed'],
  ['CCHH', 'CCH Holdings Ltd', 'Nasdaq Listed'],
  ['CCII', 'Cohen Circle Acquisition Corp. II', 'Nasdaq Listed'],
  ['CCIX', 'Churchill Capital Corp IX', 'Nasdaq Listed'],
  ['CCLD', 'CareCloud, Inc.', 'Nasdaq Listed'],
  ['CCNE', 'CNB Financial Corporation', 'Nasdaq Listed'],
  ['CCOI', 'Cogent Communications Holdings, Inc.', 'Nasdaq Listed'],
  ['CCRN', 'Cross Country Healthcare, Inc.', 'Nasdaq Listed'],
  ['CCSI', 'Consensus Cloud Solutions, Inc.', 'Nasdaq Listed'],
  ['CCTG', 'CCSC Technology International Holdings Limited', 'Nasdaq Listed'],
  ['CCXI', 'Churchill Capital Corp XI', 'Nasdaq Listed'],
  ['CD', 'Chaince Digital Holdings Inc. - American Ordinary Shares', 'Nasdaq Listed'],
  ['CDIO', 'Cardio Diagnostics Holdings Inc.', 'Nasdaq Listed'],
  ['CDLX', 'Cardlytics, Inc.', 'Nasdaq Listed'],
  ['CDNA', 'CareDx, Inc.', 'Nasdaq Listed'],
  ['CDNL', 'Cardinal Infrastructure Group Inc.', 'Nasdaq Listed'],
  ['CDRO', 'Codere Online Luxembourg, S.A.', 'Nasdaq Listed'],
  ['CDT', 'CDT Equity Inc.', 'Nasdaq Listed'],
  ['CDTG', 'CDT Environmental Technology Investment Holdings Limited', 'Nasdaq Listed'],
  ['CDXS', 'Codexis, Inc.', 'Nasdaq Listed'],
  ['CDZI', 'Cadiz, Inc.', 'Nasdaq Listed'],
  ['CECO', 'CECO Environmental Corp.', 'Nasdaq Listed'],
  ['CELC', 'Celcuity Inc.', 'Nasdaq Listed'],
  ['CELH', 'Celsius Holdings, Inc.', 'Nasdaq Listed'],
  ['CELU', 'Celularity Inc.', 'Nasdaq Listed'],
  ['CELZ', 'Creative Medical Technology Holdings, Inc.', 'Nasdaq Listed'],
  ['CENN', 'Cenntro Inc.', 'Nasdaq Listed'],
  ['CENT', 'Central Garden & Pet Company', 'Nasdaq Listed'],
  ['CENTA', 'Central Garden & Pet Company - Class A Common Stock Nonvoting', 'Nasdaq Listed'],
  ['CENX', 'Century Aluminum Company', 'Nasdaq Listed'],
  ['CEPF', 'Cantor Equity Partners IV, Inc.', 'Nasdaq Listed'],
  ['CEPO', 'Cantor Equity Partners I, Inc.', 'Nasdaq Listed'],
  ['CEPS', 'Cantor Equity Partners VI, Inc.', 'Nasdaq Listed'],
  ['CEPT', 'Cantor Equity Partners II, Inc.', 'Nasdaq Listed'],
  ['CEPV', 'Cantor Equity Partners V, Inc.', 'Nasdaq Listed'],
  ['CERS', 'Cerus Corporation', 'Nasdaq Listed'],
  ['CERT', 'Certara, Inc.', 'Nasdaq Listed'],
  ['CETX', 'Cemtrex Inc.', 'Nasdaq Listed'],
  ['CETY', 'Clean Energy Technologies, Inc.', 'Nasdaq Listed'],
  ['CEVA', 'CEVA, Inc.', 'Nasdaq Listed'],
  ['CFBK', 'CF Bankshares Inc.', 'Nasdaq Listed'],
  ['CFFI', 'C&F Financial Corporation', 'Nasdaq Listed'],
  ['CFFN', 'Capitol Federal Financial, Inc.', 'Nasdaq Listed'],
  ['CG', 'The Carlyle Group Inc.', 'Nasdaq Listed'],
  ['CGC', 'Canopy Growth Corporation', 'Nasdaq Listed'],
  ['CGCT', 'Cartesian Growth Corporation III', 'Nasdaq Listed'],
  ['CGEM', 'Cullinan Therapeutics, Inc.', 'Nasdaq Listed'],
  ['CGEN', 'Compugen Ltd.', 'Nasdaq Listed'],
  ['CGNT', 'Cognyte Software Ltd.', 'Nasdaq Listed'],
  ['CGNX', 'Cognex Corporation', 'Nasdaq Listed'],
  ['CGON', 'CG Oncology, Inc.', 'Nasdaq Listed'],
  ['CGTL', 'Creative Global Technology Holdings Limited', 'Nasdaq Listed'],
  ['CGTX', 'Cognition Therapeutics, Inc.', 'Nasdaq Listed'],
  ['CHA', 'Chagee Holdings Limited', 'Nasdaq Listed'],
  ['CHAI', 'Core AI Holdings, Inc.', 'Nasdaq Listed'],
  ['CHAR', 'Charlton Aria Acquisition Corporation', 'Nasdaq Listed'],
  ['CHCI', 'Comstock Holding Companies, Inc.', 'Nasdaq Listed'],
  ['CHCO', 'City Holding Company', 'Nasdaq Listed'],
  ['CHDN', 'Churchill Downs, Incorporated', 'Nasdaq Listed'],
  ['CHEC', 'Chenghe Acquisition III Co.', 'Nasdaq Listed'],
  ['CHEF', 'The Chefs\' Warehouse, Inc.', 'Nasdaq Listed'],
  ['CHKP', 'Check Point Software Technologies Ltd.', 'Nasdaq Listed'],
  ['CHMG', 'Chemung Financial Corp', 'Nasdaq Listed'],
  ['CHNR', 'China Natural Resources, Inc.', 'Nasdaq Listed'],
  ['CHPG', 'ChampionsGate Acquisition Corporation', 'Nasdaq Listed'],
  ['CHR', 'Cheer Holding, Inc.', 'Nasdaq Listed'],
  ['CHRD', 'Chord Energy Corporation', 'Nasdaq Listed'],
  ['CHRN', 'ChronoScale Corporation', 'Nasdaq Listed'],
  ['CHRS', 'Coherus Oncology, Inc.', 'Nasdaq Listed'],
  ['CHSN', 'Chanson International Holding', 'Nasdaq Listed'],
  ['CHYM', 'Chime Financial, Inc.', 'Nasdaq Listed'],
  ['CIFR', 'Cipher Digital Inc.', 'Nasdaq Listed'],
  ['CIIT', 'Tianci International, Inc.', 'Nasdaq Listed'],
  ['CING', 'Cingulate Inc.', 'Nasdaq Listed'],
  ['CISO', 'CISO Global, Inc.', 'Nasdaq Listed'],
  ['CISS', 'C3is Inc.', 'Nasdaq Listed'],
  ['CIVB', 'Civista Bancshares, Inc.', 'Nasdaq Listed'],
  ['CJMB', 'Callan JMB Inc.', 'Nasdaq Listed'],
  ['CLAR', 'Clarus Corporation', 'Nasdaq Listed'],
  ['CLBK', 'Columbia Financial, Inc.', 'Nasdaq Listed'],
  ['CLBT', 'Cellebrite DI Ltd.', 'Nasdaq Listed'],
  ['CLDX', 'Celldex Therapeutics, Inc.', 'Nasdaq Listed'],
  ['CLFD', 'Clearfield, Inc.', 'Nasdaq Listed'],
  ['CLGN', 'CollPlant Biotechnologies Ltd.', 'Nasdaq Listed'],
  ['CLIK', 'Click Holdings Limited - Ordinary Share', 'Nasdaq Listed'],
  ['CLIR', 'ClearSign Technologies Corporation', 'Nasdaq Listed'],
  ['CLLS', 'Cellectis S.A.', 'Nasdaq Listed'],
  ['CLMB', 'Climb Global Solutions, Inc.', 'Nasdaq Listed'],
  ['CLMT', 'Calumet, Inc', 'Nasdaq Listed'],
  ['CLNE', 'Clean Energy Fuels Corp.', 'Nasdaq Listed'],
  ['CLNN', 'Clene Inc.', 'Nasdaq Listed'],
  ['CLOV', 'Clover Health Investments, Corp.', 'Nasdaq Listed'],
  ['CLPS', 'CLPS Incorporation', 'Nasdaq Listed'],
  ['CLPT', 'ClearPoint Neuro Inc.', 'Nasdaq Listed'],
  ['CLRB', 'Cellectar Biosciences, Inc.', 'Nasdaq Listed'],
  ['CLRO', 'ClearOne, Inc.', 'Nasdaq Listed'],
  ['CLSK', 'CleanSpark, Inc.', 'Nasdaq Listed'],
  ['CLST', 'Catalyst Bancorp, Inc.', 'Nasdaq Listed'],
  ['CLWT', 'Euro Tech Holdings Company Limited', 'Nasdaq Listed'],
  ['CLYM', 'Climb Bio, Inc.', 'Nasdaq Listed'],
  ['CMCO', 'Columbus McKinnon Corporation', 'Nasdaq Listed'],
  ['CMCT', 'Creative Media', 'Nasdaq Listed'],
  ['CMII', 'Columbus Circle Capital Corp II', 'Nasdaq Listed'],
  ['CMMB', 'Chemomab Therapeutics Ltd.', 'Nasdaq Listed'],
  ['CMND', 'Clearmind Medicine Inc.', 'Nasdaq Listed'],
  ['CMPR', 'Cimpress plc', 'Nasdaq Listed'],
  ['CMPX', 'Compass Therapeutics, Inc.', 'Nasdaq Listed'],
  ['CMRC', 'Commerce.com, Inc. - Series 1 Common Stock', 'Nasdaq Listed'],
  ['CMTL', 'Comtech Telecommunications Corp.', 'Nasdaq Listed'],
  ['CMTV', 'Community Bancorp.', 'Nasdaq Listed'],
  ['CNCK', 'Coincheck Group N.V.', 'Nasdaq Listed'],
  ['CNDT', 'Conduent Incorporated', 'Nasdaq Listed'],
  ['CNET', 'ZW Data Action Technologies Inc.', 'Nasdaq Listed'],
  ['CNEY', 'CN Energy Group Inc.', 'Nasdaq Listed'],
  ['CNOB', 'ConnectOne Bancorp, Inc.', 'Nasdaq Listed'],
  ['CNSP', 'CNS Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['CNTA', 'Centessa Pharmaceuticals plc', 'Nasdaq Listed'],
  ['CNTB', 'Connect Biopharma Holdings Limited', 'Nasdaq Listed'],
  ['CNTN', 'Canton Strategic Holdings, Inc.', 'Nasdaq Listed'],
  ['CNTX', 'Context Therapeutics Inc.', 'Nasdaq Listed'],
  ['CNTY', 'Century Casinos, Inc.', 'Nasdaq Listed'],
  ['CNVS', 'Cineverse Corp.', 'Nasdaq Listed'],
  ['CNXC', 'Concentrix Corporation', 'Nasdaq Listed'],
  ['CNXN', 'PC Connection, Inc.', 'Nasdaq Listed'],
  ['CNXU', 'Conexeu Sciences Inc.', 'Nasdaq Listed'],
  ['COAG', 'Hemab Therapeutics Holdings, Inc.', 'Nasdaq Listed'],
  ['COCH', 'Envoy Medical, Inc.', 'Nasdaq Listed'],
  ['COCO', 'The Vita Coco Company, Inc.', 'Nasdaq Listed'],
  ['COCP', 'Cocrystal Pharma, Inc.', 'Nasdaq Listed'],
  ['CODA', 'Coda Octopus Group, Inc.', 'Nasdaq Listed'],
  ['CODX', 'Co-Diagnostics, Inc.', 'Nasdaq Listed'],
  ['COFS', 'ChoiceOne Financial Services, Inc.', 'Nasdaq Listed'],
  ['COGT', 'Cogent Biosciences, Inc.', 'Nasdaq Listed'],
  ['COHU', 'Cohu, Inc.', 'Nasdaq Listed'],
  ['COKE', 'Coca-Cola Consolidated, Inc.', 'Nasdaq Listed'],
  ['COLA', 'Columbus Acquisition Corp', 'Nasdaq Listed'],
  ['COLB', 'Columbia Banking System, Inc.', 'Nasdaq Listed'],
  ['COLL', 'Collegium Pharmaceutical, Inc.', 'Nasdaq Listed'],
  ['COLM', 'Columbia Sportswear Company', 'Nasdaq Listed'],
  ['COOT', 'Australian Oilseeds Holdings Limited', 'Nasdaq Listed'],
  ['CORT', 'Corcept Therapeutics Incorporated', 'Nasdaq Listed'],
  ['CORZ', 'Core Scientific, Inc.', 'Nasdaq Listed'],
  ['COSM', 'Cosmos Health Inc.', 'Nasdaq Listed'],
  ['COYA', 'Coya Therapeutics, Inc.', 'Nasdaq Listed'],
  ['CPB', 'The Campbell\'s Company', 'Nasdaq Listed'],
  ['CPBI', 'Central Plains Bancshares, Inc.', 'Nasdaq Listed'],
  ['CPHC', 'Canterbury Park Holding Corporation', 'Nasdaq Listed'],
  ['CPIX', 'Cumberland Pharmaceuticals Inc.', 'Nasdaq Listed'],
  ['CPOP', 'Pop Culture Group Co., Ltd', 'Nasdaq Listed'],
  ['CPRX', 'Catalyst Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['CPSH', 'CPS Technologies Corp.', 'Nasdaq Listed'],
  ['CPSS', 'Consumer Portfolio Services, Inc.', 'Nasdaq Listed'],
  ['CRAC', 'Crown Reserve Acquisition Corp. I', 'Nasdaq Listed'],
  ['CRAI', 'CRA International,Inc.', 'Nasdaq Listed'],
  ['CRAN', 'Crane Harbor Acquisition Corp. II', 'Nasdaq Listed'],
  ['CRAQ', 'Cal Redwood Acquisition Corp.', 'Nasdaq Listed'],
  ['CRBP', 'Corbus Pharmaceuticals Holdings, Inc.', 'Nasdaq Listed'],
  ['CRBU', 'Caribou Biosciences, Inc.', 'Nasdaq Listed'],
  ['CRCT', 'Cricut, Inc.', 'Nasdaq Listed'],
  ['CRDF', 'Cardiff Oncology, Inc.', 'Nasdaq Listed'],
  ['CRDL', 'Cardiol Therapeutics Inc. - Class A Common Shares', 'Nasdaq Listed'],
  ['CRDO', 'Credo Technology Group Holding Ltd', 'Nasdaq Listed'],
  ['CRE', 'Cre8 Enterprise Limited', 'Nasdaq Listed'],
  ['CREG', 'Smart Powerr Corp.', 'Nasdaq Listed'],
  ['CRESY', 'Cresud S.A.C.I.F. y A.', 'Nasdaq Listed'],
  ['CREX', 'Creative Realities, Inc.', 'Nasdaq Listed'],
  ['CRGO', 'Freightos Limited', 'Nasdaq Listed'],
  ['CRIS', 'Curis, Inc.', 'Nasdaq Listed'],
  ['CRMD', 'CorMedix Inc.', 'Nasdaq Listed'],
  ['CRML', 'Critical Metals Corp.', 'Nasdaq Listed'],
  ['CRMT', 'America\'s Car-Mart, Inc.', 'Nasdaq Listed'],
  ['CRNC', 'Cerence Inc.', 'Nasdaq Listed'],
  ['CRNT', 'Ceragon Networks Ltd.', 'Nasdaq Listed'],
  ['CRNX', 'Crinetics Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['CROX', 'Crocs, Inc.', 'Nasdaq Listed'],
  ['CRSP', 'CRISPR Therapeutics AG', 'Nasdaq Listed'],
  ['CRSR', 'Corsair Gaming, Inc.', 'Nasdaq Listed'],
  ['CRTO', 'Criteo S.A.', 'Nasdaq Listed'],
  ['CRUS', 'Cirrus Logic, Inc.', 'Nasdaq Listed'],
  ['CRVL', 'CorVel Corp.', 'Nasdaq Listed'],
  ['CRVO', 'CervoMed Inc.', 'Nasdaq Listed'],
  ['CRVS', 'Corvus Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['CRWS', 'Crown Crafts, Inc.', 'Nasdaq Listed'],
  ['CRWV', 'CoreWeave, Inc.', 'Nasdaq Listed'],
  ['CSAI', 'Cloudastructure, Inc.', 'Nasdaq Listed'],
  ['CSBR', 'Champions Oncology, Inc.', 'Nasdaq Listed'],
  ['CSHR', 'CoinShares PLC', 'Nasdaq Listed'],
  ['CSIQ', 'Canadian Solar Inc.', 'Nasdaq Listed'],
  ['CSPI', 'CSP Inc.', 'Nasdaq Listed'],
  ['CSTE', 'Caesarstone Ltd.', 'Nasdaq Listed'],
  ['CSTL', 'Castle Biosciences, Inc.', 'Nasdaq Listed'],
  ['CSWC', 'Capital Southwest Corporation', 'Nasdaq Listed'],
  ['CTAA', 'ClearThink 1 Acquisition Corp.', 'Nasdaq Listed'],
  ['CTKB', 'Cytek Biosciences, Inc.', 'Nasdaq Listed'],
  ['CTMX', 'CytomX Therapeutics, Inc.', 'Nasdaq Listed'],
  ['CTNM', 'Contineum Therapeutics, Inc.', 'Nasdaq Listed'],
  ['CTNT', 'Cheetah Net Supply Chain Service Inc.', 'Nasdaq Listed'],
  ['CTOR', 'Citius Oncology, Inc.', 'Nasdaq Listed'],
  ['CTRM', 'Castor Maritime Inc.', 'Nasdaq Listed'],
  ['CTRN', 'Citi Trends, Inc.', 'Nasdaq Listed'],
  ['CTSO', 'Cytosorbents Corporation', 'Nasdaq Listed'],
  ['CTW', 'CTW', 'Nasdaq Listed'],
  ['CTXR', 'Citius Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['CUB', 'Lionheart Holdings', 'Nasdaq Listed'],
  ['CUE', 'Cue Biopharma, Inc.', 'Nasdaq Listed'],
  ['CULP', 'Culp, Inc.', 'Nasdaq Listed'],
  ['CUPR', 'Cuprina Holdings (Cayman) Limited', 'Nasdaq Listed'],
  ['CURI', 'CuriosityStream Inc.', 'Nasdaq Listed'],
  ['CURR', 'Currenc Group Inc.', 'Nasdaq Listed'],
  ['CURX', 'Curanex Pharmaceuticals Inc', 'Nasdaq Listed'],
  ['CV', 'CapsoVision, Inc.', 'Nasdaq Listed'],
  ['CVBF', 'CVB Financial Corporation', 'Nasdaq Listed'],
  ['CVCO', 'Cavco Industries, Inc.', 'Nasdaq Listed'],
  ['CVGI', 'Commercial Vehicle Group, Inc.', 'Nasdaq Listed'],
  ['CVKD', 'Cadrenal Therapeutics, Inc.', 'Nasdaq Listed'],
  ['CVLT', 'Commvault Systems, Inc.', 'Nasdaq Listed'],
  ['CVRX', 'CVRx, Inc.', 'Nasdaq Listed'],
  ['CVV', 'CVD Equipment Corporation', 'Nasdaq Listed'],
  ['CWBC', 'Community West Bancshares', 'Nasdaq Listed'],
  ['CWCO', 'Consolidated Water Co. Ltd.', 'Nasdaq Listed'],
  ['CWD', 'CaliberCos Inc.', 'Nasdaq Listed'],
  ['CWST', 'Casella Waste Systems, Inc.', 'Nasdaq Listed'],
  ['CXAI', 'CXApp Inc.', 'Nasdaq Listed'],
  ['CXDO', 'Crexendo, Inc.', 'Nasdaq Listed'],
  ['CYAB', 'Cyabra, Inc.', 'Nasdaq Listed'],
  ['CYCN', 'Cyclerion Therapeutics, Inc.', 'Nasdaq Listed'],
  ['CYCU', 'Cycurion, Inc.', 'Nasdaq Listed'],
  ['CYN', 'Cyngn Inc.', 'Nasdaq Listed'],
  ['CYPH', 'Cypherpunk Technologies Inc.', 'Nasdaq Listed'],
  ['CYRX', 'CryoPort, Inc.', 'Nasdaq Listed'],
  ['CYTK', 'Cytokinetics, Incorporated', 'Nasdaq Listed'],
  ['CZFS', 'Citizens Financial Services, Inc.', 'Nasdaq Listed'],
  ['CZNC', 'Citizens & Northern Corp', 'Nasdaq Listed'],
  ['CZR', 'Caesars Entertainment, Inc.', 'Nasdaq Listed'],
  ['CZWI', 'Citizens Community Bancorp, Inc.', 'Nasdaq Listed'],
  ['DAAQ', 'Digital Asset Acquisition Corp.', 'Nasdaq Listed'],
  ['DAIC', 'CID HoldCo, Inc.', 'Nasdaq Listed'],
  ['DAIO', 'Data I/O Corporation', 'Nasdaq Listed'],
  ['DAKT', 'Daktronics, Inc.', 'Nasdaq Listed'],
  ['DARE', 'Dare Bioscience, Inc.', 'Nasdaq Listed'],
  ['DAVE', 'Dave Inc.', 'Nasdaq Listed'],
  ['DBCA', 'D. Boral Acquisition I Corp.', 'Nasdaq Listed'],
  ['DBGI', 'Digital Brands Group, Inc.', 'Nasdaq Listed'],
  ['DBVT', 'DBV Technologies S.A.', 'Nasdaq Listed'],
  ['DBX', 'Dropbox, Inc.', 'Nasdaq Listed'],
  ['DCBO', 'Docebo Inc.', 'Nasdaq Listed'],
  ['DCGO', 'DocGo Inc.', 'Nasdaq Listed'],
  ['DCOY', 'Decoy Therapeutics Inc.', 'Nasdaq Listed'],
  ['DCTH', 'Delcath Systems, Inc.', 'Nasdaq Listed'],
  ['DCX', 'Digital Currency X Technology Inc.', 'Nasdaq Listed'],
  ['DEFT', 'Defi Technologies, Inc.', 'Nasdaq Listed'],
  ['DERM', 'Journey Medical Corporation', 'Nasdaq Listed'],
  ['DETX', 'Liberty Defense Holdings, Ltd.', 'Nasdaq Listed'],
  ['DEVS', 'DevvStream Corp.', 'Nasdaq Listed'],
  ['DFDV', 'DeFi Development Corp.', 'Nasdaq Listed'],
  ['DFLI', 'Dragonfly Energy Holdings Corp', 'Nasdaq Listed'],
  ['DFNS', 'T3 Defense Inc.', 'Nasdaq Listed'],
  ['DFSC', 'DEFSEC Technologies Inc. - common stock, no R/S concurrent with offering', 'Nasdaq Listed'],
  ['DFTX', 'Definium Therapeutics, Inc.', 'Nasdaq Listed'],
  ['DGICA', 'Donegal Group, Inc.', 'Nasdaq Listed'],
  ['DGICB', 'Donegal Group, Inc.', 'Nasdaq Listed'],
  ['DGII', 'Digi International Inc.', 'Nasdaq Listed'],
  ['DGNX', 'Diginex Limited', 'Nasdaq Listed'],
  ['DH', 'Definitive Healthcare Corp.', 'Nasdaq Listed'],
  ['DIBS', '1stdibs.com, Inc.', 'Nasdaq Listed'],
  ['DIOD', 'Diodes Incorporated', 'Nasdaq Listed'],
  ['DJCO', 'Daily Journal Corp. (S.C.)', 'Nasdaq Listed'],
  ['DJT', 'Trump Media & Technology Group Corp.', 'Nasdaq Listed'],
  ['DKI', 'DarkIris Inc.', 'Nasdaq Listed'],
  ['DKNG', 'DraftKings Inc.', 'Nasdaq Listed'],
  ['DLHC', 'DLH Holdings Corp.', 'Nasdaq Listed'],
  ['DLO', 'DLocal Limited - Class A Common Shares', 'Nasdaq Listed'],
  ['DLPN', 'Dolphin Entertainment, Inc.', 'Nasdaq Listed'],
  ['DLTH', 'Duluth Holdings Inc.', 'Nasdaq Listed'],
  ['DLXY', 'Delixy Holdings Limited', 'Nasdaq Listed'],
  ['DMAA', 'Drugs Made In America Acquisition Corp.', 'Nasdaq Listed'],
  ['DMAC', 'DiaMedica Therapeutics Inc.', 'Nasdaq Listed'],
  ['DMII', 'Drugs Made In America Acquisition II Corp.', 'Nasdaq Listed'],
  ['DMRA', 'Damora Therapeutics, Inc.', 'Nasdaq Listed'],
  ['DMRC', 'Digimarc Corporation', 'Nasdaq Listed'],
  ['DNLI', 'Denali Therapeutics Inc.', 'Nasdaq Listed'],
  ['DNMX', 'Dynamix Corporation III', 'Nasdaq Listed'],
  ['DNTH', 'Dianthus Therapeutics, Inc.', 'Nasdaq Listed'],
  ['DNUT', 'Krispy Kreme, Inc.', 'Nasdaq Listed'],
  ['DOCU', 'DocuSign, Inc.', 'Nasdaq Listed'],
  ['DOGZ', 'Dogness (International) Corporation', 'Nasdaq Listed'],
  ['DOMH', 'Dominari Holdings Inc.', 'Nasdaq Listed'],
  ['DOMO', 'Domo, Inc.', 'Nasdaq Listed'],
  ['DORM', 'Dorman Products, Inc.', 'Nasdaq Listed'],
  ['DOX', 'Amdocs Limited', 'Nasdaq Listed'],
  ['DOYU', 'DouYu International Holdings Limited', 'Nasdaq Listed'],
  ['DPRO', 'Draganfly Inc.', 'Nasdaq Listed'],
  ['DRCT', 'Direct Digital Holdings, Inc.', 'Nasdaq Listed'],
  ['DRDB', 'Roman DBDR Acquisition Corp. II', 'Nasdaq Listed'],
  ['DRH', 'Diamondrock Hospitality Company', 'Nasdaq Listed'],
  ['DRIO', 'DarioHealth Corp.', 'Nasdaq Listed'],
  ['DRMA', 'Dermata Therapeutics, Inc.', 'Nasdaq Listed'],
  ['DRS', 'Leonardo DRS, Inc.', 'Nasdaq Listed'],
  ['DRTS', 'Alpha Tau Medical Ltd.', 'Nasdaq Listed'],
  ['DRUG', 'Bright Minds Biosciences Inc.', 'Nasdaq Listed'],
  ['DRVN', 'Driven Brands Holdings Inc.', 'Nasdaq Listed'],
  ['DSAC', 'Daedalus Special Acquisition Corp.', 'Nasdaq Listed'],
  ['DSGN', 'Design Therapeutics, Inc.', 'Nasdaq Listed'],
  ['DSGR', 'Distribution Solutions Group, Inc.', 'Nasdaq Listed'],
  ['DSGX', 'The Descartes Systems Group Inc.', 'Nasdaq Listed'],
  ['DSP', 'Viant Technology Inc.', 'Nasdaq Listed'],
  ['DSWL', 'Deswell Industries, Inc.', 'Nasdaq Listed'],
  ['DSY', 'Big Tree Cloud Holdings Limited', 'Nasdaq Listed'],
  ['DTCX', 'Datacentrex, Inc.', 'Nasdaq Listed'],
  ['DTI', 'Drilling Tools International Corporation', 'Nasdaq Listed'],
  ['DTIL', 'Precision BioSciences, Inc.', 'Nasdaq Listed'],
  ['DTSQ', 'DT Cloud Star Acquisition Corporation', 'Nasdaq Listed'],
  ['DTSS', 'Datasea Intelligent Technology Ltd.', 'Nasdaq Listed'],
  ['DTST', 'Data Storage Corporation', 'Nasdaq Listed'],
  ['DUKR', 'DUKE Robotics Corp.', 'Nasdaq Listed'],
  ['DUO', 'Fangdd Network Group Ltd.', 'Nasdaq Listed'],
  ['DUOL', 'Duolingo, Inc.', 'Nasdaq Listed'],
  ['DUOT', 'Duos Technologies Group, Inc.', 'Nasdaq Listed'],
  ['DVLT', 'Datavault AI Inc.', 'Nasdaq Listed'],
  ['DWSN', 'Dawson Geophysical Company', 'Nasdaq Listed'],
  ['DWTX', 'Dogwood Therapeutics, Inc.', 'Nasdaq Listed'],
  ['DXLG', 'Destination XL Group, Inc.', 'Nasdaq Listed'],
  ['DXPE', 'DXP Enterprises, Inc.', 'Nasdaq Listed'],
  ['DXST', 'Decent Holding Inc.', 'Nasdaq Listed'],
  ['DYAI', 'Dyadic International, Inc.', 'Nasdaq Listed'],
  ['DYN', 'Dyne Therapeutics, Inc.', 'Nasdaq Listed'],
  ['DYNC', 'Dynamix Corporation', 'Nasdaq Listed'],
  ['DYOR', 'Insight Digital Partners II', 'Nasdaq Listed'],
  ['EBC', 'Eastern Bankshares, Inc.', 'Nasdaq Listed'],
  ['EBMT', 'Eagle Bancorp Montana, Inc.', 'Nasdaq Listed'],
  ['EBON', 'Ebang International Holdings Inc.', 'Nasdaq Listed'],
  ['ECBK', 'ECB Bancorp, Inc.', 'Nasdaq Listed'],
  ['ECOR', 'electroCore, Inc.', 'Nasdaq Listed'],
  ['ECPG', 'Encore Capital Group Inc', 'Nasdaq Listed'],
  ['ECX', 'ECARX Holdings Inc.', 'Nasdaq Listed'],
  ['EDAP', 'EDAP TMS S.A.', 'Nasdaq Listed'],
  ['EDBL', 'Edible Garden AG Incorporated', 'Nasdaq Listed'],
  ['EDHL', 'Everbright Digital Holding Limited', 'Nasdaq Listed'],
  ['EDIT', 'Editas Medicine, Inc.', 'Nasdaq Listed'],
  ['EDRY', 'EuroDry Ltd.', 'Nasdaq Listed'],
  ['EDSA', 'Edesa Biotech, Inc.', 'Nasdaq Listed'],
  ['EDTK', 'Skillful Craftsman Education Technology Limited - Ordinary Share', 'Nasdaq Listed'],
  ['EDUC', 'Educational Development Corporation', 'Nasdaq Listed'],
  ['EEFT', 'Euronet Worldwide, Inc.', 'Nasdaq Listed'],
  ['EEIQ', 'EpicQuest Education Group International Limited', 'Nasdaq Listed'],
  ['EFOI', 'Energy Focus, Inc.', 'Nasdaq Listed'],
  ['EFSC', 'Enterprise Financial Services Corporation', 'Nasdaq Listed'],
  ['EFSI', 'Eagle Financial Services Inc', 'Nasdaq Listed'],
  ['EFTY', 'Etoiles Capital Group Co., Ltd.', 'Nasdaq Listed'],
  ['EGAN', 'eGain Corporation', 'Nasdaq Listed'],
  ['EGBN', 'Eagle Bancorp, Inc.', 'Nasdaq Listed'],
  ['EGHA', 'EGH Acquisition Corp.', 'Nasdaq Listed'],
  ['EGHT', '8x8 Inc', 'Nasdaq Listed'],
  ['EH', 'EHang Holdings Limited', 'Nasdaq Listed'],
  ['EHGO', 'Eshallgo Inc.', 'Nasdaq Listed'],
  ['EHLD', 'Euroholdings Ltd.', 'Nasdaq Listed'],
  ['EHTH', 'eHealth, Inc.', 'Nasdaq Listed'],
  ['EIKN', 'Eikon Therapeutics, Inc.', 'Nasdaq Listed'],
  ['EJH', 'E-Home Household Service Holdings Limited', 'Nasdaq Listed'],
  ['ELAB', 'PMGC Holdings Inc.', 'Nasdaq Listed'],
  ['ELBM', 'Electra Battery Materials Corporation', 'Nasdaq Listed'],
  ['ELDN', 'Eledon Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['ELE', 'Elemental Royalty Corporation', 'Nasdaq Listed'],
  ['ELMT', 'The Elmet Group Co.', 'Nasdaq Listed'],
  ['ELOG', 'Eastern International Ltd.', 'Nasdaq Listed'],
  ['ELPW', 'Elong Power Holding Limited', 'Nasdaq Listed'],
  ['ELSE', 'Electro-Sensors, Inc.', 'Nasdaq Listed'],
  ['ELTK', 'Eltek Ltd.', 'Nasdaq Listed'],
  ['ELTX', 'Elicio Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ELUT', 'Elutia, Inc.', 'Nasdaq Listed'],
  ['ELVA', 'Electrovaya Inc.', 'Nasdaq Listed'],
  ['ELVN', 'Enliven Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ELWT', 'Elauwit Connection, Inc.', 'Nasdaq Listed'],
  ['EMAT', 'Evolution Metals & Technologies Corp.', 'Nasdaq Listed'],
  ['EMBC', 'Embecta Corp.', 'Nasdaq Listed'],
  ['EMIS', 'Emmis Acquisition Corp.', 'Nasdaq Listed'],
  ['EML', 'Eastern Company (The)', 'Nasdaq Listed'],
  ['EMPD', 'Empery Digital Inc.', 'Nasdaq Listed'],
  ['EMPG', 'Empro Group Inc.', 'Nasdaq Listed'],
  ['ENGN', 'enGene Therapeutics Inc.', 'Nasdaq Listed'],
  ['ENGS', 'Energys Group Limited', 'Nasdaq Listed'],
  ['ENLT', 'Enlight Renewable Energy Ltd.', 'Nasdaq Listed'],
  ['ENLV', 'Enlivex Ltd.', 'Nasdaq Listed'],
  ['ENPH', 'Enphase Energy, Inc.', 'Nasdaq Listed'],
  ['ENSC', 'Ensysce Biosciences, Inc.', 'Nasdaq Listed'],
  ['ENSG', 'The Ensign Group, Inc.', 'Nasdaq Listed'],
  ['ENTA', 'Enanta Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['ENTG', 'Entegris, Inc.', 'Nasdaq Listed'],
  ['ENTX', 'Entera Bio Ltd.', 'Nasdaq Listed'],
  ['ENVB', 'Enveric Biosciences, Inc.', 'Nasdaq Listed'],
  ['ENVX', 'Enovix Corporation', 'Nasdaq Listed'],
  ['EOLS', 'Evolus, Inc.', 'Nasdaq Listed'],
  ['EOSE', 'Eos Energy Enterprises, Inc.', 'Nasdaq Listed'],
  ['EPOW', 'E-Power Inc.', 'Nasdaq Listed'],
  ['EPRX', 'Eupraxia Pharmaceuticals Inc.', 'Nasdaq Listed'],
  ['EPSM', 'Epsium Enterprise Limited', 'Nasdaq Listed'],
  ['EPSN', 'Epsilon Energy Ltd.', 'Nasdaq Listed'],
  ['EQ', 'Equillium, Inc.', 'Nasdaq Listed'],
  ['EQPT', 'EquipmentShare.com Inc', 'Nasdaq Listed'],
  ['ERAS', 'Erasca, Inc.', 'Nasdaq Listed'],
  ['ERIC', 'Ericsson', 'Nasdaq Listed'],
  ['ERII', 'Energy Recovery, Inc.', 'Nasdaq Listed'],
  ['ERNA', 'Ernexa Therapeutics Inc.', 'Nasdaq Listed'],
  ['ESCA', 'Escalade, Incorporated', 'Nasdaq Listed'],
  ['ESEA', 'Euroseas Ltd.', 'Nasdaq Listed'],
  ['ESLA', 'Estrella Immunopharma, Inc.', 'Nasdaq Listed'],
  ['ESLT', 'Elbit Systems Ltd.', 'Nasdaq Listed'],
  ['ESOA', 'Energy Services of America Corporation', 'Nasdaq Listed'],
  ['ESPR', 'Esperion Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ESQ', 'Esquire Financial Holdings, Inc.', 'Nasdaq Listed'],
  ['ESTA', 'Establishment Labs Holdings Inc.', 'Nasdaq Listed'],
  ['ETON', 'Eton Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['ETOR', 'eToro Group Ltd. - Class A Common Shares', 'Nasdaq Listed'],
  ['ETS', 'Elite Express Holding Inc.', 'Nasdaq Listed'],
  ['EU', 'enCore Energy Corp.', 'Nasdaq Listed'],
  ['EUDA', 'Euda Health Holdings Limited', 'Nasdaq Listed'],
  ['EURK', 'Eureka Acquisition Corp', 'Nasdaq Listed'],
  ['EVAX', 'Evaxion A/S', 'Nasdaq Listed'],
  ['EVCM', 'EverCommerce Inc.', 'Nasdaq Listed'],
  ['EVER', 'EverQuote, Inc.', 'Nasdaq Listed'],
  ['EVGN', 'Evogene Ltd.', 'Nasdaq Listed'],
  ['EVGO', 'EVgo Inc.', 'Nasdaq Listed'],
  ['EVLV', 'Evolv Technologies Holdings, Inc.', 'Nasdaq Listed'],
  ['EVO', 'Evotec SE', 'Nasdaq Listed'],
  ['EVOX', 'Evolution Global Acquisition Corp', 'Nasdaq Listed'],
  ['EVTV', 'Envirotech Vehicles, Inc.', 'Nasdaq Listed'],
  ['EWBC', 'East West Bancorp, Inc.', 'Nasdaq Listed'],
  ['EWTX', 'Edgewise Therapeutics, Inc.', 'Nasdaq Listed'],
  ['EXEL', 'Exelixis, Inc.', 'Nasdaq Listed'],
  ['EXFY', 'Expensify, Inc.', 'Nasdaq Listed'],
  ['EXLS', 'ExlService Holdings, Inc.', 'Nasdaq Listed'],
  ['EXOZ', 'eXoZymes Inc.', 'Nasdaq Listed'],
  ['EXPO', 'Exponent, Inc.', 'Nasdaq Listed'],
  ['EXTR', 'Extreme Networks, Inc.', 'Nasdaq Listed'],
  ['EXYN', 'Exyn Technologies, Inc.', 'Nasdaq Listed'],
  ['EYE', 'National Vision Holdings, Inc.', 'Nasdaq Listed'],
  ['EYPT', 'EyePoint, Inc.', 'Nasdaq Listed'],
  ['EZGO', 'EZGO Technologies Ltd.', 'Nasdaq Listed'],
  ['EZPW', 'EZCORP, Inc. - Class A Non-Voting Common Stock', 'Nasdaq Listed'],
  ['EZRA', 'Reliance Global Group, Inc.', 'Nasdaq Listed'],
  ['FA', 'First Advantage Corporation', 'Nasdaq Listed'],
  ['FABC', 'Fabric.AI, Inc.', 'Nasdaq Listed'],
  ['FACT', 'FACT II Acquisition Corp.', 'Nasdaq Listed'],
  ['FAMI', 'Farmmi, Inc.', 'Nasdaq Listed'],
  ['FATE', 'Fate Therapeutics, Inc.', 'Nasdaq Listed'],
  ['FATN', 'FatPipe, Inc.', 'Nasdaq Listed'],
  ['FBGL', 'FBS Global Limited', 'Nasdaq Listed'],
  ['FBIO', 'Fortress Biotech, Inc.', 'Nasdaq Listed'],
  ['FBIZ', 'First Business Financial Services, Inc.', 'Nasdaq Listed'],
  ['FBLA', 'FB Bancorp, Inc.', 'Nasdaq Listed'],
  ['FBLG', 'FibroBiologics, Inc.', 'Nasdaq Listed'],
  ['FBNC', 'First Bancorp', 'Nasdaq Listed'],
  ['FBRX', 'Forte Biosciences, Inc.', 'Nasdaq Listed'],
  ['FBYD', 'Falcon\'s Beyond Global, Inc.', 'Nasdaq Listed'],
  ['FCAP', 'First Capital, Inc.', 'Nasdaq Listed'],
  ['FCBC', 'First Community Bankshares, Inc.', 'Nasdaq Listed'],
  ['FCCO', 'First Community Corporation', 'Nasdaq Listed'],
  ['FCEL', 'FuelCell Energy, Inc.', 'Nasdaq Listed'],
  ['FCFS', 'FirstCash Holdings, Inc.', 'Nasdaq Listed'],
  ['FCHL', 'Fitness Champs Holdings Limited', 'Nasdaq Listed'],
  ['FCNCA', 'First Citizens BancShares, Inc.', 'Nasdaq Listed'],
  ['FCUV', 'Focus Universal Inc.', 'Nasdaq Listed'],
  ['FDBC', 'Fidelity D & D Bancorp, Inc.', 'Nasdaq Listed'],
  ['FDMT', '4D Molecular Therapeutics, Inc.', 'Nasdaq Listed'],
  ['FDSB', 'Fifth District Bancorp, Inc.', 'Nasdaq Listed'],
  ['FEAM', '5E Advanced Materials, Inc.', 'Nasdaq Listed'],
  ['FEBO', 'Fenbo Holdings Limited', 'Nasdaq Listed'],
  ['FEED', 'ENvue Medical, Inc.', 'Nasdaq Listed'],
  ['FEIM', 'Frequency Electronics, Inc.', 'Nasdaq Listed'],
  ['FELE', 'Franklin Electric Co., Inc.', 'Nasdaq Listed'],
  ['FEMY', 'Femasys Inc.', 'Nasdaq Listed'],
  ['FENC', 'Fennec Pharmaceuticals Inc.', 'Nasdaq Listed'],
  ['FERA', 'Fifth Era Acquisition Corp I', 'Nasdaq Listed'],
  ['FFAI', 'Faraday Future Intelligent Electric Inc.', 'Nasdaq Listed'],
  ['FFBC', 'First Financial Bancorp.', 'Nasdaq Listed'],
  ['FFIC', 'Flushing Financial Corporation', 'Nasdaq Listed'],
  ['FFIN', 'First Financial Bankshares, Inc.', 'Nasdaq Listed'],
  ['FGBI', 'First Guaranty Bancshares, Inc.', 'Nasdaq Listed'],
  ['FGI', 'FGI Industries Ltd.', 'Nasdaq Listed'],
  ['FGII', 'FG Imperii Acquisition Corp.', 'Nasdaq Listed'],
  ['FGL', 'Founder Group Limited', 'Nasdaq Listed'],
  ['FGMC', 'FG Merger II Corp.', 'Nasdaq Listed'],
  ['FGNX', 'FG Nexus Inc.', 'Nasdaq Listed'],
  ['FHB', 'First Hawaiian, Inc.', 'Nasdaq Listed'],
  ['FHTX', 'Foghorn Therapeutics Inc.', 'Nasdaq Listed'],
  ['FIBK', 'First Interstate BancSystem, Inc.', 'Nasdaq Listed'],
  ['FIEE', 'FiEE, Inc', 'Nasdaq Listed'],
  ['FIGR', 'Figure Technology Solutions, Inc.', 'Nasdaq Listed'],
  ['FIGX', 'FIGX Capital Acquisition Corp.', 'Nasdaq Listed'],
  ['FINW', 'FinWise Bancorp', 'Nasdaq Listed'],
  ['FIP', 'FTAI Infrastructure Inc.', 'Nasdaq Listed'],
  ['FISI', 'Financial Institutions, Inc.', 'Nasdaq Listed'],
  ['FIVE', 'Five Below, Inc.', 'Nasdaq Listed'],
  ['FIVN', 'Five9, Inc.', 'Nasdaq Listed'],
  ['FIZZ', 'National Beverage Corp.', 'Nasdaq Listed'],
  ['FKWL', 'Franklin Wireless Corp.', 'Nasdaq Listed'],
  ['FLD', 'Fold Holdings, Inc.', 'Nasdaq Listed'],
  ['FLGT', 'Fulgent Genetics, Inc.', 'Nasdaq Listed'],
  ['FLL', 'Full House Resorts, Inc.', 'Nasdaq Listed'],
  ['FLNA', 'Filana Therapeutics, Inc.', 'Nasdaq Listed'],
  ['FLNC', 'Fluence Energy, Inc.', 'Nasdaq Listed'],
  ['FLNT', 'Fluent, Inc.', 'Nasdaq Listed'],
  ['FLUX', 'Flux Power Holdings, Inc.', 'Nasdaq Listed'],
  ['FLWS', '1-800-FLOWERS.COM, Inc.', 'Nasdaq Listed'],
  ['FLX', 'BingEx Limited', 'Nasdaq Listed'],
  ['FLXS', 'Flexsteel Industries, Inc.', 'Nasdaq Listed'],
  ['FLY', 'Firefly Aerospace Inc.', 'Nasdaq Listed'],
  ['FLYE', 'Fly-E Group, Inc.', 'Nasdaq Listed'],
  ['FLYW', 'Flywire Corporation - Voting Common Stock', 'Nasdaq Listed'],
  ['FMAC', 'Future Money Acquisition Corporation', 'Nasdaq Listed'],
  ['FMAO', 'Farmers & Merchants Bancorp, Inc.', 'Nasdaq Listed'],
  ['FMBH', 'First Mid Bancshares, Inc.', 'Nasdaq Listed'],
  ['FMFC', 'Kandal M Venture Limited', 'Nasdaq Listed'],
  ['FMNB', 'Farmers National Banc Corp.', 'Nasdaq Listed'],
  ['FMST', 'Foremost Clean Energy Ltd.', 'Nasdaq Listed'],
  ['FNGR', 'FingerMotion, Inc.', 'Nasdaq Listed'],
  ['FNKO', 'Funko, Inc.', 'Nasdaq Listed'],
  ['FNLC', 'First Bancorp, Inc (ME)', 'Nasdaq Listed'],
  ['FNRN', 'First Northern Community Bancorp', 'Nasdaq Listed'],
  ['FNUC', 'Frontier Nuclear and Minerals Inc.', 'Nasdaq Listed'],
  ['FNWB', 'First Northwest Bancorp', 'Nasdaq Listed'],
  ['FNWD', 'Finward Bancorp', 'Nasdaq Listed'],
  ['FOFO', 'Hang Feng Technology Innovation Co., Ltd.', 'Nasdaq Listed'],
  ['FONR', 'Fonar Corporation', 'Nasdaq Listed'],
  ['FORM', 'FormFactor, Inc.', 'Nasdaq Listed'],
  ['FORR', 'Forrester Research, Inc.', 'Nasdaq Listed'],
  ['FORTY', 'Formula Systems (1985) Ltd.', 'Nasdaq Listed'],
  ['FOSL', 'Fossil Group, Inc.', 'Nasdaq Listed'],
  ['FOXF', 'Fox Factory Holding Corp.', 'Nasdaq Listed'],
  ['FOXX', 'Foxx Development Holdings Inc.', 'Nasdaq Listed'],
  ['FRAF', 'Franklin Financial Services Corporation', 'Nasdaq Listed'],
  ['FRBA', 'First Bank', 'Nasdaq Listed'],
  ['FRD', 'Friedman Industries Inc.', 'Nasdaq Listed'],
  ['FRGT', 'Freight Technologies, Inc.', 'Nasdaq Listed'],
  ['FRHC', 'Freedom Holding Corp.', 'Nasdaq Listed'],
  ['FRME', 'First Merchants Corporation', 'Nasdaq Listed'],
  ['FRMI', 'Fermi Inc.', 'Nasdaq Listed'],
  ['FRMM', 'Forum Markets, Incorporated', 'Nasdaq Listed'],
  ['FROG', 'JFrog Ltd.', 'Nasdaq Listed'],
  ['FRPH', 'FRP Holdings, Inc.', 'Nasdaq Listed'],
  ['FRPT', 'Freshpet, Inc.', 'Nasdaq Listed'],
  ['FRSH', 'Freshworks Inc.', 'Nasdaq Listed'],
  ['FRST', 'Primis Financial Corp.', 'Nasdaq Listed'],
  ['FRSX', 'Foresight Autonomous Holdings Ltd.', 'Nasdaq Listed'],
  ['FRVO', 'Fervo Energy Company', 'Nasdaq Listed'],
  ['FSBC', 'Five Star Bancorp', 'Nasdaq Listed'],
  ['FSBW', 'FS Bancorp, Inc.', 'Nasdaq Listed'],
  ['FSEA', 'First Seacoast Bancorp, Inc.', 'Nasdaq Listed'],
  ['FSHP', 'Flag Ship Acquisition Corp.', 'Nasdaq Listed'],
  ['FSLY', 'Fastly, Inc.', 'Nasdaq Listed'],
  ['FSTR', 'L.B. Foster Company', 'Nasdaq Listed'],
  ['FSUN', 'FirstSun Capital Bancorp', 'Nasdaq Listed'],
  ['FSV', 'FirstService Corporation', 'Nasdaq Listed'],
  ['FTAI', 'FTAI Aviation Ltd.', 'Nasdaq Listed'],
  ['FTCI', 'FTC Solar, Inc.', 'Nasdaq Listed'],
  ['FTDR', 'Frontdoor, Inc.', 'Nasdaq Listed'],
  ['FTEK', 'Fuel Tech, Inc.', 'Nasdaq Listed'],
  ['FTFT', 'Future FinTech Group Inc.', 'Nasdaq Listed'],
  ['FTHM', 'Fathom Holdings Inc.', 'Nasdaq Listed'],
  ['FTLF', 'FitLife Brands, Inc.', 'Nasdaq Listed'],
  ['FTRE', 'Fortrea Holdings Inc.', 'Nasdaq Listed'],
  ['FTRK', 'FAST TRACK GROUP', 'Nasdaq Listed'],
  ['FUFU', 'BitFuFu Inc.', 'Nasdaq Listed'],
  ['FULC', 'Fulcrum Therapeutics, Inc.', 'Nasdaq Listed'],
  ['FULT', 'Fulton Financial Corporation', 'Nasdaq Listed'],
  ['FUNC', 'First United Corporation', 'Nasdaq Listed'],
  ['FUSB', 'First US Bancshares, Inc.', 'Nasdaq Listed'],
  ['FUSE', 'Fusemachines Inc.', 'Nasdaq Listed'],
  ['FUTU', 'Futu Holdings Limited', 'Nasdaq Listed'],
  ['FVAV', 'Fortress Value Acquisition Corp. V', 'Nasdaq Listed'],
  ['FVCB', 'FVCBankcorp, Inc.', 'Nasdaq Listed'],
  ['FVN', 'Future Vision II Acquisition Corporation', 'Nasdaq Listed'],
  ['FWDI', 'Forward Industries, Inc.', 'Nasdaq Listed'],
  ['FWONA', 'Liberty Media Corporation - Series A Liberty Formula One Common Stock', 'Nasdaq Listed'],
  ['FWONK', 'Liberty Media Corporation - Series C Liberty Formula One Common Stock', 'Nasdaq Listed'],
  ['FWRD', 'Forward Air Corporation', 'Nasdaq Listed'],
  ['FWRG', 'First Watch Restaurant Group, Inc.', 'Nasdaq Listed'],
  ['FXNC', 'First National Corporation', 'Nasdaq Listed'],
  ['GABC', 'German American Bancorp, Inc.', 'Nasdaq Listed'],
  ['GAIA', 'Gaia, Inc.', 'Nasdaq Listed'],
  ['GAIN', 'Gladstone Investment Corporation - Business Development Company', 'Nasdaq Listed'],
  ['GALT', 'Galectin Therapeutics Inc.', 'Nasdaq Listed'],
  ['GAMB', 'Gambling.com Group Limited', 'Nasdaq Listed'],
  ['GAME', 'GameSquare Holdings, Inc.', 'Nasdaq Listed'],
  ['GANX', 'Gain Therapeutics, Inc.', 'Nasdaq Listed'],
  ['GASS', 'StealthGas, Inc.', 'Nasdaq Listed'],
  ['GAUZ', 'Gauzy Ltd.', 'Nasdaq Listed'],
  ['GBFH', 'GBank Financial Holdings Inc.', 'Nasdaq Listed'],
  ['GBLI', 'Global Indemnity Group, LLC - Class A Common Shares', 'Nasdaq Listed'],
  ['GCBC', 'Greene County Bancorp, Inc.', 'Nasdaq Listed'],
  ['GCL', 'GCL Global Holdings Ltd', 'Nasdaq Listed'],
  ['GCMG', 'GCM Grosvenor Inc.', 'Nasdaq Listed'],
  ['GCT', 'GigaCloud Technology Inc', 'Nasdaq Listed'],
  ['GCTK', 'GlucoTrack, Inc.', 'Nasdaq Listed'],
  ['GDC', 'GD Culture Group Limited', 'Nasdaq Listed'],
  ['GDEV', 'GDEV Inc.', 'Nasdaq Listed'],
  ['GDHG', 'Golden Heaven Group Holdings Ltd.', 'Nasdaq Listed'],
  ['GDRX', 'GoodRx Holdings, Inc.', 'Nasdaq Listed'],
  ['GDS', 'GDS Holdings Limited', 'Nasdaq Listed'],
  ['GDTC', 'CytoMed Therapeutics Limited', 'Nasdaq Listed'],
  ['GDYN', 'Grid Dynamics Holdings, Inc.', 'Nasdaq Listed'],
  ['GEG', 'Great Elm Group, Inc.', 'Nasdaq Listed'],
  ['GELS', 'Gelteq Limited', 'Nasdaq Listed'],
  ['GEMI', 'Gemini Space Station, Inc.', 'Nasdaq Listed'],
  ['GENB', 'Generate Biomedicines, Inc.', 'Nasdaq Listed'],
  ['GENK', 'GEN Restaurant Group, Inc.', 'Nasdaq Listed'],
  ['GEOS', 'Geospace Technologies Corporation', 'Nasdaq Listed'],
  ['GERN', 'Geron Corporation', 'Nasdaq Listed'],
  ['GEVO', 'Gevo, Inc.', 'Nasdaq Listed'],
  ['GFAI', 'Guardforce AI Co., Limited', 'Nasdaq Listed'],
  ['GFS', 'GlobalFoundries Inc. - Ordinary Share', 'Nasdaq Listed'],
  ['GGAL', 'Grupo Financiero Galicia S.A.', 'Nasdaq Listed'],
  ['GGR', 'Gogoro Inc.', 'Nasdaq Listed'],
  ['GGRP', 'The Glimpse Group, Inc.', 'Nasdaq Listed'],
  ['GH', 'Guardant Health, Inc.', 'Nasdaq Listed'],
  ['GHRS', 'GH Research PLC', 'Nasdaq Listed'],
  ['GIBO', 'GIBO Holdings Limited', 'Nasdaq Listed'],
  ['GIFT', 'Giftify, Inc.', 'Nasdaq Listed'],
  ['GIGM', 'GigaMedia Limited', 'Nasdaq Listed'],
  ['GIII', 'G-III Apparel Group, LTD.', 'Nasdaq Listed'],
  ['GILT', 'Gilat Satellite Networks Ltd.', 'Nasdaq Listed'],
  ['GIPR', 'Generation Income Properties Inc.', 'Nasdaq Listed'],
  ['GITS', 'Global Interactive Technologies, Inc. Common Stock', 'Nasdaq Listed'],
  ['GIW', 'GigCapital8 Corp.', 'Nasdaq Listed'],
  ['GIX', 'GigCapital9 Corp.', 'Nasdaq Listed'],
  ['GLBE', 'Global-E Online Ltd.', 'Nasdaq Listed'],
  ['GLBS', 'Globus Maritime Limited', 'Nasdaq Listed'],
  ['GLE', 'Global Engine Group Holding Limited', 'Nasdaq Listed'],
  ['GLIBA', 'Liberty Capital Corporation - Series A GCI Group Common Stock', 'Nasdaq Listed'],
  ['GLIBK', 'Liberty Capital Corporation - Series C GCI Group Common Stock', 'Nasdaq Listed'],
  ['GLMD', 'Galmed Pharmaceuticals Ltd.', 'Nasdaq Listed'],
  ['GLND', 'Greenland Energy Company', 'Nasdaq Listed'],
  ['GLNG', 'Golar LNG Limited', 'Nasdaq Listed'],
  ['GLOO', 'Gloo Holdings, Inc.', 'Nasdaq Listed'],
  ['GLPI', 'Gaming and Leisure Properties, Inc.', 'Nasdaq Listed'],
  ['GLRE', 'Greenlight Reinsurance, Ltd.', 'Nasdaq Listed'],
  ['GLSI', 'Greenwich LifeSciences, Inc.', 'Nasdaq Listed'],
  ['GLUE', 'Monte Rosa Therapeutics, Inc.', 'Nasdaq Listed'],
  ['GLXG', 'Galaxy Payroll Group Limited', 'Nasdaq Listed'],
  ['GLXY', 'Galaxy Digital Inc.', 'Nasdaq Listed'],
  ['GMAB', 'Genmab A/S', 'Nasdaq Listed'],
  ['GMEX', 'GMEX ROBOTICS CORPORATION', 'Nasdaq Listed'],
  ['GMHS', 'Gamehaus Holdings Inc.', 'Nasdaq Listed'],
  ['GMM', 'Global Mofy AI Limited', 'Nasdaq Listed'],
  ['GNLN', 'Greenlane Holdings, Inc.', 'Nasdaq Listed'],
  ['GNLX', 'Genelux Corporation', 'Nasdaq Listed'],
  ['GNPX', 'Genprex, Inc.', 'Nasdaq Listed'],
  ['GNSS', 'Genasys Inc.', 'Nasdaq Listed'],
  ['GNTA', 'Genenta Science S.p.A.', 'Nasdaq Listed'],
  ['GNTX', 'Gentex Corporation', 'Nasdaq Listed'],
  ['GO', 'Grocery Outlet Holding Corp.', 'Nasdaq Listed'],
  ['GOAI', 'Eva Live Inc.', 'Nasdaq Listed'],
  ['GOCO', 'GoHealth, Inc.', 'Nasdaq Listed'],
  ['GOGO', 'Gogo Inc.', 'Nasdaq Listed'],
  ['GOSS', 'Gossamer Bio, Inc.', 'Nasdaq Listed'],
  ['GOVX', 'GeoVax Labs, Inc.', 'Nasdaq Listed'],
  ['GP', 'GreenPower Motor Company Inc.', 'Nasdaq Listed'],
  ['GPAC', 'General Purpose Acquisition Corp.', 'Nasdaq Listed'],
  ['GPAT', 'GP-Act III Acquisition Corp.', 'Nasdaq Listed'],
  ['GPCR', 'Structure Therapeutics Inc.', 'Nasdaq Listed'],
  ['GPRE', 'Green Plains, Inc.', 'Nasdaq Listed'],
  ['GPRO', 'GoPro, Inc.', 'Nasdaq Listed'],
  ['GRAB', 'Grab Holdings Limited', 'Nasdaq Listed'],
  ['GRAL', 'GRAIL, Inc.', 'Nasdaq Listed'],
  ['GRAN', 'Grande Group Limited', 'Nasdaq Listed'],
  ['GRCE', 'Grace Therapeutics, Inc.', 'Nasdaq Listed'],
  ['GRDX', 'GridAI Technologies Corp.', 'Nasdaq Listed'],
  ['GREE', 'Greenidge Generation Holdings Inc.', 'Nasdaq Listed'],
  ['GRFS', 'Grifols, S.A.', 'Nasdaq Listed'],
  ['GRI', 'GRI Bio, Inc.', 'Nasdaq Listed'],
  ['GRML', 'Greenland Mines Ltd', 'Nasdaq Listed'],
  ['GRNQ', 'Greenpro Capital Corp.', 'Nasdaq Listed'],
  ['GROW', 'U.S. Global Investors, Inc.', 'Nasdaq Listed'],
  ['GRPN', 'Groupon, Inc.', 'Nasdaq Listed'],
  ['GRRR', 'Gorilla Technology Group Inc.', 'Nasdaq Listed'],
  ['GRVY', 'GRAVITY Co., Ltd.', 'Nasdaq Listed'],
  ['GRWG', 'GrowGeneration Corp.', 'Nasdaq Listed'],
  ['GSAT', 'Globalstar, Inc.', 'Nasdaq Listed'],
  ['GSBC', 'Great Southern Bancorp, Inc.', 'Nasdaq Listed'],
  ['GSHD', 'Goosehead Insurance, Inc.', 'Nasdaq Listed'],
  ['GSHR', 'Gesher Acquisition Corp. II', 'Nasdaq Listed'],
  ['GSIT', 'GSI Technology, Inc.', 'Nasdaq Listed'],
  ['GSIW', 'Garden Stage Limited', 'Nasdaq Listed'],
  ['GSM', 'Ferroglobe PLC', 'Nasdaq Listed'],
  ['GSRF', 'GSR IV Acquisition Corp.', 'Nasdaq Listed'],
  ['GSUN', 'Golden Sun Technology Group Limited', 'Nasdaq Listed'],
  ['GT', 'The Goodyear Tire & Rubber Company', 'Nasdaq Listed'],
  ['GTBP', 'GT Biopharma, Inc.', 'Nasdaq Listed'],
  ['GTEC', 'Greenland Technologies Holding Corporation', 'Nasdaq Listed'],
  ['GTEN', 'Gores Holdings X, Inc.', 'Nasdaq Listed'],
  ['GTERA', 'Globa Terra Acquisition Corporation', 'Nasdaq Listed'],
  ['GTIM', 'Good Times Restaurants Inc.', 'Nasdaq Listed'],
  ['GTLB', 'GitLab Inc.', 'Nasdaq Listed'],
  ['GTM', 'ZoomInfo Technologies Inc.', 'Nasdaq Listed'],
  ['GTX', 'Garrett Motion Inc.', 'Nasdaq Listed'],
  ['GURE', 'Gulf Resources, Inc.', 'Nasdaq Listed'],
  ['GUTS', 'Fractyl Health, Inc.', 'Nasdaq Listed'],
  ['GV', 'Visionary Holdings Inc.', 'Nasdaq Listed'],
  ['GWAV', 'Greenwave Technology Solutions, Inc.', 'Nasdaq Listed'],
  ['GWRS', 'Global Water Resources, Inc.', 'Nasdaq Listed'],
  ['GXAI', 'Gaxos.ai Inc.', 'Nasdaq Listed'],
  ['GYRE', 'Gyre Therapeutics, Inc.', 'Nasdaq Listed'],
  ['GYRO', 'Gyrodyne , LLC', 'Nasdaq Listed'],
  ['HACQ', 'HCM IV Acquisition Corp.', 'Nasdaq Listed'],
  ['HAFC', 'Hanmi Financial Corporation', 'Nasdaq Listed'],
  ['HAIN', 'The Hain Celestial Group, Inc.', 'Nasdaq Listed'],
  ['HALO', 'Halozyme Therapeutics, Inc.', 'Nasdaq Listed'],
  ['HAVA', 'Harvard Ave Acquisition Corporation', 'Nasdaq Listed'],
  ['HBCP', 'Home Bancorp, Inc.', 'Nasdaq Listed'],
  ['HBIO', 'Harvard Bioscience, Inc.', 'Nasdaq Listed'],
  ['HBNB', 'Hotel101 Global Holdings Corp.', 'Nasdaq Listed'],
  ['HBNC', 'Horizon Bancorp, Inc.', 'Nasdaq Listed'],
  ['HBT', 'HBT Financial, Inc.', 'Nasdaq Listed'],
  ['HCAC', 'Hall Chadwick Acquisition Corp.', 'Nasdaq Listed'],
  ['HCAI', 'Huachen AI Parking Management Technology Holding Co., Ltd.', 'Nasdaq Listed'],
  ['HCAT', 'Health Catalyst, Inc', 'Nasdaq Listed'],
  ['HCHL', 'Happy City Holdings Limited', 'Nasdaq Listed'],
  ['HCIC', 'Hennessy Capital Investment Corp. VIII', 'Nasdaq Listed'],
  ['HCKT', 'The Hackett Group, Inc.', 'Nasdaq Listed'],
  ['HCM', 'HUTCHMED (China) Limited', 'Nasdaq Listed'],
  ['HCMA', 'HCM III Acquisition Corp.', 'Nasdaq Listed'],
  ['HCSG', 'Healthcare Services Group, Inc.', 'Nasdaq Listed'],
  ['HCTI', 'Healthcare Triangle, Inc.', 'Nasdaq Listed'],
  ['HCWB', 'HCW Biologics Inc.', 'Nasdaq Listed'],
  ['HDL', 'SUPER HI INTERNATIONAL HOLDING LTD.', 'Nasdaq Listed'],
  ['HDRN', 'Hadron Energy, Inc.', 'Nasdaq Listed'],
  ['HDSN', 'Hudson Technologies, Inc.', 'Nasdaq Listed'],
  ['HELE', 'Helen of Troy Limited', 'Nasdaq Listed'],
  ['HELP', 'Cybin Inc.', 'Nasdaq Listed'],
  ['HEPS', 'D-Market Electronic Services & Trading', 'Nasdaq Listed'],
  ['HERE', 'Here Group Limited', 'Nasdaq Listed'],
  ['HFBL', 'Home Federal Bancorp, Inc. of Louisiana', 'Nasdaq Listed'],
  ['HFFG', 'HF Foods Group Inc.', 'Nasdaq Listed'],
  ['HFWA', 'Heritage Financial Corporation', 'Nasdaq Listed'],
  ['HGBL', 'Heritage Global Inc.', 'Nasdaq Listed'],
  ['HHS', 'Harte Hanks, Inc.', 'Nasdaq Listed'],
  ['HIFS', 'Hingham Institution for Savings', 'Nasdaq Listed'],
  ['HIHO', 'Highway Holdings Limited', 'Nasdaq Listed'],
  ['HIMX', 'Himax Technologies, Inc.', 'Nasdaq Listed'],
  ['HIND', 'Vyome Holdings, Inc.', 'Nasdaq Listed'],
  ['HIT', 'Health In Tech, Inc.', 'Nasdaq Listed'],
  ['HITI', 'High Tide Inc.', 'Nasdaq Listed'],
  ['HIVE', 'HIVE Digital Technologies Ltd', 'Nasdaq Listed'],
  ['HKIT', 'Hitek Global Inc.', 'Nasdaq Listed'],
  ['HKPD', 'Cellyan Biotechnology Co., Ltd', 'Nasdaq Listed'],
  ['HLIT', 'Harmonic Inc.', 'Nasdaq Listed'],
  ['HLMN', 'Hillman Solutions Corp.', 'Nasdaq Listed'],
  ['HLNE', 'Hamilton Lane Incorporated', 'Nasdaq Listed'],
  ['HLP', 'Hongli Group Inc.', 'Nasdaq Listed'],
  ['HLXC', 'Helix Acquisition Corp. III', 'Nasdaq Listed'],
  ['HMH', 'HMH Holding Inc.', 'Nasdaq Listed'],
  ['HMR', 'Heidmar Maritime Holdings Corp.', 'Nasdaq Listed'],
  ['HNNA', 'Hennessy Advisors, Inc.', 'Nasdaq Listed'],
  ['HNRG', 'Hallador Energy Company', 'Nasdaq Listed'],
  ['HNST', 'The Honest Company, Inc.', 'Nasdaq Listed'],
  ['HNVR', 'Hanover Bancorp, Inc.', 'Nasdaq Listed'],
  ['HOFT', 'Hooker Furnishings Corporation', 'Nasdaq Listed'],
  ['HOLO', 'MicroCloud Hologram Inc.', 'Nasdaq Listed'],
  ['HOPE', 'Hope Bancorp, Inc.', 'Nasdaq Listed'],
  ['HOUR', 'Hour Loop, Inc.', 'Nasdaq Listed'],
  ['HOVR', 'New Horizon Aircraft Ltd.', 'Nasdaq Listed'],
  ['HOWL', 'Werewolf Therapeutics, Inc.', 'Nasdaq Listed'],
  ['HPAI', 'Helport AI Limited', 'Nasdaq Listed'],
  ['HPK', 'HighPeak Energy, Inc.', 'Nasdaq Listed'],
  ['HQ', 'Horizon Quantum Holdings Ltd.', 'Nasdaq Listed'],
  ['HQI', 'HireQuest, Inc.', 'Nasdaq Listed'],
  ['HQY', 'HealthEquity, Inc.', 'Nasdaq Listed'],
  ['HRMY', 'Harmony Biosciences Holdings, Inc.', 'Nasdaq Listed'],
  ['HROW', 'Harrow, Inc.', 'Nasdaq Listed'],
  ['HRTX', 'Heron Therapeutics, Inc.', 'Nasdaq Listed'],
  ['HRZN', 'Horizon Technology Finance Corporation', 'Nasdaq Listed'],
  ['HSAI', 'Hesai Group', 'Nasdaq Listed'],
  ['HSCS', 'HeartSciences Inc.', 'Nasdaq Listed'],
  ['HSDT', 'Solana Company', 'Nasdaq Listed'],
  ['HSPT', 'Horizon Space Acquisition II Corp. - Ordinary share', 'Nasdaq Listed'],
  ['HSTM', 'HealthStream, Inc.', 'Nasdaq Listed'],
  ['HTCO', 'High-Trend International Group', 'Nasdaq Listed'],
  ['HTCR', 'Heartcore Enterprises, Inc.', 'Nasdaq Listed'],
  ['HTFL', 'Heartflow, Inc.', 'Nasdaq Listed'],
  ['HTHT', 'H World Group Limited', 'Nasdaq Listed'],
  ['HTLD', 'Heartland Express, Inc.', 'Nasdaq Listed'],
  ['HTLM', 'HomesToLife Ltd', 'Nasdaq Listed'],
  ['HTO', 'H2O America', 'Nasdaq Listed'],
  ['HTOO', 'Fusion Fuel Green PLC', 'Nasdaq Listed'],
  ['HTZ', 'Hertz Global Holdings, Inc', 'Nasdaq Listed'],
  ['HUBC', 'Hub Cyber Security Ltd.', 'Nasdaq Listed'],
  ['HUBG', 'Hub Group, Inc.', 'Nasdaq Listed'],
  ['HUDI', 'Huadi International Group Co., Ltd.', 'Nasdaq Listed'],
  ['HUHU', 'HUHUTECH International Group Inc.', 'Nasdaq Listed'],
  ['HUIZ', 'Huize Holding Limited', 'Nasdaq Listed'],
  ['HUMA', 'Humacyte, Inc.', 'Nasdaq Listed'],
  ['HURA', 'TuHURA Biosciences, Inc.', 'Nasdaq Listed'],
  ['HURC', 'Hurco Companies, Inc.', 'Nasdaq Listed'],
  ['HURN', 'Huron Consulting Group Inc.', 'Nasdaq Listed'],
  ['HUT', 'Hut 8 Corp.', 'Nasdaq Listed'],
  ['HVII', 'Hennessy Capital Investment Corp. VII', 'Nasdaq Listed'],
  ['HVMC', 'Highview Merger Corp.', 'Nasdaq Listed'],
  ['HWBK', 'Hawthorn Bancshares, Inc.', 'Nasdaq Listed'],
  ['HWC', 'Hancock Whitney Corporation', 'Nasdaq Listed'],
  ['HWH', 'HWH International Inc.', 'Nasdaq Listed'],
  ['HWKN', 'Hawkins, Inc.', 'Nasdaq Listed'],
  ['HXHX', 'Haoxin Holdings Limited', 'Nasdaq Listed'],
  ['HYFM', 'Hydrofarm Holdings Group, Inc.', 'Nasdaq Listed'],
  ['HYFT', 'MindWalk Holdings Corp.', 'Nasdaq Listed'],
  ['HYMC', 'Hycroft Mining Holding Corporation', 'Nasdaq Listed'],
  ['HYNE', 'Hoyne Bancorp, Inc.', 'Nasdaq Listed'],
  ['HYPD', 'Hyperion DeFi, Inc.', 'Nasdaq Listed'],
  ['HYPR', 'Hyperfine, Inc.', 'Nasdaq Listed'],
  ['IAC', 'IAC Inc.', 'Nasdaq Listed'],
  ['IACO', 'Idea Acquisition Corp.', 'Nasdaq Listed'],
  ['IART', 'Integra LifeSciences Holdings Corporation', 'Nasdaq Listed'],
  ['IBAC', 'IB Acquisition Corp.', 'Nasdaq Listed'],
  ['IBCP', 'Independent Bank Corporation', 'Nasdaq Listed'],
  ['IBG', 'Innovation Beverage Group Limited', 'Nasdaq Listed'],
  ['IBIO', 'iBio, Inc.', 'Nasdaq Listed'],
  ['IBOC', 'International Bancshares Corporation', 'Nasdaq Listed'],
  ['IBRX', 'ImmunityBio, Inc.', 'Nasdaq Listed'],
  ['ICCC', 'ImmuCell Corporation', 'Nasdaq Listed'],
  ['ICCM', 'IceCure Medical Ltd.', 'Nasdaq Listed'],
  ['ICFI', 'ICF International, Inc.', 'Nasdaq Listed'],
  ['ICG', 'Intchains Group Limited', 'Nasdaq Listed'],
  ['ICHR', 'Ichor Holdings', 'Nasdaq Listed'],
  ['ICLR', 'ICON plc', 'Nasdaq Listed'],
  ['ICMB', 'Investcorp Credit Management BDC, Inc.', 'Nasdaq Listed'],
  ['ICON', 'Icon Energy Corp.', 'Nasdaq Listed'],
  ['ICU', 'SeaStar Medical Holding Corporation', 'Nasdaq Listed'],
  ['ICUI', 'ICU Medical, Inc.', 'Nasdaq Listed'],
  ['IDAI', 'T Stamp Inc.', 'Nasdaq Listed'],
  ['IDCC', 'InterDigital, Inc.', 'Nasdaq Listed'],
  ['IDN', 'Intellicheck, Inc.', 'Nasdaq Listed'],
  ['IDYA', 'IDEAYA Biosciences, Inc.', 'Nasdaq Listed'],
  ['IEAG', 'Infinite Eagle Acquisition Corp.', 'Nasdaq Listed'],
  ['IESC', 'IES Holdings, Inc.', 'Nasdaq Listed'],
  ['IFBD', 'Infobird Co., Ltd', 'Nasdaq Listed'],
  ['IFRX', 'InflaRx N.V.', 'Nasdaq Listed'],
  ['IGAC', 'Invest Green Acquisition Corporation', 'Nasdaq Listed'],
  ['IGIC', 'International General Insurance Holdings Ltd.', 'Nasdaq Listed'],
  ['IHRT', 'iHeartMedia, Inc.', 'Nasdaq Listed'],
  ['III', 'Information Services Group, Inc.', 'Nasdaq Listed'],
  ['IIIV', 'i3 Verticals, Inc.', 'Nasdaq Listed'],
  ['IKT', 'Inhibikase Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ILAG', 'Intelligent Living Application Group Inc.', 'Nasdaq Listed'],
  ['ILLR', 'Triller Group Inc.', 'Nasdaq Listed'],
  ['ILLU', 'Illumination Acquisition Corp I', 'Nasdaq Listed'],
  ['ILMN', 'Illumina, Inc.', 'Nasdaq Listed'],
  ['IMA', 'ImageneBio, Inc.', 'Nasdaq Listed'],
  ['IMCC', 'IM Cannabis Corp.', 'Nasdaq Listed'],
  ['IMCR', 'Immunocore Holdings plc', 'Nasdaq Listed'],
  ['IMDX', 'Insight Molecular Diagnostics Inc.', 'Nasdaq Listed'],
  ['IMKTA', 'Ingles Markets, Incorporated', 'Nasdaq Listed'],
  ['IMMP', 'Immutep Limited', 'Nasdaq Listed'],
  ['IMMR', 'Immersion Corporation', 'Nasdaq Listed'],
  ['IMMX', 'Immix Biopharma, Inc.', 'Nasdaq Listed'],
  ['IMNM', 'Immunome, Inc.', 'Nasdaq Listed'],
  ['IMNN', 'Imunon, Inc.', 'Nasdaq Listed'],
  ['IMOS', 'ChipMOS TECHNOLOGIES INC.', 'Nasdaq Listed'],
  ['IMPP', 'Imperial Petroleum Inc.', 'Nasdaq Listed'],
  ['IMRN', 'Immuron Limited', 'Nasdaq Listed'],
  ['IMRX', 'Immuneering Corporation', 'Nasdaq Listed'],
  ['IMSR', 'Terrestrial Energy Inc.', 'Nasdaq Listed'],
  ['IMTE', 'Integrated Media Technology Limited', 'Nasdaq Listed'],
  ['IMTX', 'Immatics N.V.', 'Nasdaq Listed'],
  ['IMUX', 'Immunic, Inc.', 'Nasdaq Listed'],
  ['IMVT', 'Immunovant, Inc.', 'Nasdaq Listed'],
  ['IMXI', 'International Money Express, Inc.', 'Nasdaq Listed'],
  ['INAB', 'IN8bio, Inc.', 'Nasdaq Listed'],
  ['INAC', 'Indigo Acquisition Corp.', 'Nasdaq Listed'],
  ['INBK', 'First Internet Bancorp', 'Nasdaq Listed'],
  ['INBS', 'Intelligent Bio Solutions Inc.', 'Nasdaq Listed'],
  ['INBX', 'Inhibrx Biosciences, Inc.', 'Nasdaq Listed'],
  ['INCR', 'Intercure Ltd.', 'Nasdaq Listed'],
  ['INDB', 'Independent Bank Corp.', 'Nasdaq Listed'],
  ['INDI', 'indie Semiconductor, Inc.', 'Nasdaq Listed'],
  ['INDP', 'Indaptus Therapeutics, Inc.', 'Nasdaq Listed'],
  ['INDV', 'Indivior Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['INEO', 'INNEOVA Holdings Limited', 'Nasdaq Listed'],
  ['INGN', 'Inogen, Inc', 'Nasdaq Listed'],
  ['INHD', 'Inno Holdings Inc.', 'Nasdaq Listed'],
  ['INKT', 'MiNK Therapeutics, Inc.', 'Nasdaq Listed'],
  ['INLF', 'INLIF LIMITED', 'Nasdaq Listed'],
  ['INM', 'InMed Pharmaceuticals Inc.', 'Nasdaq Listed'],
  ['INMB', 'INmune Bio Inc.', 'Nasdaq Listed'],
  ['INMD', 'InMode Ltd.', 'Nasdaq Listed'],
  ['INNV', 'InnovAge Holding Corp.', 'Nasdaq Listed'],
  ['INO', 'Inovio Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['INOD', 'Innodata Inc.', 'Nasdaq Listed'],
  ['INSE', 'Inspired Entertainment, Inc.', 'Nasdaq Listed'],
  ['INSG', 'Inseego Corp.', 'Nasdaq Listed'],
  ['INTA', 'Intapp, Inc.', 'Nasdaq Listed'],
  ['INTG', 'The Intergroup Corporation', 'Nasdaq Listed'],
  ['INTJ', 'Intelligent Group Limited', 'Nasdaq Listed'],
  ['INTR', 'Inter & Co. Inc. - Class A Common Shares', 'Nasdaq Listed'],
  ['INTS', 'Intensity Therapeutics, Inc.', 'Nasdaq Listed'],
  ['INTZ', 'Intrusion Inc.', 'Nasdaq Listed'],
  ['INV', 'Innventure, Inc.', 'Nasdaq Listed'],
  ['INVA', 'Innoviva, Inc.', 'Nasdaq Listed'],
  ['INVE', 'Identiv, Inc.', 'Nasdaq Listed'],
  ['INVZ', 'Innoviz Technologies Ltd.', 'Nasdaq Listed'],
  ['IONR', 'ioneer Ltd', 'Nasdaq Listed'],
  ['IONS', 'Ionis Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['IOSP', 'Innospec Inc.', 'Nasdaq Listed'],
  ['IOTR', 'iOThree Limited', 'Nasdaq Listed'],
  ['IOVA', 'Iovance Biotherapeutics, Inc.', 'Nasdaq Listed'],
  ['IPAR', 'Interparfums, Inc.', 'Nasdaq Listed'],
  ['IPCX', 'Inflection Point Acquisition Corp. III', 'Nasdaq Listed'],
  ['IPDN', 'Professional Diversity Network, Inc.', 'Nasdaq Listed'],
  ['IPEX', 'Inflection Point Acquisition Corp.', 'Nasdaq Listed'],
  ['IPFX', 'Inflection Point Acquisition Corp. VI', 'Nasdaq Listed'],
  ['IPGP', 'IPG Photonics Corporation', 'Nasdaq Listed'],
  ['IPHA', 'Innate Pharma S.A.', 'Nasdaq Listed'],
  ['IPM', 'Intelligent Protection Management Corp.', 'Nasdaq Listed'],
  ['IPSC', 'Century Therapeutics, Inc.', 'Nasdaq Listed'],
  ['IPST', 'IP Strategy Holdings, Inc.', 'Nasdaq Listed'],
  ['IPW', 'iPower Inc.', 'Nasdaq Listed'],
  ['IPWR', 'Ideal Power Inc.', 'Nasdaq Listed'],
  ['IPX', 'IperionX Limited', 'Nasdaq Listed'],
  ['IQ', 'iQIYI, Inc.', 'Nasdaq Listed'],
  ['IQST', 'iQSTEL Inc.', 'Nasdaq Listed'],
  ['IRD', 'Opus Genetics, Inc.', 'Nasdaq Listed'],
  ['IRDM', 'Iridium Communications Inc', 'Nasdaq Listed'],
  ['IREN', 'IREN Limited', 'Nasdaq Listed'],
  ['IRHO', 'Iron Horse Acquisitions II Corp.', 'Nasdaq Listed'],
  ['IRIX', 'IRIDEX Corporation', 'Nasdaq Listed'],
  ['IRMD', 'iRadimed Corporation', 'Nasdaq Listed'],
  ['IRON', 'Disc Medicine, Inc.', 'Nasdaq Listed'],
  ['IRTC', 'iRhythm Holdings, Inc.', 'Nasdaq Listed'],
  ['IRWD', 'Ironwood Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['ISBA', 'Isabella Bank Corporation', 'Nasdaq Listed'],
  ['ISPC', 'iSpecimen Inc.', 'Nasdaq Listed'],
  ['ISPR', 'Ispire Technology Inc.', 'Nasdaq Listed'],
  ['ISSC', 'Innovative Solutions and Support, Inc.', 'Nasdaq Listed'],
  ['ISTR', 'Investar Holding Corporation', 'Nasdaq Listed'],
  ['ITHA', 'ITHAX Acquisition Corp III', 'Nasdaq Listed'],
  ['ITIC', 'Investors Title Company', 'Nasdaq Listed'],
  ['ITOC', 'iTonic Holdings Ltd', 'Nasdaq Listed'],
  ['ITRI', 'Itron, Inc.', 'Nasdaq Listed'],
  ['ITRN', 'Ituran Location and Control Ltd.', 'Nasdaq Listed'],
  ['IVDA', 'Iveda Solutions, Inc.', 'Nasdaq Listed'],
  ['IVF', 'INVO Fertility, Inc.', 'Nasdaq Listed'],
  ['IVVD', 'Invivyd, Inc.', 'Nasdaq Listed'],
  ['IXHL', 'Incannex Healthcare Inc.', 'Nasdaq Listed'],
  ['IZEA', 'IZEA Worldwide, Inc.', 'Nasdaq Listed'],
  ['IZM', 'ICZOOM Group Inc.', 'Nasdaq Listed'],
  ['JACK', 'Jack In The Box Inc.', 'Nasdaq Listed'],
  ['JAGX', 'Jaguar Health, Inc.', 'Nasdaq Listed'],
  ['JAKK', 'JAKKS Pacific, Inc.', 'Nasdaq Listed'],
  ['JANX', 'Janux Therapeutics, Inc.', 'Nasdaq Listed'],
  ['JATT', 'JATT II Acquisition Corp', 'Nasdaq Listed'],
  ['JAZZ', 'Jazz Pharmaceuticals plc', 'Nasdaq Listed'],
  ['JBDI', 'JBDI Holdings Limited', 'Nasdaq Listed'],
  ['JBIO', 'Jade Biosciences, Inc.', 'Nasdaq Listed'],
  ['JBLU', 'JetBlue Airways Corporation', 'Nasdaq Listed'],
  ['JBSS', 'John B. Sanfilippo & Son, Inc.', 'Nasdaq Listed'],
  ['JCAP', 'Jefferson Capital, Inc.', 'Nasdaq Listed'],
  ['JCSE', 'JE Cleantech Holdings Limited', 'Nasdaq Listed'],
  ['JCTC', 'Jewett-Cameron Trading Company', 'Nasdaq Listed'],
  ['JD', 'JD.com, Inc.', 'Nasdaq Listed'],
  ['JDZG', 'JIADE LIMITED', 'Nasdaq Listed'],
  ['JEM', '707 Cayman Holdings Limited', 'Nasdaq Listed'],
  ['JF', 'J and Friends Holdings Limited', 'Nasdaq Listed'],
  ['JFB', 'JFB Construction Holdings', 'Nasdaq Listed'],
  ['JFIN', 'Jiayin Group Inc.', 'Nasdaq Listed'],
  ['JFU', '9F Inc.', 'Nasdaq Listed'],
  ['JG', 'Aurora Mobile Limited', 'Nasdaq Listed'],
  ['JJSF', 'J & J Snack Foods Corp.', 'Nasdaq Listed'],
  ['JL', 'J-Long Group Limited', 'Nasdaq Listed'],
  ['JLHL', 'Julong Holding Limited', 'Nasdaq Listed'],
  ['JMSB', 'John Marshall Bancorp, Inc.', 'Nasdaq Listed'],
  ['JOUT', 'Johnson Outdoors Inc.', 'Nasdaq Listed'],
  ['JOYY', 'JOYY Inc.', 'Nasdaq Listed'],
  ['JRSH', 'Jerash Holdings (US), Inc.', 'Nasdaq Listed'],
  ['JRVR', 'James River Group Holdings, Inc.', 'Nasdaq Listed'],
  ['JSPR', 'Jasper Therapeutics, Inc.', 'Nasdaq Listed'],
  ['JTAI', 'Jet.AI Inc.', 'Nasdaq Listed'],
  ['JUNS', 'Jupiter Neurosciences, Inc.', 'Nasdaq Listed'],
  ['JVA', 'Coffee Holding Co., Inc.', 'Nasdaq Listed'],
  ['JWEL', 'Jowell Global Ltd.', 'Nasdaq Listed'],
  ['JXG', 'JX Luxventure Group Inc.', 'Nasdaq Listed'],
  ['JYD', 'Jayud Global Logistics Limited', 'Nasdaq Listed'],
  ['JYNT', 'The Joint Corp.', 'Nasdaq Listed'],
  ['JZ', 'Jianzhi Education Technology Group Company Limited', 'Nasdaq Listed'],
  ['JZXN', 'Jiuzi Holdings, Inc.', 'Nasdaq Listed'],
  ['KALA', 'KALA BIO, Inc.', 'Nasdaq Listed'],
  ['KALU', 'Kaiser Aluminum Corporation', 'Nasdaq Listed'],
  ['KALV', 'KalVista Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['KARO', 'Karooooo Ltd.', 'Nasdaq Listed'],
  ['KBON', 'Karbon Capital Partners Corp.', 'Nasdaq Listed'],
  ['KBSX', 'FST Corp.', 'Nasdaq Listed'],
  ['KC', 'Kingsoft Cloud Holdings Limited', 'Nasdaq Listed'],
  ['KCHV', 'Kochav Defense Acquisition Corp.', 'Nasdaq Listed'],
  ['KDK', 'Kodiak AI, Inc.', 'Nasdaq Listed'],
  ['KE', 'Kimball Electronics, Inc.', 'Nasdaq Listed'],
  ['KEEL', 'Keel Infrastructure Corp.', 'Nasdaq Listed'],
  ['KELYA', 'Kelly Services, Inc.', 'Nasdaq Listed'],
  ['KELYB', 'Kelly Services, Inc.', 'Nasdaq Listed'],
  ['KEQU', 'Kewaunee Scientific Corporation', 'Nasdaq Listed'],
  ['KFFB', 'Kentucky First Federal Bancorp', 'Nasdaq Listed'],
  ['KFII', 'K&F Growth Acquisition Corp. II', 'Nasdaq Listed'],
  ['KG', 'Kestrel Group, Ltd.', 'Nasdaq Listed'],
  ['KGEI', 'Kolibri Global Energy Inc.', 'Nasdaq Listed'],
  ['KIDS', 'OrthoPediatrics Corp.', 'Nasdaq Listed'],
  ['KIDZ', 'Classover Holdings, Inc.', 'Nasdaq Listed'],
  ['KINS', 'Kingstone Companies, Inc', 'Nasdaq Listed'],
  ['KITT', 'Nauticus Robotics, Inc.', 'Nasdaq Listed'],
  ['KLIC', 'Kulicke and Soffa Industries, Inc.', 'Nasdaq Listed'],
  ['KLRA', 'Kailera Therapeutics, Inc.', 'Nasdaq Listed'],
  ['KLRS', 'Kalaris Therapeutics, Inc.', 'Nasdaq Listed'],
  ['KLTR', 'Kaltura, Inc.', 'Nasdaq Listed'],
  ['KLXE', 'KLX Energy Services Holdings, Inc.', 'Nasdaq Listed'],
  ['KMDA', 'Kamada Ltd.', 'Nasdaq Listed'],
  ['KMRK', 'K-Tech Solutions Company Limited', 'Nasdaq Listed'],
  ['KMTS', 'Kestra Medical Technologies, Ltd.', 'Nasdaq Listed'],
  ['KNDI', 'Kandi Technologies Group, Inc.', 'Nasdaq Listed'],
  ['KNSA', 'Kiniksa Pharmaceuticals International, plc', 'Nasdaq Listed'],
  ['KOD', 'Kodiak Sciences Inc', 'Nasdaq Listed'],
  ['KOPN', 'Kopin Corporation', 'Nasdaq Listed'],
  ['KOSS', 'Koss Corporation', 'Nasdaq Listed'],
  ['KOYN', 'CSLM Digital Asset Acquisition Corp III', 'Nasdaq Listed'],
  ['KPLT', 'Katapult Holdings, Inc.', 'Nasdaq Listed'],
  ['KPRX', 'Kiora Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['KPTI', 'Karyopharm Therapeutics Inc.', 'Nasdaq Listed'],
  ['KRAQ', 'KRAKacquisition Corp', 'Nasdaq Listed'],
  ['KRKR', '36Kr Holdings Inc.', 'Nasdaq Listed'],
  ['KRMD', 'KORU Medical Systems, Inc.', 'Nasdaq Listed'],
  ['KRNT', 'Kornit Digital Ltd.', 'Nasdaq Listed'],
  ['KRNY', 'Kearny Financial', 'Nasdaq Listed'],
  ['KROS', 'Keros Therapeutics, Inc.', 'Nasdaq Listed'],
  ['KRRO', 'Korro Bio, Inc.', 'Nasdaq Listed'],
  ['KRT', 'Karat Packaging Inc.', 'Nasdaq Listed'],
  ['KRUS', 'Kura Sushi USA, Inc.', 'Nasdaq Listed'],
  ['KRYS', 'Krystal Biotech, Inc.', 'Nasdaq Listed'],
  ['KSCP', 'Knightscope, Inc.', 'Nasdaq Listed'],
  ['KTCC', 'Key Tronic Corporation', 'Nasdaq Listed'],
  ['KTOS', 'Kratos Defense & Security Solutions, Inc.', 'Nasdaq Listed'],
  ['KTTA', 'Pasithea Therapeutics Corp.', 'Nasdaq Listed'],
  ['KTWO', 'K2 Capital Acquisition Corporation', 'Nasdaq Listed'],
  ['KURA', 'Kura Oncology, Inc.', 'Nasdaq Listed'],
  ['KUST', 'Kustom Entertainment, Inc.', 'Nasdaq Listed'],
  ['KVAC', 'Keen Vision Acquisition Corporation', 'Nasdaq Listed'],
  ['KVHI', 'KVH Industries, Inc.', 'Nasdaq Listed'],
  ['KWM', 'K Wave Media, Ltd.', 'Nasdaq Listed'],
  ['KXIN', 'Kaixin Holdings', 'Nasdaq Listed'],
  ['KYIV', 'Kyivstar Group Ltd.', 'Nasdaq Listed'],
  ['KYMR', 'Kymera Therapeutics, Inc.', 'Nasdaq Listed'],
  ['KYNB', 'Kyntra Bio, Inc.', 'Nasdaq Listed'],
  ['KYTX', 'Kyverna Therapeutics, Inc.', 'Nasdaq Listed'],
  ['KZIA', 'Kazia Therapeutics Limited', 'Nasdaq Listed'],
  ['LAB', 'Standard BioTools Inc.', 'Nasdaq Listed'],
  ['LABT', 'Lakewood-Amedex Biotherapeutics Inc.', 'Nasdaq Listed'],
  ['LAES', 'SEALSQ Corp', 'Nasdaq Listed'],
  ['LAFA', 'LaFayette Acquisition Corp. - Ordinary Share', 'Nasdaq Listed'],
  ['LAKE', 'Lakeland Industries, Inc.', 'Nasdaq Listed'],
  ['LAMR', 'Lamar Advertising Company', 'Nasdaq Listed'],
  ['LAND', 'Gladstone Land Corporation', 'Nasdaq Listed'],
  ['LARK', 'Landmark Bancorp Inc.', 'Nasdaq Listed'],
  ['LASE', 'Laser Photonics Corporation', 'Nasdaq Listed'],
  ['LASR', 'nLIGHT, Inc.', 'Nasdaq Listed'],
  ['LATA', 'Galata Acquisition Corp. II', 'Nasdaq Listed'],
  ['LAUR', 'Laureate Education, Inc.', 'Nasdaq Listed'],
  ['LAWR', 'Robot Consulting Co., Ltd.', 'Nasdaq Listed'],
  ['LBGJ', 'Li Bang International Corporation Inc.', 'Nasdaq Listed'],
  ['LBRDA', 'Liberty Broadband Corporation', 'Nasdaq Listed'],
  ['LBRDK', 'Liberty Broadband Corporation', 'Nasdaq Listed'],
  ['LBRX', 'LB Pharmaceuticals Inc', 'Nasdaq Listed'],
  ['LBTYA', 'Liberty Global Ltd. - Class A Common Shares', 'Nasdaq Listed'],
  ['LBTYB', 'Liberty Global Ltd. - Class B Common Shares', 'Nasdaq Listed'],
  ['LBTYK', 'Liberty Global Ltd. - Class C Common Shares', 'Nasdaq Listed'],
  ['LCCC', 'Lakeshore Acquisition III Corp.', 'Nasdaq Listed'],
  ['LCFY', 'Locafy Limited - Ordinary Share', 'Nasdaq Listed'],
  ['LCID', 'Lucid Group, Inc.', 'Nasdaq Listed'],
  ['LCNB', 'LCNB Corporation', 'Nasdaq Listed'],
  ['LCUT', 'Lifetime Brands, Inc.', 'Nasdaq Listed'],
  ['LE', 'Lands\' End, Inc.', 'Nasdaq Listed'],
  ['LECO', 'Lincoln Electric Holdings, Inc.', 'Nasdaq Listed'],
  ['LEDS', 'SemiLEDS Corporation', 'Nasdaq Listed'],
  ['LEE', 'Lee Enterprises, Incorporated', 'Nasdaq Listed'],
  ['LEGH', 'Legacy Housing Corporation', 'Nasdaq Listed'],
  ['LEGN', 'Legend Biotech Corporation', 'Nasdaq Listed'],
  ['LENZ', 'LENZ Therapeutics, Inc.', 'Nasdaq Listed'],
  ['LESL', 'Leslie\'s, Inc.', 'Nasdaq Listed'],
  ['LEXX', 'Lexaria Bioscience Corp.', 'Nasdaq Listed'],
  ['LFAC', 'Leapfrog Acquisition Corporation', 'Nasdaq Listed'],
  ['LFCR', 'Lifecore Biomedical, Inc.', 'Nasdaq Listed'],
  ['LFMD', 'LifeMD, Inc.', 'Nasdaq Listed'],
  ['LFS', 'LEIFRAS Co., Ltd.', 'Nasdaq Listed'],
  ['LFST', 'LifeStance Health Group, Inc.', 'Nasdaq Listed'],
  ['LFUS', 'Littelfuse, Inc.', 'Nasdaq Listed'],
  ['LFVN', 'Lifevantage Corporation', 'Nasdaq Listed'],
  ['LFWD', 'Lifeward Ltd.', 'Nasdaq Listed'],
  ['LGCL', 'Lucas GC Limited', 'Nasdaq Listed'],
  ['LGHL', 'Lion Group Holding Ltd.', 'Nasdaq Listed'],
  ['LGIH', 'LGI Homes, Inc.', 'Nasdaq Listed'],
  ['LGN', 'Legence Corp.', 'Nasdaq Listed'],
  ['LGND', 'Ligand Pharmaceuticals Incorporated', 'Nasdaq Listed'],
  ['LGO', 'Largo Inc.', 'Nasdaq Listed'],
  ['LGVN', 'Longeveron Inc.', 'Nasdaq Listed'],
  ['LHAI', 'Linkhome Holdings Inc.', 'Nasdaq Listed'],
  ['LHSW', 'Lianhe Sowell International Group Ltd', 'Nasdaq Listed'],
  ['LI', 'Li Auto Inc.', 'Nasdaq Listed'],
  ['LICN', 'Lichen International Limited', 'Nasdaq Listed'],
  ['LIDR', 'AEye, Inc.', 'Nasdaq Listed'],
  ['LIEN', 'Chicago Atlantic BDC, Inc.', 'Nasdaq Listed'],
  ['LIF', 'Life360, Inc.', 'Nasdaq Listed'],
  ['LIFE', 'Ethos Technologies Inc.', 'Nasdaq Listed'],
  ['LILA', 'Liberty Latin America Ltd.', 'Nasdaq Listed'],
  ['LILAK', 'Liberty Latin America Ltd.', 'Nasdaq Listed'],
  ['LIMN', 'Liminatus Pharma, Inc.', 'Nasdaq Listed'],
  ['LINC', 'Lincoln Educational Services Corporation', 'Nasdaq Listed'],
  ['LIND', 'Lindblad Expeditions Holdings Inc.', 'Nasdaq Listed'],
  ['LINE', 'Lineage, Inc.', 'Nasdaq Listed'],
  ['LINK', 'Interlink Electronics, Inc.', 'Nasdaq Listed'],
  ['LIQT', 'LiqTech International, Inc.', 'Nasdaq Listed'],
  ['LITS', 'Lite Strategy, Inc.', 'Nasdaq Listed'],
  ['LIVE', 'Live Ventures Incorporated', 'Nasdaq Listed'],
  ['LIVN', 'LivaNova PLC', 'Nasdaq Listed'],
  ['LIXT', 'Lixte Biotechnology Holdings, Inc.', 'Nasdaq Listed'],
  ['LKFN', 'Lakeland Financial Corporation', 'Nasdaq Listed'],
  ['LKFT', 'Lakefront Biotherapeutics', 'Nasdaq Listed'],
  ['LKQ', 'LKQ Corporation', 'Nasdaq Listed'],
  ['LKSP', 'Lake Superior Acquisition Corp.', 'Nasdaq Listed'],
  ['LLYVA', 'Liberty Live Holdings, Inc. - Series A Liberty Live Group Common Stock', 'Nasdaq Listed'],
  ['LLYVK', 'Liberty Live Holdings, Inc. - Series C Liberty Live Group Common Stock', 'Nasdaq Listed'],
  ['LMAT', 'LeMaitre Vascular, Inc.', 'Nasdaq Listed'],
  ['LMB', 'Limbach Holdings, Inc.', 'Nasdaq Listed'],
  ['LMFA', 'LM Funding America, Inc.', 'Nasdaq Listed'],
  ['LMNR', 'Limoneira Co', 'Nasdaq Listed'],
  ['LMRI', 'Lumexa Imaging Holdings, Inc.', 'Nasdaq Listed'],
  ['LNAI', 'Lunai Bioworks Inc.', 'Nasdaq Listed'],
  ['LNKS', 'Linkers Industries Limited', 'Nasdaq Listed'],
  ['LNSR', 'LENSAR, Inc.', 'Nasdaq Listed'],
  ['LNTH', 'Lantheus Holdings, Inc.', 'Nasdaq Listed'],
  ['LNZA', 'LanzaTech Global, Inc.', 'Nasdaq Listed'],
  ['LOAN', 'Manhattan Bridge Capital, Inc', 'Nasdaq Listed'],
  ['LOBO', 'LOBO TECHNOLOGIES LTD.', 'Nasdaq Listed'],
  ['LOCO', 'El Pollo Loco Holdings, Inc.', 'Nasdaq Listed'],
  ['LOKV', 'Live Oak Acquisition Corp. V', 'Nasdaq Listed'],
  ['LONA', 'LeonaBio, Inc.', 'Nasdaq Listed'],
  ['LOOP', 'Loop Industries, Inc.', 'Nasdaq Listed'],
  ['LOPE', 'Grand Canyon Education, Inc.', 'Nasdaq Listed'],
  ['LOT', 'Lotus Technology Inc.', 'Nasdaq Listed'],
  ['LOVE', 'The Lovesac Company', 'Nasdaq Listed'],
  ['LPAA', 'Launch One Acquisition Corp.', 'Nasdaq Listed'],
  ['LPBB', 'Launch Two Acquisition Corp.', 'Nasdaq Listed'],
  ['LPCN', 'Lipocine Inc.', 'Nasdaq Listed'],
  ['LPCV', 'Launchpad Cadenza Acquisition Corp I', 'Nasdaq Listed'],
  ['LPLA', 'LPL Financial Holdings Inc.', 'Nasdaq Listed'],
  ['LPRO', 'Open Lending Corporation', 'Nasdaq Listed'],
  ['LPSN', 'LivePerson, Inc.', 'Nasdaq Listed'],
  ['LPTH', 'LightPath Technologies, Inc.', 'Nasdaq Listed'],
  ['LQDA', 'Liquidia Corporation', 'Nasdaq Listed'],
  ['LQDT', 'Liquidity Services, Inc.', 'Nasdaq Listed'],
  ['LRE', 'Lead Real Estate Co., Ltd', 'Nasdaq Listed'],
  ['LRHC', 'La Rosa Holdings Corp.', 'Nasdaq Listed'],
  ['LRMR', 'Larimar Therapeutics, Inc.', 'Nasdaq Listed'],
  ['LSAK', 'Lesaka Technologies, Inc.', 'Nasdaq Listed'],
  ['LSBK', 'Lake Shore Bancorp, Inc.', 'Nasdaq Listed'],
  ['LSCC', 'Lattice Semiconductor Corporation', 'Nasdaq Listed'],
  ['LSE', 'Leishen Energy Holding Co., Ltd.', 'Nasdaq Listed'],
  ['LSH', 'Lakeside Holding Limited', 'Nasdaq Listed'],
  ['LSTA', 'Lisata Therapeutics, Inc.', 'Nasdaq Listed'],
  ['LSTR', 'Landstar System, Inc.', 'Nasdaq Listed'],
  ['LTBR', 'Lightbridge Corporation', 'Nasdaq Listed'],
  ['LTRN', 'Lantern Pharma Inc.', 'Nasdaq Listed'],
  ['LTRX', 'Lantronix, Inc.', 'Nasdaq Listed'],
  ['LUCD', 'Lucid Diagnostics Inc.', 'Nasdaq Listed'],
  ['LUCY', 'Innovative Eyewear, Inc.', 'Nasdaq Listed'],
  ['LUNG', 'Pulmonx Corporation', 'Nasdaq Listed'],
  ['LUNR', 'Intuitive Machines, Inc.', 'Nasdaq Listed'],
  ['LVLU', 'Lulu\'s Fashion Lounge Holdings, Inc.', 'Nasdaq Listed'],
  ['LVO', 'LiveOne, Inc.', 'Nasdaq Listed'],
  ['LWAC', 'LightWave Acquisition Corp.', 'Nasdaq Listed'],
  ['LWAY', 'Lifeway Foods, Inc.', 'Nasdaq Listed'],
  ['LWLG', 'Lightwave Logic, Inc.', 'Nasdaq Listed'],
  ['LX', 'LexinFintech Holdings Ltd.', 'Nasdaq Listed'],
  ['LXEH', 'Lixiang Education Holding Co., Ltd.', 'Nasdaq Listed'],
  ['LXEO', 'Lexeo Therapeutics, Inc.', 'Nasdaq Listed'],
  ['LXRX', 'Lexicon Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['LYEL', 'Lyell Immunopharma, Inc.', 'Nasdaq Listed'],
  ['LYFT', 'Lyft, Inc.', 'Nasdaq Listed'],
  ['LYTS', 'LSI Industries Inc.', 'Nasdaq Listed'],
  ['LZ', 'LegalZoom.com, Inc.', 'Nasdaq Listed'],
  ['LZMH', 'LZ Technology Holdings Limited', 'Nasdaq Listed'],
  ['MAAS', 'Maase Inc.', 'Nasdaq Listed'],
  ['MACI', 'Melar Acquisition Corp. I', 'Nasdaq Listed'],
  ['MAGH', 'Magnitude International Ltd', 'Nasdaq Listed'],
  ['MAKO', 'Mako Mining Corp', 'Nasdaq Listed'],
  ['MAMA', 'Mama\'s Creations, Inc.', 'Nasdaq Listed'],
  ['MAMK', 'MaxsMaking Inc.', 'Nasdaq Listed'],
  ['MAMO', 'Massimo Group', 'Nasdaq Listed'],
  ['MANH', 'Manhattan Associates, Inc.', 'Nasdaq Listed'],
  ['MARA', 'MARA Holdings, Inc.', 'Nasdaq Listed'],
  ['MASI', 'Masimo Corporation', 'Nasdaq Listed'],
  ['MASK', '3 E Network Technology Group Ltd', 'Nasdaq Listed'],
  ['MASS', '908 Devices Inc.', 'Nasdaq Listed'],
  ['MAT', 'Mattel, Inc.', 'Nasdaq Listed'],
  ['MATH', 'Metalpha Technology Holding Limited', 'Nasdaq Listed'],
  ['MATW', 'Matthews International Corporation', 'Nasdaq Listed'],
  ['MAYS', 'J. W. Mays, Inc.', 'Nasdaq Listed'],
  ['MAZE', 'Maze Therapeutics, Inc.', 'Nasdaq Listed'],
  ['MB', 'MasterBeef Group', 'Nasdaq Listed'],
  ['MBAI', 'Check-Cap Ltd. - Ordinary Share', 'Nasdaq Listed'],
  ['MBAV', 'M3-Brigade Acquisition V Corp.', 'Nasdaq Listed'],
  ['MBBC', 'Marathon Bancorp, Inc.', 'Nasdaq Listed'],
  ['MBIN', 'Merchants Bancorp', 'Nasdaq Listed'],
  ['MBIO', 'Mustang Bio, Inc.', 'Nasdaq Listed'],
  ['MBLY', 'Mobileye Global Inc.', 'Nasdaq Listed'],
  ['MBOT', 'Microbot Medical Inc.', 'Nasdaq Listed'],
  ['MBRX', 'Moleculin Biotech, Inc.', 'Nasdaq Listed'],
  ['MBUU', 'Malibu Boats, Inc.', 'Nasdaq Listed'],
  ['MBVI', 'M3-Brigade Acquisition VI Corp.', 'Nasdaq Listed'],
  ['MBWM', 'Mercantile Bank Corporation', 'Nasdaq Listed'],
  ['MBX', 'MBX Biosciences, Inc.', 'Nasdaq Listed'],
  ['MCBS', 'MetroCity Bankshares, Inc.', 'Nasdaq Listed'],
  ['MCFT', 'MasterCraft Boat Holdings, Inc.', 'Nasdaq Listed'],
  ['MCGA', 'Yorkville Acquisition Corp.', 'Nasdaq Listed'],
  ['MCHB', 'Mechanics Bancorp', 'Nasdaq Listed'],
  ['MCHX', 'Marchex, Inc.', 'Nasdaq Listed'],
  ['MCRB', 'Seres Therapeutics, Inc.', 'Nasdaq Listed'],
  ['MCRI', 'Monarch Casino & Resort, Inc.', 'Nasdaq Listed'],
  ['MCTA', 'Charming Medical Limited', 'Nasdaq Listed'],
  ['MDAI', 'Spectral AI, Inc.', 'Nasdaq Listed'],
  ['MDB', 'MongoDB, Inc.', 'Nasdaq Listed'],
  ['MDBH', 'MDB Capital Holdings, LLC - Class A common', 'Nasdaq Listed'],
  ['MDCX', 'Medicus Pharma Ltd.', 'Nasdaq Listed'],
  ['MDGL', 'Madrigal Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['MDIA', 'Mediaco Holding Inc.', 'Nasdaq Listed'],
  ['MDLN', 'Medline Inc.', 'Nasdaq Listed'],
  ['MDRR', 'Medalist Diversified, Inc.', 'Nasdaq Listed'],
  ['MDWD', 'MediWound Ltd.', 'Nasdaq Listed'],
  ['MDXG', 'MiMedx Group, Inc', 'Nasdaq Listed'],
  ['MDXH', 'MDxHealth SA', 'Nasdaq Listed'],
  ['MEDP', 'Medpace Holdings, Inc.', 'Nasdaq Listed'],
  ['MEGL', 'Magic Empire Global Limited', 'Nasdaq Listed'],
  ['MEHA', 'Functional Brands, Inc.', 'Nasdaq Listed'],
  ['MENS', 'Jyong Biotech Ltd.', 'Nasdaq Listed'],
  ['MEOH', 'Methanex Corporation', 'Nasdaq Listed'],
  ['MERC', 'Mercer International Inc.', 'Nasdaq Listed'],
  ['MESH', 'Meshflow Acquisition Corp.', 'Nasdaq Listed'],
  ['MESO', 'Mesoblast Limited', 'Nasdaq Listed'],
  ['METC', 'Ramaco Resources, Inc.', 'Nasdaq Listed'],
  ['METCB', 'Ramaco Resources, Inc.', 'Nasdaq Listed'],
  ['MEVO', 'M Evo Global Acquisition Corp II', 'Nasdaq Listed'],
  ['MFI', 'mF International Limited', 'Nasdaq Listed'],
  ['MFIN', 'Medallion Financial Corp.', 'Nasdaq Listed'],
  ['MGEE', 'MGE Energy Inc.', 'Nasdaq Listed'],
  ['MGIH', 'Millennium Group International Holdings Limited', 'Nasdaq Listed'],
  ['MGN', 'Megan Holdings Limited', 'Nasdaq Listed'],
  ['MGNI', 'Magnite, Inc.', 'Nasdaq Listed'],
  ['MGNX', 'MacroGenics, Inc.', 'Nasdaq Listed'],
  ['MGPI', 'MGP Ingredients, Inc.', 'Nasdaq Listed'],
  ['MGRC', 'McGrath RentCorp', 'Nasdaq Listed'],
  ['MGRT', 'Mega Fortune Company Limited', 'Nasdaq Listed'],
  ['MGRX', 'Mangoceuticals, Inc.', 'Nasdaq Listed'],
  ['MGTX', 'MeiraGTx Holdings plc', 'Nasdaq Listed'],
  ['MGX', 'Metagenomi Therapeutics, Inc.', 'Nasdaq Listed'],
  ['MGYR', 'Magyar Bancorp, Inc.', 'Nasdaq Listed'],
  ['MIDD', 'The Middleby Corporation', 'Nasdaq Listed'],
  ['MIMI', 'Mint Incorporation Limited', 'Nasdaq Listed'],
  ['MIND', 'MIND Technology, Inc.', 'Nasdaq Listed'],
  ['MIRA', 'MIRA Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['MIRM', 'Mirum Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['MIST', 'Milestone Pharmaceuticals Inc.', 'Nasdaq Listed'],
  ['MITK', 'Mitek Systems, Inc.', 'Nasdaq Listed'],
  ['MKDW', 'MKDWELL Tech Inc.', 'Nasdaq Listed'],
  ['MKLY', 'McKinley Acquisition Corporation', 'Nasdaq Listed'],
  ['MKSI', 'MKS Inc.', 'Nasdaq Listed'],
  ['MKTW', 'MarketWise, Inc.', 'Nasdaq Listed'],
  ['MKTX', 'MarketAxess Holdings, Inc.', 'Nasdaq Listed'],
  ['MKZR', 'MacKenzie Realty Capital, Inc.', 'Nasdaq Listed'],
  ['MLAA', 'Mountain Lake Acquisition Corp. II', 'Nasdaq Listed'],
  ['MLAB', 'Mesa Laboratories, Inc.', 'Nasdaq Listed'],
  ['MLAC', 'Mountain Lake Acquisition Corp.', 'Nasdaq Listed'],
  ['MLCI', 'Mount Logan Capital Inc.', 'Nasdaq Listed'],
  ['MLCO', 'Melco Resorts & Entertainment Limited', 'Nasdaq Listed'],
  ['MLEC', 'Moolec Science SA', 'Nasdaq Listed'],
  ['MLGO', 'MicroAlgo, Inc.', 'Nasdaq Listed'],
  ['MLKN', 'MillerKnoll, Inc.', 'Nasdaq Listed'],
  ['MLTX', 'MoonLake Immunotherapeutics', 'Nasdaq Listed'],
  ['MLYS', 'Mineralys Therapeutics, Inc.', 'Nasdaq Listed'],
  ['MMED', 'MiniMed Group, Inc.', 'Nasdaq Listed'],
  ['MMSI', 'Merit Medical Systems, Inc.', 'Nasdaq Listed'],
  ['MMTX', 'Miluna Acquisition Corp', 'Nasdaq Listed'],
  ['MMYT', 'MakeMyTrip Limited', 'Nasdaq Listed'],
  ['MNDO', 'MIND C.T.I. Ltd.', 'Nasdaq Listed'],
  ['MNDR', 'Mobile-health Network Solutions', 'Nasdaq Listed'],
  ['MNDY', 'monday.com Ltd.', 'Nasdaq Listed'],
  ['MNKD', 'MannKind Corporation', 'Nasdaq Listed'],
  ['MNOV', 'MediciNova, Inc.', 'Nasdaq Listed'],
  ['MNPR', 'Monopar Therapeutics Inc.', 'Nasdaq Listed'],
  ['MNRO', 'Monro, Inc.', 'Nasdaq Listed'],
  ['MNSB', 'MainStreet Bancshares, Inc.', 'Nasdaq Listed'],
  ['MNTK', 'Montauk Renewables, Inc.', 'Nasdaq Listed'],
  ['MNTS', 'Momentus Inc.', 'Nasdaq Listed'],
  ['MNY', 'MoneyHero Limited', 'Nasdaq Listed'],
  ['MOB', 'Mobilicom Limited', 'Nasdaq Listed'],
  ['MOBI', 'Mobia Medical, Inc.', 'Nasdaq Listed'],
  ['MOBX', 'Mobix Labs, Inc.', 'Nasdaq Listed'],
  ['MODD', 'Modular Medical, Inc.', 'Nasdaq Listed'],
  ['MOLN', 'Molecular Partners AG', 'Nasdaq Listed'],
  ['MOMO', 'Hello Group Inc.', 'Nasdaq Listed'],
  ['MORN', 'Morningstar, Inc.', 'Nasdaq Listed'],
  ['MOVE', 'Corvex, Inc.', 'Nasdaq Listed'],
  ['MPAA', 'Motorcar Parts of America, Inc.', 'Nasdaq Listed'],
  ['MPB', 'Mid Penn Bancorp', 'Nasdaq Listed'],
  ['MPLT', 'MapLight Therapeutics, Inc.', 'Nasdaq Listed'],
  ['MQ', 'Marqeta, Inc.', 'Nasdaq Listed'],
  ['MRAM', 'Everspin Technologies, Inc.', 'Nasdaq Listed'],
  ['MRBK', 'Meridian Corporation', 'Nasdaq Listed'],
  ['MRCY', 'Mercury Systems Inc', 'Nasdaq Listed'],
  ['MRDN', 'Meridian Holdings Inc.', 'Nasdaq Listed'],
  ['MREO', 'Mereo BioPharma Group plc', 'Nasdaq Listed'],
  ['MRKR', 'Marker Therapeutics, Inc.', 'Nasdaq Listed'],
  ['MRLN', 'Merlin, Inc.', 'Nasdaq Listed'],
  ['MRM', 'MEDIROM Healthcare Technologies Inc.', 'Nasdaq Listed'],
  ['MRNO', 'Murano Global Investments PLC', 'Nasdaq Listed'],
  ['MRTN', 'Marten Transport, Ltd.', 'Nasdaq Listed'],
  ['MRVI', 'Maravai LifeSciences Holdings, Inc.', 'Nasdaq Listed'],
  ['MRX', 'Marex Group plc', 'Nasdaq Listed'],
  ['MSAI', 'MultiSensor AI Holdings, Inc.', 'Nasdaq Listed'],
  ['MSBI', 'Midland States Bancorp, Inc.', 'Nasdaq Listed'],
  ['MSEX', 'Middlesex Water Company', 'Nasdaq Listed'],
  ['MSGM', 'Motorsport Games Inc.', 'Nasdaq Listed'],
  ['MSGY', 'Masonglory Limited', 'Nasdaq Listed'],
  ['MSLE', 'Satellos Bioscience Inc.', 'Nasdaq Listed'],
  ['MSS', 'Maison Solutions Inc.', 'Nasdaq Listed'],
  ['MSW', 'Ming Shing Group Holdings Limited', 'Nasdaq Listed'],
  ['MTC', 'MMTec, Inc.', 'Nasdaq Listed'],
  ['MTCH', 'Match Group, Inc.', 'Nasdaq Listed'],
  ['MTEK', 'Maris-Tech Ltd.', 'Nasdaq Listed'],
  ['MTEN', 'Mingteng International Corporation Inc.', 'Nasdaq Listed'],
  ['MTEX', 'Mannatech, Incorporated', 'Nasdaq Listed'],
  ['MTLS', 'Materialise NV', 'Nasdaq Listed'],
  ['MTRX', 'Matrix Service Company', 'Nasdaq Listed'],
  ['MTSI', 'MACOM Technology Solutions Holdings, Inc.', 'Nasdaq Listed'],
  ['MTVA', 'MetaVia Inc.', 'Nasdaq Listed'],
  ['MUZE', 'Muzero Acquisition Corp', 'Nasdaq Listed'],
  ['MVBF', 'MVB Financial Corp.', 'Nasdaq Listed'],
  ['MVIS', 'MicroVision, Inc.', 'Nasdaq Listed'],
  ['MVST', 'Microvast Holdings, Inc.', 'Nasdaq Listed'],
  ['MWC', 'Micware Co., Ltd.', 'Nasdaq Listed'],
  ['MWH', 'SOLV Energy, Inc.', 'Nasdaq Listed'],
  ['MWYN', 'Marwynn Holdings, Inc.', 'Nasdaq Listed'],
  ['MXCT', 'MaxCyte, Inc.', 'Nasdaq Listed'],
  ['MXL', 'MaxLinear, Inc', 'Nasdaq Listed'],
  ['MYFW', 'First Western Financial, Inc.', 'Nasdaq Listed'],
  ['MYGN', 'Myriad Genetics, Inc.', 'Nasdaq Listed'],
  ['MYPS', 'PLAYSTUDIOS, Inc.', 'Nasdaq Listed'],
  ['MYRG', 'MYR Group, Inc.', 'Nasdaq Listed'],
  ['MYSE', 'Myseum.AI, Inc.', 'Nasdaq Listed'],
  ['MYSZ', 'My Size, Inc.', 'Nasdaq Listed'],
  ['MYX', 'Maywood Acquisition Corp. 2', 'Nasdaq Listed'],
  ['MZTI', 'The Marzetti Company', 'Nasdaq Listed'],
  ['NA', 'Nano Labs Ltd', 'Nasdaq Listed'],
  ['NAAS', 'NaaS Technology Inc.', 'Nasdaq Listed'],
  ['NAGE', 'Niagen Bioscience, Inc.', 'Nasdaq Listed'],
  ['NAII', 'Natural Alternatives International, Inc.', 'Nasdaq Listed'],
  ['NAKA', 'Nakamoto Inc.', 'Nasdaq Listed'],
  ['NAMI', 'Jinxin Technology Holding Company', 'Nasdaq Listed'],
  ['NAMM', 'Namib Minerals', 'Nasdaq Listed'],
  ['NAMS', 'NewAmsterdam Pharma Company N.V.', 'Nasdaq Listed'],
  ['NATH', 'Nathan\'s Famous, Inc.', 'Nasdaq Listed'],
  ['NATR', 'Nature\'s Sunshine Products, Inc.', 'Nasdaq Listed'],
  ['NAUT', 'Nautilus Biotechnology, Inc.', 'Nasdaq Listed'],
  ['NAVI', 'Navient Corporation', 'Nasdaq Listed'],
  ['NAVN', 'Navan, Inc.', 'Nasdaq Listed'],
  ['NB', 'NioCorp Developments Ltd.', 'Nasdaq Listed'],
  ['NBBK', 'NB Bancorp, Inc.', 'Nasdaq Listed'],
  ['NBIS', 'Nebius Group N.V.', 'Nasdaq Listed'],
  ['NBIX', 'Neurocrine Biosciences, Inc.', 'Nasdaq Listed'],
  ['NBN', 'Northeast Bank', 'Nasdaq Listed'],
  ['NBP', 'NovaBridge Biosciences', 'Nasdaq Listed'],
  ['NBRG', 'Newbridge Acquisition Limited', 'Nasdaq Listed'],
  ['NBTB', 'NBT Bancorp Inc.', 'Nasdaq Listed'],
  ['NBTX', 'Nanobiotix S.A.', 'Nasdaq Listed'],
  ['NCEL', 'NewcelX Ltd.', 'Nasdaq Listed'],
  ['NCEW', 'New Century Logistics (BVI) Limited', 'Nasdaq Listed'],
  ['NCI', 'Neo-Concept International Group Holdings Limited', 'Nasdaq Listed'],
  ['NCMI', 'National CineMedia, Inc.', 'Nasdaq Listed'],
  ['NCNA', 'NuCana plc', 'Nasdaq Listed'],
  ['NCNO', 'nCino, Inc.', 'Nasdaq Listed'],
  ['NCPL', 'Netcapital Inc.', 'Nasdaq Listed'],
  ['NCRA', 'Nocera, Inc.', 'Nasdaq Listed'],
  ['NCSM', 'NCS Multistage Holdings, Inc.', 'Nasdaq Listed'],
  ['NCT', 'Intercont (Cayman) Limited', 'Nasdaq Listed'],
  ['NDLS', 'Noodles & Company', 'Nasdaq Listed'],
  ['NDRA', 'ENDRA Life Sciences Inc.', 'Nasdaq Listed'],
  ['NECB', 'NorthEast Community Bancorp, Inc.', 'Nasdaq Listed'],
  ['NEGG', 'Newegg Commerce, Inc.', 'Nasdaq Listed'],
  ['NEO', 'NeoGenomics, Inc.', 'Nasdaq Listed'],
  ['NEOG', 'Neogen Corporation', 'Nasdaq Listed'],
  ['NEON', 'Neonode Inc.', 'Nasdaq Listed'],
  ['NEOV', 'NeoVolta Inc.', 'Nasdaq Listed'],
  ['NEPH', 'Nephros, Inc.', 'Nasdaq Listed'],
  ['NERV', 'Minerva Neurosciences, Inc', 'Nasdaq Listed'],
  ['NESR', 'National Energy Services Reunited Corp', 'Nasdaq Listed'],
  ['NEUP', 'Neuphoria Therapeutics Inc.', 'Nasdaq Listed'],
  ['NEWT', 'NewtekOne, Inc.', 'Nasdaq Listed'],
  ['NEXM', 'NexMetals Mining Corp.', 'Nasdaq Listed'],
  ['NEXN', 'Nexxen International Ltd.', 'Nasdaq Listed'],
  ['NEXR', 'Nexera Technologies Ltd', 'Nasdaq Listed'],
  ['NEXT', 'NextDecade Corporation', 'Nasdaq Listed'],
  ['NFBK', 'Northfield Bancorp, Inc.', 'Nasdaq Listed'],
  ['NFE', 'New Fortress Energy Inc.', 'Nasdaq Listed'],
  ['NGEN', 'NervGen Pharma Corp.', 'Nasdaq Listed'],
  ['NGNE', 'Neurogene Inc.', 'Nasdaq Listed'],
  ['NHIC', 'NewHold Investment Corp III', 'Nasdaq Listed'],
  ['NHP', 'National Healthcare Properties, Inc.', 'Nasdaq Listed'],
  ['NHTC', 'Natural Health Trends Corp.', 'Nasdaq Listed'],
  ['NICE', 'NICE Ltd', 'Nasdaq Listed'],
  ['NICM', 'Nicola Mining Inc.', 'Nasdaq Listed'],
  ['NIPG', 'NIP Group Inc.', 'Nasdaq Listed'],
  ['NIU', 'Niu Technologies', 'Nasdaq Listed'],
  ['NIVF', 'NewGenIvf Group Limited', 'Nasdaq Listed'],
  ['NIXX', 'Nixxy, Inc.', 'Nasdaq Listed'],
  ['NKLR', 'Terra Innovatum Global N.V.', 'Nasdaq Listed'],
  ['NKSH', 'National Bankshares, Inc.', 'Nasdaq Listed'],
  ['NKTR', 'Nektar Therapeutics', 'Nasdaq Listed'],
  ['NKTX', 'Nkarta, Inc.', 'Nasdaq Listed'],
  ['NMFC', 'New Mountain Finance Corporation', 'Nasdaq Listed'],
  ['NMIH', 'NMI Holdings Inc', 'Nasdaq Listed'],
  ['NMP', 'NMP Acquisition Corp.', 'Nasdaq Listed'],
  ['NMRA', 'Neumora Therapeutics, Inc.', 'Nasdaq Listed'],
  ['NMRK', 'Newmark Group, Inc.', 'Nasdaq Listed'],
  ['NMTC', 'NeuroOne Medical Technologies Corporation', 'Nasdaq Listed'],
  ['NN', 'NextNav Inc.', 'Nasdaq Listed'],
  ['NNBR', 'NN, Inc.', 'Nasdaq Listed'],
  ['NNDM', 'Nano Dimension Ltd.', 'Nasdaq Listed'],
  ['NNNN', 'Anbio Biotechnology', 'Nasdaq Listed'],
  ['NNOX', 'NANO-X IMAGING LTD', 'Nasdaq Listed'],
  ['NODK', 'NI Holdings, Inc.', 'Nasdaq Listed'],
  ['NOEM', 'CO2 Energy Transition Corp.', 'Nasdaq Listed'],
  ['NOMA', 'NOMADAR Corp.', 'Nasdaq Listed'],
  ['NOTV', 'Inotiv, Inc.', 'Nasdaq Listed'],
  ['NOVT', 'Novanta Inc.', 'Nasdaq Listed'],
  ['NPAC', 'New Providence Acquisition Corp. III', 'Nasdaq Listed'],
  ['NPCE', 'Neuropace, Inc.', 'Nasdaq Listed'],
  ['NPT', 'Texxon Holding Limited', 'Nasdaq Listed'],
  ['NRC', 'NRC Health', 'Nasdaq Listed'],
  ['NRDS', 'NerdWallet, Inc.', 'Nasdaq Listed'],
  ['NRIM', 'Northrim BanCorp Inc', 'Nasdaq Listed'],
  ['NRIX', 'Nurix Therapeutics, Inc.', 'Nasdaq Listed'],
  ['NRSN', 'NeuroSense Therapeutics Ltd.', 'Nasdaq Listed'],
  ['NRXP', 'NRX Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['NSIT', 'Insight Enterprises, Inc.', 'Nasdaq Listed'],
  ['NSPR', 'InspireMD Inc.', 'Nasdaq Listed'],
  ['NSSC', 'NAPCO Security Technologies, Inc.', 'Nasdaq Listed'],
  ['NSTS', 'NSTS Bancorp, Inc.', 'Nasdaq Listed'],
  ['NSYS', 'Nortech Systems Incorporated', 'Nasdaq Listed'],
  ['NTCL', 'NETCLASS TECHNOLOGY INC', 'Nasdaq Listed'],
  ['NTCT', 'NetScout Systems, Inc.', 'Nasdaq Listed'],
  ['NTES', 'NetEase, Inc.', 'Nasdaq Listed'],
  ['NTGR', 'NETGEAR, Inc.', 'Nasdaq Listed'],
  ['NTHI', 'NeOnc Technologies Holdings, Inc.', 'Nasdaq Listed'],
  ['NTIC', 'Northern Technologies International Corporation', 'Nasdaq Listed'],
  ['NTLA', 'Intellia Therapeutics, Inc.', 'Nasdaq Listed'],
  ['NTNX', 'Nutanix, Inc.', 'Nasdaq Listed'],
  ['NTRA', 'Natera, Inc.', 'Nasdaq Listed'],
  ['NTRB', 'Nutriband Inc.', 'Nasdaq Listed'],
  ['NTRP', 'NextTrip, Inc.', 'Nasdaq Listed'],
  ['NTSK', 'Netskope, Inc.', 'Nasdaq Listed'],
  ['NTWK', 'NETSOL Technologies Inc.', 'Nasdaq Listed'],
  ['NTWO', 'Newbury Street II Acquisition Corp', 'Nasdaq Listed'],
  ['NUAI', 'New Era Energy & Digital, Inc.', 'Nasdaq Listed'],
  ['NUCL', 'Eagle Nuclear Energy Corp.', 'Nasdaq Listed'],
  ['NUTR', 'Nusatrip Incorporated', 'Nasdaq Listed'],
  ['NUTX', 'Nutex Health Inc.', 'Nasdaq Listed'],
  ['NUVL', 'Nuvalent, Inc.', 'Nasdaq Listed'],
  ['NUWE', 'Nuwellis, Inc.', 'Nasdaq Listed'],
  ['NVA', 'Nova Minerals Limited', 'Nasdaq Listed'],
  ['NVAX', 'Novavax, Inc.', 'Nasdaq Listed'],
  ['NVCR', 'NovoCure Limited', 'Nasdaq Listed'],
  ['NVCT', 'Nuvectis Pharma, Inc.', 'Nasdaq Listed'],
  ['NVEC', 'NVE Corporation', 'Nasdaq Listed'],
  ['NVMI', 'Nova Ltd.', 'Nasdaq Listed'],
  ['NVNI', 'Nvni Group Limited', 'Nasdaq Listed'],
  ['NVNO', 'enVVeno Medical Corporation', 'Nasdaq Listed'],
  ['NVTS', 'Navitas Semiconductor Corporation', 'Nasdaq Listed'],
  ['NVVE', 'Nuvve Holding Corp.', 'Nasdaq Listed'],
  ['NWBI', 'Northwest Bancshares, Inc.', 'Nasdaq Listed'],
  ['NWE', 'NorthWestern Energy Group, Inc.', 'Nasdaq Listed'],
  ['NWFL', 'Norwood Financial Corp.', 'Nasdaq Listed'],
  ['NWGL', 'CL Workshop Group Limited', 'Nasdaq Listed'],
  ['NWL', 'Newell Brands Inc.', 'Nasdaq Listed'],
  ['NWPX', 'NWPX Infrastructure, Inc.', 'Nasdaq Listed'],
  ['NWTG', 'Newton Golf Company, Inc.', 'Nasdaq Listed'],
  ['NXGL', 'NexGel, Inc', 'Nasdaq Listed'],
  ['NXL', 'Nexalin Technology, Inc.', 'Nasdaq Listed'],
  ['NXPL', 'NextPlat Corp', 'Nasdaq Listed'],
  ['NXST', 'Nexstar Media Group, Inc.', 'Nasdaq Listed'],
  ['NXT', 'Nextpower Inc.', 'Nasdaq Listed'],
  ['NXTC', 'NextCure, Inc.', 'Nasdaq Listed'],
  ['NXTS', 'Nexentis Technologies Inc.', 'Nasdaq Listed'],
  ['NXTT', 'Next Technology Holding Inc.', 'Nasdaq Listed'],
  ['NXXT', 'NextNRG, Inc.', 'Nasdaq Listed'],
  ['NYAX', 'Nayax Ltd.', 'Nasdaq Listed'],
  ['NYXH', 'Nyxoah SA', 'Nasdaq Listed'],
  ['OABI', 'OmniAb, Inc.', 'Nasdaq Listed'],
  ['OACC', 'Oaktree Acquisition Corp. III Life Sciences', 'Nasdaq Listed'],
  ['OBA', 'Oxley Bridge Acquisition Limited', 'Nasdaq Listed'],
  ['OBIO', 'Orchestra BioMed Holdings, Inc.', 'Nasdaq Listed'],
  ['OBT', 'Orange County Bancorp, Inc.', 'Nasdaq Listed'],
  ['OCC', 'Optical Cable Corporation', 'Nasdaq Listed'],
  ['OCFC', 'OceanFirst Financial Corp.', 'Nasdaq Listed'],
  ['OCG', 'Oriental Culture Holding LTD', 'Nasdaq Listed'],
  ['OCGN', 'Ocugen, Inc.', 'Nasdaq Listed'],
  ['OCS', 'Oculis Holding AG', 'Nasdaq Listed'],
  ['OCTV', 'Octave Intelligence plc', 'Nasdaq Listed'],
  ['OCUL', 'Ocular Therapeutix, Inc.', 'Nasdaq Listed'],
  ['ODD', 'ODDITY Tech Ltd.', 'Nasdaq Listed'],
  ['ODTX', 'Odyssey Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ODYS', 'Odysight.ai Inc.', 'Nasdaq Listed'],
  ['OESX', 'Orion Energy Systems, Inc.', 'Nasdaq Listed'],
  ['OFAL', 'OFA Group', 'Nasdaq Listed'],
  ['OFIX', 'Orthofix Medical Inc.', 'Nasdaq Listed'],
  ['OFLX', 'Omega Flex, Inc.', 'Nasdaq Listed'],
  ['OGI', 'Organigram Global Inc.', 'Nasdaq Listed'],
  ['OIM', 'OneIM Acquisition Corp.', 'Nasdaq Listed'],
  ['OIO', 'OIO Group', 'Nasdaq Listed'],
  ['OKTA', 'Okta, Inc.', 'Nasdaq Listed'],
  ['OKUR', 'OnKure Therapeutics, Inc.', 'Nasdaq Listed'],
  ['OKYO', 'OKYO Pharma Limited', 'Nasdaq Listed'],
  ['OLB', 'The OLB Group, Inc.', 'Nasdaq Listed'],
  ['OLED', 'Universal Display Corporation', 'Nasdaq Listed'],
  ['OLLI', 'Ollie\'s Bargain Outlet Holdings, Inc.', 'Nasdaq Listed'],
  ['OLMA', 'Olema Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['OLOX', 'Olenox Industries Inc.', 'Nasdaq Listed'],
  ['OLPX', 'Olaplex Holdings, Inc.', 'Nasdaq Listed'],
  ['OM', 'Outset Medical, Inc.', 'Nasdaq Listed'],
  ['OMAB', 'Grupo Aeroportuario del Centro Norte S.A.B. de C.V.', 'Nasdaq Listed'],
  ['OMCL', 'Omnicell, Inc.', 'Nasdaq Listed'],
  ['OMDA', 'Omada Health, Inc.', 'Nasdaq Listed'],
  ['OMER', 'Omeros Corporation', 'Nasdaq Listed'],
  ['OMEX', 'Odyssey Marine Exploration, Inc.', 'Nasdaq Listed'],
  ['OMH', 'Ohmyhome Limited', 'Nasdaq Listed'],
  ['OMSE', 'OMS Energy Technologies Inc.', 'Nasdaq Listed'],
  ['ONB', 'Old National Bancorp', 'Nasdaq Listed'],
  ['ONC', 'BeOne Medicines Ltd.', 'Nasdaq Listed'],
  ['ONCH', '1RT Acquisition Corp.', 'Nasdaq Listed'],
  ['ONCO', 'Onconetix, Inc.', 'Nasdaq Listed'],
  ['ONCY', 'Oncolytics Biotech Inc.', 'Nasdaq Listed'],
  ['ONDS', 'Ondas Inc', 'Nasdaq Listed'],
  ['ONEG', 'OneConstruction Group Limited', 'Nasdaq Listed'],
  ['ONEW', 'OneWater Marine Inc.', 'Nasdaq Listed'],
  ['ONFO', 'Onfolio Holdings Inc.', 'Nasdaq Listed'],
  ['ONMD', 'OneMedNet Corp', 'Nasdaq Listed'],
  ['OPAL', 'OPAL Fuels Inc.', 'Nasdaq Listed'],
  ['OPBK', 'OP Bancorp', 'Nasdaq Listed'],
  ['OPCH', 'Option Care Health, Inc.', 'Nasdaq Listed'],
  ['OPEN', 'Opendoor Technologies Inc', 'Nasdaq Listed'],
  ['OPK', 'Opko Health, Inc.', 'Nasdaq Listed'],
  ['OPRA', 'Opera Limited', 'Nasdaq Listed'],
  ['OPRT', 'Oportun Financial Corporation', 'Nasdaq Listed'],
  ['OPRX', 'OptimizeRx Corporation', 'Nasdaq Listed'],
  ['OPTH', 'Optimi Health Corp.', 'Nasdaq Listed'],
  ['OPTX', 'Syntec Optics Holdings, Inc.', 'Nasdaq Listed'],
  ['OPXS', 'Optex Systems Holdings, Inc.', 'Nasdaq Listed'],
  ['ORBS', 'Eightco Holdings Inc.', 'Nasdaq Listed'],
  ['ORGN', 'Origin Materials, Inc.', 'Nasdaq Listed'],
  ['ORIC', 'Oric Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['ORIO', 'Orion Digital Corp.', 'Nasdaq Listed'],
  ['ORIQ', 'Origin Investment Corp I', 'Nasdaq Listed'],
  ['ORIS', 'Oriental Rise Holdings Limited', 'Nasdaq Listed'],
  ['ORKA', 'Oruka Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ORKT', 'Orangekloud Technology Inc.', 'Nasdaq Listed'],
  ['ORMP', 'Oramed Pharmaceuticals Inc.', 'Nasdaq Listed'],
  ['ORRF', 'Orrstown Financial Services, Inc.', 'Nasdaq Listed'],
  ['OSBC', 'Old Second Bancorp, Inc.', 'Nasdaq Listed'],
  ['OSIS', 'OSI Systems, Inc.', 'Nasdaq Listed'],
  ['OSPN', 'OneSpan Inc.', 'Nasdaq Listed'],
  ['OSRH', 'OSR Holdings, Inc.', 'Nasdaq Listed'],
  ['OSS', 'One Stop Systems, Inc.', 'Nasdaq Listed'],
  ['OST', 'Ostin Technology Group Co., Ltd.', 'Nasdaq Listed'],
  ['OSUR', 'OraSure Technologies, Inc.', 'Nasdaq Listed'],
  ['OSW', 'OneSpaWorld Holdings Limited', 'Nasdaq Listed'],
  ['OTEX', 'Open Text Corporation', 'Nasdaq Listed'],
  ['OTGA', 'OTG Acquisition Corp. I', 'Nasdaq Listed'],
  ['OTLK', 'Outlook Therapeutics, Inc.', 'Nasdaq Listed'],
  ['OTLY', 'Oatly Group AB', 'Nasdaq Listed'],
  ['OTTR', 'Otter Tail Corporation', 'Nasdaq Listed'],
  ['OUST', 'Ouster, Inc.', 'Nasdaq Listed'],
  ['OVBC', 'Ohio Valley Banc Corp.', 'Nasdaq Listed'],
  ['OVID', 'Ovid Therapeutics Inc.', 'Nasdaq Listed'],
  ['OVLY', 'Oak Valley Bancorp (CA)', 'Nasdaq Listed'],
  ['OWLS', 'OBOOK Holdings Inc. - Class A Common Shares', 'Nasdaq Listed'],
  ['OXBR', 'Oxbridge Re Holdings Limited', 'Nasdaq Listed'],
  ['OYSE', 'Oyster Enterprises II Acquisition Corp', 'Nasdaq Listed'],
  ['OZK', 'Bank OZK', 'Nasdaq Listed'],
  ['PAAC', 'Proem Acquisition Corp I', 'Nasdaq Listed'],
  ['PACB', 'Pacific Biosciences of California, Inc.', 'Nasdaq Listed'],
  ['PACH', 'Pioneer Acquisition I Corp', 'Nasdaq Listed'],
  ['PAHC', 'Phibro Animal Health Corporation', 'Nasdaq Listed'],
  ['PAL', 'Proficient Auto Logistics, Inc.', 'Nasdaq Listed'],
  ['PALI', 'Palisade Bio, Inc.', 'Nasdaq Listed'],
  ['PALO', 'Paloma Acquisition Corp I', 'Nasdaq Listed'],
  ['PAMT', 'PAMT CORP', 'Nasdaq Listed'],
  ['PANL', 'Pangaea Logistics Solutions Ltd.', 'Nasdaq Listed'],
  ['PARK', 'Park Dental Partners, Inc.', 'Nasdaq Listed'],
  ['PASG', 'Passage Bio, Inc.', 'Nasdaq Listed'],
  ['PASW', 'Ping An Biomedical Co., Ltd.', 'Nasdaq Listed'],
  ['PATK', 'Patrick Industries, Inc.', 'Nasdaq Listed'],
  ['PAVM', 'PAVmed Inc.', 'Nasdaq Listed'],
  ['PAVS', 'Paranovus Entertainment Technology Ltd.', 'Nasdaq Listed'],
  ['PAX', 'Patria Investments Limited - Class A Common Shares', 'Nasdaq Listed'],
  ['PAYO', 'Payoneer Global Inc.', 'Nasdaq Listed'],
  ['PAYS', 'Paysign, Inc.', 'Nasdaq Listed'],
  ['PBFS', 'Pioneer Bancorp, Inc.', 'Nasdaq Listed'],
  ['PBHC', 'Pathfinder Bancorp, Inc.', 'Nasdaq Listed'],
  ['PBM', 'Psyence Biomedical Ltd.', 'Nasdaq Listed'],
  ['PBYI', 'Puma Biotechnology Inc', 'Nasdaq Listed'],
  ['PC', 'Premium Catering (Holdings) Limited', 'Nasdaq Listed'],
  ['PCAP', 'ProCap Acquisition Corp', 'Nasdaq Listed'],
  ['PCB', 'PCB Bancorp', 'Nasdaq Listed'],
  ['PCLA', 'PicoCELA Inc.', 'Nasdaq Listed'],
  ['PCRX', 'Pacira BioSciences, Inc.', 'Nasdaq Listed'],
  ['PCSA', 'Processa Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['PCSC', 'Perceptive Capital Solutions Corp', 'Nasdaq Listed'],
  ['PCT', 'PureCycle Technologies, Inc.', 'Nasdaq Listed'],
  ['PCTY', 'Paylocity Holding Corporation', 'Nasdaq Listed'],
  ['PCVX', 'Vaxcyte, Inc.', 'Nasdaq Listed'],
  ['PCYO', 'Pure Cycle Corporation', 'Nasdaq Listed'],
  ['PDC', 'Perpetuals.com Ltd', 'Nasdaq Listed'],
  ['PDEX', 'Pro-Dex, Inc.', 'Nasdaq Listed'],
  ['PDFS', 'PDF Solutions, Inc.', 'Nasdaq Listed'],
  ['PDLB', 'Ponce Financial Group, Inc.', 'Nasdaq Listed'],
  ['PDSB', 'PDS Biotechnology Corporation', 'Nasdaq Listed'],
  ['PDYN', 'Palladyne AI Corp.', 'Nasdaq Listed'],
  ['PEBK', 'Peoples Bancorp of North Carolina, Inc.', 'Nasdaq Listed'],
  ['PEBO', 'Peoples Bancorp Inc.', 'Nasdaq Listed'],
  ['PECO', 'Phillips Edison & Company, Inc.', 'Nasdaq Listed'],
  ['PEGA', 'Pegasystems Inc.', 'Nasdaq Listed'],
  ['PENG', 'Penguin Solutions, Inc.', 'Nasdaq Listed'],
  ['PENN', 'PENN Entertainment, Inc.', 'Nasdaq Listed'],
  ['PEPG', 'PepGen Inc.', 'Nasdaq Listed'],
  ['PERI', 'Perion Network Ltd', 'Nasdaq Listed'],
  ['PESI', 'Perma-Fix Environmental Services, Inc.', 'Nasdaq Listed'],
  ['PETS', 'PetMed Express, Inc.', 'Nasdaq Listed'],
  ['PETZ', 'TDH Holdings, Inc.', 'Nasdaq Listed'],
  ['PFAI', 'Pinnacle Food Group Limited - Class A Common Shares', 'Nasdaq Listed'],
  ['PFIS', 'Peoples Financial Services Corp.', 'Nasdaq Listed'],
  ['PFSA', 'Profusa, Inc.', 'Nasdaq Listed'],
  ['PFX', 'PhenixFIN Corporation', 'Nasdaq Listed'],
  ['PGAC', 'Pantages Capital Acquisition Corporation', 'Nasdaq Listed'],
  ['PGC', 'Peapack-Gladstone Financial Corporation', 'Nasdaq Listed'],
  ['PGEN', 'Precigen, Inc.', 'Nasdaq Listed'],
  ['PGNY', 'Progyny, Inc.', 'Nasdaq Listed'],
  ['PGY', 'Pagaya Technologies Ltd.', 'Nasdaq Listed'],
  ['PHAR', 'Pharming Group N.V.', 'Nasdaq Listed'],
  ['PHAT', 'Phathom Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['PHIO', 'Phio Pharmaceuticals Corp.', 'Nasdaq Listed'],
  ['PHOE', 'Phoenix Asia Holdings Limited', 'Nasdaq Listed'],
  ['PHUN', 'Phunware, Inc.', 'Nasdaq Listed'],
  ['PHVS', 'Pharvaris N.V.', 'Nasdaq Listed'],
  ['PI', 'Impinj, Inc.', 'Nasdaq Listed'],
  ['PICS', 'PicS N.V. - Class A Common Shares', 'Nasdaq Listed'],
  ['PIII', 'P3 Health Partners Inc.', 'Nasdaq Listed'],
  ['PKBK', 'Parke Bancorp, Inc.', 'Nasdaq Listed'],
  ['PKOH', 'Park-Ohio Holdings Corp.', 'Nasdaq Listed'],
  ['PLAB', 'Photronics, Inc.', 'Nasdaq Listed'],
  ['PLAY', 'Dave & Buster\'s Entertainment, Inc.', 'Nasdaq Listed'],
  ['PLBC', 'Plumas Bancorp', 'Nasdaq Listed'],
  ['PLBL', 'Polibeli Group Ltd', 'Nasdaq Listed'],
  ['PLBY', 'Playboy, Inc.', 'Nasdaq Listed'],
  ['PLCE', 'Children\'s Place, Inc. (The)', 'Nasdaq Listed'],
  ['PLMK', 'Plum Acquisition Corp. IV', 'Nasdaq Listed'],
  ['PLMR', 'Palomar Holdings, Inc.', 'Nasdaq Listed'],
  ['PLPC', 'Preformed Line Products Company', 'Nasdaq Listed'],
  ['PLRX', 'Pliant Therapeutics, Inc.', 'Nasdaq Listed'],
  ['PLRZ', 'Polyrizon Ltd.', 'Nasdaq Listed'],
  ['PLSE', 'Pulse Biosciences, Inc', 'Nasdaq Listed'],
  ['PLSM', 'Pulsenmore Ltd.', 'Nasdaq Listed'],
  ['PLTK', 'Playtika Holding Corp.', 'Nasdaq Listed'],
  ['PLTS', 'Platinum Analytics Cayman Limited', 'Nasdaq Listed'],
  ['PLUG', 'Plug Power, Inc.', 'Nasdaq Listed'],
  ['PLUR', 'Pluri Inc.', 'Nasdaq Listed'],
  ['PLUS', 'ePlus inc.', 'Nasdaq Listed'],
  ['PLUT', 'Plutus Financial Group Limited', 'Nasdaq Listed'],
  ['PLXS', 'Plexus Corp.', 'Nasdaq Listed'],
  ['PLYX', 'Polaryx Therapeutics, Inc.', 'Nasdaq Listed'],
  ['PMAX', 'Powell Max Limited', 'Nasdaq Listed'],
  ['PMCB', 'PharmaCyte Biotech, Inc.', 'Nasdaq Listed'],
  ['PMEC', 'Primech Holdings Ltd.', 'Nasdaq Listed'],
  ['PMN', 'ProMIS Neurosciences Inc.', 'Nasdaq Listed'],
  ['PMTR', 'Perimeter Acquisition Corp. I', 'Nasdaq Listed'],
  ['PMTS', 'CPI Card Group Inc.', 'Nasdaq Listed'],
  ['PMVP', 'PMV Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['PN', 'Skycorp Solar Group Limited', 'Nasdaq Listed'],
  ['PNBK', 'Patriot National Bancorp Inc.', 'Nasdaq Listed'],
  ['PNRG', 'PrimeEnergy Resources Corporation', 'Nasdaq Listed'],
  ['PNTG', 'The Pennant Group, Inc.', 'Nasdaq Listed'],
  ['POCI', 'Precision Optics Corporation, Inc.', 'Nasdaq Listed'],
  ['PODC', 'PodcastOne, Inc.', 'Nasdaq Listed'],
  ['POET', 'POET Technologies Inc.', 'Nasdaq Listed'],
  ['POLA', 'Polar Power, Inc.', 'Nasdaq Listed'],
  ['POLE', 'Andretti Acquisition Corp. II', 'Nasdaq Listed'],
  ['POM', 'POMDOCTOR LIMITED', 'Nasdaq Listed'],
  ['PONO', 'Pono Capital Four, Inc.', 'Nasdaq Listed'],
  ['PONY', 'Pony AI Inc.', 'Nasdaq Listed'],
  ['POOL', 'Pool Corporation', 'Nasdaq Listed'],
  ['POWI', 'Power Integrations, Inc.', 'Nasdaq Listed'],
  ['POWL', 'Powell Industries, Inc.', 'Nasdaq Listed'],
  ['POWW', 'Outdoor Holding Company', 'Nasdaq Listed'],
  ['PPBT', 'Purple Biotech Ltd.', 'Nasdaq Listed'],
  ['PPC', 'Pilgrim\'s Pride Corporation', 'Nasdaq Listed'],
  ['PPCB', 'Propanc Biopharma, Inc.', 'Nasdaq Listed'],
  ['PPHC', 'Public Policy Holding Company, Inc.', 'Nasdaq Listed'],
  ['PPIH', 'Perma-Pipe International Holdings, Inc.', 'Nasdaq Listed'],
  ['PPSI', 'Pioneer Power Solutions, Inc.', 'Nasdaq Listed'],
  ['PPTA', 'Perpetua Resources Corp.', 'Nasdaq Listed'],
  ['PRAA', 'PRA Group, Inc.', 'Nasdaq Listed'],
  ['PRAX', 'Praxis Precision Medicines, Inc.', 'Nasdaq Listed'],
  ['PRCH', 'Porch Group, Inc.', 'Nasdaq Listed'],
  ['PRCT', 'PROCEPT BioRobotics Corporation', 'Nasdaq Listed'],
  ['PRDO', 'Perdoceo Education Corporation', 'Nasdaq Listed'],
  ['PRE', 'Prenetics Global Limited', 'Nasdaq Listed'],
  ['PRFX', 'PRF Technologies Ltd.', 'Nasdaq Listed'],
  ['PRGS', 'Progress Software Corporation', 'Nasdaq Listed'],
  ['PRHI', 'Presurance Holdings, Inc.', 'Nasdaq Listed'],
  ['PRLD', 'Prelude Therapeutics Incorporated', 'Nasdaq Listed'],
  ['PRME', 'Prime Medicine, Inc.', 'Nasdaq Listed'],
  ['PROF', 'Profound Medical Corp.', 'Nasdaq Listed'],
  ['PROK', 'ProKidney Corp.', 'Nasdaq Listed'],
  ['PROP', 'Prairie Operating Co.', 'Nasdaq Listed'],
  ['PROV', 'Provident Financial Holdings, Inc.', 'Nasdaq Listed'],
  ['PRPL', 'Purple Innovation, Inc.', 'Nasdaq Listed'],
  ['PRPO', 'Precipio, Inc.', 'Nasdaq Listed'],
  ['PRQR', 'ProQR Therapeutics N.V.', 'Nasdaq Listed'],
  ['PRSO', 'Peraso Inc.', 'Nasdaq Listed'],
  ['PRTA', 'Prothena Corporation plc', 'Nasdaq Listed'],
  ['PRTH', 'Priority Technology Holdings, Inc.', 'Nasdaq Listed'],
  ['PRTS', 'CarParts.com, Inc.', 'Nasdaq Listed'],
  ['PRVA', 'Privia Health Group, Inc.', 'Nasdaq Listed'],
  ['PRZO', 'ParaZero Technologies Ltd.', 'Nasdaq Listed'],
  ['PSHG', 'Performance Shipping Inc.', 'Nasdaq Listed'],
  ['PSIG', 'PS International Group Ltd.', 'Nasdaq Listed'],
  ['PSIX', 'Power Solutions International, Inc.', 'Nasdaq Listed'],
  ['PSMT', 'PriceSmart, Inc.', 'Nasdaq Listed'],
  ['PSNL', 'Personalis, Inc.', 'Nasdaq Listed'],
  ['PSNY', 'Polestar Automotive Holding UK Limited - Class A ADS', 'Nasdaq Listed'],
  ['PSNYW', 'Polestar Automotive Holding UK Limited - Class C-1 ADS (ADW)', 'Nasdaq Listed'],
  ['PSTV', 'PLUS THERAPEUTICS, Inc.', 'Nasdaq Listed'],
  ['PTCT', 'PTC Therapeutics, Inc.', 'Nasdaq Listed'],
  ['PTEN', 'Patterson-UTI Energy, Inc.', 'Nasdaq Listed'],
  ['PTGX', 'Protagonist Therapeutics, Inc.', 'Nasdaq Listed'],
  ['PTLE', 'PTL LTD', 'Nasdaq Listed'],
  ['PTLO', 'Portillo\'s Inc.', 'Nasdaq Listed'],
  ['PTN', 'Palatin Technologies, Inc.', 'Nasdaq Listed'],
  ['PTNM', 'Pitanium Limited', 'Nasdaq Listed'],
  ['PTON', 'Peloton Interactive, Inc.', 'Nasdaq Listed'],
  ['PTOR', 'Praetorian Acquisition Corp.', 'Nasdaq Listed'],
  ['PTRN', 'Pattern Group Inc. - Series A Common Stock', 'Nasdaq Listed'],
  ['PUBM', 'PubMatic, Inc.', 'Nasdaq Listed'],
  ['PULM', 'Pulmatrix, Inc.', 'Nasdaq Listed'],
  ['PURR', 'Hyperliquid Strategies Inc', 'Nasdaq Listed'],
  ['PUSA', 'Aureus Greenway Holdings Inc.', 'Nasdaq Listed'],
  ['PVLA', 'Palvella Therapeutics, Inc.', 'Nasdaq Listed'],
  ['PWP', 'Perella Weinberg Partners', 'Nasdaq Listed'],
  ['PWRL', 'Powerlaw Corp.', 'Nasdaq Listed'],
  ['PXLW', 'Pixelworks, Inc.', 'Nasdaq Listed'],
  ['PXS', 'Pyxis Tankers Inc.', 'Nasdaq Listed'],
  ['PYPD', 'PolyPid Ltd.', 'Nasdaq Listed'],
  ['PYXS', 'Pyxis Oncology, Inc.', 'Nasdaq Listed'],
  ['PZZA', 'Papa John\'s International, Inc.', 'Nasdaq Listed'],
  ['QADR', 'QDRO Acquisition Corp.', 'Nasdaq Listed'],
  ['QCLS', 'Q/C Technologies, Inc.', 'Nasdaq Listed'],
  ['QCRH', 'QCR Holdings, Inc.', 'Nasdaq Listed'],
  ['QDEL', 'QuidelOrtho Corporation', 'Nasdaq Listed'],
  ['QETA', 'Quetta Acquisition Corporation', 'Nasdaq Listed'],
  ['QFIN', 'Qfin Holdings, Inc.', 'Nasdaq Listed'],
  ['QLYS', 'Qualys, Inc.', 'Nasdaq Listed'],
  ['QMCO', 'Quantum Corporation', 'Nasdaq Listed'],
  ['QMMM', 'QMMM Holdings Limited', 'Nasdaq Listed'],
  ['QNCX', 'Quince Therapeutics, Inc.', 'Nasdaq Listed'],
  ['QNRX', 'Quoin Pharmaceuticals, Ltd.', 'Nasdaq Listed'],
  ['QNST', 'QuinStreet, Inc.', 'Nasdaq Listed'],
  ['QRHC', 'Quest Resource Holding Corporation', 'Nasdaq Listed'],
  ['QRVO', 'Qorvo, Inc.', 'Nasdaq Listed'],
  ['QS', 'QuantumScape Corporation', 'Nasdaq Listed'],
  ['QSEA', 'Quartzsea Acquisition Corporation', 'Nasdaq Listed'],
  ['QSI', 'Quantum-Si Incorporated', 'Nasdaq Listed'],
  ['QTEX', 'QTREX Quantum Ltd.', 'Nasdaq Listed'],
  ['QTI', 'QT Imaging Holdings, Inc.', 'Nasdaq Listed'],
  ['QTRX', 'Quanterix Corporation', 'Nasdaq Listed'],
  ['QTTB', 'Q32 Bio Inc.', 'Nasdaq Listed'],
  ['QUBT', 'Quantum Computing Inc.', 'Nasdaq Listed'],
  ['QUCY', 'Quantum Cyber N.V.', 'Nasdaq Listed'],
  ['QUIK', 'QuickLogic Corporation', 'Nasdaq Listed'],
  ['QUMS', 'Quantumsphere Acquisition Corp.', 'Nasdaq Listed'],
  ['QURE', 'uniQure N.V.', 'Nasdaq Listed'],
  ['QXL', 'Quantum X Labs Inc.', 'Nasdaq Listed'],
  ['RAAQ', 'Real Asset Acquisition Corp.', 'Nasdaq Listed'],
  ['RACC', 'Research Alliance Corporation III', 'Nasdaq Listed'],
  ['RADX', 'Radiopharm Theranostics Limited', 'Nasdaq Listed'],
  ['RAIL', 'Freightcar America, Inc.', 'Nasdaq Listed'],
  ['RAIN', 'Rain Enhancement Technologies Holdco, Inc.', 'Nasdaq Listed'],
  ['RANG', 'Range Capital Acquisition Corp.', 'Nasdaq Listed'],
  ['RANI', 'Rani Therapeutics Holdings, Inc.', 'Nasdaq Listed'],
  ['RAPP', 'Rapport Therapeutics, Inc.', 'Nasdaq Listed'],
  ['RARE', 'Ultragenyx Pharmaceutical Inc.', 'Nasdaq Listed'],
  ['RAVE', 'Rave Restaurant Group, Inc.', 'Nasdaq Listed'],
  ['RAY', 'Raytech Holding Limited', 'Nasdaq Listed'],
  ['RAYA', 'Erayak Power Solution Group Inc.', 'Nasdaq Listed'],
  ['RBB', 'RBB Bancorp', 'Nasdaq Listed'],
  ['RBBN', 'Ribbon Communications Inc.', 'Nasdaq Listed'],
  ['RBCAA', 'Republic Bancorp, Inc.', 'Nasdaq Listed'],
  ['RBKB', 'Rhinebeck Bancorp, Inc.', 'Nasdaq Listed'],
  ['RBNE', 'Robin Energy Ltd.', 'Nasdaq Listed'],
  ['RCAT', 'Red Cat Holdings, Inc.', 'Nasdaq Listed'],
  ['RCEL', 'Avita Medical, Inc.', 'Nasdaq Listed'],
  ['RCKT', 'Rocket Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['RCKY', 'Rocky Brands, Inc.', 'Nasdaq Listed'],
  ['RCMT', 'RCM Technologies, Inc.', 'Nasdaq Listed'],
  ['RCON', 'Recon Technology, Ltd.', 'Nasdaq Listed'],
  ['RCT', 'RedCloud Holdings plc', 'Nasdaq Listed'],
  ['RDAC', 'Rising Dragon Acquisition Corp.', 'Nasdaq Listed'],
  ['RDAG', 'Republic Digital Acquisition Company', 'Nasdaq Listed'],
  ['RDCM', 'Radcom Ltd.', 'Nasdaq Listed'],
  ['RDGT', 'Ridgetech, Inc.', 'Nasdaq Listed'],
  ['RDHL', 'Redhill Biopharma Ltd.', 'Nasdaq Listed'],
  ['RDI', 'Reading International Inc - Class A Non-voting Common Stock', 'Nasdaq Listed'],
  ['RDIB', 'Reading International Inc - Class B Voting Common Stock', 'Nasdaq Listed'],
  ['RDNT', 'RadNet, Inc.', 'Nasdaq Listed'],
  ['RDNW', 'RideNow Group, Inc.', 'Nasdaq Listed'],
  ['RDVT', 'Red Violet, Inc.', 'Nasdaq Listed'],
  ['RDWR', 'Radware Ltd.', 'Nasdaq Listed'],
  ['RDZN', 'Roadzen, Inc.', 'Nasdaq Listed'],
  ['REAL', 'The RealReal, Inc.', 'Nasdaq Listed'],
  ['REAX', 'The Real Brokerage, Inc.', 'Nasdaq Listed'],
  ['REBN', 'Reborn Coffee, Inc.', 'Nasdaq Listed'],
  ['RECT', 'Rectitude Holdings Ltd', 'Nasdaq Listed'],
  ['REE', 'REE Automotive Ltd.', 'Nasdaq Listed'],
  ['REFI', 'Chicago Atlantic Real Estate Finance, Inc.', 'Nasdaq Listed'],
  ['REFR', 'Research Frontiers Incorporated', 'Nasdaq Listed'],
  ['REKR', 'Rekor Systems, Inc.', 'Nasdaq Listed'],
  ['RELL', 'Richardson Electronics, Ltd.', 'Nasdaq Listed'],
  ['RELY', 'Remitly Global, Inc.', 'Nasdaq Listed'],
  ['RENT', 'Rent the Runway, Inc.', 'Nasdaq Listed'],
  ['RENX', 'RenX Enterprises Corp.', 'Nasdaq Listed'],
  ['REPL', 'Replimune Group, Inc.', 'Nasdaq Listed'],
  ['REVB', 'Revelation Biosciences, Inc.', 'Nasdaq Listed'],
  ['REYN', 'Reynolds Consumer Products Inc.', 'Nasdaq Listed'],
  ['RFAI', 'RF Acquisition Corp II', 'Nasdaq Listed'],
  ['RFAM', 'RF Acquisition Corp III', 'Nasdaq Listed'],
  ['RFIL', 'RF Industries, Ltd.', 'Nasdaq Listed'],
  ['RGC', 'Regencell Bioscience Holdings Limited', 'Nasdaq Listed'],
  ['RGCO', 'RGC Resources Inc.', 'Nasdaq Listed'],
  ['RGEN', 'Repligen Corporation', 'Nasdaq Listed'],
  ['RGLD', 'Royal Gold, Inc.', 'Nasdaq Listed'],
  ['RGNX', 'REGENXBIO Inc.', 'Nasdaq Listed'],
  ['RGP', 'Resources Connection, Inc.', 'Nasdaq Listed'],
  ['RGS', 'Regis Corporation', 'Nasdaq Listed'],
  ['RGTI', 'Rigetti Computing, Inc.', 'Nasdaq Listed'],
  ['RIBB', 'Ribbon Acquisition Corp', 'Nasdaq Listed'],
  ['RICK', 'RCI Hospitality Holdings, Inc.', 'Nasdaq Listed'],
  ['RIGL', 'Rigel Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['RILY', 'BRC Group Holdings, Inc.', 'Nasdaq Listed'],
  ['RIME', 'Algorhythm Holdings, Inc.', 'Nasdaq Listed'],
  ['RIOT', 'Riot Platforms, Inc.', 'Nasdaq Listed'],
  ['RITR', 'Reitar Logtech Holdings Limited', 'Nasdaq Listed'],
  ['RIVN', 'Rivian Automotive, Inc.', 'Nasdaq Listed'],
  ['RJET', 'Republic Airways Holdings Inc.', 'Nasdaq Listed'],
  ['RKDA', 'Arcadia Biosciences, Inc.', 'Nasdaq Listed'],
  ['RKLB', 'Rocket Lab Corporation', 'Nasdaq Listed'],
  ['RKTO', 'Rocket One Inc.', 'Nasdaq Listed'],
  ['RLAY', 'Relay Therapeutics, Inc.', 'Nasdaq Listed'],
  ['RLMD', 'Relmada Therapeutics, Inc.', 'Nasdaq Listed'],
  ['RLYB', 'Rallybio Corporation', 'Nasdaq Listed'],
  ['RMBI', 'Richmond Mutual Bancorporation, Inc.', 'Nasdaq Listed'],
  ['RMBS', 'Rambus, Inc.', 'Nasdaq Listed'],
  ['RMCF', 'Rocky Mountain Chocolate Factory, Inc.', 'Nasdaq Listed'],
  ['RMCO', 'Royalty Management Holding Corporation', 'Nasdaq Listed'],
  ['RMIX', 'Suncrete, Inc.', 'Nasdaq Listed'],
  ['RMNI', 'Rimini Street, Inc.', 'Nasdaq Listed'],
  ['RMR', 'The RMR Group Inc.', 'Nasdaq Listed'],
  ['RMSG', 'Real Messenger Corporation', 'Nasdaq Listed'],
  ['RMTI', 'Rockwell Medical, Inc.', 'Nasdaq Listed'],
  ['RNA', 'Atrium Therapeutics, Inc.', 'Nasdaq Listed'],
  ['RNAC', 'Cartesian Therapeutics, Inc.', 'Nasdaq Listed'],
  ['RNAZ', 'TransCode Therapeutics, Inc.', 'Nasdaq Listed'],
  ['RNGT', 'Range Capital Acquisition Corp II', 'Nasdaq Listed'],
  ['RNTX', 'Rein Therapeutics, Inc.', 'Nasdaq Listed'],
  ['RNXT', 'RenovoRx, Inc.', 'Nasdaq Listed'],
  ['ROAD', 'Construction Partners, Inc.', 'Nasdaq Listed'],
  ['ROC', 'Rank One Computing Corporation', 'Nasdaq Listed'],
  ['ROCK', 'Gibraltar Industries, Inc.', 'Nasdaq Listed'],
  ['ROIV', 'Roivant Sciences Ltd.', 'Nasdaq Listed'],
  ['ROKU', 'Roku, Inc.', 'Nasdaq Listed'],
  ['ROMA', 'Roma Green Finance Limited', 'Nasdaq Listed'],
  ['ROOT', 'Root, Inc.', 'Nasdaq Listed'],
  ['RPAY', 'Repay Holdings Corporation', 'Nasdaq Listed'],
  ['RPD', 'Rapid7, Inc.', 'Nasdaq Listed'],
  ['RPGL', 'Republic Power Group Limited', 'Nasdaq Listed'],
  ['RPID', 'Rapid Micro Biosystems, Inc.', 'Nasdaq Listed'],
  ['RPRX', 'Royalty Pharma plc', 'Nasdaq Listed'],
  ['RR', 'Richtech Robotics Inc.', 'Nasdaq Listed'],
  ['RRBI', 'Red River Bancshares, Inc.', 'Nasdaq Listed'],
  ['RREV', 'RRE Ventures Acquisition Corp.', 'Nasdaq Listed'],
  ['RRGB', 'Red Robin Gourmet Burgers, Inc.', 'Nasdaq Listed'],
  ['RRR', 'Red Rock Resorts, Inc.', 'Nasdaq Listed'],
  ['RSSS', 'Research Solutions, Inc', 'Nasdaq Listed'],
  ['RSVR', 'Reservoir Media, Inc..', 'Nasdaq Listed'],
  ['RTAC', 'Renatus Tactical Acquisition Corp I', 'Nasdaq Listed'],
  ['RTB', 'RTB Digital, Inc.', 'Nasdaq Listed'],
  ['RUBI', 'Rubico Inc.', 'Nasdaq Listed'],
  ['RUM', 'Rumble Inc.', 'Nasdaq Listed'],
  ['RUN', 'Sunrun Inc.', 'Nasdaq Listed'],
  ['RUSHA', 'Rush Enterprises, Inc.', 'Nasdaq Listed'],
  ['RUSHB', 'Rush Enterprises, Inc.', 'Nasdaq Listed'],
  ['RVMD', 'Revolution Medicines, Inc.', 'Nasdaq Listed'],
  ['RVSB', 'Riverview Bancorp Inc', 'Nasdaq Listed'],
  ['RVSN', 'Rail Vision Ltd.', 'Nasdaq Listed'],
  ['RWAY', 'Runway Growth Finance Corp.', 'Nasdaq Listed'],
  ['RXRX', 'Recursion Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['RXST', 'RxSight, Inc.', 'Nasdaq Listed'],
  ['RXT', 'Rackspace Technology, Inc.', 'Nasdaq Listed'],
  ['RYAAY', 'Ryanair Holdings plc', 'Nasdaq Listed'],
  ['RYET', 'Ruanyun Edai Technology Inc.', 'Nasdaq Listed'],
  ['RYM', 'RYTHM, Inc.', 'Nasdaq Listed'],
  ['RYOJ', 'rYojbaba Co., Ltd.', 'Nasdaq Listed'],
  ['RYTM', 'Rhythm Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['RZLT', 'Rezolute, Inc. - Common Stock (NV)', 'Nasdaq Listed'],
  ['RZLV', 'Rezolve AI PLC', 'Nasdaq Listed'],
  ['SAAQ', 'Space Asset Acquisition Corp.', 'Nasdaq Listed'],
  ['SABR', 'Sabre Corporation', 'Nasdaq Listed'],
  ['SABS', 'SAB Biotherapeutics, Inc.', 'Nasdaq Listed'],
  ['SAFT', 'Safety Insurance Group, Inc.', 'Nasdaq Listed'],
  ['SAFX', 'XCF Global, Inc.', 'Nasdaq Listed'],
  ['SAGT', 'SAGTEC GLOBAL LIMITED', 'Nasdaq Listed'],
  ['SAIA', 'Saia, Inc.', 'Nasdaq Listed'],
  ['SAIC', 'Science Applications International Corporation', 'Nasdaq Listed'],
  ['SAIH', 'SAIHEAT Limited', 'Nasdaq Listed'],
  ['SAIL', 'SailPoint, Inc.', 'Nasdaq Listed'],
  ['SAMG', 'Silvercrest Asset Management Group Inc.', 'Nasdaq Listed'],
  ['SANA', 'Sana Biotechnology, Inc.', 'Nasdaq Listed'],
  ['SANG', 'Sangoma Technologies Corporation', 'Nasdaq Listed'],
  ['SANM', 'Sanmina Corporation', 'Nasdaq Listed'],
  ['SATL', 'Satellogic Inc.', 'Nasdaq Listed'],
  ['SBC', 'SBC Medical Group Holdings Incorporated', 'Nasdaq Listed'],
  ['SBCF', 'Seacoast Banking Corporation of Florida', 'Nasdaq Listed'],
  ['SBET', 'Sharplink, Inc.', 'Nasdaq Listed'],
  ['SBFG', 'SB Financial Group, Inc.', 'Nasdaq Listed'],
  ['SBFM', 'Sunshine Biopharma Inc.', 'Nasdaq Listed'],
  ['SBGI', 'Sinclair, Inc.', 'Nasdaq Listed'],
  ['SBLK', 'Star Bulk Carriers Corp.', 'Nasdaq Listed'],
  ['SBRA', 'Sabra Health Care REIT, Inc.', 'Nasdaq Listed'],
  ['SCAG', 'Scage Future', 'Nasdaq Listed'],
  ['SCHL', 'Scholastic Corporation', 'Nasdaq Listed'],
  ['SCII', 'SC II Acquisition Corp.', 'Nasdaq Listed'],
  ['SCKT', 'Socket Mobile, Inc.', 'Nasdaq Listed'],
  ['SCLX', 'Scilex Holding Company', 'Nasdaq Listed'],
  ['SCNI', 'Scinai Immunotherapeutics Ltd.', 'Nasdaq Listed'],
  ['SCNX', 'Scienture Holdings, Inc.', 'Nasdaq Listed'],
  ['SCOR', 'comScore, Inc.', 'Nasdaq Listed'],
  ['SCPQ', 'Social Commerce Partners Corporation', 'Nasdaq Listed'],
  ['SCSC', 'ScanSource, Inc.', 'Nasdaq Listed'],
  ['SCVL', 'Shoe Carnival, Inc.', 'Nasdaq Listed'],
  ['SCWO', '374Water Inc.', 'Nasdaq Listed'],
  ['SCYX', 'SCYNEXIS, Inc.', 'Nasdaq Listed'],
  ['SCZM', 'Santacruz Silver Mining Ltd.', 'Nasdaq Listed'],
  ['SDA', 'SunCar Technology Group Inc.', 'Nasdaq Listed'],
  ['SDGR', 'Schrodinger, Inc.', 'Nasdaq Listed'],
  ['SDHI', 'Siddhi Acquisition Corp', 'Nasdaq Listed'],
  ['SDM', 'Smart Digital Group Limited', 'Nasdaq Listed'],
  ['SDOT', 'Sadot Group Inc.', 'Nasdaq Listed'],
  ['SDST', 'Stardust Power Inc.', 'Nasdaq Listed'],
  ['SEAT', 'Vivid Seats Inc.', 'Nasdaq Listed'],
  ['SEDG', 'SolarEdge Technologies, Inc.', 'Nasdaq Listed'],
  ['SEED', 'Origin Agritech Limited', 'Nasdaq Listed'],
  ['SEER', 'Seer, Inc.', 'Nasdaq Listed'],
  ['SEGG', 'Sports Entertainment Gaming Global Corporation', 'Nasdaq Listed'],
  ['SEIC', 'SEI Investments Company', 'Nasdaq Listed'],
  ['SELF', 'Global Self Storage, Inc.', 'Nasdaq Listed'],
  ['SELX', 'Semilux International Ltd.', 'Nasdaq Listed'],
  ['SENEA', 'Seneca Foods Corp.', 'Nasdaq Listed'],
  ['SENEB', 'Seneca Foods Corp.', 'Nasdaq Listed'],
  ['SENS', 'Senseonics Holdings, Inc.', 'Nasdaq Listed'],
  ['SEPN', 'Septerna, Inc.', 'Nasdaq Listed'],
  ['SERA', 'Sera Prognostics, Inc.', 'Nasdaq Listed'],
  ['SERV', 'Serve Robotics Inc.', 'Nasdaq Listed'],
  ['SEV', 'Aptera Motors Corp.', 'Nasdaq Listed'],
  ['SEZL', 'Sezzle Inc.', 'Nasdaq Listed'],
  ['SFBC', 'Sound Financial Bancorp, Inc.', 'Nasdaq Listed'],
  ['SFD', 'Smithfield Foods, Inc.', 'Nasdaq Listed'],
  ['SFHG', 'Samfine Creation Holdings Group Limited', 'Nasdaq Listed'],
  ['SFIX', 'Stitch Fix, Inc.', 'Nasdaq Listed'],
  ['SFM', 'Sprouts Farmers Market, Inc.', 'Nasdaq Listed'],
  ['SFNC', 'Simmons First National Corporation', 'Nasdaq Listed'],
  ['SFST', 'Southern First Bancshares, Inc.', 'Nasdaq Listed'],
  ['SFWL', 'Shengfeng Development Limited', 'Nasdaq Listed'],
  ['SGA', 'Saga Communications, Inc.', 'Nasdaq Listed'],
  ['SGC', 'Superior Group of Companies, Inc.', 'Nasdaq Listed'],
  ['SGHT', 'Sight Sciences, Inc.', 'Nasdaq Listed'],
  ['SGLY', 'Singularity Future Technology Ltd.', 'Nasdaq Listed'],
  ['SGML', 'Sigma Lithium Corporation', 'Nasdaq Listed'],
  ['SGMT', 'Sagimet Biosciences Inc. - Series A Common Stock', 'Nasdaq Listed'],
  ['SGP', 'SpyGlass Pharma, Inc.', 'Nasdaq Listed'],
  ['SGRP', 'SPAR Group, Inc.', 'Nasdaq Listed'],
  ['SGRY', 'Surgery Partners, Inc.', 'Nasdaq Listed'],
  ['SHAZ', 'SharonAI Holdings, Inc.', 'Nasdaq Listed'],
  ['SHBI', 'Shore Bancshares, Inc.', 'Nasdaq Listed'],
  ['SHC', 'Sotera Health Company', 'Nasdaq Listed'],
  ['SHEN', 'Shenandoah Telecommunications Co', 'Nasdaq Listed'],
  ['SHFS', 'SHF Holdings, Inc.', 'Nasdaq Listed'],
  ['SHIM', 'Shimmick Corporation', 'Nasdaq Listed'],
  ['SHIP', 'Seanergy Maritime Holdings Corp.', 'Nasdaq Listed'],
  ['SHLS', 'Shoals Technologies Group, Inc.', 'Nasdaq Listed'],
  ['SHMD', 'SCHMID Group N.V.', 'Nasdaq Listed'],
  ['SHOO', 'Steven Madden, Ltd.', 'Nasdaq Listed'],
  ['SHPH', 'Shuttle Pharmaceuticals Holdings, Inc.', 'Nasdaq Listed'],
  ['SIBN', 'SI-BONE, Inc.', 'Nasdaq Listed'],
  ['SIDU', 'Sidus Space, Inc.', 'Nasdaq Listed'],
  ['SIEB', 'Siebert Financial Corp.', 'Nasdaq Listed'],
  ['SIGA', 'SIGA Technologies Inc.', 'Nasdaq Listed'],
  ['SIGI', 'Selective Insurance Group, Inc.', 'Nasdaq Listed'],
  ['SILC', 'Silicom Ltd', 'Nasdaq Listed'],
  ['SILO', 'Silo Pharma, Inc.', 'Nasdaq Listed'],
  ['SIMA', 'SIM Acquisition Corp. I', 'Nasdaq Listed'],
  ['SIMO', 'Silicon Motion Technology Corporation', 'Nasdaq Listed'],
  ['SINT', 'SiNtx Technologies, Inc.', 'Nasdaq Listed'],
  ['SION', 'Sionna Therapeutics, Inc.', 'Nasdaq Listed'],
  ['SIRI', 'SiriusXM Holdings Inc.', 'Nasdaq Listed'],
  ['SITM', 'SiTime Corporation', 'Nasdaq Listed'],
  ['SJ', 'Scienjoy Holding Corporation', 'Nasdaq Listed'],
  ['SKBL', 'Skyline Builders Group Holding Limited', 'Nasdaq Listed'],
  ['SKIN', 'SkinHealth Systems Inc.', 'Nasdaq Listed'],
  ['SKK', 'SKK Holdings Limited', 'Nasdaq Listed'],
  ['SKWD', 'Skyward Specialty Insurance Group, Inc.', 'Nasdaq Listed'],
  ['SKYA', 'SkyAI, Inc.', 'Nasdaq Listed'],
  ['SKYE', 'Skye Bioscience, Inc.', 'Nasdaq Listed'],
  ['SKYQ', 'Sky Quarry Inc.', 'Nasdaq Listed'],
  ['SKYT', 'SkyWater Technology, Inc.', 'Nasdaq Listed'],
  ['SKYW', 'SkyWest, Inc.', 'Nasdaq Listed'],
  ['SKYX', 'SKYX Platforms Corp.', 'Nasdaq Listed'],
  ['SLAB', 'Silicon Laboratories, Inc.', 'Nasdaq Listed'],
  ['SLDB', 'Solid Biosciences Inc.', 'Nasdaq Listed'],
  ['SLDE', 'Slide Insurance Holdings, Inc.', 'Nasdaq Listed'],
  ['SLDP', 'Solid Power, Inc.', 'Nasdaq Listed'],
  ['SLE', 'Super League Enterprise, Inc.', 'Nasdaq Listed'],
  ['SLGB', 'Smart Logistics Global Limited', 'Nasdaq Listed'],
  ['SLGL', 'Sol-Gel Technologies Ltd.', 'Nasdaq Listed'],
  ['SLM', 'SLM Corporation', 'Nasdaq Listed'],
  ['SLMT', 'Brera Holdings PLC', 'Nasdaq Listed'],
  ['SLNG', 'Stabilis Solutions, Inc.', 'Nasdaq Listed'],
  ['SLNH', 'Soluna Holdings, Inc.', 'Nasdaq Listed'],
  ['SLP', 'Simulations Plus, Inc.', 'Nasdaq Listed'],
  ['SLS', 'SELLAS Life Sciences Group, Inc.', 'Nasdaq Listed'],
  ['SLSN', 'Solesence, Inc.', 'Nasdaq Listed'],
  ['SLXN', 'Silexion Therapeutics Corp', 'Nasdaq Listed'],
  ['SMBC', 'Southern Missouri Bancorp, Inc.', 'Nasdaq Listed'],
  ['SMID', 'Smith-Midland Corporation', 'Nasdaq Listed'],
  ['SMMT', 'Summit Therapeutics Inc.', 'Nasdaq Listed'],
  ['SMPL', 'The Simply Good Foods Company', 'Nasdaq Listed'],
  ['SMSI', 'Smith Micro Software, Inc.', 'Nasdaq Listed'],
  ['SMTC', 'Semtech Corporation', 'Nasdaq Listed'],
  ['SMTI', 'Sanara MedTech Inc.', 'Nasdaq Listed'],
  ['SMTK', 'SmartKem, Inc.', 'Nasdaq Listed'],
  ['SMX', 'SMX (Security Matters) Public Limited Company', 'Nasdaq Listed'],
  ['SMXT', 'Solarmax Technology Inc.', 'Nasdaq Listed'],
  ['SNAL', 'Snail, Inc.', 'Nasdaq Listed'],
  ['SNBR', 'Sleep Number Corporation', 'Nasdaq Listed'],
  ['SND', 'Smart Sand, Inc.', 'Nasdaq Listed'],
  ['SNDL', 'SNDL Inc.', 'Nasdaq Listed'],
  ['SNDX', 'Syndax Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['SNES', 'SenesTech, Inc.', 'Nasdaq Listed'],
  ['SNEX', 'StoneX Group Inc.', 'Nasdaq Listed'],
  ['SNFCA', 'Security National Financial Corporation', 'Nasdaq Listed'],
  ['SNGX', 'Soligenix, Inc.', 'Nasdaq Listed'],
  ['SNOA', 'Sonoma Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['SNSE', 'Sensei Biotherapeutics, Inc.', 'Nasdaq Listed'],
  ['SNT', 'Senstar Technologies Corporation', 'Nasdaq Listed'],
  ['SNTG', 'Sentage Holdings Inc.', 'Nasdaq Listed'],
  ['SNTI', 'Senti Biosciences Holdings, Inc.', 'Nasdaq Listed'],
  ['SNWV', 'SANUWAVE Health, Inc.', 'Nasdaq Listed'],
  ['SNY', 'Sanofi', 'Nasdaq Listed'],
  ['SNYR', 'Synergy CHC Corp.', 'Nasdaq Listed'],
  ['SOBR', 'SOBR Safe, Inc.', 'Nasdaq Listed'],
  ['SOCA', 'Solarius Capital Acquisition Corp.', 'Nasdaq Listed'],
  ['SOFI', 'SoFi Technologies, Inc.', 'Nasdaq Listed'],
  ['SOGP', 'Sound Group Inc.', 'Nasdaq Listed'],
  ['SOHU', 'Sohu.com Limited', 'Nasdaq Listed'],
  ['SOLS', 'Solstice Advanced Materials Inc.', 'Nasdaq Listed'],
  ['SONM', 'DNA X, Inc.', 'Nasdaq Listed'],
  ['SONO', 'Sonos, Inc.', 'Nasdaq Listed'],
  ['SOPH', 'SOPHiA GENETICS SA', 'Nasdaq Listed'],
  ['SORA', 'AsiaStrategy', 'Nasdaq Listed'],
  ['SORN', 'Soren Acquisition Corp.', 'Nasdaq Listed'],
  ['SOTK', 'Sono-Tek Corporation', 'Nasdaq Listed'],
  ['SOUN', 'SoundHound AI, Inc.', 'Nasdaq Listed'],
  ['SOWG', 'Sow Good Inc.', 'Nasdaq Listed'],
  ['SPAI', 'Safe Pro Group Inc.', 'Nasdaq Listed'],
  ['SPCB', 'SuperCom, Ltd.', 'Nasdaq Listed'],
  ['SPEG', 'Silver Pegasus Acquisition Corp', 'Nasdaq Listed'],
  ['SPFI', 'South Plains Financial, Inc.', 'Nasdaq Listed'],
  ['SPHL', 'Springview Holdings Ltd', 'Nasdaq Listed'],
  ['SPKL', 'Spark I Acquisition Corp.', 'Nasdaq Listed'],
  ['SPOK', 'Spok Holdings, Inc.', 'Nasdaq Listed'],
  ['SPPL', 'SIMPPLE LTD.', 'Nasdaq Listed'],
  ['SPRB', 'Spruce Biosciences, Inc.', 'Nasdaq Listed'],
  ['SPRC', 'SciSparc Ltd.', 'Nasdaq Listed'],
  ['SPRO', 'Spero Therapeutics, Inc.', 'Nasdaq Listed'],
  ['SPRY', 'ARS Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['SPSC', 'SPS Commerce, Inc.', 'Nasdaq Listed'],
  ['SPT', 'Sprout Social, Inc', 'Nasdaq Listed'],
  ['SPTX', 'Seaport Therapeutics, Inc.', 'Nasdaq Listed'],
  ['SPWH', 'Sportsman\'s Warehouse Holdings, Inc.', 'Nasdaq Listed'],
  ['SPWR', 'SunPower Inc.', 'Nasdaq Listed'],
  ['SRAD', 'Sportradar Group AG', 'Nasdaq Listed'],
  ['SRBK', 'SR Bancorp, Inc.', 'Nasdaq Listed'],
  ['SRCE', '1st Source Corporation', 'Nasdaq Listed'],
  ['SRPT', 'Sarepta Therapeutics, Inc.', 'Nasdaq Listed'],
  ['SRRK', 'Scholar Rock Holding Corporation', 'Nasdaq Listed'],
  ['SRTA', 'Strata Critical Medical, Inc.', 'Nasdaq Listed'],
  ['SRTS', 'Sensus Healthcare, Inc.', 'Nasdaq Listed'],
  ['SRZN', 'Surrozen, Inc.', 'Nasdaq Listed'],
  ['SSAC', 'SPACSphere Acquisition Corp.', 'Nasdaq Listed'],
  ['SSBI', 'Summit State Bank', 'Nasdaq Listed'],
  ['SSEA', 'Starry Sea Acquisition Corp', 'Nasdaq Listed'],
  ['SSII', 'SS Innovations International Inc.', 'Nasdaq Listed'],
  ['SSM', 'Sono Group N.V.', 'Nasdaq Listed'],
  ['SSNC', 'SS&C Technologies Holdings, Inc.', 'Nasdaq Listed'],
  ['SSP', 'E.W. Scripps Company (The)', 'Nasdaq Listed'],
  ['SSRM', 'SSR Mining Inc.', 'Nasdaq Listed'],
  ['SSTI', 'SoundThinking, Inc.', 'Nasdaq Listed'],
  ['SSYS', 'Stratasys, Ltd.', 'Nasdaq Listed'],
  ['STAA', 'STAAR Surgical Company', 'Nasdaq Listed'],
  ['STAK', 'STAK Inc.', 'Nasdaq Listed'],
  ['STBA', 'S&T Bancorp, Inc.', 'Nasdaq Listed'],
  ['STEP', 'StepStone Group Inc.', 'Nasdaq Listed'],
  ['STEX', 'Streamex Corp.', 'Nasdaq Listed'],
  ['STFS', 'Star Fashion Culture Holdings Limited', 'Nasdaq Listed'],
  ['STGW', 'Stagwell Inc.', 'Nasdaq Listed'],
  ['STI', 'Solidion Technology, Inc.', 'Nasdaq Listed'],
  ['STIM', 'Neuronetics, Inc.', 'Nasdaq Listed'],
  ['STKE', 'Sol Strategies Inc.', 'Nasdaq Listed'],
  ['STKH', 'Steakholder Foods Ltd.', 'Nasdaq Listed'],
  ['STKS', 'The ONE Group Hospitality, Inc.', 'Nasdaq Listed'],
  ['STNE', 'StoneCo Ltd. - Class A Common Share', 'Nasdaq Listed'],
  ['STOK', 'Stoke Therapeutics, Inc.', 'Nasdaq Listed'],
  ['STRA', 'Strategic Education, Inc.', 'Nasdaq Listed'],
  ['STRL', 'Sterling Infrastructure, Inc.', 'Nasdaq Listed'],
  ['STRO', 'Sutro Biopharma, Inc.', 'Nasdaq Listed'],
  ['STRR', 'Star Equity Holdings, Inc.', 'Nasdaq Listed'],
  ['STRS', 'Stratus Properties Inc.', 'Nasdaq Listed'],
  ['STRT', 'STRATTEC SECURITY CORPORATION', 'Nasdaq Listed'],
  ['STRZ', 'Starz Entertainment Corp.', 'Nasdaq Listed'],
  ['STTK', 'Shattuck Labs, Inc.', 'Nasdaq Listed'],
  ['SUGP', 'SU Group Holdings Limited', 'Nasdaq Listed'],
  ['SUIG', 'Sui Group Holdings Limited', 'Nasdaq Listed'],
  ['SUJA', 'Suja Life, Inc.', 'Nasdaq Listed'],
  ['SUMA', 'SUMA Acquisition Corporation', 'Nasdaq Listed'],
  ['SUNE', 'SUNation Energy, Inc.', 'Nasdaq Listed'],
  ['SUPN', 'Supernus Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['SUPX', 'SuperX AI Technology Limited', 'Nasdaq Listed'],
  ['SURG', 'SurgePays, Inc.', 'Nasdaq Listed'],
  ['SUUN', 'PowerBank Corporation', 'Nasdaq Listed'],
  ['SVA', 'Sinovac Biotech, Ltd. - Ordinary Shares (Antigua/Barbudo)', 'Nasdaq Listed'],
  ['SVAC', 'Spring Valley Acquisition Corp. III', 'Nasdaq Listed'],
  ['SVAQ', 'Silicon Valley Acquisition Corp.', 'Nasdaq Listed'],
  ['SVCC', 'Stellar V Capital Corp.', 'Nasdaq Listed'],
  ['SVCO', 'Silvaco Group, Inc.', 'Nasdaq Listed'],
  ['SVIV', 'Spring Valley Acquisition Corp. IV', 'Nasdaq Listed'],
  ['SVRA', 'Savara, Inc.', 'Nasdaq Listed'],
  ['SVRE', 'SaverOne 2014 Ltd.', 'Nasdaq Listed'],
  ['SVRN', 'OceanPal Inc.', 'Nasdaq Listed'],
  ['SWAG', 'Stran & Company, Inc.', 'Nasdaq Listed'],
  ['SWBI', 'Smith & Wesson Brands, Inc.', 'Nasdaq Listed'],
  ['SWIM', 'Latham Group, Inc.', 'Nasdaq Listed'],
  ['SWMR', 'Swarmer, Inc', 'Nasdaq Listed'],
  ['SWVL', 'Swvl Holdings Corp', 'Nasdaq Listed'],
  ['SXTC', 'China SXT Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['SXTP', '60 Degrees Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['SYBT', 'Stock Yards Bancorp, Inc.', 'Nasdaq Listed'],
  ['SYM', 'Symbotic Inc.', 'Nasdaq Listed'],
  ['SYNA', 'Synaptics Incorporated', 'Nasdaq Listed'],
  ['SYPR', 'Sypris Solutions, Inc.', 'Nasdaq Listed'],
  ['SYRE', 'Spyre Therapeutics, Inc.', 'Nasdaq Listed'],
  ['SZZL', 'Sizzle Acquisition Corp. II', 'Nasdaq Listed'],
  ['TACH', 'Titan Acquisition Corp.', 'Nasdaq Listed'],
  ['TACO', 'Berto Acquisition Corp.', 'Nasdaq Listed'],
  ['TACT', 'TransAct Technologies Incorporated', 'Nasdaq Listed'],
  ['TALK', 'Talkspace, Inc.', 'Nasdaq Listed'],
  ['TANH', 'Tantech Holdings Ltd. - Class A Common Shares', 'Nasdaq Listed'],
  ['TAOP', 'Taoping Inc.', 'Nasdaq Listed'],
  ['TAOX', 'Tao Synergies Inc.', 'Nasdaq Listed'],
  ['TARA', 'Protara Therapeutics, Inc.', 'Nasdaq Listed'],
  ['TARS', 'Tarsus Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['TASK', 'TaskUs, Inc.', 'Nasdaq Listed'],
  ['TATT', 'TAT Technologies Ltd.', 'Nasdaq Listed'],
  ['TAVI', 'Tavia Acquisition Corp.', 'Nasdaq Listed'],
  ['TAYD', 'Taylor Devices, Inc.', 'Nasdaq Listed'],
  ['TBBK', 'The Bancorp, Inc.', 'Nasdaq Listed'],
  ['TBCH', 'Turtle Beach Corporation', 'Nasdaq Listed'],
  ['TBH', 'Brag House Holdings, Inc.', 'Nasdaq Listed'],
  ['TBLA', 'Taboola.com Ltd.', 'Nasdaq Listed'],
  ['TBPH', 'Theravance Biopharma, Inc.', 'Nasdaq Listed'],
  ['TBRG', 'TruBridge, Inc.', 'Nasdaq Listed'],
  ['TC', 'Token Cat Limited', 'Nasdaq Listed'],
  ['TCBI', 'Texas Capital Bancshares, Inc.', 'Nasdaq Listed'],
  ['TCBK', 'TriCo Bancshares', 'Nasdaq Listed'],
  ['TCBS', 'Texas Community Bancshares, Inc.', 'Nasdaq Listed'],
  ['TCMD', 'Tactile Systems Technology, Inc.', 'Nasdaq Listed'],
  ['TCOM', 'Trip.com Group Limited', 'Nasdaq Listed'],
  ['TCRT', 'Alaunos Therapeutics, Inc.', 'Nasdaq Listed'],
  ['TCRX', 'TScan Therapeutics, Inc.', 'Nasdaq Listed'],
  ['TCX', 'Tucows Inc.', 'Nasdaq Listed'],
  ['TDAC', 'Translational Development Acquisition Corp.', 'Nasdaq Listed'],
  ['TDIC', 'Dreamland Limited', 'Nasdaq Listed'],
  ['TDUP', 'ThredUp Inc.', 'Nasdaq Listed'],
  ['TDWD', 'Tailwind 2.0 Acquisition Corp.', 'Nasdaq Listed'],
  ['TEAD', 'Teads Holding Co.', 'Nasdaq Listed'],
  ['TEAM', 'Atlassian Corporation', 'Nasdaq Listed'],
  ['TECX', 'Tectonic Therapeutic, Inc.', 'Nasdaq Listed'],
  ['TELA', 'TELA Bio, Inc.', 'Nasdaq Listed'],
  ['TELO', 'Telomir Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['TEM', 'Tempus AI, Inc.', 'Nasdaq Listed'],
  ['TENB', 'Tenable Holdings, Inc.', 'Nasdaq Listed'],
  ['TENX', 'Tenax Therapeutics, Inc.', 'Nasdaq Listed'],
  ['TFSL', 'TFS Financial Corporation', 'Nasdaq Listed'],
  ['TGHL', 'The GrowHub Limited', 'Nasdaq Listed'],
  ['TGL', 'Treasure Global Inc.', 'Nasdaq Listed'],
  ['TGTX', 'TG Therapeutics, Inc.', 'Nasdaq Listed'],
  ['TH', 'Target Hospitality Corp.', 'Nasdaq Listed'],
  ['THCH', 'TH International Limited', 'Nasdaq Listed'],
  ['THFF', 'First Financial Corporation', 'Nasdaq Listed'],
  ['THH', 'TryHard Holdings Limited', 'Nasdaq Listed'],
  ['THRM', 'Gentherm Inc', 'Nasdaq Listed'],
  ['THRY', 'Thryv Holdings, Inc.', 'Nasdaq Listed'],
  ['TIGO', 'Millicom International Cellular S.A.', 'Nasdaq Listed'],
  ['TIGR', 'UP Fintech Holding Limited', 'Nasdaq Listed'],
  ['TIL', 'Instil Bio, Inc.', 'Nasdaq Listed'],
  ['TILE', 'Interface, Inc.', 'Nasdaq Listed'],
  ['TIPT', 'Tiptree Inc.', 'Nasdaq Listed'],
  ['TITN', 'Titan Machinery Inc.', 'Nasdaq Listed'],
  ['TJGC', 'TJGC Group Limited', 'Nasdaq Listed'],
  ['TKLF', 'Tokyo Lifestyle Co., Ltd.', 'Nasdaq Listed'],
  ['TKNO', 'Alpha Teknova, Inc.', 'Nasdaq Listed'],
  ['TLF', 'Tandy Leather Factory, Inc.', 'Nasdaq Listed'],
  ['TLIH', 'Ten-League International Holdings Limited', 'Nasdaq Listed'],
  ['TLN', 'Talen Energy Corporation', 'Nasdaq Listed'],
  ['TLNC', 'Talon Capital Corp.', 'Nasdaq Listed'],
  ['TLPH', 'Talphera, Inc.', 'Nasdaq Listed'],
  ['TLRY', 'Tilray Brands, Inc.', 'Nasdaq Listed'],
  ['TLS', 'Telos Corporation', 'Nasdaq Listed'],
  ['TLSA', 'Tiziana Life Sciences Ltd', 'Nasdaq Listed'],
  ['TLSI', 'TriSalus Life Sciences, Inc.', 'Nasdaq Listed'],
  ['TLX', 'Telix Pharmaceuticals Limited', 'Nasdaq Listed'],
  ['TMC', 'TMC the metals company Inc.', 'Nasdaq Listed'],
  ['TMCI', 'Treace Medical Concepts, Inc.', 'Nasdaq Listed'],
  ['TMCR', 'The Metals Royalty Company Inc.', 'Nasdaq Listed'],
  ['TMDX', 'TransMedics Group, Inc.', 'Nasdaq Listed'],
  ['TMTS', 'Spartacus Acquisition Corp. II', 'Nasdaq Listed'],
  ['TNDM', 'Tandem Diabetes Care, Inc.', 'Nasdaq Listed'],
  ['TNGX', 'Tango Therapeutics, Inc.', 'Nasdaq Listed'],
  ['TNMG', 'TNL Mediagene', 'Nasdaq Listed'],
  ['TNON', 'Tenon Medical, Inc.', 'Nasdaq Listed'],
  ['TNXP', 'Tonix Pharmaceuticals Holding Corp.', 'Nasdaq Listed'],
  ['TNYA', 'Tenaya Therapeutics, Inc.', 'Nasdaq Listed'],
  ['TOI', 'The Oncology Institute, Inc.', 'Nasdaq Listed'],
  ['TOMZ', 'TOMI Environmental Solutions, Inc.', 'Nasdaq Listed'],
  ['TONX', 'TON Strategy Company', 'Nasdaq Listed'],
  ['TOP', 'TOP Financial Group Limited', 'Nasdaq Listed'],
  ['TORO', 'Toro Corp.', 'Nasdaq Listed'],
  ['TOUR', 'Tuniu Corporation', 'Nasdaq Listed'],
  ['TOWN', 'Towne Bank', 'Nasdaq Listed'],
  ['TOYO', 'TOYO Co., Ltd', 'Nasdaq Listed'],
  ['TPCS', 'TechPrecision Corporation', 'Nasdaq Listed'],
  ['TPG', 'TPG Inc.', 'Nasdaq Listed'],
  ['TPST', 'Tempest Therapeutics, Inc.', 'Nasdaq Listed'],
  ['TRAW', 'Traws Pharma, Inc.', 'Nasdaq Listed'],
  ['TRAX', 'First Tracks Biotherapeutics, Inc.', 'Nasdaq Listed'],
  ['TRDA', 'Entrada Therapeutics, Inc.', 'Nasdaq Listed'],
  ['TREE', 'LendingTree, Inc.', 'Nasdaq Listed'],
  ['TRGS', 'TRG Latin America Acquisitions Corp.', 'Nasdaq Listed'],
  ['TRIB', 'Trinity Biotech plc', 'Nasdaq Listed'],
  ['TRIN', 'Trinity Capital Inc.', 'Nasdaq Listed'],
  ['TRIP', 'TripAdvisor, Inc.', 'Nasdaq Listed'],
  ['TRMD', 'TORM plc', 'Nasdaq Listed'],
  ['TRMK', 'Trustmark Corporation', 'Nasdaq Listed'],
  ['TRNR', 'Interactive Strength Inc.', 'Nasdaq Listed'],
  ['TRNS', 'Transcat, Inc.', 'Nasdaq Listed'],
  ['TRON', 'Tron Inc.', 'Nasdaq Listed'],
  ['TROO', 'TROOPS, Inc.', 'Nasdaq Listed'],
  ['TRS', 'TriMas Corporation', 'Nasdaq Listed'],
  ['TRSG', 'Tungray Technologies Inc', 'Nasdaq Listed'],
  ['TRST', 'TrustCo Bank Corp NY', 'Nasdaq Listed'],
  ['TRUG', 'TruGolf Holdings, Inc.', 'Nasdaq Listed'],
  ['TRUP', 'Trupanion, Inc.', 'Nasdaq Listed'],
  ['TRVG', 'trivago N.V.', 'Nasdaq Listed'],
  ['TRVI', 'Trevi Therapeutics, Inc.', 'Nasdaq Listed'],
  ['TSAT', 'Telesat Corporation - Class A Common Shares and Class B Variable Voting Shares', 'Nasdaq Listed'],
  ['TSBK', 'Timberland Bancorp, Inc.', 'Nasdaq Listed'],
  ['TSEM', 'Tower Semiconductor Ltd.', 'Nasdaq Listed'],
  ['TSHA', 'Taysha Gene Therapies, Inc.', 'Nasdaq Listed'],
  ['TSSI', 'TSS, Inc.', 'Nasdaq Listed'],
  ['TTAN', 'ServiceTitan, Inc.', 'Nasdaq Listed'],
  ['TTEC', 'TTEC Holdings, Inc.', 'Nasdaq Listed'],
  ['TTEK', 'Tetra Tech, Inc.', 'Nasdaq Listed'],
  ['TTGT', 'TechTarget, Inc.', 'Nasdaq Listed'],
  ['TTMI', 'TTM Technologies, Inc.', 'Nasdaq Listed'],
  ['TTRX', 'Turn Therapeutics Inc.', 'Nasdaq Listed'],
  ['TULP', 'Bloomia Holdings, Inc.', 'Nasdaq Listed'],
  ['TURB', 'Turbo Energy, S.A.', 'Nasdaq Listed'],
  ['TUSK', 'Mammoth Energy Services, Inc.', 'Nasdaq Listed'],
  ['TVA', 'Texas Ventures Acquisition III Corp', 'Nasdaq Listed'],
  ['TVAI', 'Thayer Ventures Acquisition Corporation II', 'Nasdaq Listed'],
  ['TVGN', 'Tevogen Bio Holdings Inc.', 'Nasdaq Listed'],
  ['TVRD', 'Tvardi Therapeutics, Inc.', 'Nasdaq Listed'],
  ['TVTX', 'Travere Therapeutics, Inc.', 'Nasdaq Listed'],
  ['TW', 'Tradeweb Markets Inc.', 'Nasdaq Listed'],
  ['TWAV', 'TaoWeave, Inc.', 'Nasdaq Listed'],
  ['TWFG', 'TWFG, Inc.', 'Nasdaq Listed'],
  ['TWG', 'Top Wealth Group Holding Limited', 'Nasdaq Listed'],
  ['TWIN', 'Twin Disc, Incorporated', 'Nasdaq Listed'],
  ['TWLV', 'Twelve Seas Investment Company III', 'Nasdaq Listed'],
  ['TWST', 'Twist Bioscience Corporation', 'Nasdaq Listed'],
  ['TXG', '10x Genomics, Inc.', 'Nasdaq Listed'],
  ['TXMD', 'TherapeuticsMD, Inc.', 'Nasdaq Listed'],
  ['TXRH', 'Texas Roadhouse, Inc.', 'Nasdaq Listed'],
  ['TYGO', 'Tigo Energy, Inc.', 'Nasdaq Listed'],
  ['TYRA', 'Tyra Biosciences, Inc.', 'Nasdaq Listed'],
  ['TZOO', 'Travelzoo', 'Nasdaq Listed'],
  ['UBCP', 'United Bancorp, Inc.', 'Nasdaq Listed'],
  ['UBSI', 'United Bankshares, Inc.', 'Nasdaq Listed'],
  ['UBXG', 'U-BX Technology Ltd.', 'Nasdaq Listed'],
  ['UCAR', 'U Power Limited', 'Nasdaq Listed'],
  ['UCFI', 'CN Healthy Food Tech Group Corp.', 'Nasdaq Listed'],
  ['UCL', 'uCloudlink Group Inc.', 'Nasdaq Listed'],
  ['UCTT', 'Ultra Clean Holdings, Inc.', 'Nasdaq Listed'],
  ['UEIC', 'Universal Electronics Inc.', 'Nasdaq Listed'],
  ['UFCS', 'United Fire Group, Inc', 'Nasdaq Listed'],
  ['UFG', 'Uni-Fuels Holdings Limited', 'Nasdaq Listed'],
  ['UFPI', 'UFP Industries, Inc.', 'Nasdaq Listed'],
  ['UFPT', 'UFP Technologies, Inc.', 'Nasdaq Listed'],
  ['UG', 'United-Guardian, Inc.', 'Nasdaq Listed'],
  ['UGRO', 'urban-gro, Inc.', 'Nasdaq Listed'],
  ['UK', 'Ucommune International Ltd', 'Nasdaq Listed'],
  ['ULBI', 'Ultralife Corporation', 'Nasdaq Listed'],
  ['ULCC', 'Frontier Group Holdings, Inc.', 'Nasdaq Listed'],
  ['ULH', 'Universal Logistics Holdings, Inc.', 'Nasdaq Listed'],
  ['UMBF', 'UMB Financial Corporation', 'Nasdaq Listed'],
  ['UNB', 'Union Bankshares, Inc.', 'Nasdaq Listed'],
  ['UNCY', 'Unicycive Therapeutics, Inc.', 'Nasdaq Listed'],
  ['UNIT', 'Uniti Group Inc.', 'Nasdaq Listed'],
  ['UNTY', 'Unity Bancorp, Inc.', 'Nasdaq Listed'],
  ['UONE', 'Urban One, Inc.', 'Nasdaq Listed'],
  ['UONEK', 'Urban One, Inc.', 'Nasdaq Listed'],
  ['UPB', 'Upstream Bio, Inc.', 'Nasdaq Listed'],
  ['UPBD', 'Upbound Group, Inc.', 'Nasdaq Listed'],
  ['UPC', 'Universe Pharmaceuticals Inc', 'Nasdaq Listed'],
  ['UPLD', 'Upland Software, Inc.', 'Nasdaq Listed'],
  ['UPST', 'Upstart Holdings, Inc.', 'Nasdaq Listed'],
  ['UPWK', 'Upwork Inc.', 'Nasdaq Listed'],
  ['UPXI', 'Upexi, Inc.', 'Nasdaq Listed'],
  ['URBN', 'Urban Outfitters, Inc.', 'Nasdaq Listed'],
  ['URGN', 'UroGen Pharma Ltd.', 'Nasdaq Listed'],
  ['UROY', 'Uranium Royalty Corp.', 'Nasdaq Listed'],
  ['USAR', 'USA Rare Earth, Inc.', 'Nasdaq Listed'],
  ['USAU', 'U.S. Gold Corp.', 'Nasdaq Listed'],
  ['USCB', 'USCB Financial Holdings, Inc.', 'Nasdaq Listed'],
  ['USEA', 'United Maritime Corporation', 'Nasdaq Listed'],
  ['USEG', 'U.S. Energy Corp.', 'Nasdaq Listed'],
  ['USGO', 'U.S. GoldMining Inc.', 'Nasdaq Listed'],
  ['USIO', 'Usio, Inc.', 'Nasdaq Listed'],
  ['USLM', 'United States Lime & Minerals, Inc.', 'Nasdaq Listed'],
  ['UTHR', 'United Therapeutics Corporation', 'Nasdaq Listed'],
  ['UTMD', 'Utah Medical Products, Inc.', 'Nasdaq Listed'],
  ['UTSI', 'UTStarcom Holdings Corp', 'Nasdaq Listed'],
  ['UVSP', 'Univest Financial Corporation', 'Nasdaq Listed'],
  ['UXIN', 'Uxin Limited', 'Nasdaq Listed'],
  ['UYSC', 'UY Scuti Acquisition Corp.', 'Nasdaq Listed'],
  ['UZX', 'Linkage Global Inc', 'Nasdaq Listed'],
  ['VABK', 'Virginia National Bankshares Corporation', 'Nasdaq Listed'],
  ['VACH', 'Voyager Acquisition Corp', 'Nasdaq Listed'],
  ['VALN', 'Valneva SE', 'Nasdaq Listed'],
  ['VALU', 'Value Line, Inc.', 'Nasdaq Listed'],
  ['VANI', 'Vivani Medical, Inc.', 'Nasdaq Listed'],
  ['VBIO', 'Valion Bio, Inc.', 'Nasdaq Listed'],
  ['VBNK', 'VersaBank', 'Nasdaq Listed'],
  ['VC', 'Visteon Corporation', 'Nasdaq Listed'],
  ['VCEL', 'Vericel Corporation', 'Nasdaq Listed'],
  ['VCIG', 'VCI Global Limited - Ordinary Share', 'Nasdaq Listed'],
  ['VCTR', 'Victory Capital Holdings, Inc.', 'Nasdaq Listed'],
  ['VCYT', 'Veracyte, Inc.', 'Nasdaq Listed'],
  ['VECO', 'Veeco Instruments Inc.', 'Nasdaq Listed'],
  ['VEEA', 'Veea Inc.', 'Nasdaq Listed'],
  ['VEEE', 'Twin Vee PowerCats Co.', 'Nasdaq Listed'],
  ['VELO', 'Velo3D, Inc.', 'Nasdaq Listed'],
  ['VEON', 'VEON Ltd.', 'Nasdaq Listed'],
  ['VERA', 'Vera Therapeutics, Inc.', 'Nasdaq Listed'],
  ['VERI', 'Veritone, Inc.', 'Nasdaq Listed'],
  ['VERU', 'Veru Inc.', 'Nasdaq Listed'],
  ['VERX', 'Vertex, Inc.', 'Nasdaq Listed'],
  ['VFF', 'Village Farms International, Inc.', 'Nasdaq Listed'],
  ['VFS', 'VinFast Auto Ltd.', 'Nasdaq Listed'],
  ['VGAS', 'Verde Clean Fuels, Inc.', 'Nasdaq Listed'],
  ['VHC', 'VirnetX Holding Corp', 'Nasdaq Listed'],
  ['VHCP', 'Vine Hill Capital Investment Corp. II', 'Nasdaq Listed'],
  ['VHUB', 'VenHub Global, Inc.', 'Nasdaq Listed'],
  ['VIAV', 'Viavi Solutions Inc.', 'Nasdaq Listed'],
  ['VICR', 'Vicor Corporation', 'Nasdaq Listed'],
  ['VINP', 'Vinci Compass Investments Ltd. - Class A Common Shares', 'Nasdaq Listed'],
  ['VIOT', 'Viomi Technology Co., Ltd', 'Nasdaq Listed'],
  ['VIR', 'Vir Biotechnology, Inc.', 'Nasdaq Listed'],
  ['VIRC', 'Virco Manufacturing Corporation', 'Nasdaq Listed'],
  ['VISN', 'Vistance Networks, Inc.', 'Nasdaq Listed'],
  ['VITL', 'Vital Farms, Inc.', 'Nasdaq Listed'],
  ['VIVK', 'Vivakor, Inc.', 'Nasdaq Listed'],
  ['VIVO', 'VivoPower PLC', 'Nasdaq Listed'],
  ['VIVS', 'VivoSim Labs, Inc.', 'Nasdaq Listed'],
  ['VKTX', 'Viking Therapeutics, Inc.', 'Nasdaq Listed'],
  ['VLGEA', 'Village Super Market, Inc.', 'Nasdaq Listed'],
  ['VLY', 'Valley National Bancorp', 'Nasdaq Listed'],
  ['VMAR', 'Vision Marine Technologies Inc.', 'Nasdaq Listed'],
  ['VMD', 'Viemed Healthcare, Inc.', 'Nasdaq Listed'],
  ['VMET', 'Versamet Royalties Corporation', 'Nasdaq Listed'],
  ['VNCE', 'Vince Holding Corp.', 'Nasdaq Listed'],
  ['VNDA', 'Vanda Pharmaceuticals Inc.', 'Nasdaq Listed'],
  ['VNET', 'VNET Group, Inc.', 'Nasdaq Listed'],
  ['VNME', 'Vendome Acquisition Corporation I', 'Nasdaq Listed'],
  ['VNOM', 'Viper Energy, Inc.', 'Nasdaq Listed'],
  ['VOD', 'Vodafone Group Plc', 'Nasdaq Listed'],
  ['VOR', 'Vor Biopharma Inc.', 'Nasdaq Listed'],
  ['VOXR', 'Vox Royalty Corp.', 'Nasdaq Listed'],
  ['VRA', 'Vera Bradley, Inc.', 'Nasdaq Listed'],
  ['VRAX', 'Virax Biolabs Group Limited', 'Nasdaq Listed'],
  ['VRCA', 'Verrica Pharmaceuticals Inc.', 'Nasdaq Listed'],
  ['VRDN', 'Viridian Therapeutics, Inc.', 'Nasdaq Listed'],
  ['VREX', 'Varex Imaging Corporation', 'Nasdaq Listed'],
  ['VRM', 'Vroom, Inc.', 'Nasdaq Listed'],
  ['VRME', 'VerifyMe, Inc.', 'Nasdaq Listed'],
  ['VRNS', 'Varonis Systems, Inc.', 'Nasdaq Listed'],
  ['VRRM', 'Verra Mobility Corporation', 'Nasdaq Listed'],
  ['VS', 'Versus Systems Inc.', 'Nasdaq Listed'],
  ['VSA', 'VisionSys AI Inc.', 'Nasdaq Listed'],
  ['VSAT', 'ViaSat, Inc.', 'Nasdaq Listed'],
  ['VSEC', 'VSE Corporation', 'Nasdaq Listed'],
  ['VSEE', 'VSee Health, Inc.', 'Nasdaq Listed'],
  ['VSME', 'VS Media Holdings Limited', 'Nasdaq Listed'],
  ['VSNT', 'Versant Media Group, Inc.', 'Nasdaq Listed'],
  ['VSTD', 'Vestand Inc.', 'Nasdaq Listed'],
  ['VSTM', 'Verastem, Inc.', 'Nasdaq Listed'],
  ['VTGN', 'Vistagen Therapeutics, Inc.', 'Nasdaq Listed'],
  ['VTIX', 'Virtuix Holdings Inc.', 'Nasdaq Listed'],
  ['VTSI', 'VirTra, Inc.', 'Nasdaq Listed'],
  ['VTVT', 'vTv Therapeutics Inc.', 'Nasdaq Listed'],
  ['VUZI', 'Vuzix Corporation', 'Nasdaq Listed'],
  ['VVOS', 'Vivos Therapeutics, Inc.', 'Nasdaq Listed'],
  ['VWAV', 'VisionWave Holdings, Inc.', 'Nasdaq Listed'],
  ['VYGR', 'Voyager Therapeutics, Inc.', 'Nasdaq Listed'],
  ['VYNE', 'VYNE Therapeutics Inc.', 'Nasdaq Listed'],
  ['WABC', 'Westamerica Bancorporation', 'Nasdaq Listed'],
  ['WAFD', 'WaFd, Inc.', 'Nasdaq Listed'],
  ['WAFU', 'Wah Fu Education Group Limited', 'Nasdaq Listed'],
  ['WAI', 'Top KingWin Ltd', 'Nasdaq Listed'],
  ['WALD', 'Waldencast plc', 'Nasdaq Listed'],
  ['WATT', 'Energous Corporation', 'Nasdaq Listed'],
  ['WAVE', 'Eco Wave Power Global AB (publ)', 'Nasdaq Listed'],
  ['WAY', 'Waystar Holding Corp.', 'Nasdaq Listed'],
  ['WB', 'Weibo Corporation', 'Nasdaq Listed'],
  ['WBTN', 'WEBTOON Entertainment Inc.', 'Nasdaq Listed'],
  ['WBUY', 'WEBUY GLOBAL LTD.', 'Nasdaq Listed'],
  ['WCT', 'Wellchange Holdings Company Limited', 'Nasdaq Listed'],
  ['WDFC', 'WD-40 Company', 'Nasdaq Listed'],
  ['WEN', 'Wendy\'s Company (The)', 'Nasdaq Listed'],
  ['WENN', 'Wen Acquisition Corp', 'Nasdaq Listed'],
  ['WERN', 'Werner Enterprises, Inc.', 'Nasdaq Listed'],
  ['WEST', 'Westrock Coffee Company', 'Nasdaq Listed'],
  ['WETH', 'Wetouch Technology Inc.', 'Nasdaq Listed'],
  ['WETO', 'Wetour Robotics Limited', 'Nasdaq Listed'],
  ['WEYS', 'Weyco Group, Inc.', 'Nasdaq Listed'],
  ['WFCF', 'Where Food Comes From, Inc.', 'Nasdaq Listed'],
  ['WFF', 'WF Holding Limited', 'Nasdaq Listed'],
  ['WFRD', 'Weatherford International plc', 'Nasdaq Listed'],
  ['WGRX', 'Wellgistics Health, Inc.', 'Nasdaq Listed'],
  ['WGS', 'GeneDx Holdings Corp.', 'Nasdaq Listed'],
  ['WHWK', 'Whitehawk Therapeutics, Inc.', 'Nasdaq Listed'],
  ['WILC', 'G. Willi-Food International, Ltd.', 'Nasdaq Listed'],
  ['WIMI', 'WiMi Hologram Cloud Inc.', 'Nasdaq Listed'],
  ['WINA', 'Winmark Corporation', 'Nasdaq Listed'],
  ['WING', 'Wingstop Inc.', 'Nasdaq Listed'],
  ['WIX', 'Wix.com Ltd.', 'Nasdaq Listed'],
  ['WKEY', 'WISeKey International Holding Ltd', 'Nasdaq Listed'],
  ['WKHS', 'Workhorse Group, Inc.', 'Nasdaq Listed'],
  ['WKSP', 'Worksport, Ltd.', 'Nasdaq Listed'],
  ['WLDN', 'Willdan Group, Inc.', 'Nasdaq Listed'],
  ['WLDS', 'Wearable Devices Ltd. - Ordinary Share', 'Nasdaq Listed'],
  ['WLFC', 'Willis Lease Finance Corporation', 'Nasdaq Listed'],
  ['WLII', 'Willow Lane Acquisition Corp. II', 'Nasdaq Listed'],
  ['WLTH', 'Wealthfront Corporation', 'Nasdaq Listed'],
  ['WMG', 'Warner Music Group Corp.', 'Nasdaq Listed'],
  ['WNEB', 'Western New England Bancorp, Inc.', 'Nasdaq Listed'],
  ['WNW', 'Meiwu Technology Company Limited', 'Nasdaq Listed'],
  ['WOK', 'WORK Medical Technology Group LTD', 'Nasdaq Listed'],
  ['WOOF', 'Petco Health and Wellness Company, Inc.', 'Nasdaq Listed'],
  ['WPRT', 'Westport Fuel Systems Inc', 'Nasdaq Listed'],
  ['WRAP', 'Wrap Technologies, Inc.', 'Nasdaq Listed'],
  ['WRD', 'WeRide Inc.', 'Nasdaq Listed'],
  ['WRLD', 'World Acceptance Corporation', 'Nasdaq Listed'],
  ['WSBC', 'WesBanco, Inc.', 'Nasdaq Listed'],
  ['WSBF', 'Waterstone Financial, Inc.', 'Nasdaq Listed'],
  ['WSBK', 'Winchester Bancorp, Inc.', 'Nasdaq Listed'],
  ['WSC', 'WillScot Holdings Corporation', 'Nasdaq Listed'],
  ['WSE', 'Wise Group plc', 'Nasdaq Listed'],
  ['WSFS', 'WSFS Financial Corporation', 'Nasdaq Listed'],
  ['WSHP', 'WeShop Holdings Limited', 'Nasdaq Listed'],
  ['WSTN', 'Westin Acquisition Corp', 'Nasdaq Listed'],
  ['WTBA', 'West Bancorporation', 'Nasdaq Listed'],
  ['WTF', 'Waton Financial Limited', 'Nasdaq Listed'],
  ['WTFC', 'Wintrust Financial Corporation', 'Nasdaq Listed'],
  ['WTG', 'Wintergreen Acquisition Corp.', 'Nasdaq Listed'],
  ['WTO', 'UTime Limited', 'Nasdaq Listed'],
  ['WULF', 'TeraWulf Inc.', 'Nasdaq Listed'],
  ['WVE', 'Wave Life Sciences Ltd.', 'Nasdaq Listed'],
  ['WVVI', 'Willamette Valley Vineyards, Inc.', 'Nasdaq Listed'],
  ['WW', 'WW International, Inc.', 'Nasdaq Listed'],
  ['WWD', 'Woodward, Inc.', 'Nasdaq Listed'],
  ['WXM', 'WF International Limited', 'Nasdaq Listed'],
  ['WYFI', 'WhiteFiber, Inc.', 'Nasdaq Listed'],
  ['WYHG', 'Wing Yip Food Holdings Group Limited', 'Nasdaq Listed'],
  ['XAIR', 'Beyond Air, Inc.', 'Nasdaq Listed'],
  ['XBIO', 'Xenetic Biosciences, Inc.', 'Nasdaq Listed'],
  ['XBIT', 'XBiotech Inc.', 'Nasdaq Listed'],
  ['XBP', 'XBP Global Holdings, Inc.', 'Nasdaq Listed'],
  ['XCBE', 'X3 Acquisition Corp. Ltd.', 'Nasdaq Listed'],
  ['XCH', 'XCHG Limited', 'Nasdaq Listed'],
  ['XCUR', 'Exicure, Inc.', 'Nasdaq Listed'],
  ['XE', 'X-Energy, Inc.', 'Nasdaq Listed'],
  ['XELB', 'Xcel Brands, Inc', 'Nasdaq Listed'],
  ['XENE', 'Xenon Pharmaceuticals Inc.', 'Nasdaq Listed'],
  ['XERS', 'Xeris Biopharma Holdings, Inc.', 'Nasdaq Listed'],
  ['XFOR', 'X4 Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['XGN', 'Exagen Inc.', 'Nasdaq Listed'],
  ['XHG', 'XChange TEC.INC', 'Nasdaq Listed'],
  ['XHLD', 'TEN Holdings, Inc.', 'Nasdaq Listed'],
  ['XLO', 'Xilio Therapeutics, Inc.', 'Nasdaq Listed'],
  ['XMAX', 'XMAX, Inc.', 'Nasdaq Listed'],
  ['XMTR', 'Xometry, Inc.', 'Nasdaq Listed'],
  ['XNCR', 'Xencor, Inc.', 'Nasdaq Listed'],
  ['XNET', 'Xunlei Limited', 'Nasdaq Listed'],
  ['XOMA', 'XOMA Royalty Corporation', 'Nasdaq Listed'],
  ['XOS', 'Xos, Inc.', 'Nasdaq Listed'],
  ['XP', 'XP Inc.', 'Nasdaq Listed'],
  ['XPEL', 'XPEL, Inc.', 'Nasdaq Listed'],
  ['XPON', 'Expion360 Inc.', 'Nasdaq Listed'],
  ['XRAY', 'DENTSPLY SIRONA Inc.', 'Nasdaq Listed'],
  ['XRPN', 'Armada Acquisition Corp. II', 'Nasdaq Listed'],
  ['XRTX', 'XORTX Therapeutics Inc.', 'Nasdaq Listed'],
  ['XRX', 'Xerox Holdings Corporation', 'Nasdaq Listed'],
  ['XSLL', 'Xsolla SPAC 1', 'Nasdaq Listed'],
  ['XTIA', 'XTI Aerospace, Inc. Common Stock', 'Nasdaq Listed'],
  ['XTLB', 'XTL Biopharmaceuticals Ltd.', 'Nasdaq Listed'],
  ['XWEL', 'XWELL, Inc.', 'Nasdaq Listed'],
  ['XXII', '22nd Century Group, Inc', 'Nasdaq Listed'],
  ['YAAS', 'Youxin Technology Ltd', 'Nasdaq Listed'],
  ['YB', 'Yuanbao Inc.', 'Nasdaq Listed'],
  ['YDDL', 'One and One Green Technologies. INC', 'Nasdaq Listed'],
  ['YDES', 'YD Bio Limited', 'Nasdaq Listed'],
  ['YDKG', 'Yueda Digital Holding', 'Nasdaq Listed'],
  ['YHC', 'LQR House Inc.', 'Nasdaq Listed'],
  ['YHGJ', 'Yunhong Green CTI Ltd.', 'Nasdaq Listed'],
  ['YHNA', 'YHN Acquisition I Limited', 'Nasdaq Listed'],
  ['YI', '111, Inc.', 'Nasdaq Listed'],
  ['YIBO', 'Planet Image International Limited', 'Nasdaq Listed'],
  ['YMAT', 'J-Star Holding Co., Ltd.', 'Nasdaq Listed'],
  ['YMT', 'Yimutian Inc.', 'Nasdaq Listed'],
  ['YOOV', 'Concorde International Group Ltd', 'Nasdaq Listed'],
  ['YORW', 'The York Water Company', 'Nasdaq Listed'],
  ['YOUL', 'Youlife Group Inc.', 'Nasdaq Listed'],
  ['YQ', '17 Education & Technology Group Inc.', 'Nasdaq Listed'],
  ['YSWY', 'Yesway, Inc.', 'Nasdaq Listed'],
  ['YSXT', 'YSX Tech. Co., Ltd', 'Nasdaq Listed'],
  ['YTRA', 'Yatra Online, Inc.', 'Nasdaq Listed'],
  ['YYAI', 'AiRWA Inc.', 'Nasdaq Listed'],
  ['YYGH', 'YY Group Holding Limited', 'Nasdaq Listed'],
  ['ZAZZT', 'Tick Pilot Test Stock Class A Common Stock', 'Nasdaq Listed'],
  ['ZBAO', 'Zhibao Technology Inc.', 'Nasdaq Listed'],
  ['ZBIO', 'Zenas BioPharma, Inc.', 'Nasdaq Listed'],
  ['ZBZZT', 'Test Pilot Test Stock Class B Common Stock', 'Nasdaq Listed'],
  ['ZCMD', 'Zhongchao Inc.', 'Nasdaq Listed'],
  ['ZD', 'Ziff Davis, Inc.', 'Nasdaq Listed'],
  ['ZDAI', 'DirectBooking Technology Co., Ltd.', 'Nasdaq Listed'],
  ['ZENA', 'ZenaTech, Inc.', 'Nasdaq Listed'],
  ['ZEO', 'Zeo Energy Corporation', 'Nasdaq Listed'],
  ['ZG', 'Zillow Group, Inc.', 'Nasdaq Listed'],
  ['ZION', 'Zions Bancorporation N.A.', 'Nasdaq Listed'],
  ['ZJK', 'ZJK Industrial Co., Ltd.', 'Nasdaq Listed'],
  ['ZJYL', 'JIN MEDICAL INTERNATIONAL LTD.', 'Nasdaq Listed'],
  ['ZKIN', 'ZK International Group Co., Ltd - Ordinary Share', 'Nasdaq Listed'],
  ['ZKP', 'Lafayette Digital Acquisition Corp. I', 'Nasdaq Listed'],
  ['ZLAB', 'Zai Lab Limited', 'Nasdaq Listed'],
  ['ZM', 'Zoom Communications, Inc.', 'Nasdaq Listed'],
  ['ZNB', 'Zeta Network Group', 'Nasdaq Listed'],
  ['ZNTL', 'Zentalis Pharmaceuticals, Inc.', 'Nasdaq Listed'],
  ['ZOOZ', 'ZOOZ Strategy Ltd.', 'Nasdaq Listed'],
  ['ZSQR', 'Z Squared Inc.', 'Nasdaq Listed'],
  ['ZSTK', 'ZeroStack Corp.', 'Nasdaq Listed'],
  ['ZTEK', 'Zentek Ltd.', 'Nasdaq Listed'],
  ['ZTG', 'Zenta Group Company Limited', 'Nasdaq Listed'],
  ['ZUMZ', 'Zumiez Inc.', 'Nasdaq Listed'],
  ['ZURA', 'Zura Bio Limited', 'Nasdaq Listed'],
  ['ZVRA', 'Zevra Therapeutics, Inc.', 'Nasdaq Listed'],
  ['ZXYZ.A', 'Nasdaq Symbology Test Common Stock', 'Nasdaq Listed'],
  ['ZYBT', 'Zhengye Biotechnology Holding Limited', 'Nasdaq Listed'],
  ['ZYME', 'Zymeworks Inc.', 'Nasdaq Listed'],
  ['BWXT', 'BWX Technologies, Inc.', 'Nuclear'],
  ['NNE', 'Nano Nuclear Energy Inc.', 'Nuclear'],
  ['OKLO', 'Oklo Inc.', 'Nuclear'],
  ['SMR', 'NuScale Power Corporation', 'Nuclear'],
  ['AMT', 'American Tower', 'Real Estate'],
  ['ARE', 'Alexandria Real Estate Equities', 'Real Estate'],
  ['AVB', 'AvalonBay Communities', 'Real Estate'],
  ['BXP', 'BXP, Inc.', 'Real Estate'],
  ['CBRE', 'CBRE Group', 'Real Estate'],
  ['CCI', 'Crown Castle', 'Real Estate'],
  ['CPT', 'Camden Property Trust', 'Real Estate'],
  ['CSGP', 'CoStar Group', 'Real Estate'],
  ['DLR', 'Digital Realty', 'Real Estate'],
  ['DOC', 'Healthpeak Properties', 'Real Estate'],
  ['EQIX', 'Equinix', 'Real Estate'],
  ['EQR', 'Equity Residential', 'Real Estate'],
  ['ESS', 'Essex Property Trust', 'Real Estate'],
  ['EXR', 'Extra Space Storage', 'Real Estate'],
  ['FRT', 'Federal Realty Investment Trust', 'Real Estate'],
  ['HST', 'Host Hotels & Resorts', 'Real Estate'],
  ['INVH', 'Invitation Homes', 'Real Estate'],
  ['IRM', 'Iron Mountain', 'Real Estate'],
  ['KIM', 'Kimco Realty', 'Real Estate'],
  ['MAA', 'Mid-America Apartment Communities', 'Real Estate'],
  ['O', 'Realty Income', 'Real Estate'],
  ['PLD', 'Prologis', 'Real Estate'],
  ['PSA', 'Public Storage', 'Real Estate'],
  ['REG', 'Regency Centers', 'Real Estate'],
  ['SBAC', 'SBA Communications', 'Real Estate'],
  ['SPG', 'Simon Property Group', 'Real Estate'],
  ['UDR', 'UDR, Inc.', 'Real Estate'],
  ['VICI', 'Vici Properties', 'Real Estate'],
  ['VTR', 'Ventas', 'Real Estate'],
  ['WELL', 'Welltower', 'Real Estate'],
  ['WY', 'Weyerhaeuser', 'Real Estate'],
  ['ARM', 'Arm Holdings', 'Technology'],
  ['ASML', 'ASML Holding', 'Technology'],
  ['MSTR', 'MicroStrategy', 'Technology'],
  ['PDD', 'PDD Holdings', 'Technology'],
  ['SHOP', 'Shopify', 'Technology'],
  ['TRI', 'Thomson Reuters', 'Technology'],
  ['ZS', 'Zscaler', 'Technology'],
  ['CCJ', 'Cameco Corporation', 'Uranium'],
  ['DNN', 'Denison Mines Corp.', 'Uranium'],
  ['LEU', 'Centrus Energy Corp.', 'Uranium'],
  ['NXE', 'NexGen Energy Ltd.', 'Uranium'],
  ['UEC', 'Uranium Energy Corp.', 'Uranium'],
  ['UUUU', 'Energy Fuels Inc.', 'Uranium'],
  ['AEE', 'Ameren', 'Utilities'],
  ['AEP', 'American Electric Power', 'Utilities'],
  ['AES', 'AES Corporation', 'Utilities'],
  ['ATO', 'Atmos Energy', 'Utilities'],
  ['AWK', 'American Water Works', 'Utilities'],
  ['CEG', 'Constellation Energy', 'Utilities'],
  ['CMS', 'CMS Energy', 'Utilities'],
  ['CNP', 'CenterPoint Energy', 'Utilities'],
  ['D', 'Dominion Energy', 'Utilities'],
  ['DTE', 'DTE Energy', 'Utilities'],
  ['DUK', 'Duke Energy', 'Utilities'],
  ['ED', 'Consolidated Edison', 'Utilities'],
  ['EIX', 'Edison International', 'Utilities'],
  ['ES', 'Eversource Energy', 'Utilities'],
  ['ETR', 'Entergy', 'Utilities'],
  ['EVRG', 'Evergy', 'Utilities'],
  ['EXC', 'Exelon', 'Utilities'],
  ['FE', 'FirstEnergy', 'Utilities'],
  ['LNT', 'Alliant Energy', 'Utilities'],
  ['NEE', 'NextEra Energy', 'Utilities'],
  ['NI', 'NiSource', 'Utilities'],
  ['NRG', 'NRG Energy', 'Utilities'],
  ['PCG', 'PG&E Corporation', 'Utilities'],
  ['PEG', 'Public Service Enterprise Group', 'Utilities'],
  ['PNW', 'Pinnacle West Capital', 'Utilities'],
  ['PPL', 'PPL Corporation', 'Utilities'],
  ['SO', 'Southern Company', 'Utilities'],
  ['SRE', 'Sempra', 'Utilities'],
  ['VST', 'Vistra Corp.', 'Utilities'],
  ['WEC', 'WEC Energy Group', 'Utilities'],
  ['XEL', 'Xcel Energy', 'Utilities']
].map(([symbol, name, category]) => ({
  symbol,
  name,
  category,
  price: '--',
  notional: '--',
  change: '--',
  tone: 'neutral'
}))

function doesExploreRowMatchQuery(row, query) {
  const normalizedQuery = String(query || '').trim().toUpperCase()
  if (!normalizedQuery) {
    return true
  }

  const symbol = String(row?.symbol || '').toUpperCase()
  const name = String(row?.name || '').toUpperCase()
  const category = String(row?.category || '').toUpperCase()
  return symbol.includes(normalizedQuery) || name.includes(normalizedQuery) || category.includes(normalizedQuery)
}

function isStockExploreLiveSearchQuery(rawQuery) {
  const cleanedSymbol = normalizeTradeSymbolInput(rawQuery)
  return /^[A-Z][A-Z0-9.]{0,9}$/.test(cleanedSymbol)
}

function buildStockExploreLiveSearchRow(symbol, stockData = {}) {
  const cleanedSymbol = normalizeTradeSymbolInput(symbol || stockData.symbol)
  const currentPrice = Number(stockData.currentPrice)
  const previousClose = Number(stockData.previousClose || currentPrice)
  const changePct = previousClose ? (((currentPrice - previousClose) / previousClose) * 100) : 0

  return {
    symbol: cleanedSymbol,
    name: stockData.companyName || cleanedSymbol,
    category: stockData.sector || stockData.industry || 'Live market',
    price: Number.isFinite(currentPrice) ? formatMarketPrice(currentPrice) : '--',
    notional: '--',
    change: Number.isFinite(changePct) ? formatPercent(Number(changePct.toFixed(2))) : '--',
    tone: changePct > 0 ? 'positive' : changePct < 0 ? 'negative' : 'neutral',
    source: 'live-search'
  }
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

  const modePages = authenticatedPages.filter((page) => {
    if (page === 'Stock Trade') {
      return !isCryptoMode.value
    }

    if (page === 'Crypto Trade') {
      return isCryptoMode.value
    }

    return true
  })

  if (currentUser.value?.isAdmin) {
    return [...modePages, 'Admin']
  }

  return modePages
})
function t(key) {
  return activeCopy.value?.[key] ?? uiCopy.en[key] ?? key
}

function formatPageLabel(page) {
  return activeCopy.value?.pageLabels?.[page] ?? uiCopy.en.pageLabels[page] ?? page
}

function getSpeechLanguage() {
  return languageOptions.find((language) => language.code === uiLanguage.value)?.voiceLang || 'en-US'
}

const selectedIndicators = computed(() => indicators.value.filter((indicator) => indicator.active))
const appliedIndicatorSet = computed(() => new Set(
  activeTradeResponse.value?.request?.indicators
  || activeTradeResponse.value?.patternAnalysis?.selectedIndicators
  || []
))
const appliedIndicators = computed(() => indicators.value
  .filter((indicator) => appliedIndicatorSet.value.has(indicator.name))
  .map((indicator) => ({ ...indicator, active: true })))
const newsFeed = computed(() => {
  if (isCryptoMode.value) {
    return buildHourlyCryptoNewsFeed(activeMarketSymbol.value, feedRefreshKey.value)
  }

  return marketNewsFeed.value.length ? marketNewsFeed.value : buildHourlyNewsFeed(activeSymbol.value, feedRefreshKey.value)
})
const scrollingNewsFeed = computed(() => [...newsFeed.value, ...newsFeed.value])
const socialFeed = computed(() => (
  isCryptoMode.value
    ? buildHourlyCryptoSocialFeed(activeMarketSymbol.value, feedRefreshKey.value)
    : buildHourlySocialFeed(activeSymbol.value, feedRefreshKey.value)
))
const marketFocusLabel = computed(() => {
  if (isCryptoMode.value) {
    return `${activeMarketSymbol.value || 'Crypto'} Crypto`
  }

  if (activeSymbol.value && top50Symbols.includes(activeSymbol.value)) {
    return 'Hot Market'
  }

  return 'Hot Market'
})
const currentUserName = computed(() => currentUser.value?.fullName || 'Guest')
const currentUserCode = computed(() => formatAdminUserCode(currentUser.value?.displayCode ?? currentUser.value?.id))
const marketOverviewCards = computed(() => (isCryptoMode.value ? cryptoMarketOverviewCards : stockMarketOverviewCards))
const dashboardAnnouncements = computed(() => (isCryptoMode.value ? cryptoDashboardAnnouncements : stockDashboardAnnouncements))
const moreFeatures = computed(() => (isCryptoMode.value ? cryptoMoreFeatures : stockMoreFeatures))
const cryptoExploreUniverseRows = computed(() => (
  cryptoExploreLiveRows.value.length ? cryptoExploreLiveRows.value : cryptoExploreRows
))
const currentExploreRows = computed(() => {
  if (isCryptoMode.value) {
    return cryptoExploreUniverseRows.value
  }

  return exploreRankings[currentExploreTab.value] || exploreRankings.Watchlist
})
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
  return stockMarketUniverseRows
})
const visibleFullMarketBoardRows = computed(() => fullMarketBoardRows.value.slice(0, stockMarketVisibleCount.value))
const hasMoreStockMarketRows = computed(() => stockMarketVisibleCount.value < fullMarketBoardRows.value.length)
const stockMarketBoardStatus = computed(() => {
  const visibleCount = Math.min(stockMarketVisibleCount.value, fullMarketBoardRows.value.length)
  return `${visibleCount}/${fullMarketBoardRows.value.length} stocks`
})
const visibleExploreRows = computed(() => {
  if (isCryptoMode.value) {
    return cryptoExploreUniverseRows.value
  }

  if (exploreViewMode.value === 'full') {
    return visibleFullMarketBoardRows.value
  }

  return currentExploreRows.value
})
const filteredExploreRows = computed(() => {
  const query = exploreSearchQuery.value.trim().toUpperCase()
  const sourceRows = isCryptoMode.value ? cryptoExploreUniverseRows.value : (query ? fullMarketBoardRows.value : visibleExploreRows.value)

  if (!query) {
    return sourceRows
  }

  const filteredRows = sourceRows.filter((row) => doesExploreRowMatchQuery(row, query))
  if (isCryptoMode.value) {
    return filteredRows
  }

  const mergedRows = new Map()
  filteredRows.forEach((row) => {
    mergedRows.set(row.symbol, row)
  })
  exploreLiveSearchRows.value
    .filter((row) => doesExploreRowMatchQuery(row, query))
    .forEach((row) => {
      mergedRows.set(row.symbol, row)
    })

  return [...mergedRows.values()]
})
const filteredCryptoExploreRows = computed(() => {
  const query = exploreSearchQuery.value.trim().toUpperCase()

  if (!query) {
    return cryptoExploreUniverseRows.value
  }

  return cryptoExploreUniverseRows.value.filter((row) => {
    const symbol = String(row.symbol || '').toUpperCase()
    const name = String(row.name || '').toUpperCase()
    const category = String(row.category || '').toUpperCase()
    return symbol.includes(query) || name.includes(query) || category.includes(query)
  })
})
const portfolioSymbols = computed(() => {
  return [...new Set(holdings.value.map((holding) => String(holding.symbol || '').trim().toUpperCase()).filter(Boolean))]
})
const activeStarredSymbols = computed(() => (isCryptoMode.value ? cryptoStarredSymbols.value : starredSymbols.value))
const starredLookup = computed(() => new Set(activeStarredSymbols.value))
const dashboardWatchlistRows = computed(() => {
  return activeStarredSymbols.value
    .map((symbol) => {
      const cleanedSymbol = String(symbol || '').trim().toUpperCase()
      if (isCryptoMode.value) {
        const cryptoRow = cryptoExploreUniverseRows.value.find((row) => row.symbol === cleanedSymbol)
        if (cryptoRow) {
          return {
            symbol: cryptoRow.symbol,
            price: '--',
            change: '--',
            tone: 'neutral',
            note: cryptoRow.category
          }
        }

        return {
          symbol: cleanedSymbol,
          price: '--',
          change: '--',
          tone: 'neutral',
          note: 'Saved crypto'
        }
      }

      const liveQuote = liveStockQuoteLookup.value[cleanedSymbol]
      if (liveQuote) {
        return liveQuote
      }

      if (String(stockResponse.value?.stock?.symbol || '').toUpperCase() === cleanedSymbol && stockResponse.value?.dataSource === 'live') {
        const responseQuote = buildLiveStockQuoteRow(cleanedSymbol, stockResponse.value.stock)
        if (responseQuote) {
          return {
            ...responseQuote,
            note: 'Recently viewed'
          }
        }
      }

      const marketRow = fullMarketBoardRows.value.find((row) => row.symbol === cleanedSymbol)
      return {
        symbol: cleanedSymbol,
        price: '--',
        change: '--',
        tone: 'neutral',
        note: marketRow?.category || 'Saved stock'
      }
    })
})
const sortedWatchlistScanResults = computed(() => {
  return [...watchlistScanResults.value].sort((left, right) => right.probability - left.probability)
})
const watchlistScanThresholdLabel = computed(() => `${normalizeProbabilityThreshold(watchlistScanThreshold.value).toFixed(0)}%`)
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
  if (activeTradeResponse.value.dataSource === 'idle') {
    return {
      label: 'Market Data',
      description: 'Search a symbol to load market data',
      tone: 'live'
    }
  }

  if (activeTradeResponse.value.dataSource === 'live') {
    return {
      label: 'Market Data',
      description: 'Connected market feed',
      tone: 'live'
    }
  }

  if (activeTradeResponse.value.dataSource === 'cached') {
    return {
      label: 'Market Data',
      description: 'Connected market feed',
      tone: 'live'
    }
  }

  if (activeTradeResponse.value.dataSource === 'demo') {
    return {
      label: 'Market Data',
      description: 'Loading market feed',
      tone: 'live'
    }
  }

  return {
    label: 'Market Data',
    description: 'Loading market feed',
    tone: 'live'
  }
})
const voiceActionLabel = computed(() => {
  if (isGenerating.value) {
    return t('generating')
  }

  if (isSearching.value) {
    return t('searching')
  }

  if (voiceIsSpeaking.value) {
    return t('speaking')
  }

  if (voiceListening.value) {
    return t('listening')
  }

  return voiceAssistantEnabled.value ? t('aiModeOnShort') : t('aiModeOffShort')
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
  const savedCount = activeStarredSymbols.value.length
  const qualifiedCount = sortedWatchlistScanResults.value.length
  const bestMatch = sortedWatchlistScanResults.value[0]

  return [
    { label: 'Saved Symbols', value: String(savedCount), note: `${isCryptoMode.value ? 'Crypto assets' : 'Stocks'} pinned for batch scanning` },
    { label: 'Scan Threshold', value: watchlistScanThresholdLabel.value, note: 'Minimum upside probability required to pass' },
    { label: 'Qualified Matches', value: String(qualifiedCount), note: qualifiedCount ? 'Sorted from highest probability to lowest' : 'Run Scan to generate ranked probabilities' },
    { label: 'Best Probability', value: bestMatch ? `${bestMatch.probability.toFixed(2)}%` : 'Pending', note: bestMatch ? `${bestMatch.symbol} is currently the strongest match` : 'Waiting for the next scan result' }
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
  const setupCandles = replayPattern.value.historicalCandles || []
  const futureCandles = (replayPattern.value.futureCandles || []).slice(0, setupCandles.length)
  const candles = [...setupCandles, ...futureCandles]

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
  if (typeof window !== 'undefined') {
    const savedLanguage = window.localStorage?.getItem(UI_LANGUAGE_KEY)
    if (languageOptions.some((language) => language.code === savedLanguage)) {
      uiLanguage.value = savedLanguage
    }

    const savedMode = window.localStorage?.getItem(APP_MODE_KEY)
    if (['stock', 'crypto'].includes(savedMode)) {
      appMode.value = savedMode
    }
  }

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

watch([activeMarketSymbol, feedRefreshKey, appMode], () => {
  loadMarketNews()
})

watch(uiLanguage, (language) => {
  if (typeof window !== 'undefined') {
    window.localStorage?.setItem(UI_LANGUAGE_KEY, language)
  }

  refreshPreferredVoice()

  if (voiceRecognition.value) {
    voiceRecognition.value.lang = getSpeechLanguage()
  }
})

watch(appMode, (mode) => {
  if (typeof window !== 'undefined') {
    window.localStorage?.setItem(APP_MODE_KEY, mode)
  }

  if (mode === 'crypto' && isAuthenticated.value) {
    void loadCryptoExploreUniverse()
  }
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
  clearExploreLiveSearchTimer()
  clearStockMatchDetailReveal()
  if (stockChartWarmTimer) {
    window.clearTimeout(stockChartWarmTimer)
    stockChartWarmTimer = null
  }

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
      installMessage.value = 'NoobTrade is being added as an app on this device.'
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
  if (isCryptoMode.value) {
    marketNewsFeed.value = []
    return
  }

  try {
    const response = await fetch(`${API_BASE_URL}/market-news?symbol=${encodeURIComponent(activeMarketSymbol.value)}&limit=5`)
    const payload = await parseJsonResponse(
      response,
      'The server returned a non-JSON response while loading market news.'
    )

    if (!response.ok) {
      throw new Error(payload.message || 'Could not load market news.')
    }

    marketNewsFeed.value = Array.isArray(payload.items) ? payload.items : []
  } catch (error) {
    marketNewsFeed.value = buildHourlyNewsFeed(activeMarketSymbol.value, feedRefreshKey.value)
  }
}

function createDefaultResponse() {
  return {
    dataSource: 'idle',
    request: {
      symbol: '',
      interval: 'daily',
      indicators: []
    },
    stock: {
      symbol: '',
      companyName: 'Search a stock',
      sector: 'Market Data',
      industry: 'Search first',
      currentPrice: null,
      previousClose: null,
      open: null,
      volume: 0,
      week52High: null,
      week52Low: null
    },
    patternAnalysis: {
      selectedIndicators: [],
      probabilityOfIncrease: null,
      probabilityOfDecrease: null,
      avgReturn: null,
      maxDrawdown: null,
      matchedPatternsCount: 0,
      signalClassification: 'Search first',
      futureFiveDayProbabilities: {
        up: [],
        down: []
      },
      recommendedSellPrice: null,
      recommendedSellDate: null,
      stopLossPrice: null,
      matchedHistoricalPatterns: [],
      highFitHistoricalPaths: []
    },
    chartData: {
      series: {}
    }
  }
}

function createCryptoWorkspaceResponse(symbol = '') {
  const normalizedSymbol = String(symbol || '').trim().toUpperCase()
  if (!normalizedSymbol) {
    return {
      ...createDefaultResponse(),
      stock: {
        symbol: '',
        companyName: 'Search a crypto asset',
        sector: 'Crypto',
        industry: 'Search first',
        currentPrice: null,
        previousClose: null,
        open: null,
        volume: 0,
        week52High: null,
        week52Low: null
      },
      patternAnalysis: {
        ...createDefaultResponse().patternAnalysis,
        signalClassification: 'Search first'
      }
    }
  }

  return {
    dataSource: 'idle',
    request: {
      symbol: normalizedSymbol,
      interval: 'daily',
      indicators: []
    },
    stock: {
      symbol: normalizedSymbol,
      companyName: `${normalizedSymbol} Crypto`,
      sector: 'Crypto',
      industry: 'Search first',
      currentPrice: null,
      previousClose: null,
      open: null,
      volume: 0,
      week52High: null,
      week52Low: null
    },
    patternAnalysis: {
      selectedIndicators: [],
      probabilityOfIncrease: null,
      probabilityOfDecrease: null,
      avgReturn: null,
      maxDrawdown: null,
      matchedPatternsCount: 0,
      signalClassification: 'Search first',
      futureFiveDayProbabilities: {
        up: [],
        down: []
      },
      recommendedSellPrice: null,
      recommendedSellDate: null,
      stopLossPrice: null,
      matchedHistoricalPatterns: [],
      highFitHistoricalPaths: []
    },
    chartData: {
      series: {}
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
    { id: 4, date: '2026-03-18', symbol: 'JPM', side: 'Buy', quantity: 12, price: 198.6, total: 2383.2, status: 'Filled' }
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

function formatProbabilityDisplay(value) {
  if (value === null || value === undefined || value === '') {
    return '--'
  }

  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) {
    return '--'
  }

  return `${numericValue.toFixed(0)}%`
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(value)
}

function formatMarketPrice(value) {
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) {
    return '--'
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(numericValue)
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
  const cleanedSymbol = String(symbol || '').trim().toUpperCase()
  const parseDisplayPrice = (value) => {
    const parsed = Number(String(value || '').replace('$', '').replace(',', ''))
    return Number.isFinite(parsed) ? parsed : 0
  }

  if (cleanedSymbol === String(stockResponse.value.stock.symbol || '').toUpperCase() && stockResponse.value.dataSource === 'live') {
    const price = Number(stockResponse.value.stock.currentPrice)
    return Number.isFinite(price) ? price : 0
  }

  if (cleanedSymbol === String(cryptoResponse.value.stock.symbol || '').toUpperCase() && cryptoResponse.value.dataSource === 'live') {
    const price = Number(cryptoResponse.value.stock.currentPrice)
    return Number.isFinite(price) ? price : 0
  }

  const liveQuote = liveStockQuoteLookup.value[cleanedSymbol]
  if (liveQuote) {
    return parseDisplayPrice(liveQuote.price)
  }

  const starredRow = dashboardWatchlistRows.value.find((row) => row.symbol === cleanedSymbol)
  if (starredRow) {
    return parseDisplayPrice(starredRow.price)
  }

  return 0
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

function getAllIndicatorNames() {
  return indicators.value.map((indicator) => indicator.name)
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
      voiceStatus.value = getVoiceShortReply('unsupported')
    }
    return
  }

  const recognition = new SpeechRecognitionConstructor()
  recognition.lang = getSpeechLanguage()
  recognition.continuous = true
  recognition.interimResults = true
  recognition.maxAlternatives = 1

  recognition.onstart = () => {
    voiceListening.value = true
    voiceStatus.value = getVoiceShortReply('listen')
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
      setVoiceShortStatus('unsupported', { speak: false })
      return
    }

    if (errorName !== 'no-speech' && errorName !== 'aborted') {
      setVoiceShortStatus('misunderstood', { speak: false, resetErrorCount: false })
    }

    scheduleVoiceRestart(900)
  }

  recognition.onresult = (event) => {
    const results = Array.from(event.results || [])
      .slice(event.resultIndex || 0)

    const interimTranscript = results
      .filter((result) => !result?.isFinal)
      .map((result) => result?.[0]?.transcript || '')
      .join(' ')
      .trim()

    const finalTranscript = results
      .filter((result) => result?.isFinal)
      .map((result) => result?.[0]?.transcript || '')
      .join(' ')
      .trim()

    const liveTranscript = finalTranscript || interimTranscript
    if (liveTranscript) {
      voiceTranscript.value = liveTranscript
      interruptVoiceSpeechForUserInput(liveTranscript)
    }

    if (finalTranscript) {
      handleVoiceCommand(finalTranscript).catch((error) => {
        console.error(error)
        reportVoiceMisunderstanding(finalTranscript)
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
  ) {
    return
  }

  clearVoiceRestartTimer()
  voiceRestartTimer = window.setTimeout(() => {
    voiceRestartTimer = null

    if (!voiceAssistantEnabled.value || voiceListening.value) {
      return
    }

    startVoiceListening({ silent: true, cancelSpeech: false })
  }, delayMs)
}

function getPreferredVoice() {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    return null
  }

  const voices = window.speechSynthesis.getVoices?.() || []
  const speechLang = getSpeechLanguage()
  const languagePrefix = speechLang.split('-')[0]
  const matchingVoices = voices.filter((voice) => String(voice.lang || '').toLowerCase().startsWith(languagePrefix))
  const preferredNamesByLanguage = {
    en: ['Samantha', 'Victoria', 'Ava', 'Allison', 'Susan', 'Karen', 'Moira', 'Tessa', 'Fiona', 'Google US English', 'Microsoft Aria', 'Microsoft Jenny', 'Microsoft Zira'],
    zh: ['Ting-Ting', 'Mei-Jia', 'Sin-ji', 'Google 普通话', 'Google 國語', 'Microsoft Xiaoxiao', 'Microsoft Huihui', 'Li-Mu'],
    es: ['Monica', 'Paulina', 'Marisol', 'Google español', 'Microsoft Elvira', 'Microsoft Helena'],
    fr: ['Amelie', 'Audrey', 'Aurelie', 'Google français', 'Microsoft Denise', 'Microsoft Hortense']
  }
  const preferredNames = preferredNamesByLanguage[uiLanguage.value] || preferredNamesByLanguage.en

  for (const preferredName of preferredNames) {
    const matchedVoice = matchingVoices.find((voice) => voice.name.toLowerCase().includes(preferredName.toLowerCase()))
    if (matchedVoice) {
      return matchedVoice
    }
  }

  return matchingVoices[0] || voices[0] || null
}

function getReadableMarketDataError(message, symbol = '') {
  const rawMessage = String(message || '').trim()
  const normalizedMessage = rawMessage.toLowerCase()
  const rawSymbol = symbol || symbolInput.value || activeSymbol.value
  const normalizedSymbol = rawSymbol
    ? normalizeTradeSymbolInput(rawSymbol, { isCrypto: activePage.value === 'Crypto Trade' })
    : ''
  const symbolLabel = normalizedSymbol || 'This symbol'
  const hasTechnicalDetails = hasTechnicalMarketDataDetails(rawMessage)

  if (hasTechnicalDetails) {
    return `${symbolLabel} market data connection timed out. Please try again in a moment.`
  }

  if (normalizedMessage.includes('temporarily unavailable') || normalizedMessage.includes('temporarily disabled') || normalizedMessage.includes('not accessible')) {
    return `${symbolLabel} data is not accessible right now. Please try again in a moment.`
  }

  if (rawMessage.length > 220) {
    return `${symbolLabel} data request did not finish cleanly. Please try again in a moment.`
  }

  return rawMessage || 'This data is not accessible right now.'
}

function hasTechnicalMarketDataDetails(message) {
  const normalizedMessage = String(message || '').toLowerCase()
  return voiceTechnicalErrorPatterns.some((pattern) => normalizedMessage.includes(pattern))
}

function getSpeakableVoiceText(text) {
  const rawText = String(text || '').trim()
  const readableText = hasTechnicalMarketDataDetails(rawText)
    ? getReadableMarketDataError(rawText)
    : rawText

  if (readableText.length <= voiceSpeechMaxCharacters) {
    return readableText
  }

  const firstSentence = readableText.match(/^.{36,160}?[.!?。！？](?:\s|$)/u)?.[0]?.trim()
  if (firstSentence) {
    return firstSentence
  }

  return `${readableText.slice(0, voiceSpeechMaxCharacters).trim()}...`
}

function isVoiceOutputActive() {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    return voiceIsSpeaking.value
  }

  return voiceIsSpeaking.value || window.speechSynthesis.speaking || window.speechSynthesis.pending
}

function interruptVoiceSpeechForUserInput(transcript) {
  const normalizedTranscript = normalizeVoiceText(transcript)

  if (!normalizedTranscript || !isVoiceOutputActive()) {
    return false
  }

  if (isLikelyAssistantSpeechEcho(normalizedTranscript)) {
    return false
  }

  stopVoiceSpeech({ restartListening: false })
  voiceStatus.value = getVoiceShortReply('listen')
  return true
}

function stopVoiceSpeech({ restartListening = true } = {}) {
  if (typeof window !== 'undefined') {
    window.speechSynthesis?.cancel()
  }

  voiceSpeechToken += 1
  voiceIsSpeaking.value = false

  if (restartListening) {
    scheduleVoiceRestart(120)
  }
}

function speakVoice(text) {
  if (typeof window === 'undefined' || !window.speechSynthesis || !text) {
    return
  }

  const speakableText = getSpeakableVoiceText(text)
  const speechSignature = normalizeVoiceText(speakableText)
  const now = Date.now()

  if (speechSignature && speechSignature === voiceLastSpeechSignature && now - voiceLastSpeechAt < 7000) {
    return
  }

  window.speechSynthesis.cancel()
  const speechToken = voiceSpeechToken + 1
  voiceSpeechToken = speechToken
  voiceLastSpeechSignature = speechSignature
  voiceLastSpeechAt = now

  const utterance = new SpeechSynthesisUtterance(speakableText)
  const preferredVoice = getPreferredVoice()

  if (preferredVoice) {
    utterance.voice = preferredVoice
    utterance.lang = preferredVoice.lang || 'en-US'
    voicePreferredVoiceName.value = preferredVoice.name
  } else {
    utterance.lang = getSpeechLanguage()
  }

  utterance.rate = 0.94
  utterance.pitch = 1.08
  utterance.volume = 0.88
  utterance.onstart = () => {
    if (speechToken === voiceSpeechToken) {
      voiceIsSpeaking.value = true
      scheduleVoiceRestart(220)
    }
  }
  utterance.onend = () => {
    if (speechToken === voiceSpeechToken) {
      voiceIsSpeaking.value = false
      scheduleVoiceRestart(420)
    }
  }
  utterance.onerror = () => {
    if (speechToken === voiceSpeechToken) {
      voiceIsSpeaking.value = false
      scheduleVoiceRestart(420)
    }
  }
  window.speechSynthesis.speak(utterance)
}

function setVoiceStatus(message, { speak = false, transcript = '' } = {}) {
  voiceStatus.value = message

  if (transcript || message) {
    const latestLog = voiceCommandLog.value[0]
    const sameLog = latestLog
      && normalizeVoiceText(latestLog.transcript) === normalizeVoiceText(transcript || 'Noob AI')
      && normalizeVoiceText(latestLog.response) === normalizeVoiceText(message)

    if (!sameLog) {
      voiceCommandLog.value = [
        {
          transcript: transcript || 'Noob AI',
          response: message,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        },
        ...voiceCommandLog.value
      ].slice(0, 4)
    }
  }

  if (speak) {
    speakVoice(message)
  }
}

function detectVoiceReplyLanguage(text = '') {
  const rawText = String(text || '')
  const normalizedText = normalizeVoiceText(rawText)

  if (/[\u4e00-\u9fff]/u.test(rawText)) {
    return 'zh'
  }

  if (includesVoicePhrase(normalizedText, ['hola', 'espanol', 'español', 'gracias', 'ayuda', 'abrir', 'buscar', 'escanear', 'quiero', 'necesito', 'noticias'])) {
    return 'es'
  }

  if (includesVoicePhrase(normalizedText, ['bonjour', 'francais', 'français', 'merci', 'aide', 'ouvrir', 'chercher', 'scanner', 'je veux', 'j ai besoin', 'nouvelles'])) {
    return 'fr'
  }

  return uiLanguage.value || 'en'
}

function getVoiceShortReply(key, language = uiLanguage.value) {
  const replies = voiceShortReplies[language] || voiceShortReplies.en
  return replies[key] || voiceShortReplies.en[key] || ''
}

function setVoiceShortStatus(key, { speak = true, transcript = '', resetErrorCount = true, language = '' } = {}) {
  if (resetErrorCount) {
    voiceMisunderstandingCount.value = 0
  }

  const message = getVoiceShortReply(key, language || detectVoiceReplyLanguage(transcript))
  setVoiceStatus(message, { speak, transcript })
}

function reportVoiceMisunderstanding(transcript = '') {
  voiceMisunderstandingCount.value += 1
  setVoiceShortStatus(
    voiceMisunderstandingCount.value >= 3 ? 'manualFallback' : 'misunderstood',
    {
      speak: true,
      transcript,
      resetErrorCount: false
    }
  )
}

function getNavigationShortReply(page, transcript = '') {
  const language = detectVoiceReplyLanguage(transcript)
  return page === 'Dashboard' ? getVoiceShortReply('dashboard', language) : getVoiceShortReply('pageOpened', language)
}

function openVoiceNewsPanel(transcript = '') {
  navigateTo('Markets')

  if (typeof window !== 'undefined') {
    window.setTimeout(() => {
      document.querySelector('.news-ticker-window')?.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      })
    }, 120)
  }

  setVoiceShortStatus('news', { transcript })
}

function openVoiceFullMarketBoard(transcript = '') {
  if (!isAuthenticated.value) {
    activePage.value = 'Sign In'
    setVoiceShortStatus('signIn', { transcript })
    return true
  }

  appMode.value = 'stock'
  activePage.value = 'Explore'
  exploreViewMode.value = 'full'
  exploreSearchQuery.value = ''
  setVoiceShortStatus('pageOpened', { transcript })
  return true
}

function revealVoiceMoreMarketRows(transcript = '') {
  if (!isAuthenticated.value) {
    activePage.value = 'Sign In'
    setVoiceShortStatus('signIn', { transcript })
    return true
  }

  appMode.value = 'stock'
  activePage.value = 'Explore'
  exploreViewMode.value = 'full'
  exploreSearchQuery.value = ''

  if (hasMoreStockMarketRows.value) {
    revealMoreStockMarketRows()
    setVoiceShortStatus('more', { transcript })
    return true
  }

  setVoiceShortStatus('done', { transcript })
  return true
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
    voiceStatus.value = getVoiceShortReply('ready')
  }
}

function minimizeVoiceAssistantPanel() {
  voiceAssistantOpen.value = false
}

function enableVoiceAssistant() {
  if (!isAuthenticated.value) {
    setVoiceShortStatus('signIn')
    return
  }

  voiceAssistantOpen.value = true
  voiceAssistantEnabled.value = true
  initializeVoiceAssistant()
  refreshPreferredVoice()

  if (!voiceSupported.value || !voiceRecognition.value) {
    voiceAssistantEnabled.value = false
    setVoiceShortStatus('unsupported')
    return
  }

  setVoiceShortStatus('ready')
  scheduleVoiceRestart(900)
}

function disableVoiceAssistant() {
  voiceAssistantEnabled.value = false
  voicePendingAction.value = null
  clearVoiceRestartTimer()
  stopVoiceListening()
  stopVoiceSpeech({ restartListening: false })
  voiceStatus.value = getVoiceShortReply('stopped')
}

function startVoiceListening({ silent = false, cancelSpeech = true } = {}) {
  if (!isAuthenticated.value) {
    setVoiceShortStatus('signIn')
    return
  }

  initializeVoiceAssistant()

  if (!voiceSupported.value || !voiceRecognition.value) {
    setVoiceShortStatus('unsupported')
    return
  }

  try {
    if (cancelSpeech) {
      stopVoiceSpeech({ restartListening: false })
    }
    voiceRecognition.value.lang = getSpeechLanguage()
    voiceRecognition.value.start()
  } catch {
    if (!silent) {
      setVoiceShortStatus('listen', { speak: false })
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
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^\p{Letter}\p{Number}%.\s-]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function includesVoicePhrase(command, phrases) {
  const normalizedCommand = normalizeVoiceText(command)
  return phrases.some((phrase) => normalizedCommand.includes(normalizeVoiceText(phrase)))
}

function normalizeTradeSymbolInput(rawValue, { isCrypto = false } = {}) {
  const rawSymbol = String(rawValue || '').trim()
  const compactSymbol = rawSymbol.replace(/\s+/g, '').toUpperCase()

  if (!compactSymbol) {
    return ''
  }

  if (isCrypto) {
    return compactSymbol
  }

  const stockCorrections = {
    APL: 'AAPL',
    APPL: 'AAPL',
    BRKB: 'BRK.B',
    'BRK-B': 'BRK.B',
    BRK_B: 'BRK.B',
    BFB: 'BF.B',
    'BF-B': 'BF.B',
    BF_B: 'BF.B'
  }

  return stockCorrections[compactSymbol] || compactSymbol
}

function findVoiceSymbolAlias(command) {
  const normalizedCommand = normalizeVoiceText(command)
  const framedCommand = ` ${normalizedCommand} `
  const aliases = Object.entries(voiceSymbolAliases)
    .map(([alias, symbol]) => [normalizeVoiceText(alias), symbol])
    .filter(([alias]) => alias)
    .sort((left, right) => right[0].length - left[0].length)

  for (const [alias, symbol] of aliases) {
    if (framedCommand.includes(` ${alias} `)) {
      return symbol
    }
  }

  return ''
}

function isLikelyAssistantSpeechEcho(command) {
  if (!isVoiceOutputActive() || !voiceLastSpeechSignature) {
    return false
  }

  const normalizedCommand = normalizeVoiceText(command)
  if (normalizedCommand.length < 8) {
    return false
  }

  if (voiceLastSpeechSignature.includes(normalizedCommand) || normalizedCommand.includes(voiceLastSpeechSignature)) {
    return true
  }

  const commandTokens = new Set(normalizedCommand.split(' ').filter((token) => token.length > 2))
  const speechTokens = new Set(voiceLastSpeechSignature.split(' ').filter((token) => token.length > 2))
  if (!commandTokens.size || !speechTokens.size) {
    return false
  }

  const speechTokenList = [...speechTokens]
  const overlap = [...commandTokens].filter((token) => (
    speechTokens.has(token)
    || speechTokenList.some((speechToken) => (
      token.length > 4
      && speechToken.length > 4
      && (speechToken.startsWith(token.slice(0, 5)) || token.startsWith(speechToken.slice(0, 5)))
    ))
  )).length
  return overlap / commandTokens.size >= 0.75
}

function fuzzyMatchVoicePhrase(command, documents, fuse, { maxScore = 0.42 } = {}) {
  const normalizedCommand = normalizeVoiceText(command)

  if (!normalizedCommand || !documents.length) {
    return null
  }

  const exactMatch = documents.find((document) => (
    normalizedCommand.includes(document.phrase) || document.phrase.includes(normalizedCommand)
  ))

  if (exactMatch) {
    return { ...exactMatch, score: 0 }
  }

  const tokens = normalizedCommand.split(' ').filter((token) => token.length > 2)
  const tokenWindows = []

  for (let index = 0; index < tokens.length; index += 1) {
    tokenWindows.push(tokens[index])

    if (tokens[index + 1]) {
      tokenWindows.push(`${tokens[index]} ${tokens[index + 1]}`)
    }

    if (tokens[index + 2]) {
      tokenWindows.push(`${tokens[index]} ${tokens[index + 1]} ${tokens[index + 2]}`)
    }
  }

  const queries = [normalizedCommand, ...tokenWindows]
  let bestMatch = null

  queries.forEach((query) => {
    const [result] = fuse.search(query, { limit: 1 })

    if (!result || result.score > maxScore) {
      return
    }

    if (!bestMatch || result.score < bestMatch.score) {
      bestMatch = { ...result.item, score: result.score }
    }
  })

  return bestMatch
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

function resolveVoiceSymbol(rawValue, { allowLooseTicker = true } = {}) {
  const cleanedValue = normalizeVoiceText(rawValue)
  if (!cleanedValue) {
    return ''
  }

  const directAlias = findVoiceSymbolAlias(cleanedValue)
  if (directAlias) {
    return directAlias
  }

  const compactValue = cleanedValue.replace(/\s+/g, '')
  if (voiceSymbolAliases[compactValue]) {
    return voiceSymbolAliases[compactValue]
  }

  if (allowLooseTicker && /^[a-z0-9]{1,10}$/.test(compactValue)) {
    return normalizeTradeSymbolInput(compactValue)
  }

  return ''
}

function extractVoiceSymbol(command, { allowLooseTicker = true } = {}) {
  const aliasSymbol = findVoiceSymbolAlias(command)
  if (aliasSymbol) {
    return aliasSymbol
  }

  const commandWords = new Set([
    'generate', 'search', 'analyze', 'analyse', 'run', 'for', 'stock', 'crypto', 'ticker', 'symbol',
    'quote', 'price', 'open', 'go', 'to', 'page', 'trade', 'look', 'up', 'down', 'top', 'bottom',
    'scroll', 'scrolling', 'move', 'screen', 'little', 'bit', 'more', 'less', 'back', 'forward',
    'show', 'the', 'a', 'stocks', 'market', 'markets', 'analysis', 'scorlling', 'scorll',
    'scrool', 'scroolling', 'lower', 'higher', 'again', 'continue', 'further',
    'full', 'board', 'pool', 'universe', 'guide', 'manual', 'user', 'learn'
  ])
  const tokens = command.split(' ').filter(Boolean)

  if (!allowLooseTicker) {
    return ''
  }

  for (let index = tokens.length - 1; index >= 0; index -= 1) {
    const token = tokens[index]
    if (!commandWords.has(token) && /^[a-z0-9]{1,10}$/.test(token)) {
      return resolveVoiceSymbol(token)
    }
  }

  return ''
}

function extractVoiceProbability(command, fallback = watchlistScanThreshold.value) {
  const explicitPercent = command.match(/(\d{1,3}(?:\.\d+)?)\s*(percent|per cent|%)/)

  if (explicitPercent) {
    return normalizeProbabilityThreshold(explicitPercent[1])
  }

  const numericToken = command.match(/\b(\d{1,3}(?:\.\d+)?)\b/)
  return numericToken ? normalizeProbabilityThreshold(numericToken[1]) : normalizeProbabilityThreshold(fallback)
}

function getScrollDistance(command) {
  if (includesVoicePhrase(command, ['a little', 'little bit', 'small scroll', 'little more', 'bit more', 'a little bit more', '再来一点', '再一点', '一点', 'un poco', 'un peu'])) {
    return 0.3
  }

  if (includesVoicePhrase(command, ['a lot', 'big scroll', 'far down', 'far up', 'much more', 'a lot more', '很多', '多一点', 'mucho mas', 'mucho más', 'beaucoup plus'])) {
    return 1
  }

  return 0.68
}

function getScrollDistanceFromAmount(amount) {
  if (amount === 'small') {
    return 0.3
  }

  if (amount === 'large' || amount === 'full') {
    return 1
  }

  return 0.68
}

function rememberVoiceIntent(type, direction = '') {
  voiceLastIntent.value = {
    type,
    direction,
    at: Date.now()
  }
}

function hasVoiceScrollDirection(command) {
  return includesVoicePhrase(command, [
    'scroll', 'scorll', 'scrool', 'down', 'up', 'lower', 'higher', 'top', 'bottom',
    '滚动', '下', '上', '顶部', '底部',
    'abajo', 'arriba', 'bajar', 'subir',
    'defiler', 'défiler', 'bas', 'haut', 'descendre', 'monter'
  ])
}

function getVoiceScrollIntent(command) {
  const normalizedCommand = normalizeVoiceText(command)
  const recentScroll = voiceLastIntent.value.type === 'scroll'
    && Date.now() - voiceLastIntent.value.at < 45 * 1000

  if (recentScroll && includesVoicePhrase(normalizedCommand, voiceFollowUpPhrases)) {
    return voiceLastIntent.value.direction === 'up' ? 'scrollUp' : 'scrollDown'
  }

  if (!hasVoiceScrollDirection(normalizedCommand)) {
    return ''
  }

  const directIntent = fuzzyMatchVoicePhrase(
    normalizedCommand,
    voiceScrollIntentDocuments,
    voiceScrollIntentFuse,
    { maxScore: normalizedCommand.length <= 12 ? 0.36 : 0.46 }
  )

  if (directIntent) {
    return directIntent.intent
  }

  return ''
}

function executeVoiceScrollIntent(direction, amount = 'normal') {
  if (typeof window === 'undefined') {
    return ''
  }

  const normalizedDirection = String(direction || '').toLowerCase()
  const distance = Math.max(220, window.innerHeight * getScrollDistanceFromAmount(amount))

  if (normalizedDirection === 'down') {
    window.scrollBy({ top: distance, left: 0, behavior: 'smooth' })
    rememberVoiceIntent('scroll', 'down')
    return getVoiceShortReply('done')
  }

  if (normalizedDirection === 'up') {
    window.scrollBy({ top: -distance, left: 0, behavior: 'smooth' })
    rememberVoiceIntent('scroll', 'up')
    return getVoiceShortReply('done')
  }

  if (normalizedDirection === 'top') {
    window.scrollTo({ top: 0, behavior: 'smooth' })
    rememberVoiceIntent('scroll', 'up')
    return getVoiceShortReply('done')
  }

  if (normalizedDirection === 'bottom') {
    window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' })
    rememberVoiceIntent('scroll', 'down')
    return getVoiceShortReply('done')
  }

  return ''
}

function runVoiceScreenControl(command) {
  if (typeof window === 'undefined') {
    return ''
  }

  const scrollIntent = getVoiceScrollIntent(command)
  const amount = includesVoicePhrase(command, ['a little', 'little bit', 'small scroll', 'little more', 'bit more', 'a little bit more', '再来一点', '再一点', '一点', 'un poco', 'un peu'])
    ? 'small'
    : includesVoicePhrase(command, ['a lot', 'big scroll', 'far down', 'far up', 'much more', 'a lot more', '很多', '多一点', 'mucho mas', 'mucho más', 'beaucoup plus'])
      ? 'large'
      : 'normal'

  if (scrollIntent === 'scrollDown') {
    return executeVoiceScrollIntent('down', amount)
  }

  if (scrollIntent === 'scrollUp') {
    return executeVoiceScrollIntent('up', amount)
  }

  if (scrollIntent === 'scrollTop') {
    return executeVoiceScrollIntent('top', 'full')
  }

  if (scrollIntent === 'scrollBottom') {
    return executeVoiceScrollIntent('bottom', 'full')
  }

  if (includesVoicePhrase(command, ['go back', 'back page', 'previous page'])) {
    window.history.back()
    return getVoiceShortReply('done')
  }

  if (includesVoicePhrase(command, ['minimize ai', 'shrink ai', 'hide ai', 'close panel', 'close ai panel'])) {
    minimizeVoiceAssistantPanel()
    return getVoiceShortReply('done')
  }

  if (includesVoicePhrase(command, ['open ai panel', 'show ai panel', 'expand ai', 'open assistant'])) {
    openVoiceAssistantPanel()
    return getVoiceShortReply('done')
  }

  if (includesVoicePhrase(command, ['turn off ai', 'disable ai mode', 'stop ai mode'])) {
    disableVoiceAssistant()
    return getVoiceShortReply('stopped')
  }

  return ''
}

function routeVoiceSymbol(symbol) {
  const normalizedSymbol = normalizeTradeSymbolInput(symbol, { isCrypto: activePage.value === 'Crypto Trade' })
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
  const normalizedSymbol = resolveVoiceSymbol(symbol) || normalizeTradeSymbolInput(symbolInput.value || activeSymbol.value, { isCrypto: activePage.value === 'Crypto Trade' })

  if (normalizedSymbol) {
    routeVoiceSymbol(normalizedSymbol)
  } else if (!isTradeWorkspacePage.value) {
    navigateTo('Stock Trade')
  }

  setVoiceShortStatus(source === 'generate' ? 'generateStart' : 'searchStart', { transcript })
  await runSearch(source)

  if (errorMessage.value) {
    reportVoiceMisunderstanding(transcript)
    return
  }

  setVoiceShortStatus(source === 'generate' ? 'generateDone' : 'searchDone', { transcript })
}

function queueVoiceAction(action) {
  voicePendingAction.value = action
  setVoiceStatus(action.prompt, { speak: true })
}

function confirmVoiceAction() {
  const action = voicePendingAction.value

  if (!action) {
    reportVoiceMisunderstanding()
    return
  }

  voicePendingAction.value = null

  if (action.type === 'signOut') {
    signOut()
    setVoiceShortStatus('stopped')
  }
}

function cancelVoiceAction() {
  voicePendingAction.value = null
  setVoiceShortStatus('stopped')
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
  const pageLabel = formatPageLabel(activePage.value)
  const indicatorText = selected.length ? selected.join(', ') : 'none'

  if (uiLanguage.value === 'zh') {
    return `你现在在${pageLabel}页面。当前标的是 ${symbol}。已选择指标：${indicatorText}。`
  }

  if (uiLanguage.value === 'es') {
    return `Estás en ${pageLabel}. El símbolo actual es ${symbol}. Indicadores seleccionados: ${indicatorText}.`
  }

  if (uiLanguage.value === 'fr') {
    return `Vous êtes sur ${pageLabel}. Le symbole actuel est ${symbol}. Indicateurs sélectionnés : ${indicatorText}.`
  }

  return `You are on ${pageLabel}. Current symbol is ${symbol}. Selected indicators are ${indicatorText}.`
}

function buildConversationalReply(command) {
  if (includesVoicePhrase(command, ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'are you there', 'you there', 'noob trade', 'assistant', '你好', '您好', '嗨', '你在吗', '在吗', 'hola', 'bonjour', 'salut'])) {
    return getVoiceShortReply('ready')
  }

  if (includesVoicePhrase(command, ['thank you', 'thanks', 'nice', 'great', '谢谢', '感谢', 'gracias', 'merci'])) {
    return getVoiceShortReply('ready')
  }

  return getVoiceShortReply('misunderstood')
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
  let command = normalizeVoiceText(rawTranscript)
  let effectiveTranscript = rawTranscript
  let correctionTranscript = ''
  voiceTranscript.value = rawTranscript

  if (!command) {
    reportVoiceMisunderstanding(rawTranscript)
    return
  }

  if (isLikelyAssistantSpeechEcho(command)) {
    return
  }

  if (
    ['stop', 'cancel', 'pause', '停', '停止', '别念了', '不要念了'].includes(command)
    || includesVoicePhrase(command, voiceStopSpeechPhrases)
  ) {
    stopVoiceSpeech({ restartListening: true })
    voicePendingAction.value = null
    setVoiceShortStatus('stopped', { speak: false, transcript: rawTranscript })
    return
  }

  if (isVoiceOutputActive()) {
    stopVoiceSpeech({ restartListening: false })
  }

  if (isVoiceCorrectionCommand(command) && voiceLastAssistantPrediction.value) {
    const correctionText = extractVoiceCorrectionText(rawTranscript)
    if (!correctionText) {
      await saveAssistantFeedback({ correctionTranscript: rawTranscript })
      reportVoiceMisunderstanding(rawTranscript)
      return
    }

    correctionTranscript = correctionText
    effectiveTranscript = correctionText
    command = normalizeVoiceText(correctionText)
    voiceTranscript.value = correctionText
    setVoiceShortStatus('ready', { transcript: rawTranscript })
  }

  if (includesVoicePhrase(command, ['中文', 'chinese', 'mandarin', '普通话'])) {
    uiLanguage.value = 'zh'
    setVoiceShortStatus('ready', { transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['spanish', 'espanol', 'español'])) {
    uiLanguage.value = 'es'
    setVoiceShortStatus('ready', { transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['french', 'francais', 'français'])) {
    uiLanguage.value = 'fr'
    setVoiceShortStatus('ready', { transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['english', '英语', 'anglais', 'ingles'])) {
    uiLanguage.value = 'en'
    setVoiceShortStatus('ready', { transcript: rawTranscript })
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

  const assistantContext = buildAssistantIntentContext()
  const assistantIntent = await fetchAssistantIntent(effectiveTranscript)
  if (assistantIntent && await applyAssistantIntent(assistantIntent, effectiveTranscript)) {
    if (correctionTranscript) {
      await saveAssistantFeedback({
        correctionTranscript,
        correctedIntent: assistantIntent
      })
    }

    voiceLastAssistantPrediction.value = {
      transcript: effectiveTranscript,
      intent: assistantIntent,
      context: assistantContext,
      at: Date.now()
    }
    return
  }

  if (correctionTranscript) {
    await saveAssistantFeedback({ correctionTranscript })
  }

  if (includesVoicePhrase(command, ['help', 'what can you do', 'commands', '帮助', '帮我', '你会什么', 'ayuda', 'que puedes hacer', 'aide', 'que peux tu faire'])) {
    setVoiceShortStatus('ready', { transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['buy ', 'sell ', 'place order', 'submit order', 'market order', 'limit order', 'short ', 'go long', 'go short', '买入', '卖出', '下单', '做空', '做多', 'comprar', 'vender', 'orden', 'acheter', 'vendre', 'ordre'])) {
    setVoiceShortStatus('blockedTrading', { transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['sign out', 'log out', 'logout', '退出登录', '登出', 'cerrar sesion', 'cerrar sesión', 'deconnexion', 'déconnexion'])) {
    queueVoiceAction({
      type: 'signOut',
      prompt: getVoiceShortReply('ready')
    })
    return
  }

  if (includesVoicePhrase(command, ['open news', 'show news', 'read news', 'market news', 'latest news', '打开新闻', '查看新闻', '看新闻', '市场新闻', 'abrir noticias', 'mostrar noticias', 'ver noticias', 'ouvrir nouvelles', 'voir nouvelles', 'ouvrir les nouvelles'])) {
    openVoiceNewsPanel(rawTranscript)
    return
  }

  if (includesVoicePhrase(command, voiceViewMoreMarketPhrases)) {
    revealVoiceMoreMarketRows(rawTranscript)
    return
  }

  if (includesVoicePhrase(command, voiceFullMarketPhrases)) {
    openVoiceFullMarketBoard(rawTranscript)
    return
  }

  const requestedPage = findVoicePage(command)
  const guideQuestion = requestedPage === 'User Guide' && includesVoicePhrase(command, [
    'how noobtrade works', 'how noob trade works', 'how does noobtrade work', 'how does noob trade work',
    'what is noobtrade', 'what does noobtrade do', 'how it works',
    '怎么用', '如何使用', '工作原理', 'noobtrade是什么', 'noob trade是什么'
  ])
  if (requestedPage && (guideQuestion || includesVoicePhrase(command, ['open', 'go to', 'show', 'switch to', 'navigate', '打开', '进入', '切换到', '显示', 'abrir', 'ir a', 'mostrar', 'cambiar a', 'ouvrir', 'aller a', 'aller à', 'afficher', 'passer a', 'passer à']))) {
    navigateTo(requestedPage)
    setVoiceStatus(getNavigationShortReply(requestedPage, rawTranscript), { speak: true, transcript: rawTranscript })
    return
  }

  const screenControlReply = runVoiceScreenControl(command)
  if (screenControlReply) {
    setVoiceStatus(screenControlReply, { speak: true, transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['clear indicators', 'turn off all indicators', 'disable all indicators', '清空指标', '关闭所有指标', '取消所有指标', 'quitar todos los indicadores', 'desactivar todos los indicadores', 'retirer tous les indicateurs', 'desactiver tous les indicateurs'])) {
    indicators.value = indicators.value.map((indicator) => ({ ...indicator, active: false }))
    setVoiceShortStatus('indicators', { transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['reset indicators', 'default indicators', 'restore indicators', '重置指标', '默认指标', 'restablecer indicadores', 'indicadores predeterminados', 'retablir indicateurs', 'réinitialiser indicateurs'])) {
    const defaultSelected = new Set(['MA', 'EMA', 'MACD', 'BOLL', 'VOL'])
    indicators.value = indicators.value.map((indicator) => ({
      ...indicator,
      active: defaultSelected.has(String(indicator.name).toUpperCase())
    }))
    setVoiceShortStatus('indicators', { transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, [
    'scan', 'scan watchlist', 'scan saved', 'batch generate', 'full indicator scan', 'full indicators scan',
    '扫描', '扫描自选', '星标扫描', '集体generate', '批量generate', '全指标扫描',
    'escanear', 'scanner'
  ])) {
    const threshold = extractVoiceProbability(command)
    watchlistScanThreshold.value = threshold
    navigateTo('Dashboard')
    setVoiceShortStatus('scanStart', { transcript: rawTranscript })
    await scanStarredWatchlist()
    setVoiceShortStatus('scanDone', { transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['select all indicators', 'enable all indicators', 'turn on all indicators', '选择所有指标', '打开所有指标', 'seleccionar todos los indicadores', 'activar todos los indicadores', 'selectionner tous les indicateurs', 'activer tous les indicateurs'])) {
    indicators.value = indicators.value.map((indicator) => ({ ...indicator, active: true }))
    setVoiceShortStatus('indicators', { transcript: rawTranscript })
    return
  }

  const mentionedIndicators = findVoiceIndicators(command)
  if (mentionedIndicators.length) {
    if (includesVoicePhrase(command, voiceOnlyPhrases)) {
      setOnlyVoiceIndicators(mentionedIndicators)
      setVoiceShortStatus('indicators', { transcript: rawTranscript })
      return
    }

    if (includesVoicePhrase(command, voiceDisablePhrases)) {
      setIndicatorActive(mentionedIndicators, false)
      setVoiceShortStatus('indicators', { transcript: rawTranscript })
      return
    }

    if (!includesVoicePhrase(command, voiceEnablePhrases) && !includesVoicePhrase(command, ['indicator', 'indicators'])) {
      const toggledIndicator = toggleVoiceIndicator(mentionedIndicators[0])
      if (toggledIndicator) {
        setVoiceShortStatus('indicators', { transcript: rawTranscript })
        return
      }
    }

    if (includesVoicePhrase(command, voiceEnablePhrases) || includesVoicePhrase(command, ['indicator', 'indicators'])) {
      setIndicatorActive(mentionedIndicators, true)
      setVoiceShortStatus('indicators', { transcript: rawTranscript })
      return
    }
  }

  const requestedInterval = findVoiceInterval(command)
  if (requestedInterval && includesVoicePhrase(command, ['interval', 'chart', 'time frame', 'timeframe', 'switch', '周期', '图表', '切换', 'intervalo', 'grafico', 'gráfico', 'cambiar', 'intervalle', 'graphique', 'changer'])) {
    await handleChartIntervalChange(requestedInterval)
    setVoiceShortStatus('interval', { transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['generate', 'run analysis', 'analyze', 'analyse', '生成', '分析', 'analizar', 'genera', 'generar', 'analyse', 'analyser', 'generer', 'générer'])) {
    await runVoiceAnalysis('generate', extractVoiceSymbol(command), rawTranscript)
    return
  }

  if (includesVoicePhrase(command, ['search', 'look up', 'quote', 'price', '搜索', '查找', '查询', '价格', 'buscar', 'precio', 'cotizacion', 'cotización', 'chercher', 'rechercher', 'prix', 'cours'])) {
    await runVoiceAnalysis('search', extractVoiceSymbol(command), rawTranscript)
    return
  }

  const naturalSymbol = extractVoiceSymbol(command)
  if (naturalSymbol && includesVoicePhrase(command, ['show', 'check', 'open', 'load', 'what about', '看一下', '查看', '打开', '加载', 'mostrar', 'abrir', 'cargar', 'voir', 'ouvrir', 'charger'])) {
    await runVoiceAnalysis('search', naturalSymbol, rawTranscript)
    return
  }

  reportVoiceMisunderstanding(rawTranscript)
}

function navigateTo(page) {
  const pageAliases = {
    Analysis: 'Stock Trade',
    Myself: 'Settings'
  }
  const normalizedPage = pageAliases[page] || page

  if (normalizedPage === 'User Guide') {
    if (isAuthenticated.value) {
      openUserGuide()
      authMessage.value = ''
      errorMessage.value = ''
    } else {
      activePage.value = 'Sign In'
      authMessage.value = 'Please sign in first to open the guide.'
    }
    return
  }

  if (accessiblePages.value.includes(normalizedPage)) {
    activePage.value = normalizedPage
    authMessage.value = ''
    errorMessage.value = ''

    if (normalizedPage === 'Crypto Trade') {
      appMode.value = 'crypto'
      symbolInput.value = cryptoResponse.value.stock.symbol || ''
    } else if (normalizedPage === 'Stock Trade') {
      appMode.value = 'stock'
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

function toggleFullMarketBoard() {
  exploreViewMode.value = exploreViewMode.value === 'full' ? 'ranked' : 'full'
}

function revealMoreStockMarketRows() {
  stockMarketVisibleCount.value = Math.min(
    stockMarketVisibleCount.value + STOCK_MARKET_PAGE_SIZE,
    fullMarketBoardRows.value.length
  )
}

function normalizeCryptoExploreAsset(asset) {
  const symbol = normalizeTradeSymbolInput(asset?.symbol, { isCrypto: true })
  if (!symbol) {
    return null
  }

  const rawCategory = String(asset?.category || asset?.exchange || 'Crypto').trim()
  const price = Number(asset?.current_price)

  return {
    symbol,
    name: String(asset?.name || `${symbol} Crypto`).trim(),
    category: rawCategory === 'Market Cap Top Crypto' ? 'Crypto' : rawCategory,
    price: Number.isFinite(price) ? formatMarketPrice(price) : '--',
    notional: '--',
    change: '--',
    tone: 'neutral'
  }
}

function applyCryptoExploreUniverse(assets) {
  if (!Array.isArray(assets)) {
    return
  }

  const mergedRows = new Map()
  assets
    .map(normalizeCryptoExploreAsset)
    .filter(Boolean)
    .forEach((row) => {
      if (!mergedRows.has(row.symbol)) {
        mergedRows.set(row.symbol, row)
      }
    })

  if (!mergedRows.size) {
    return
  }

  cryptoExploreLiveRows.value = [...mergedRows.values()]
  cryptoExploreUniverseLoaded.value = true
  cryptoExploreLiveRows.value.forEach((row) => voiceCryptoSymbols.add(row.symbol))
}

async function loadCryptoExploreUniverse({ force = false } = {}) {
  if (!isAuthenticated.value && !force) {
    return
  }

  if (cryptoExploreUniverseLoaded.value && !force) {
    return
  }

  if (cryptoExploreUniverseLoadPromise && !force) {
    return cryptoExploreUniverseLoadPromise
  }

  cryptoExploreUniverseLoadPromise = (async () => {
    try {
      const query = new URLSearchParams({
        source: 'okx',
        limit: String(CRYPTO_EXPLORE_UNIVERSE_SIZE)
      })
      const response = await secureFetch(`${API_BASE_URL}/crypto/top50?${query.toString()}`, {
        timeoutMs: 12000
      })
      const payload = await parseJsonResponse(response, 'Could not load crypto assets right now.')

      if (!response.ok) {
        throw new Error(payload.message || 'Could not load crypto assets right now.')
      }

      applyCryptoExploreUniverse(payload.assets || [])
    } catch (error) {
      console.warn('Could not load crypto explore universe.', error)
    } finally {
      cryptoExploreUniverseLoadPromise = null
    }
  })()

  return cryptoExploreUniverseLoadPromise
}

function switchTradingMode() {
  const nextMode = isCryptoMode.value ? 'stock' : 'crypto'
  appMode.value = nextMode
  errorMessage.value = ''
  watchlistScanResults.value = []
  watchlistScanMessage.value = ''
  watchlistScanScannedAt.value = ''

  if (nextMode === 'crypto') {
    if (activePage.value === 'Stock Trade') {
      activePage.value = 'Crypto Trade'
      symbolInput.value = cryptoResponse.value.stock.symbol || ''
    }
    return
  }

  if (activePage.value === 'Crypto Trade') {
    activePage.value = 'Stock Trade'
    symbolInput.value = activeSymbol.value
  }
}

function selectPopularSymbol(symbol) {
  symbolInput.value = symbol
  runSearch()
}

function normalizeProbabilityThreshold(value) {
  const numericValue = Number(value)

  if (!Number.isFinite(numericValue)) {
    return 60
  }

  return Math.min(Math.max(numericValue, 0), 100)
}

function getAnalysisUpsideProbability(data) {
  const rawProbability = data?.patternAnalysis?.probabilityOfIncrease

  if (rawProbability !== null && rawProbability !== undefined && rawProbability !== '') {
    const directProbability = Number(rawProbability)
    if (Number.isFinite(directProbability)) {
      return directProbability
    }
  }

  const ladder = data?.patternAnalysis?.futureFiveDayProbabilities?.up || []
  const onePercentHit = ladder.find((item) => Number(item.threshold) === 1)
  const ladderProbability = Number(onePercentHit?.probability)

  return Number.isFinite(ladderProbability) ? ladderProbability : 0
}

function formatScanTimestamp(date = new Date()) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

async function runLimitedTasks(items, worker, limit = 4, onSettled = null) {
  const results = []
  let nextIndex = 0

  async function runWorker() {
    while (nextIndex < items.length) {
      const currentIndex = nextIndex
      nextIndex += 1

      try {
        results[currentIndex] = {
          status: 'fulfilled',
          value: await worker(items[currentIndex], currentIndex)
        }
      } catch (error) {
        results[currentIndex] = {
          status: 'rejected',
          reason: error
        }
      }

      if (typeof onSettled === 'function') {
        onSettled(results[currentIndex], items[currentIndex], currentIndex)
      }
    }
  }

  const workers = Array.from({ length: Math.min(limit, items.length) }, () => runWorker())
  await Promise.all(workers)
  return results
}

async function scanStarredWatchlist() {
  if (isWatchlistScanning.value) {
    return
  }

  const threshold = normalizeProbabilityThreshold(watchlistScanThreshold.value)
  watchlistScanThreshold.value = threshold
  const symbols = [...new Set(activeStarredSymbols.value.map((symbol) => String(symbol || '').trim().toUpperCase()).filter(Boolean))]

  if (!symbols.length) {
    watchlistScanResults.value = []
    watchlistScanMessage.value = isCryptoMode.value ? 'Star crypto assets first, then run a scan.' : 'Star stocks first, then run a scan.'
    return
  }

  isWatchlistScanning.value = true
  watchlistScanResults.value = []
  const scanIndicators = getAllIndicatorNames()
  watchlistScanMessage.value = `Scanning ${symbols.length} saved ${isCryptoMode.value ? 'crypto assets' : 'stocks'} with full-indicator Generate...`
  const passedResults = []
  const failedSymbols = []
  const scanBatchId = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
  let completedSymbols = 0

  const applyScanResult = (result, symbol) => {
    completedSymbols += 1

    if (result?.status !== 'fulfilled') {
      failedSymbols.push(symbol)
    } else if (result.value.probability >= threshold) {
      passedResults.push(result.value)
      watchlistScanResults.value = [...passedResults].sort((left, right) => right.probability - left.probability)
    }

    watchlistScanMessage.value = `Scanning ${symbols.length} saved ${isCryptoMode.value ? 'crypto assets' : 'stocks'}: ${completedSymbols}/${symbols.length} checked, ${passedResults.length} passed >= ${threshold.toFixed(0)}%.`
  }

  try {
    await runLimitedTasks(symbols, async (symbol) => {
      const data = isCryptoMode.value
        ? await fetchCryptoAnalysis(symbol, {
          analysisMode: 'full',
          compact: true,
          cacheResult: false,
          indicatorNames: scanIndicators,
          usageContext: 'dashboard-scan',
          usageBatchId: scanBatchId,
        })
        : await fetchStockAnalysis(symbol, {
          analysisMode: 'full',
          compact: true,
          cacheResult: false,
          indicatorNames: scanIndicators,
          usageContext: 'dashboard-scan',
          usageBatchId: scanBatchId,
        })
      const probability = getAnalysisUpsideProbability(data)
      const currentPrice = Number(data?.stock?.currentPrice)

      return {
        symbol,
        probability,
        price: Number.isFinite(currentPrice) ? formatCurrency(currentPrice) : '--',
        signal: data?.patternAnalysis?.signalClassification || 'Generated',
        matchedCount: Number(data?.patternAnalysis?.matchedPatternsCount || data?.patternAnalysis?.matchedHistoricalPatterns?.length || 0),
        dataSource: data?.dataSource || 'live'
      }
    }, symbols.length, applyScanResult)

    watchlistScanResults.value = passedResults.sort((left, right) => right.probability - left.probability)
    watchlistScanScannedAt.value = formatScanTimestamp()

    const passedLabel = `${watchlistScanResults.value.length}/${symbols.length} passed >= ${threshold.toFixed(0)}%`
    watchlistScanMessage.value = failedSymbols.length
      ? `${passedLabel}. ${failedSymbols.length} symbol${failedSymbols.length === 1 ? '' : 's'} could not be scanned.`
      : `${passedLabel}.`
  } catch (error) {
    watchlistScanMessage.value = error?.message || 'Watchlist scan could not finish right now.'
  } finally {
    isWatchlistScanning.value = false
  }
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

  appMode.value = 'stock'
  symbolInput.value = symbol
  activePage.value = 'Stock Trade'

  if (symbol !== activeSymbol.value || stockResponse.value?.dataSource !== 'live') {
    runSearch()
  }
}

function openCryptoAnalysis(symbol = '') {
  if (!isAuthenticated.value) {
    activePage.value = 'Sign In'
    authMessage.value = 'Please sign in first to access the crypto trade workspace.'
    return
  }

  const cleanedSymbol = normalizeTradeSymbolInput(symbol, { isCrypto: true })
  appMode.value = 'crypto'
  symbolInput.value = cleanedSymbol
  activePage.value = 'Crypto Trade'
  if (cleanedSymbol) {
    void runSearch()
  }
}

function openModeAnalysis(symbol) {
  if (isCryptoMode.value) {
    openCryptoAnalysis(symbol)
    return
  }

  openAnalysis(symbol)
}

function openUserGuide() {
  activePage.value = 'User Guide'
  requestAnimationFrame(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

function buildAnalysisCacheKey(
  symbol,
  analysisMode = 'full',
  assetType = 'stock',
  indicatorNames = getSelectedIndicators(),
  interval = selectedChartInterval.value
) {
  return [
    assetType,
    String(symbol || '').trim().toUpperCase(),
    interval,
    indicatorNames.join(','),
    analysisMode
  ].join('|')
}

function hasChartSeries(response, interval) {
  const candles = response?.chartData?.series?.[interval]
  return Array.isArray(candles) && candles.length > 0
}

function hasProbabilitySummary(response) {
  const patternAnalysis = response?.patternAnalysis || {}
  const directProbability = Number(patternAnalysis.probabilityOfIncrease)
  if (Number.isFinite(directProbability)) {
    return true
  }

  const ladderProbability = Number(
    patternAnalysis.futureFiveDayProbabilities?.up?.find((item) => Number(item.threshold) === 1)?.probability
  )
  return Number.isFinite(ladderProbability) || Number(patternAnalysis.matchedPatternsCount) > 0
}

function isCachedAnalysisUsable(response, { compact = false, interval = selectedChartInterval.value } = {}) {
  return compact ? hasProbabilitySummary(response) : hasChartSeries(response, interval)
}

async function fetchStockAnalysis(symbol, { analysisMode = 'full', compact = false, cacheResult = true, indicatorNames = null, matchDetails = false, usageContext = '', usageBatchId = '' } = {}) {
  const cleanedSymbol = normalizeTradeSymbolInput(symbol)
  const analysisIndicators = Array.isArray(indicatorNames) && indicatorNames.length ? indicatorNames : getSelectedIndicators()
  const requestInterval = analysisMode === 'full' ? STOCK_GENERATE_INTERVAL : selectedChartInterval.value
  const requiredChartInterval = compact ? STOCK_GENERATE_INTERVAL : selectedChartInterval.value
  const cacheKey = buildAnalysisCacheKey(cleanedSymbol, analysisMode, 'stock', analysisIndicators, requestInterval)

  if (cacheResult) {
    const cachedAnalysis = analysisCache.value[cacheKey]
    if (cachedAnalysis && isCachedAnalysisUsable(cachedAnalysis, { compact, interval: requiredChartInterval })) {
      return cachedAnalysis
    }

    if (cachedAnalysis) {
      const { [cacheKey]: _staleAnalysis, ...freshCache } = analysisCache.value
      analysisCache.value = freshCache
    }
  }

  const query = new URLSearchParams({
    indicators: analysisIndicators.join(','),
    analysis: analysisMode,
  })
  query.set('interval', STOCK_GENERATE_INTERVAL)
  query.set('chartInterval', compact ? STOCK_GENERATE_INTERVAL : selectedChartInterval.value)
  if (compact) {
    query.set('compact', '1')
  }
  if (matchDetails) {
    query.set('matchDetails', '1')
  }
  if (usageContext) {
    query.set('usage', usageContext)
  }
  if (usageBatchId) {
    query.set('scanBatchId', usageBatchId)
  }

  const requestUrl = `${API_BASE_URL}/stock/${encodeURIComponent(cleanedSymbol)}?${query.toString()}`
  const response = await fetchWithDatabaseWarmRetry(
    requestUrl,
    { timeoutMs: analysisMode === 'search' ? 12000 : 35000 },
    `${cleanedSymbol} data is not accessible right now.`,
    analysisMode === 'full' ? GENERATE_WARM_RETRY_ATTEMPTS : 2
  )

  const data = await response.json()
  if (cacheResult) {
    analysisCache.value = {
      ...analysisCache.value,
      [cacheKey]: data
    }
  }

  return data
}

async function fetchStockChartData(symbol, interval) {
  const cleanedSymbol = normalizeTradeSymbolInput(symbol)
  const cacheKey = `${cleanedSymbol}|${interval}`
  if (stockChartRequestPromises.has(cacheKey)) {
    return stockChartRequestPromises.get(cacheKey)
  }

  const query = new URLSearchParams({
    interval
  })
  const requestUrl = `${API_BASE_URL}/stock/${encodeURIComponent(cleanedSymbol)}/chart?${query.toString()}`
  const requestPromise = (async () => {
    const response = await fetchWithDatabaseWarmRetry(
      requestUrl,
      { timeoutMs: 15000 },
      `${cleanedSymbol} chart data is not accessible right now.`,
      2
    )

    const data = await response.json()
    if (hasChartSeries(data, interval)) {
      loadedChartSeriesKeys.add(cacheKey)
    }
    return data
  })()

  stockChartRequestPromises.set(cacheKey, requestPromise)
  try {
    return await requestPromise
  } finally {
    stockChartRequestPromises.delete(cacheKey)
  }
}

async function fetchCryptoChartData(symbol, interval) {
  const cleanedSymbol = normalizeTradeSymbolInput(symbol, { isCrypto: true })
  const cacheKey = `crypto|${cleanedSymbol}|${interval}`
  if (stockChartRequestPromises.has(cacheKey)) {
    return stockChartRequestPromises.get(cacheKey)
  }

  const query = new URLSearchParams({
    interval
  })
  const requestUrl = `${API_BASE_URL}/crypto/${encodeURIComponent(cleanedSymbol)}/chart?${query.toString()}`
  const requestPromise = (async () => {
    const response = await fetchWithDatabaseWarmRetry(
      requestUrl,
      { timeoutMs: 15000 },
      `${cleanedSymbol} crypto chart data is not accessible right now.`,
      2
    )

    const data = await response.json()
    if (hasChartSeries(data, interval)) {
      loadedChartSeriesKeys.add(cacheKey)
    }
    return data
  })()

  stockChartRequestPromises.set(cacheKey, requestPromise)
  try {
    return await requestPromise
  } finally {
    stockChartRequestPromises.delete(cacheKey)
  }
}

async function fetchStockLiveQuoteData(symbol) {
  const cleanedSymbol = normalizeTradeSymbolInput(symbol)
  const query = new URLSearchParams({
    indicators: '',
    analysis: 'search',
    interval: STOCK_GENERATE_INTERVAL,
    chartInterval: 'daily',
    compact: '1'
  })
  const response = await secureFetch(`${API_BASE_URL}/stock/${encodeURIComponent(cleanedSymbol)}?${query.toString()}`, {
    timeoutMs: 8000
  })

  if (!response.ok) {
    const payload = await parseErrorResponse(
      response,
      `${cleanedSymbol} quote is not accessible right now.`
    )
    throw new Error(payload.message || `${cleanedSymbol} quote is not accessible right now.`)
  }

  return response.json()
}

function buildLiveStockQuoteRow(symbol, stockData) {
  const cleanedSymbol = String(symbol || stockData?.symbol || '').trim().toUpperCase()
  const currentPrice = Number(stockData?.currentPrice)
  const previousClose = Number(stockData?.previousClose || currentPrice)

  if (!cleanedSymbol || !Number.isFinite(currentPrice) || currentPrice <= 0) {
    return null
  }

  const changePct = previousClose ? (((currentPrice - previousClose) / previousClose) * 100) : 0

  return {
    symbol: cleanedSymbol,
    price: formatMarketPrice(currentPrice),
    change: Number.isFinite(changePct) ? formatPercent(Number(changePct.toFixed(2))) : '--',
    tone: changePct >= 0 ? 'positive' : 'negative',
    note: 'Live quote'
  }
}

async function refreshStockWatchlistQuotes(symbols) {
  const cleanedSymbols = [...new Set(
    (symbols || [])
      .map((symbol) => String(symbol || '').trim().toUpperCase())
      .filter(Boolean)
  )]

  if (!cleanedSymbols.length) {
    return
  }

  await runLimitedTasks(cleanedSymbols, async (symbol) => {
    const quoteData = await fetchStockLiveQuoteData(symbol)
    const quoteRow = buildLiveStockQuoteRow(symbol, quoteData?.stock)
    if (!quoteRow) {
      return
    }

    liveStockQuoteLookup.value = {
      ...liveStockQuoteLookup.value,
      [symbol]: quoteRow
    }
  }, 3)
}

function clearExploreLiveSearchTimer() {
  if (exploreLiveSearchTimer) {
    window.clearTimeout(exploreLiveSearchTimer)
    exploreLiveSearchTimer = null
  }
}

function scheduleExploreLiveSearch() {
  clearExploreLiveSearchTimer()
  const cleanedSymbol = normalizeTradeSymbolInput(exploreSearchQuery.value)
  exploreLiveSearchRequestVersion += 1
  const requestVersion = exploreLiveSearchRequestVersion

  if (
    !isAuthenticated.value
    || activePage.value !== 'Explore'
    || isCryptoMode.value
    || !isStockExploreLiveSearchQuery(exploreSearchQuery.value)
  ) {
    exploreLiveSearchRows.value = []
    return
  }

  if (fullMarketBoardRows.value.some((row) => row.symbol === cleanedSymbol)) {
    exploreLiveSearchRows.value = exploreLiveSearchRows.value.filter((row) => row.symbol === cleanedSymbol)
    return
  }

  exploreLiveSearchRows.value = []
  exploreLiveSearchTimer = window.setTimeout(async () => {
    try {
      const quoteData = await fetchStockLiveQuoteData(cleanedSymbol)
      if (requestVersion !== exploreLiveSearchRequestVersion) {
        return
      }

      const liveRow = buildStockExploreLiveSearchRow(cleanedSymbol, quoteData?.stock)
      if (!liveRow.symbol) {
        return
      }

      exploreLiveSearchRows.value = [liveRow]
    } catch (error) {
      if (requestVersion === exploreLiveSearchRequestVersion) {
        exploreLiveSearchRows.value = []
      }
      console.warn(`Explore live search could not find ${cleanedSymbol}.`, error)
    }
  }, STOCK_EXPLORE_LIVE_SEARCH_DELAY_MS)
}

function mergeStockChartData(currentResponse, chartResponse) {
  const existingChartData = currentResponse?.chartData || {}
  const incomingChartData = chartResponse?.chartData || {}

  return {
    ...currentResponse,
    ...chartResponse,
    dataSource: chartResponse?.dataSource || currentResponse?.dataSource,
    request: {
      ...(currentResponse?.request || {}),
      ...(chartResponse?.request || {})
    },
    stock: {
      ...(currentResponse?.stock || {}),
      ...(chartResponse?.stock || {}),
      companyName: currentResponse?.stock?.companyName || chartResponse?.stock?.companyName,
      sector: currentResponse?.stock?.sector || chartResponse?.stock?.sector,
      industry: currentResponse?.stock?.industry || chartResponse?.stock?.industry
    },
    chartData: {
      ...existingChartData,
      ...incomingChartData,
      series: {
        ...(existingChartData.series || {}),
        ...(incomingChartData.series || {})
      },
      history: {
        ...(existingChartData.history || {}),
        ...(incomingChartData.history || {})
      }
    }
  }
}

function mergeActiveStockResponse(incomingResponse) {
  const incomingSymbol = String(incomingResponse?.stock?.symbol || '').toUpperCase()
  const currentSymbol = String(stockResponse.value?.stock?.symbol || '').toUpperCase()

  if (incomingSymbol && currentSymbol === incomingSymbol) {
    stockResponse.value = mergeStockChartData(stockResponse.value, incomingResponse)
    return
  }

  stockResponse.value = incomingResponse
}

function warmStockChartIntervals(symbol, preferredInterval = selectedChartInterval.value) {
  const cleanedSymbol = normalizeTradeSymbolInput(symbol)
  if (!cleanedSymbol) {
    return
  }

  if (stockChartWarmTimer) {
    window.clearTimeout(stockChartWarmTimer)
  }

  stockChartWarmTimer = window.setTimeout(() => {
    stockChartWarmTimer = null
    const currentSymbol = String(stockResponse.value?.stock?.symbol || '').toUpperCase()
    if (
      currentSymbol !== cleanedSymbol
      || activePage.value !== 'Stock Trade'
      || isSearching.value
      || isGenerating.value
    ) {
      return
    }

    const orderedIntervals = [
      preferredInterval,
      ...STOCK_CHART_PREFETCH_INTERVALS
    ].filter((interval, index, intervals) => interval && intervals.indexOf(interval) === index)
    const existingSeries = stockResponse.value?.chartData?.series || {}
    const missingIntervals = orderedIntervals.filter(
      (interval) => !isChartSeriesReady(cleanedSymbol, interval, existingSeries)
    )

    void runLimitedTasks(missingIntervals, async (interval) => {
      try {
        const chartData = await fetchStockChartData(cleanedSymbol, interval)
        const activeSymbolCode = String(stockResponse.value?.stock?.symbol || '').toUpperCase()
        if (activeSymbolCode !== cleanedSymbol) {
          return
        }
        stockResponse.value = mergeStockChartData(stockResponse.value, chartData)
      } catch (error) {
        console.warn(`Could not warm ${cleanedSymbol} ${interval} chart data.`, error)
      }
    }, 1)
  }, 2500)
}

async function fetchCryptoAnalysis(symbol, { analysisMode = 'full', compact = false, cacheResult = true, indicatorNames = null, matchDetails = false, usageContext = '', usageBatchId = '' } = {}) {
  const cleanedSymbol = normalizeTradeSymbolInput(symbol, { isCrypto: true })
  const analysisIndicators = Array.isArray(indicatorNames) && indicatorNames.length ? indicatorNames : getSelectedIndicators()
  const requestInterval = analysisMode === 'full' ? CRYPTO_GENERATE_INTERVAL : selectedChartInterval.value
  const cacheKey = buildAnalysisCacheKey(cleanedSymbol, analysisMode, 'crypto', analysisIndicators, requestInterval)

  if (cacheResult) {
    const cachedAnalysis = analysisCache.value[cacheKey]
    if (cachedAnalysis && isCachedAnalysisUsable(cachedAnalysis, { compact, interval: requestInterval })) {
      return cachedAnalysis
    }

    if (cachedAnalysis) {
      const { [cacheKey]: _staleAnalysis, ...freshCache } = analysisCache.value
      analysisCache.value = freshCache
    }
  }

  const query = new URLSearchParams({
    indicators: analysisIndicators.join(','),
    analysis: analysisMode
  })
  query.set('interval', requestInterval)
  if (compact) {
    query.set('compact', '1')
  }
  if (matchDetails) {
    query.set('matchDetails', '1')
  }
  if (usageContext) {
    query.set('usage', usageContext)
  }
  if (usageBatchId) {
    query.set('scanBatchId', usageBatchId)
  }

  const requestUrl = `${API_BASE_URL}/crypto/${encodeURIComponent(cleanedSymbol)}?${query.toString()}`
  const response = await fetchWithDatabaseWarmRetry(
    requestUrl,
    { timeoutMs: analysisMode === 'search' ? 12000 : 35000 },
    `${cleanedSymbol} crypto data is not accessible right now.`,
    analysisMode === 'full' ? GENERATE_WARM_RETRY_ATTEMPTS : 2
  )

  const data = await response.json()
  if (cacheResult) {
    analysisCache.value = {
      ...analysisCache.value,
      [cacheKey]: data
    }
  }

  return data
}

function scrollAnalysisWorkspaceToTop() {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    })
  })
}

function normalizeAnalysisResponseCollections(data) {
  return {
    ...data,
    patternAnalysis: {
      ...(data?.patternAnalysis || {}),
      matchedHistoricalPatterns: Array.isArray(data?.patternAnalysis?.matchedHistoricalPatterns)
        ? data.patternAnalysis.matchedHistoricalPatterns
        : [],
      highFitHistoricalPaths: Array.isArray(data?.patternAnalysis?.highFitHistoricalPaths)
        ? data.patternAnalysis.highFitHistoricalPaths
        : [],
    },
  }
}

function applyAnalysisResponse(data, isCryptoPage) {
  const normalizedData = normalizeAnalysisResponseCollections(data)
  if (isCryptoPage) {
    const incomingSymbol = String(normalizedData?.stock?.symbol || '').toUpperCase()
    const currentSymbol = String(cryptoResponse.value?.stock?.symbol || '').toUpperCase()
    cryptoResponse.value = incomingSymbol && incomingSymbol === currentSymbol
      ? normalizeAnalysisResponseCollections(mergeStockChartData(cryptoResponse.value, normalizedData))
      : normalizedData
    symbolInput.value = normalizedData.stock.symbol
    return
  }

  mergeActiveStockResponse(normalizedData)
  activeSymbol.value = normalizedData.stock.symbol
  symbolInput.value = normalizedData.stock.symbol
  activePage.value = 'Stock Trade'
  warmStockChartIntervals(normalizedData.stock.symbol)
}

function isCryptoWorkspaceReady(symbol = DEFAULT_CRYPTO_SYMBOL) {
  const cleanedSymbol = normalizeTradeSymbolInput(symbol, { isCrypto: true }) || DEFAULT_CRYPTO_SYMBOL
  const currentSymbol = String(cryptoResponse.value?.stock?.symbol || '').toUpperCase()

  return (
    currentSymbol === cleanedSymbol
    && cryptoResponse.value?.dataSource === 'live'
    && hasChartSeries(cryptoResponse.value, selectedChartInterval.value)
  )
}

async function ensureCryptoWorkspaceReady(symbol = DEFAULT_CRYPTO_SYMBOL, { scrollToTop = false } = {}) {
  const cleanedSymbol = normalizeTradeSymbolInput(symbol, { isCrypto: true }) || DEFAULT_CRYPTO_SYMBOL

  if (!isAuthenticated.value || activePage.value !== 'Crypto Trade') {
    return false
  }

  symbolInput.value = cleanedSymbol

  if (isCryptoWorkspaceReady(cleanedSymbol)) {
    return true
  }

  const loadKey = `${cleanedSymbol}|${selectedChartInterval.value}`
  if (cryptoWorkspaceLoadPromises.has(loadKey)) {
    await cryptoWorkspaceLoadPromises.get(loadKey)
    return isCryptoWorkspaceReady(cleanedSymbol)
  }

  const loadPromise = (async () => {
    if (cleanedSymbol === DEFAULT_CRYPTO_SYMBOL && defaultLiveLoadPromises.crypto) {
      await defaultLiveLoadPromises.crypto
      if (isCryptoWorkspaceReady(cleanedSymbol)) {
        return true
      }
    }

    const data = await fetchCryptoAnalysis(cleanedSymbol, {
      analysisMode: 'search'
    })

    if (!isAuthenticated.value || activePage.value !== 'Crypto Trade') {
      return false
    }

    applyAnalysisResponse(data, true)
    if (scrollToTop) {
      scrollAnalysisWorkspaceToTop()
    }
    return true
  })()

  cryptoWorkspaceLoadPromises.set(loadKey, loadPromise)
  try {
    return await loadPromise
  } finally {
    cryptoWorkspaceLoadPromises.delete(loadKey)
  }
}

async function preloadDefaultLiveWorkspaces() {
  if (!isAuthenticated.value) {
    return
  }

  const selectedIndicators = getSelectedIndicators()
  const defaultStockWarmKey = buildLoginGenerateWarmKey('stock', DEFAULT_STOCK_SYMBOL, selectedIndicators)
  const defaultCryptoWarmKey = buildLoginGenerateWarmKey('crypto', DEFAULT_CRYPTO_SYMBOL, selectedIndicators)

  if (!defaultLiveLoadPromises.stock) {
    loginGenerateWarmKeys.add(defaultStockWarmKey)
    defaultLiveLoadPromises.stock = fetchStockAnalysis(DEFAULT_STOCK_SYMBOL, {
      analysisMode: 'full',
      compact: true,
      cacheResult: true,
      indicatorNames: selectedIndicators,
    })
      .catch((error) => {
        loginGenerateWarmKeys.delete(defaultStockWarmKey)
        console.warn('Default stock Generate warmup failed.', error)
        defaultLiveLoadPromises.stock = null
      })
  }

  if (!defaultLiveLoadPromises.crypto) {
    loginGenerateWarmKeys.add(defaultCryptoWarmKey)
    defaultLiveLoadPromises.crypto = fetchCryptoAnalysis(DEFAULT_CRYPTO_SYMBOL, {
      analysisMode: 'full',
      compact: true,
      cacheResult: true,
      indicatorNames: selectedIndicators,
    })
      .catch((error) => {
        loginGenerateWarmKeys.delete(defaultCryptoWarmKey)
        console.warn('Default crypto Generate warmup failed.', error)
        defaultLiveLoadPromises.crypto = null
      })
  }

  void Promise.allSettled([
    defaultLiveLoadPromises.stock,
    defaultLiveLoadPromises.crypto
  ])
}

function buildLoginGenerateWarmKey(assetType, symbol, indicatorNames) {
  return `${assetType}|${String(symbol || '').trim().toUpperCase()}|${indicatorNames.join(',')}`
}

async function refreshFullGenerateInBackground(symbol, isCryptoPage, requestVersion) {
  const analysisIndicatorNames = isCryptoPage ? null : getSelectedIndicators()
  const chartIntervalAtRequest = selectedChartInterval.value
  try {
    let data = isCryptoPage
      ? await fetchCryptoAnalysis(symbol, {
        analysisMode: 'full',
        compact: true,
        cacheResult: true,
      })
      : await fetchStockAnalysis(symbol, {
        analysisMode: 'full',
        compact: true,
        cacheResult: true,
        indicatorNames: analysisIndicatorNames,
      })

    if (isCryptoPage && chartIntervalAtRequest !== CRYPTO_GENERATE_INTERVAL) {
      try {
        const scoringRequest = data?.request || {}
        const chartData = await fetchCryptoChartData(symbol, chartIntervalAtRequest)
        data = mergeStockChartData(data, chartData)
        data.request = {
          ...(data.request || {}),
          ...scoringRequest,
          interval: CRYPTO_GENERATE_INTERVAL,
        }
      } catch (error) {
        console.warn(`Crypto ${chartIntervalAtRequest} chart refresh could not finish after Generate.`, error)
      }
    }

    if (requestVersion !== analysisRequestVersion) {
      return
    }

    const responseSymbol = String(data?.stock?.symbol || '').toUpperCase()
    if (responseSymbol !== String(symbol || '').toUpperCase()) {
      isMatchDetailsLoading.value = false
      return
    }

    if (isCryptoPage && activePage.value !== 'Crypto Trade') {
      return
    }
    if (!isCryptoPage && activePage.value !== 'Stock Trade') {
      return
    }

    applyAnalysisResponse(data, isCryptoPage)
    if (isCryptoPage) {
      void refreshCryptoMatchDetailsInBackground(symbol, requestVersion)
    } else {
      void refreshStockMatchDetailsInBackground(symbol, requestVersion, analysisIndicatorNames)
    }
  } catch (error) {
    console.warn('Full Generate refresh could not finish.', error)
  } finally {
    if (requestVersion === analysisRequestVersion) {
      isPredictionLoading.value = false
      isGenerating.value = false
    }
  }
}

function isActiveCryptoGenerateRequest(symbol, requestVersion) {
  const currentSymbol = String(cryptoResponse.value?.stock?.symbol || '').toUpperCase()
  return (
    requestVersion === analysisRequestVersion
    && activePage.value === 'Crypto Trade'
    && currentSymbol === String(symbol || '').toUpperCase()
  )
}

async function refreshCryptoMatchDetailsInBackground(symbol, requestVersion) {
  if (!isActiveCryptoGenerateRequest(symbol, requestVersion)) {
    return
  }

  isMatchDetailsLoading.value = true
  try {
    const data = await fetchCryptoAnalysis(symbol, {
      analysisMode: 'full',
      compact: false,
      matchDetails: true,
      cacheResult: false,
    })

    if (!isActiveCryptoGenerateRequest(symbol, requestVersion)) {
      return
    }

    const responseSymbol = String(data?.stock?.symbol || '').toUpperCase()
    if (responseSymbol !== String(symbol || '').toUpperCase()) {
      return
    }

    cryptoResponse.value = normalizeAnalysisResponseCollections(
      mergeStockChartData(cryptoResponse.value, data)
    )
  } catch (error) {
    if (isActiveCryptoGenerateRequest(symbol, requestVersion)) {
      console.warn('Crypto matched history details could not finish.', error)
    }
  } finally {
    if (isActiveCryptoGenerateRequest(symbol, requestVersion)) {
      isMatchDetailsLoading.value = false
    }
  }
}

function clearStockMatchDetailReveal({ resetLoading = true } = {}) {
  if (stockMatchDetailRevealTimer) {
    window.clearTimeout(stockMatchDetailRevealTimer)
    stockMatchDetailRevealTimer = null
  }

  if (resetLoading) {
    isMatchDetailsLoading.value = false
  }
}

function isActiveStockGenerateRequest(symbol, requestVersion) {
  const currentSymbol = String(stockResponse.value?.stock?.symbol || '').toUpperCase()
  return (
    requestVersion === analysisRequestVersion
    && activePage.value === 'Stock Trade'
    && currentSymbol === String(symbol || '').toUpperCase()
  )
}

function applyStockResponseWithoutChartWarmup(data) {
  const normalizedData = normalizeAnalysisResponseCollections(data)
  mergeActiveStockResponse(normalizedData)
  activeSymbol.value = normalizedData.stock.symbol
  symbolInput.value = normalizedData.stock.symbol
}

function buildStockResponseWithVisibleMatches(data, visiblePatterns, visiblePaths) {
  return {
    ...data,
    patternAnalysis: {
      ...(data.patternAnalysis || {}),
      matchedHistoricalPatterns: visiblePatterns,
      highFitHistoricalPaths: visiblePaths,
    },
  }
}

function revealStockMatchDetailsProgressively(data, symbol, requestVersion) {
  clearStockMatchDetailReveal({ resetLoading: false })

  const patterns = data?.patternAnalysis?.matchedHistoricalPatterns || []
  const highFitPaths = data?.patternAnalysis?.highFitHistoricalPaths || []
  if (!patterns.length) {
    if (isActiveStockGenerateRequest(symbol, requestVersion)) {
      applyStockResponseWithoutChartWarmup(data)
    }
    isMatchDetailsLoading.value = false
    return
  }

  let visibleCount = 0
  const revealNext = () => {
    if (!isActiveStockGenerateRequest(symbol, requestVersion)) {
      clearStockMatchDetailReveal()
      return
    }

    visibleCount += 1
    applyStockResponseWithoutChartWarmup(
      buildStockResponseWithVisibleMatches(
        data,
        patterns.slice(0, visibleCount),
        highFitPaths.slice(0, visibleCount),
      )
    )

    if (visibleCount < patterns.length) {
      stockMatchDetailRevealTimer = window.setTimeout(revealNext, 120)
      return
    }

    stockMatchDetailRevealTimer = null
    isMatchDetailsLoading.value = false
  }

  revealNext()
}

async function refreshStockMatchDetailsInBackground(symbol, requestVersion, indicatorNames) {
  if (!isActiveStockGenerateRequest(symbol, requestVersion)) {
    return
  }

  isMatchDetailsLoading.value = true
  try {
    const data = await fetchStockAnalysis(symbol, {
      analysisMode: 'full',
      compact: true,
      matchDetails: true,
      cacheResult: false,
      indicatorNames,
    })

    const responseSymbol = String(data?.stock?.symbol || '').toUpperCase()
    if (!isActiveStockGenerateRequest(symbol, requestVersion)) {
      return
    }

    if (responseSymbol !== String(symbol || '').toUpperCase()) {
      isMatchDetailsLoading.value = false
      return
    }

    revealStockMatchDetailsProgressively(data, symbol, requestVersion)
  } catch (error) {
    if (isActiveStockGenerateRequest(symbol, requestVersion)) {
      console.warn('Stock matched history details could not finish.', error)
    }
    isMatchDetailsLoading.value = false
  }
}

async function runSearch(source = 'search') {
  const isCryptoPage = activePage.value === 'Crypto Trade'
  const cleanedSymbol = normalizeTradeSymbolInput(symbolInput.value, { isCrypto: isCryptoPage })

  if (!cleanedSymbol) {
    errorMessage.value = isCryptoPage
      ? 'Please enter a crypto ticker before searching.'
      : 'Please enter a stock symbol before searching.'
    return
  }

  if (!/^[A-Z0-9.]{1,10}$/.test(cleanedSymbol)) {
    errorMessage.value = isCryptoPage
      ? 'Please enter a valid crypto ticker using letters or numbers, such as BTC or OKB.'
      : 'Please enter a valid symbol, such as AAPL or BRK.B.'
    return
  }

  if (!isAuthenticated.value) {
    activePage.value = 'Sign In'
    authMessage.value = 'Sign in to run stock analysis and place trades.'
    return
  }

  symbolInput.value = cleanedSymbol
  const isGenerateAction = source === 'generate'
  const requestVersion = ++analysisRequestVersion
  clearStockMatchDetailReveal()
  if (isGenerateAction) {
    isGenerating.value = true
    isPredictionLoading.value = true
  } else {
    isSearching.value = true
    isPredictionLoading.value = false
    isGenerating.value = false
  }
  errorMessage.value = ''

  if (isCryptoPage) {
    try {
      if (isGenerateAction) {
        scrollAnalysisWorkspaceToTop()
        void refreshFullGenerateInBackground(cleanedSymbol, true, requestVersion)
      } else {
        const data = await fetchCryptoAnalysis(cleanedSymbol, {
          analysisMode: 'search'
        })
        applyAnalysisResponse(data, true)
        scrollAnalysisWorkspaceToTop()
      }
    } catch (error) {
      if (isGenerateAction) {
        isPredictionLoading.value = false
        isGenerating.value = false
      }
      errorMessage.value = getReadableMarketDataError(error?.message, cleanedSymbol)
      console.error(error)
    } finally {
      if (!isGenerateAction) {
        isSearching.value = false
      }
    }
    return
  }

  if (isGenerateAction) {
    scrollAnalysisWorkspaceToTop()
    void refreshFullGenerateInBackground(cleanedSymbol, false, requestVersion)
    return
  }

  try {
    const data = await fetchStockAnalysis(cleanedSymbol, {
      analysisMode: 'search'
    })

    applyAnalysisResponse(data, false)
    scrollAnalysisWorkspaceToTop()
  } catch (error) {
    errorMessage.value = getReadableMarketDataError(error?.message, cleanedSymbol)
    console.error(error)
  } finally {
    isSearching.value = false
  }
}

async function handleChartIntervalChange(interval) {
  const previousInterval = selectedChartInterval.value

  const isCryptoPage = activePage.value === 'Crypto Trade'
  const responseRef = isCryptoPage ? cryptoResponse : stockResponse
  const symbol = responseRef.value?.stock?.symbol
  const availableSeries = responseRef.value?.chartData?.series || {}

  if (!symbol || isChartSeriesReady(symbol, interval, availableSeries, isCryptoPage)) {
    selectedChartInterval.value = interval
    return
  }

  const requestVersion = ++chartIntervalRequestVersion
  try {
    if (isCryptoPage) {
      selectedChartInterval.value = interval
      const data = await fetchCryptoChartData(symbol, interval)
      if (requestVersion !== chartIntervalRequestVersion) {
        return
      }
      const currentSymbol = String(cryptoResponse.value?.stock?.symbol || '').toUpperCase()
      if (currentSymbol !== String(symbol || '').toUpperCase()) {
        return
      }
      const mergedData = mergeStockChartData(cryptoResponse.value, data)
      cryptoResponse.value = mergedData
      symbolInput.value = mergedData.stock.symbol
      return
    }

    const chartData = await fetchStockChartData(symbol, interval)
    if (requestVersion !== chartIntervalRequestVersion) {
      return
    }
    const currentSymbol = String(stockResponse.value?.stock?.symbol || '').toUpperCase()
    if (currentSymbol !== String(symbol || '').toUpperCase()) {
      return
    }
    const mergedData = mergeStockChartData(stockResponse.value, chartData)
    stockResponse.value = mergedData
    activeSymbol.value = mergedData.stock.symbol
    symbolInput.value = mergedData.stock.symbol
    selectedChartInterval.value = hasChartSeries(mergedData, interval) ? interval : previousInterval
  } catch (error) {
    selectedChartInterval.value = previousInterval
    errorMessage.value = getReadableMarketDataError(error?.message, symbol)
  }
}

function isChartSeriesReady(symbol, interval, availableSeries, isCryptoPage = false) {
  const cleanedSymbol = normalizeTradeSymbolInput(symbol, { isCrypto: isCryptoPage })
  const cacheKey = isCryptoPage
    ? `crypto|${cleanedSymbol}|${interval}`
    : `${cleanedSymbol}|${interval}`
  const bars = availableSeries?.[interval]

  if (loadedChartSeriesKeys.has(cacheKey)) {
    return Array.isArray(bars) && bars.length > 0
  }

  const minimumBars = CHART_SERIES_MINIMUM_BARS[interval] || 1
  return Array.isArray(bars) && bars.length >= minimumBars
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

function buildCryptoFocusUniverse(symbol, refreshKey) {
  const symbols = cryptoExploreUniverseRows.value.map((row) => row.symbol)
  const normalizedSymbol = String(symbol || '').toUpperCase()
  const baseIndex = hashSeed(`${normalizedSymbol || 'crypto'}-${refreshKey}`) % symbols.length
  const pool = normalizedSymbol && symbols.includes(normalizedSymbol) ? [normalizedSymbol] : []

  for (let index = 0; index < symbols.length && pool.length < 5; index += 1) {
    const candidate = symbols[(baseIndex + index) % symbols.length]
    if (!pool.includes(candidate)) {
      pool.push(candidate)
    }
  }

  return pool
}

function buildHourlyCryptoNewsFeed(symbol, refreshKey) {
  const templates = [
    '{symbol} liquidity leads the crypto board as traders compare spot demand and funding pressure.',
    '{symbol} stays in focus while digital asset breadth rotates between majors and exchange tokens.',
    'Crypto desks watch {symbol} for continuation after the latest volatility reset.',
    '{symbol} traders are weighing whether momentum can hold without chasing overheated candles.',
    'Digital asset flows keep attention on {symbol} as 24/7 markets digest macro risk.'
  ]
  const summaries = [
    'This crypto-mode feed is a product preview focused on market structure, liquidity, and volatility context.',
    'NoobTrade keeps the same workflow while separating digital asset research from the stock board.',
    'The goal is to surface clean crypto context without mixing it into the stock dashboard.',
    'Momentum looks constructive, but crypto risk can reset faster than regular-market sessions.',
    'The board emphasizes leaders first so future crypto probability research has a clear starting point.'
  ]
  const seed = hashSeed(`${symbol || 'crypto'}-crypto-news-${refreshKey}`)

  return buildCryptoFocusUniverse(symbol, refreshKey).map((focusSymbol, index) => ({
    title: templates[(seed + index) % templates.length].replaceAll('{symbol}', focusSymbol),
    source: ['Crypto Desk', 'On-chain Pulse', 'Digital Assets Wire', 'Macro Crypto'][index % 4],
    time: `${9 + ((seed + index * 13) % 42)} min ago`,
    summary: summaries[(seed + index * 2) % summaries.length],
    href: buildCryptoNewsLink(focusSymbol, templates[(seed + index) % templates.length].replaceAll('{symbol}', focusSymbol)),
    symbol: focusSymbol
  }))
}

function buildGoogleNewsLink(symbol, title) {
  const query = `${symbol} stock news ${title}`
  return `https://news.google.com/search?q=${encodeURIComponent(query)}`
}

function buildCryptoNewsLink(symbol, title) {
  const query = `${symbol} crypto news ${title}`
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
    if (isCryptoMode.value) {
      cryptoStarredSymbols.value = cryptoStarredSymbols.value.filter((item) => item !== cleanedSymbol)
    } else {
      starredSymbols.value = starredSymbols.value.filter((item) => item !== cleanedSymbol)
    }
    return
  }

  if (isCryptoMode.value) {
    cryptoStarredSymbols.value = [...cryptoStarredSymbols.value, cleanedSymbol]
  } else {
    starredSymbols.value = [...starredSymbols.value, cleanedSymbol]
  }
}

function setStarredSymbol(symbol, active = true) {
  const cleanedSymbol = String(symbol || '').trim().toUpperCase()

  if (!cleanedSymbol) {
    return false
  }

  if (active && !isStarredSymbol(cleanedSymbol)) {
    if (isCryptoMode.value) {
      cryptoStarredSymbols.value = [...cryptoStarredSymbols.value, cleanedSymbol]
    } else {
      starredSymbols.value = [...starredSymbols.value, cleanedSymbol]
    }
  }

  if (!active && isStarredSymbol(cleanedSymbol)) {
    if (isCryptoMode.value) {
      cryptoStarredSymbols.value = cryptoStarredSymbols.value.filter((item) => item !== cleanedSymbol)
    } else {
      starredSymbols.value = starredSymbols.value.filter((item) => item !== cleanedSymbol)
    }
  }

  return true
}

function toggleVoiceIndicator(indicatorName) {
  const matchedName = normalizeAssistantIndicatorName(indicatorName)
  if (!matchedName) {
    return null
  }

  const currentIndicator = indicators.value.find((indicator) => indicator.name === matchedName)
  const nextActive = !currentIndicator?.active
  setIndicatorActive([matchedName], nextActive)
  return { name: matchedName, active: nextActive }
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

watch(
  () => [isAuthenticated.value, activePage.value, appMode.value, activeStarredSymbols.value.join('|')],
  ([authenticated, page]) => {
    if (!authenticated || page !== 'Dashboard' || isCryptoMode.value) {
      return
    }

    refreshStockWatchlistQuotes(activeStarredSymbols.value).catch((error) => {
      console.warn('Could not refresh dashboard stock quotes.', error)
    })
  },
  { immediate: true }
)

watch(
  () => [isAuthenticated.value, activePage.value, appMode.value, exploreSearchQuery.value],
  () => {
    scheduleExploreLiveSearch()
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

function buildHourlyCryptoSocialFeed(symbol, refreshKey) {
  const cryptoTemplates = [
    '{symbol} is acting like the liquidity tell for this crypto rotation.',
    'Watching {symbol} structure here. Clean continuation matters more than a single green candle.',
    '{symbol} looks tradable only if volume confirms and the next pullback stays controlled.',
    'Crypto mode keeps me focused on leaders first. {symbol} is still one of the board names to watch.'
  ]
  const seed = hashSeed(`${symbol || 'crypto'}-crypto-social-${refreshKey}`)

  return buildCryptoFocusUniverse(symbol, refreshKey)
    .slice(0, 4)
    .map((focusSymbol, index) => {
      const post = cryptoTemplates[(seed + index * 3) % cryptoTemplates.length].replaceAll('{symbol}', focusSymbol)
      return {
        handle: ['@chainflow', '@coinstructure', '@volatilitydesk', '@cryptotape'][index % 4],
        tone: socialTonePool[(seed + index * 2) % socialTonePool.length],
        post,
        href: buildXSearchLink(focusSymbol, post)
      }
    })
}

function buildXSearchLink(symbol, postText) {
  const query = `${symbol} stock ${postText}`
  return `https://x.com/search?q=${encodeURIComponent(query)}&src=typed_query&f=live`
}

function openUsagePaywall(payload = {}) {
  const upgrade = payload.upgrade || {}
  usagePaywall.value = {
    open: true,
    title: 'Request limit reached',
    message: payload.message || 'You have reached the free request limit for this feature. Upgrade for unlimited requests.',
    usageLabel: payload.usageLabel || 'NoobTrade requests',
    limitLabel: payload.limitLabel || '',
    retryAfterSeconds: Number(payload.retryAfterSeconds || 0),
    planName: upgrade.planName || 'NoobTrade Pro',
    displayPrice: upgrade.displayPrice || '$29.99/month',
    benefit: upgrade.benefit || 'Unlimited Generate, Dashboard Scan, live chart, and matched-history requests.'
  }
}

function closeUsagePaywall() {
  usagePaywall.value = {
    ...usagePaywall.value,
    open: false
  }
}

function maybeOpenUsagePaywall(response, payload) {
  if (response?.status === 429 && payload?.upgrade?.required) {
    openUsagePaywall(payload)
    return true
  }
  return false
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
    const payload = JSON.parse(rawText)
    maybeOpenUsagePaywall(response, payload)
    return payload
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

function waitForRetry(delayMs) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, delayMs)
  })
}

async function fetchWithDatabaseWarmRetry(url, options, fallbackMessage, maxAttempts = 1) {
  const attempts = Math.max(1, Number(maxAttempts) || 1)

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    let response
    try {
      response = await secureFetch(url, options)
    } catch (error) {
      if (attempt >= attempts - 1) {
        throw error
      }

      await waitForRetry(350 + (attempt * 300))
      continue
    }

    if (response.ok) {
      return response
    }

    const payload = await parseErrorResponse(response, fallbackMessage)
    const message = payload.message || fallbackMessage
    const canRetry = attempt < attempts - 1
      && (
        response.status === 503
        || response.status === 502
        || response.status === 504
      )

    if (!canRetry) {
      const error = new Error(message)
      error.status = response.status
      if (response.status === 429 && payload?.upgrade?.required) {
        error.isUsageLimit = true
        error.usagePayload = payload
      }
      throw error
    }

    const retryAfterSeconds = Number(response.headers.get('Retry-After'))
    const retryAfterMs = Number.isFinite(retryAfterSeconds) && retryAfterSeconds > 0
      ? retryAfterSeconds * 1000
      : 550 + (attempt * 450)
    await waitForRetry(retryAfterMs)
  }

  throw new Error(fallbackMessage)
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

function normalizeAssistantIndicatorName(name) {
  const normalized = String(name || '').trim().toUpperCase()
  const matched = indicators.value.find((indicator) => String(indicator.name).toUpperCase() === normalized)
  return matched?.name || ''
}

function formatProbabilitySide(side) {
  return side === 'down' ? 'downside' : 'upside'
}

function setVoiceProbabilityThreshold(side, value) {
  if (!predictionSummaryRef.value?.setProbabilityThreshold) {
    return null
  }

  const normalizedSide = side === 'down' ? 'down' : 'up'
  return predictionSummaryRef.value.setProbabilityThreshold(normalizedSide, value)
}

function getVoiceProbabilitySnapshot(side = 'up', value = null) {
  if (!predictionSummaryRef.value?.getProbabilitySnapshot) {
    return null
  }

  return predictionSummaryRef.value.getProbabilitySnapshot(side, value)
}

function openVoiceHistoricalPattern(index = 0) {
  const pattern = matchedPatternsRef.value?.openPatternByIndex?.(index)
  if (!pattern) {
    return null
  }

  return {
    pattern,
    index
  }
}

function summarizeHistoricalPattern(pattern) {
  if (!pattern) {
    return getVoiceShortReply('misunderstood')
  }

  return getVoiceShortReply('history')
}

function buildAssistantIntentContext() {
  return {
    activePage: activePage.value,
    language: uiLanguage.value,
    symbol: activeTradeResponse.value?.stock?.symbol || activeSymbol.value,
    selectedIndicators: getSelectedIndicators(),
    availablePages: isAuthenticated.value ? [...accessiblePages.value, 'User Guide'] : accessiblePages.value,
    availableIndicators: indicators.value.map((indicator) => indicator.name),
    probabilitySnapshot: getVoiceProbabilitySnapshot('up'),
    matchedPatternCount: activeTradeResponse.value?.patternAnalysis?.matchedHistoricalPatterns?.length || 0,
    lastIntent: voiceLastIntent.value,
  }
}

async function fetchAssistantIntent(rawTranscript) {
  try {
    const response = await secureFetch(`${API_BASE_URL}/assistant/intent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        transcript: rawTranscript,
        language: uiLanguage.value,
        context: buildAssistantIntentContext()
      }),
      timeoutMs: 4500,
    })
    const payload = await parseJsonResponse(response, 'AI intent parser is not available right now.')

    if (!response.ok) {
      return null
    }

    return payload?.intent || null
  } catch (error) {
    console.warn('Cloud assistant intent failed:', error)
    return null
  }
}

function isVoiceCorrectionCommand(command) {
  return includesVoicePhrase(command, [
    'wrong', 'not that', 'no i meant', 'i meant', 'actually', '不是', '错了', '不对', '我的意思是', '我是说',
    'no era eso', 'quise decir', 'non', 'je voulais dire'
  ])
}

function extractVoiceCorrectionText(rawTranscript) {
  const text = String(rawTranscript || '').trim()
  const patterns = [
    /no[, ]+i meant\s+/i,
    /i meant\s+/i,
    /actually\s+/i,
    /not that[, ]+/i,
    /wrong[, ]+/i,
    /不是[，, ]*/i,
    /错了[，, ]*/i,
    /不对[，, ]*/i,
    /我的意思是[，, ]*/i,
    /我是说[，, ]*/i,
    /quise decir\s+/i,
    /je voulais dire\s+/i,
  ]

  for (const pattern of patterns) {
    const cleaned = text.replace(pattern, '').trim()
    if (cleaned && cleaned !== text) {
      return cleaned
    }
  }

  return ''
}

async function saveAssistantFeedback({ correctionTranscript = '', correctedIntent = null } = {}) {
  const lastPrediction = voiceLastAssistantPrediction.value

  if (!lastPrediction?.transcript || !lastPrediction?.intent) {
    return false
  }

  try {
    await secureFetch(`${API_BASE_URL}/assistant/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        transcript: lastPrediction.transcript,
        prediction: lastPrediction.intent,
        correction: correctedIntent || {
          intent: 'unknown',
          reply: correctionTranscript
        },
        language: uiLanguage.value,
        source: 'voice_correction',
        context: {
          ...lastPrediction.context,
          correctionTranscript
        }
      }),
      timeoutMs: 4500,
    })
    return true
  } catch (error) {
    console.warn('Assistant feedback save failed:', error)
    return false
  }
}

async function applyAssistantIntent(intentPayload, rawTranscript) {
  const intent = String(intentPayload?.intent || '')
  const confidence = Number(intentPayload?.confidence || 0)

  if (!intent || confidence < 0.55) {
    return false
  }

  if (intent === 'blocked_trading') {
    setVoiceShortStatus('blockedTrading', { transcript: rawTranscript })
    return true
  }

  if (intent === 'open_full_market') {
    return openVoiceFullMarketBoard(rawTranscript)
  }

  if (intent === 'view_more_market') {
    return revealVoiceMoreMarketRows(rawTranscript)
  }

  if (intent === 'navigate' && intentPayload.page) {
    navigateTo(intentPayload.page)
    setVoiceStatus(getNavigationShortReply(intentPayload.page, rawTranscript), { speak: true, transcript: rawTranscript })
    return true
  }

  if (intent === 'scroll') {
    const reply = executeVoiceScrollIntent(intentPayload.direction, intentPayload.amount)
    if (reply) {
      setVoiceStatus(reply, { speak: true, transcript: rawTranscript })
      return true
    }
  }

  if (intent === 'generate') {
    await runVoiceAnalysis('generate', intentPayload.symbol || '', rawTranscript)
    return true
  }

  if (intent === 'search') {
    await runVoiceAnalysis('search', intentPayload.symbol || '', rawTranscript)
    return true
  }

  if (intent === 'scan_watchlist') {
    if (Number.isFinite(Number(intentPayload.threshold))) {
      watchlistScanThreshold.value = normalizeProbabilityThreshold(intentPayload.threshold)
    }
    navigateTo('Dashboard')
    setVoiceShortStatus('scanStart', { transcript: rawTranscript })
    await scanStarredWatchlist()
    setVoiceShortStatus('scanDone', { transcript: rawTranscript })
    return true
  }

  if (intent === 'adjust_probability') {
    const snapshot = setVoiceProbabilityThreshold(intentPayload.side, intentPayload.value)
    if (snapshot) {
      setVoiceShortStatus('probability', { transcript: rawTranscript })
      return true
    }
  }

  if (intent === 'summarize_probability') {
    const snapshot = getVoiceProbabilitySnapshot(intentPayload.side || 'up', intentPayload.value)
    if (snapshot) {
      const thresholdPrefix = snapshot.side === 'down' ? '-' : '+'
      setVoiceStatus(`${thresholdPrefix}${Number(snapshot.threshold).toFixed(1)}%: ${snapshot.probability}.`, { speak: true, transcript: rawTranscript })
      return true
    }
  }

  if (intent === 'open_historical_pattern') {
    const index = Number.isFinite(Number(intentPayload.index)) ? Math.max(Number(intentPayload.index) - 1, 0) : 0
    const opened = openVoiceHistoricalPattern(index)
    if (opened) {
      setVoiceShortStatus('history', { transcript: rawTranscript })
      return true
    }

    reportVoiceMisunderstanding(rawTranscript)
    return true
  }

  if (intent === 'open_news') {
    openVoiceNewsPanel(rawTranscript)
    return true
  }

  if (intent === 'load_more_patterns') {
    matchedPatternsRef.value?.loadMorePatterns?.()
    setVoiceShortStatus('more', { transcript: rawTranscript })
    return true
  }

  if (intent === 'set_star') {
    const targetSymbol = intentPayload.symbol || activeTradeResponse.value?.stock?.symbol || activeSymbol.value
    if (setStarredSymbol(targetSymbol, intentPayload.active !== false)) {
      setVoiceShortStatus(intentPayload.active === false ? 'starRemoved' : 'starAdded', { transcript: rawTranscript })
      return true
    }
  }

  if (intent === 'clear_indicators') {
    indicators.value = indicators.value.map((indicator) => ({ ...indicator, active: false }))
    setVoiceShortStatus('indicators', { transcript: rawTranscript })
    return true
  }

  if (intent === 'reset_indicators') {
    const defaultSelected = new Set(['MA', 'EMA', 'MACD', 'BOLL', 'VOL'])
    indicators.value = indicators.value.map((indicator) => ({
      ...indicator,
      active: defaultSelected.has(String(indicator.name).toUpperCase())
    }))
    setVoiceShortStatus('indicators', { transcript: rawTranscript })
    return true
  }

  if (intent === 'select_only_indicators' && Array.isArray(intentPayload.indicators)) {
    const normalizedIndicators = intentPayload.indicators.map(normalizeAssistantIndicatorName).filter(Boolean)
    if (normalizedIndicators.length) {
      setOnlyVoiceIndicators(normalizedIndicators)
      setVoiceShortStatus('indicators', { transcript: rawTranscript })
      return true
    }
  }

  if (intent === 'set_indicator' && Array.isArray(intentPayload.indicators)) {
    const normalizedIndicators = intentPayload.indicators.map(normalizeAssistantIndicatorName).filter(Boolean)
    if (normalizedIndicators.length) {
      setIndicatorActive(normalizedIndicators, intentPayload.active !== false)
      setVoiceShortStatus('indicators', { transcript: rawTranscript })
      return true
    }
  }

  if (intent === 'set_interval' && intentPayload.interval) {
    await handleChartIntervalChange(intentPayload.interval)
    setVoiceShortStatus('interval', { transcript: rawTranscript })
    return true
  }

  if (intent === 'sign_out') {
    queueVoiceAction({
      type: 'signOut',
      prompt: getVoiceShortReply('ready')
    })
    return true
  }

  if (intent === 'language' && intentPayload.language) {
    uiLanguage.value = intentPayload.language
    setVoiceShortStatus('ready', { transcript: rawTranscript })
    return true
  }

  if (intent === 'greeting' || intent === 'help' || intent === 'chat') {
    setVoiceStatus(buildConversationalReply(normalizeVoiceText(rawTranscript)), { speak: true, transcript: rawTranscript })
    return true
  }

  return false
}

function applyAuthenticatedState(user, message = '') {
  currentUser.value = user
  isAuthenticated.value = true
  activePage.value = 'Dashboard'
  authMessage.value = message
  void loadCryptoExploreUniverse()
  void preloadDefaultLiveWorkspaces()
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

    applyAuthenticatedState(
      payload.user,
      payload.message || `Welcome to NoobTrade, ${payload.user.fullName}.`
    )
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
  defaultLiveLoadPromises.stock = null
  defaultLiveLoadPromises.crypto = null
  loginGenerateWarmKeys.clear()
  if (stockChartWarmTimer) {
    window.clearTimeout(stockChartWarmTimer)
    stockChartWarmTimer = null
  }
  symbolInput.value = ''
  activeSymbol.value = ''
  exploreLiveSearchRows.value = []
  stockResponse.value = createDefaultResponse()
  cryptoResponse.value = createCryptoWorkspaceResponse()
  clearStockMatchDetailReveal()
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
      const pageAliases = {
        Analysis: 'Stock Trade',
        Myself: 'Settings'
      }
      const normalizedPage = pageAliases[page] || page
      if (normalizedPage === 'User Guide' && isAuthenticated.value) {
        openUserGuide()
        return
      }
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
  <div class="app-shell" :class="{ 'crypto-mode': isAuthenticated && isCryptoMode }">
    <header class="topbar">
      <div class="topbar-brand-block">
        <div class="topbar-brand">NoobTrade</div>
      </div>

      <nav class="topbar-nav">
        <button
          v-for="page in visiblePages"
          :key="page"
          class="topbar-link"
          :class="{ active: activePage === page }"
          @click="navigateTo(page)"
        >
          {{ formatPageLabel(page) }}
        </button>
      </nav>

      <div v-if="canInstallApp || isAuthenticated" class="topbar-actions">
        <button
          v-if="canInstallApp"
          class="topbar-button secondary"
          @click="triggerInstall"
        >
          {{ t('installApp') }}
        </button>
        <template v-if="isAuthenticated">
          <button class="topbar-button mode-switch-button" @click="switchTradingMode">{{ modeSwitchLabel }}</button>
        </template>
      </div>
    </header>

    <main v-if="!isAuthenticated && activePage === 'Home'" class="product-page public-page">
      <section class="hero-surface public-hero">
        <div class="public-hero-copy">
          <p class="eyebrow">Public Home</p>
          <h1 class="page-title">Learn the tape before you risk real money.</h1>
          <div class="hero-actions public-hero-actions">
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
          <p>Saved Market View</p>
          <h2>Watchlist Scan</h2>
          <span>Pin favorite symbols, scan probabilities, and move into analysis without an account book.</span>
        </article>
      </section>
    </main>

    <main v-else-if="!isAuthenticated && activePage === 'Sign In'" class="product-page auth-page">
      <section class="auth-shell">
        <article class="auth-card">
          <p class="eyebrow">User Authentication</p>
          <h1>Sign in to your workspace</h1>
          <p class="page-subtitle">
            Sign in with your registered email and password to open your NoobTrade dashboard.
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
          <h1>Register for NoobTrade</h1>
          <p class="page-subtitle">
            Register with your email and password. Regular users must verify by email, while the preconfigured admin accounts can sign in directly.
          </p>

          <form @submit.prevent="submitRegistration">
            <div v-if="authMessage" class="status-message loading-message">
              {{ authMessage }}
            </div>

            <div class="auth-form-grid auth-form-grid--register">
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
              <label class="auth-field auth-field--register-password">
                <span>Password</span>
                <input v-model="registrationForm.password" type="password" placeholder="Create a password" />
                <small class="auth-field-hint">Use at least 8 characters and include one special symbol such as _, !, or #.</small>
              </label>
            </div>

            <div class="auth-actions auth-actions--register">
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
          <p class="eyebrow">{{ modeLabel }} Probability Dashboard</p>
          <h1 class="page-title">{{ isCryptoMode ? 'Crypto probability scan center.' : 'Stock probability scan center.' }}</h1>
          <p class="page-subtitle">
            {{ isCryptoMode
              ? 'Scan saved crypto assets with the full indicator set, rank the strongest setups, and open Crypto Trade for custom single-symbol review.'
              : 'Scan saved stocks with the full indicator set, rank the strongest setups, and open Stock Trade for custom single-symbol review.' }}
          </p>
        </div>

        <div class="dashboard-chart-panel">
          <div class="dashboard-chart-copy">
            <span class="section-chip">Probability Workflow</span>
            <span class="dashboard-chart-note">Search one symbol in Trade, or scan starred names with full indicators</span>
          </div>

          <div class="task-list">
            <div class="task-row">
              <strong>1. Build Watchlist</strong>
              <span>Star names from Explore so Dashboard has a focused scan universe.</span>
            </div>
            <div class="task-row">
              <strong>2. Set Probability</strong>
              <span>Choose the minimum upside probability you want the full-indicator scan to pass.</span>
            </div>
            <div class="task-row">
              <strong>3. Review Matches</strong>
              <span>Generated matches appear ranked by probability, ready to open in Trade.</span>
            </div>
          </div>

          <div v-if="!isCryptoMode" class="workflow-guide-actions">
            <button class="topbar-button secondary" type="button" @click="openUserGuide">
              How NoobTrade Works
            </button>
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
        <article class="table-surface dashboard-card dashboard-card--wide">
          <div class="table-header">
            <h2>{{ isCryptoMode ? 'Self-Selected Crypto' : 'Self-Selected Stocks' }}</h2>
            <span class="section-chip">{{ activeStarredSymbols.length }} saved</span>
          </div>
          <form class="watchlist-scan-bar" @submit.prevent="scanStarredWatchlist">
            <label class="watchlist-scan-input">
              <span>{{ isCryptoMode ? 'Minimum crypto upside probability based on preview pattern logic' : 'Minimum probability of +1% gain in the next 5 days based on historical patterns' }}</span>
              <span class="percent-input-shell">
                <input
                  v-model.number="watchlistScanThreshold"
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  inputmode="decimal"
                  aria-label="Minimum probability threshold"
                />
                <strong>%</strong>
              </span>
            </label>
            <button class="topbar-button" type="submit" :disabled="isWatchlistScanning || !dashboardWatchlistRows.length">
              {{ isWatchlistScanning ? 'Scanning...' : 'Scan' }}
            </button>
          </form>
          <p v-if="watchlistScanMessage" class="watchlist-scan-message">
            {{ watchlistScanMessage }}
            <span v-if="watchlistScanScannedAt">Last scan {{ watchlistScanScannedAt }}</span>
          </p>
          <div v-if="dashboardWatchlistRows.length" class="data-table dashboard-watchlist-table">
            <div class="data-row data-head dashboard-watchlist-head">
              <span>Symbol</span>
              <span>Price</span>
              <span>1D</span>
              <span>Star</span>
            </div>
            <div v-for="row in dashboardWatchlistRows" :key="row.symbol" class="data-row dashboard-watchlist-row">
              <button class="watchlist-link explore-symbol-link" @click="openModeAnalysis(row.symbol)">{{ row.symbol }}</button>
              <span>{{ row.price }}</span>
              <strong :class="row.tone">{{ row.change }}</strong>
              <button
                type="button"
                class="star-toggle"
                :class="{ active: isStarredSymbol(row.symbol) }"
                :aria-label="isStarredSymbol(row.symbol) ? `Remove ${row.symbol} from starred ${isCryptoMode ? 'crypto' : 'stocks'}` : `Star ${row.symbol}`"
                @click="toggleStarredSymbol(row.symbol)"
              >
                {{ isStarredSymbol(row.symbol) ? '★' : '☆' }}
              </button>
            </div>
          </div>
          <div v-else class="empty-state empty-state--compact">
            {{ isCryptoMode ? 'Star crypto assets in Explore and they will appear here.' : 'Star stocks in Explore and they will appear here as your self-selected list.' }}
          </div>
          <div v-if="sortedWatchlistScanResults.length" class="watchlist-scan-results">
            <div class="table-header compact">
              <h3>Generated Matches</h3>
              <div class="watchlist-scan-heading-meta">
                <p>Approximate results from a simplified Generate pass. Run Generate on each symbol for more detailed data.</p>
                <span class="section-chip">>= {{ watchlistScanThresholdLabel }}</span>
              </div>
            </div>
            <div class="data-table watchlist-scan-table">
              <div class="data-row data-head watchlist-scan-head">
                <span>Rank</span>
                <span>Symbol</span>
                <span>Upside Probability</span>
                <span>Price</span>
                <span>Signal</span>
              </div>
              <div
                v-for="(result, index) in sortedWatchlistScanResults"
                :key="`scan-${result.symbol}`"
                class="data-row watchlist-scan-row"
              >
                <span>#{{ index + 1 }}</span>
                <button class="watchlist-link explore-symbol-link" @click="openModeAnalysis(result.symbol)">
                  {{ result.symbol }}
                </button>
                <strong class="positive">{{ result.probability.toFixed(2) }}%</strong>
                <span>{{ result.price }}</span>
                <span>{{ result.signal }}</span>
              </div>
            </div>
          </div>
        </article>

        <article class="table-surface dashboard-card">
          <div class="table-header">
            <h2>Desk Notices</h2>
            <span class="section-chip">{{ isCryptoMode ? '24 / 7' : 'Updated today' }}</span>
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
            <h2>Scan Focus</h2>
            <span class="section-chip">Probability first</span>
          </div>
          <div class="task-list">
            <div class="task-row">
              <strong>Watchlist In</strong>
              <span>Only starred {{ isCryptoMode ? 'crypto assets' : 'stocks' }} are scanned from Dashboard.</span>
              <small>{{ activeStarredSymbols.length }} saved</small>
            </div>
            <div class="task-row">
              <strong>Probability Out</strong>
              <span>Results are filtered by your minimum upside probability and sorted high to low.</span>
              <small>{{ watchlistScanThresholdLabel }}</small>
            </div>
            <div class="task-row">
              <strong>Deep Dive</strong>
              <span>Open a symbol to inspect indicators, chart context, and historical matches.</span>
              <small>{{ isCryptoMode ? 'Crypto Trade' : 'Stock Trade' }}</small>
            </div>
          </div>
        </article>
      </section>
    </main>

    <main v-else-if="activePage === 'User Guide'" class="product-page">
      <section class="hero-surface compact">
        <div>
          <p class="eyebrow">User Guide</p>
          <h1 class="page-title">How NoobTrade Works</h1>
          <p class="page-subtitle">
            NoobTrade is a research workspace for reading stocks and crypto with live market data,
            historical context, probability scoring, and a guided path from watchlist to deeper review.
          </p>
          <div class="workflow-guide-actions">
            <button class="topbar-button secondary" type="button" @click="navigateTo('Dashboard')">Back to Dashboard</button>
            <button class="topbar-button" type="button" @click="navigateTo(isCryptoMode ? 'Crypto Trade' : 'Stock Trade')">
              Open {{ isCryptoMode ? 'Crypto Trade' : 'Stock Trade' }}
            </button>
          </div>
        </div>
      </section>

      <section class="more-story-grid guide-story-grid">
        <article class="more-card feature-story-card">
          <p class="eyebrow">Purpose</p>
          <h2>What the site is for</h2>
          <p>
            The platform helps users turn a broad market list into a focused research list. It is built for reviewing price action,
            live quotes, selected indicators, similar historical setups, and probability-style outcomes before deciding what deserves more attention.
          </p>
          <p>
            It is not a promise that a stock or crypto asset will rise or fall. Treat it as a decision-support dashboard, not a broker,
            investment adviser, or guarantee of future performance.
          </p>
        </article>

        <article class="more-card feature-story-card">
          <p class="eyebrow">Quick Start</p>
          <h2>Search one symbol or scan a saved list</h2>
          <div class="task-list guide-task-list">
            <div class="task-row">
              <strong>1. Single Search</strong>
              <span>Open Stock Trade or Crypto Trade, enter one symbol, and run Generate when you want a focused review with your current indicator choices.</span>
            </div>
            <div class="task-row">
              <strong>2. Star Scan</strong>
              <span>Star names in Explore, then use Dashboard Scan when you want NoobTrade to evaluate every saved stock or crypto asset together.</span>
            </div>
            <div class="task-row">
              <strong>3. Indicator Difference</strong>
              <span>Dashboard Scan uses the full indicator set by default. To customize indicators, open Trade and Generate a single symbol.</span>
            </div>
          </div>
        </article>

        <article class="more-card feature-story-card">
          <p class="eyebrow">Dashboard Scan</p>
          <h2>Scan is batch Generate</h2>
          <p>
            Dashboard Scan runs a full-indicator Generate-style analysis across every starred symbol in your current mode. In stock mode it scans only
            starred stocks; in crypto mode it scans only starred crypto assets. Results are filtered by your threshold and sorted from stronger upside
            probability to weaker.
          </p>
          <p>
            This is meant for fast triage with a consistent default setting. Use it to find which names deserve attention first, then open Trade for a
            single-symbol review or a custom indicator setup.
          </p>
        </article>

        <article class="more-card feature-story-card">
          <p class="eyebrow">Single Symbol</p>
          <h2>Generate one stock or crypto asset</h2>
          <p>
            On Stock Trade or Crypto Trade, enter a symbol and run Generate. The page first loads a fast market snapshot so the workspace responds quickly,
            then refreshes deeper historical context in the background when available.
          </p>
          <p>
            Single-symbol Generate respects the indicators selected on the Trade page. Use it when you want to change the indicator mix, inspect one chart
            more closely, or review matched historical moments before deciding what to study next.
          </p>
        </article>

        <article class="more-card feature-story-card">
          <p class="eyebrow">Probability</p>
          <h2>Why up and down do not add to 100%</h2>
          <p>
            The upside and downside probabilities answer different event questions. For example, an upside value may estimate how often similar setups touched
            +1% within a forward window, while a downside value may estimate how often similar setups touched -1% within that same window.
          </p>
          <p>
            Both events can happen in the same window, and neither event can happen. That is why the two numbers are not complements and should not be read
            as “up chance plus down chance equals 100%.”
          </p>
        </article>

        <article class="more-card feature-story-card">
          <p class="eyebrow">Data Separation</p>
          <h2>Stocks and crypto stay separate</h2>
          <p>
            Stock mode and crypto mode share the same product workflow, but they keep separate watchlists, dashboards, trade workspaces, and data sources.
            This avoids mixing equity history with digital asset history.
          </p>
          <p>
            Stock Explore currently includes 3,663 U.S. stock symbols drawn from the S&P 500, Nasdaq-listed common stocks and ADRs,
            Dow Jones 30 names, and selected research names for starring and Dashboard Scan. Stock Trade can also request supported
            symbols from the live stock data feed when users want a single-symbol review.
          </p>
          <p>
            Crypto Explore shows up to 250 OKX USDT spot crypto assets from the live market feed, while Crypto Trade reads supported OKX public spot markets for
            single-symbol review. Crypto data remains separate from stock history throughout the workflow.
          </p>
          <p>
            Market data is used where available, while historical context is used to frame probability-style research. If a feed is slow or unavailable,
            the app may use cached context or show a clear data-source label.
          </p>
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
          :is-crypto-mode="isCryptoMode"
          :selected-interval="selectedChartInterval"
          :sector="activeTradeResponse.stock.sector"
          @update:selected-interval="handleChartIntervalChange"
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
          ref="predictionSummaryRef"
          :format-percent="formatPercent"
          :request-data="activeTradeResponse.request"
          :stock-data="activeTradeResponse.stock"
          :analysis-data="activeTradeResponse.patternAnalysis"
          :is-loading="isPredictionLoading"
          :loading-title="predictionLoadingTitle"
          :loading-message="predictionLoadingMessage"
        />

        <MatchedPatterns
          ref="matchedPatternsRef"
          :matched-patterns="activeTradeResponse.patternAnalysis.matchedHistoricalPatterns"
          :high-fit-paths="activeTradeResponse.patternAnalysis.highFitHistoricalPaths"
          :is-loading-details="isMatchDetailsLoading"
          @open-replay="openHistoricalReplay"
        />

      </section>
    </main>

    <main v-else-if="activePage === 'Explore'" class="product-page">
      <section class="hero-surface compact explore-hero">
        <div>
          <p class="eyebrow">{{ isCryptoMode ? 'Crypto Explore' : 'Explore' }}</p>
          <h1 class="page-title">{{ isCryptoMode ? 'Ranked crypto board for digital asset discovery.' : exploreViewMode === 'full' ? 'Full market board for scrolling the entire list.' : 'Ranked market board for scanning all stocks.' }}</h1>
          <p class="page-subtitle">
            {{ isCryptoMode
              ? 'This crypto discovery page keeps the same Explore workflow, but the table is focused on Bitcoin, Ethereum, exchange tokens, and Layer 1 assets.'
              : exploreViewMode === 'full'
              ? 'This full-board mode is built for scrolling through the complete market list in one long page before jumping into Trade.'
              : 'This is the broad market discovery page: rankings, movers, gainers, and volume leaders in one place before you drill into Trade.' }}
          </p>
        </div>
      </section>

      <section class="explore-toolbar">
        <label class="explore-search-field">
          <span>{{ isCryptoMode ? 'Search crypto' : 'Search stocks' }}</span>
          <input
            v-model="exploreSearchQuery"
            type="search"
            :placeholder="isCryptoMode ? 'Search symbol or asset' : 'Search symbol or company'"
          />
        </label>
        <div v-if="!isCryptoMode" class="table-filters">
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
        <div v-if="!isCryptoMode" class="explore-toolbar-actions">
          <button
            class="topbar-button secondary"
            @click="toggleFullMarketBoard"
          >
            {{ exploreViewMode === 'full' ? 'Back To Ranked View' : 'Open Full Market Board' }}
          </button>
        </div>
      </section>

      <section class="explore-layout explore-layout--full">
        <article class="table-surface explore-market-panel">
          <div class="table-header">
            <h2>{{ isCryptoMode ? 'Crypto' : 'Stock' }}</h2>
            <span class="section-chip">{{ exploreSearchQuery ? 'Search Results' : isCryptoMode ? 'Ranked Crypto' : exploreViewMode === 'full' ? 'Full Market Board' : currentExploreTab }}</span>
          </div>

          <div class="data-table explore-table">
            <div class="data-row data-head explore-head">
              <span>Symbol</span>
              <span>Name</span>
              <span>Category</span>
              <span>Star</span>
            </div>
            <div
              v-for="row in filteredExploreRows"
              :key="row.symbol + row.category"
              class="data-row explore-row"
            >
              <button
                class="watchlist-link explore-symbol-link"
                @click="openModeAnalysis(row.symbol)"
              >
                {{ row.symbol }}
              </button>
              <span>{{ row.name }}</span>
              <span>{{ row.category }}</span>
              <button
                type="button"
                class="star-toggle"
                :class="{ active: isStarredSymbol(row.symbol) }"
                :aria-label="isStarredSymbol(row.symbol) ? `Remove ${row.symbol} from starred ${isCryptoMode ? 'crypto' : 'stocks'}` : `Star ${row.symbol}`"
                @click="toggleStarredSymbol(row.symbol)"
              >
                {{ isStarredSymbol(row.symbol) ? '★' : '☆' }}
              </button>
            </div>
          </div>

          <div
            v-if="!isCryptoMode && exploreViewMode === 'full' && !exploreSearchQuery"
            class="full-market-actions"
          >
            <span>{{ stockMarketBoardStatus }}</span>
            <button
              class="topbar-button secondary"
              type="button"
              :disabled="!hasMoreStockMarketRows"
              @click="revealMoreStockMarketRows"
            >
              {{ hasMoreStockMarketRows ? 'View More' : 'All Stocks Loaded' }}
            </button>
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
                  <small>Market data required</small>
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
          <p class="eyebrow">{{ isCryptoMode ? 'Crypto Markets' : 'Markets' }}</p>
          <h1 class="page-title">{{ isCryptoMode ? 'Digital asset signal, news, and social pulse' : 'Signal, news, and social pulse' }}</h1>
          <p class="page-subtitle">
            {{ isCryptoMode
              ? 'A black-and-white crypto desk for watching 24/7 liquidity, leader rotation, and what digital asset traders are saying around your focus symbol.'
              : 'A market desk for monitoring the tape, reading the story, and tracking what traders are saying around your focus symbol.' }}
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
            <span class="section-chip">{{ activeMarketSymbol }}</span>
          </div>

          <div class="spotlight-grid">
            <div class="spotlight-item">
              <span>Current Price</span>
              <strong>{{ formatMarketPrice(activeTradeResponse.stock.currentPrice) }}</strong>
            </div>
            <div class="spotlight-item">
              <span>52W High</span>
              <strong>{{ formatMarketPrice(activeTradeResponse.stock.week52High) }}</strong>
            </div>
            <div class="spotlight-item">
              <span>52W Low</span>
              <strong>{{ formatMarketPrice(activeTradeResponse.stock.week52Low) }}</strong>
            </div>
            <div class="spotlight-item">
              <span>Probability</span>
              <strong>{{ formatProbabilityDisplay(activeTradeResponse.patternAnalysis.probabilityOfIncrease) }}</strong>
            </div>
          </div>
        </article>
      </section>
    </main>

    <main v-else-if="activePage === 'Settings'" class="product-page">
      <section class="hero-surface compact">
        <div>
          <p class="eyebrow">{{ t('settingsEyebrow') }}</p>
          <h1 class="page-title">{{ t('settingsTitle') }}</h1>
          <p class="page-subtitle">{{ t('settingsSubtitle') }}</p>
        </div>
      </section>

      <section class="dashboard-grid myself-grid">
        <article class="table-surface dashboard-card">
          <div class="table-header">
            <h2>{{ t('accountDetails') }}</h2>
            <span class="section-chip">{{ currentUser?.isAdmin ? t('adminRole') : t('userRole') }}</span>
          </div>
          <div class="task-list myself-detail-list">
            <div class="task-row">
              <strong>{{ t('accountId') }}</strong>
              <small>{{ currentUserCode }}</small>
            </div>
            <div class="task-row">
              <strong>{{ t('fullName') }}</strong>
              <small>{{ currentUser?.fullName || currentUserName }}</small>
            </div>
            <div class="task-row">
              <strong>{{ t('email') }}</strong>
              <small>{{ currentUser?.email || t('notAvailable') }}</small>
            </div>
            <div class="task-row">
              <strong>{{ t('membership') }}</strong>
              <small>{{ currentUser?.membership || t('regularUser') }}</small>
            </div>
            <div class="task-row">
              <strong>{{ t('joined') }}</strong>
              <small>{{ currentUser?.joinedAt || t('recent') }}</small>
            </div>
          </div>
        </article>

        <article class="table-surface dashboard-card">
          <div class="table-header">
            <h2>{{ t('settingsEyebrow') }}</h2>
            <span class="section-chip">{{ t('session') }}</span>
          </div>
          <div class="dashboard-card-grid">
            <div class="dashboard-mini-card">
              <span>{{ t('currentLogin') }}</span>
              <strong>{{ currentUser?.emailVerified ? t('verified') : t('pendingVerification') }}</strong>
            </div>
          </div>
          <div class="myself-actions">
            <label class="language-selector settings-language-selector">
              <span>{{ t('selectLanguage') }}</span>
              <select v-model="uiLanguage" :aria-label="t('selectLanguage')">
                <option
                  v-for="language in languageOptions"
                  :key="language.code"
                  :value="language.code"
                >
                  {{ language.label }}
                </option>
              </select>
            </label>
            <button class="topbar-button" @click="signOut">{{ t('signOut') }}</button>
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
          <p class="eyebrow">{{ isCryptoMode ? 'Crypto More' : 'More' }}</p>
          <h1 class="page-title">{{ isCryptoMode ? 'What NoobTrade Crypto mode is preparing' : 'What NoobTrade is building' }}</h1>
          <p class="page-subtitle">
            {{ isCryptoMode
              ? 'A preview of how the same NoobTrade workflow can expand into digital asset research without mixing crypto screens into the stock experience.'
              : 'A beginner-first stock analysis workspace designed to make pattern-based trading more understandable, structured, and less intimidating.' }}
          </p>
        </div>
      </section>

      <section class="more-story-grid">
        <article class="more-card feature-story-card">
          <p class="eyebrow">{{ isCryptoMode ? 'About Crypto Mode' : 'About NoobTrade' }}</p>
          <h2>{{ isCryptoMode ? 'NoobTrade Crypto' : 'NoobTrade' }}</h2>
          <p>
            {{ isCryptoMode
              ? 'Crypto mode keeps the same dashboard, trade, explore, markets, settings, and admin shell, but presents it as a separate black-and-white digital asset workspace.'
              : 'NoobTrade turns stock pattern analysis into a cleaner workflow: search a symbol, inspect price structure, compare historical matches, and plan exits before acting.' }}
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
            {{ isCryptoMode
              ? 'The next crypto step is replacing preview data with a dedicated crypto probability engine, crypto-native indicators, and a research dataset separate from stock history.'
              : 'The next step is turning NoobTrade into a polished mobile product ready for global release on the Apple App Store and Google Play, with a cleaner onboarding flow, stronger production infrastructure, and a launch-ready experience for first-time traders.' }}
          </p>
        </article>
      </section>
    </main>

    <div
      v-if="usagePaywall.open"
      class="paywall-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="usage-paywall-title"
    >
      <div class="paywall-modal">
        <div class="paywall-topline">
          <span class="section-chip">NoobTrade Pro</span>
          <button class="topbar-button secondary" type="button" @click="closeUsagePaywall">Close</button>
        </div>
        <div class="paywall-price-row">
          <div>
            <p class="eyebrow">{{ usagePaywall.usageLabel }}</p>
            <h2 id="usage-paywall-title">{{ usagePaywall.title }}</h2>
          </div>
          <strong>{{ usagePaywall.displayPrice }}</strong>
        </div>
        <p>{{ usagePaywall.message }}</p>
        <p v-if="usagePaywall.limitLabel" class="paywall-limit-copy">Free limit: {{ usagePaywall.limitLabel }}.</p>
        <div class="paywall-benefit-list">
          <span>Unlimited Generate</span>
          <span>Unlimited Dashboard Scan</span>
          <span>Unlimited matched history</span>
        </div>
        <div class="paywall-actions">
          <a class="topbar-button" :href="usagePaywallUpgradeHref">Upgrade for $29.99/month</a>
          <button class="topbar-button secondary" type="button" @click="closeUsagePaywall">Maybe later</button>
        </div>
      </div>
    </div>

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
            <span class="source-pill source-pill--live">Historical Match</span>
          </div>
          <button class="topbar-button secondary" @click="closeHistoricalReplay">Close</button>
        </div>

        <div class="replay-meta-grid">
          <div class="spotlight-item">
            <span>Similar Move</span>
            <strong>{{ replayPattern.patternName }}</strong>
          </div>
          <div class="spotlight-item">
            <span>Similarity</span>
            <strong>{{ replayPattern.matchScore }}%</strong>
          </div>
          <div class="spotlight-item">
            <span>End Date</span>
            <strong>{{ replayPattern.date }}</strong>
          </div>
          <div class="spotlight-item">
            <span>5D High Touch</span>
            <strong>{{ formatPercent(replayPattern.futureReturn5d) }}</strong>
          </div>
        </div>

        <ChartPanel
          :active-indicators="appliedIndicators"
          :active-symbol="replayPattern.symbol"
          :chart-data="replayChartData"
          :chart-intervals="[replayPattern.timeframe]"
          :company-name="`${replayPattern.symbol} historical replay`"
          :comparison-anchor-index="Math.max((replayPattern.historicalCandles?.length || 1) - 1, 0)"
          comparison-anchor-label="Current-like moment"
          :industry="'Historical match'"
          :is-crypto-mode="isCryptoMode"
          :selected-interval="replayInterval"
          :sector="'Historical replay'"
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
        aria-label="NoobTrade voice assistant"
      >
        <div class="voice-panel-header">
          <div>
            <span class="section-chip">{{ t('aiMode') }}</span>
            <h2>{{ t('aiTitle') }}</h2>
          </div>
          <div class="voice-header-actions">
            <span class="voice-state" :class="{ active: voiceListening }">{{ voiceActionLabel }}</span>
            <button class="voice-minimize-button" type="button" @click="minimizeVoiceAssistantPanel">{{ t('shrink') }}</button>
          </div>
        </div>

        <p class="voice-disclaimer">
          {{ t('aiDisclaimer') }}
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
            <strong>{{ voiceAssistantEnabled ? t('aiModeOn') : t('aiModeOff') }}</strong>
            <small>{{ voiceAssistantEnabled ? t('aiListening') : t('aiManual') }}</small>
          </span>
        </button>

        <div class="voice-command-box" aria-live="polite">
          <small>{{ t('assistantStatus') }}</small>
          <strong>{{ voiceStatus }}</strong>
          <p>{{ voiceTranscript ? `${t('heardPrefix')}: ${voiceTranscript}` : t('sayCommand') }}</p>
        </div>

        <div class="voice-text-input">
          <input
            v-model="voiceInputDraft"
            type="text"
            :placeholder="t('typeCommand')"
            @keyup.enter="submitVoiceTextCommand"
          />
          <button class="topbar-button secondary" type="button" @click="submitVoiceTextCommand">{{ t('send') }}</button>
        </div>

        <div v-if="voicePendingAction" class="voice-confirm-card">
          <strong>{{ t('confirmationRequired') }}</strong>
          <p>{{ voicePendingAction.prompt }}</p>
          <div class="voice-actions">
            <button class="topbar-button" type="button" @click="confirmVoiceAction">{{ t('confirm') }}</button>
            <button class="topbar-button secondary" type="button" @click="cancelVoiceAction">{{ t('cancel') }}</button>
          </div>
        </div>

        <div class="voice-hints">
          <span v-for="example in voiceCommandExamples" :key="example">{{ example }}</span>
        </div>

        <div class="voice-footer">
          <span>{{ t('voiceLabel') }}: {{ voicePreferredVoiceName }}</span>
          <span>{{ voiceSupported ? t('voiceEnabled') : t('voiceUnsupported') }}</span>
        </div>

        <div class="voice-log">
          <div v-if="!voiceChatTimeline.length" class="voice-log-empty">
            <strong>Noob AI</strong>
            <small>{{ t('noobAiIntro') }}</small>
          </div>
          <div v-for="item in voiceChatTimeline" :key="`${item.time}-${item.transcript}-${item.response}`" class="voice-chat-turn">
            <div class="voice-bubble user">
              <span>{{ t('you') }} · {{ item.time }}</span>
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
        <h2>Add NoobTrade to Home Screen</h2>
        <p>
          In Safari, tap the Share button, then choose <strong>Add to Home Screen</strong>. After that, NoobTrade
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
        <span class="mobile-tab-label">{{ formatPageLabel(page) }}</span>
      </button>
    </nav>
  </div>
</template>
