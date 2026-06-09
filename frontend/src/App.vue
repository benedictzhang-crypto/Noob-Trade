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
    settingsNote: 'Your account stays stored in Render Postgres while market data and product features evolve.',
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
    settingsNote: '用户账户存储在 Render Postgres，市场数据和产品功能可以独立更新。',
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
    settingsNote: 'Tu cuenta se guarda en Render Postgres mientras evolucionan los datos y funciones.',
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
    settingsNote: 'Votre compte reste dans Render Postgres pendant l’évolution des données et fonctions.',
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
  'Open Stock Trade',
  'Scroll down',
  'Enable MACD and Bollinger',
  'Generate AAPL',
  'Scan watchlist 60 percent',
  'Search BTC',
  'Open Explore'
]
const voiceCryptoSymbols = new Set(['BTC', 'ETH', 'OKB', 'SOL', 'BNB'])
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
  { page: 'Markets', phrases: ['markets', 'market', '市场', 'mercados', 'mercado', 'marches', 'marchés'] },
  { page: 'Settings', phrases: ['settings', 'setting', 'myself', 'profile', 'account', 'configuration', 'configuracion', 'ajustes', 'parametres', 'paramètres', 'reglages', 'réglages', '设置', '账户', '账号', '个人信息'] },
  { page: 'More', phrases: ['more', 'more page', '更多', 'mas', 'más', 'plus'] },
  { page: 'Admin', phrases: ['admin', 'admin page', '后台', '管理员'] }
]
const voiceIntervalAliases = [
  { interval: '1min', phrases: ['1 minute', 'one minute', 'one min', '1 min'] },
  { interval: '5min', phrases: ['5 minute', 'five minute', '5 min', 'five min'] },
  { interval: '15min', phrases: ['15 minute', 'fifteen minute', '15 min', 'fifteen min'] },
  { interval: '30min', phrases: ['30 minute', 'thirty minute', '30 min', 'thirty min'] },
  { interval: '1hour', phrases: ['hourly', 'one hour', '1 hour', '60 minute'] },
  { interval: 'daily', phrases: ['daily', 'day chart', 'one day'] },
  { interval: '5day', phrases: ['five day', '5 day', 'five days', '5 days'] },
  { interval: 'weekly', phrases: ['weekly', 'week chart', 'one week'] },
  { interval: '2week', phrases: ['two week', '2 week', 'two weeks', '2 weeks'] },
  { interval: 'monthly', phrases: ['monthly', 'month chart', 'one month'] }
]
const voiceConfirmPhrases = ['confirm', 'yes', 'proceed', 'do it', 'run it', 'continue', '确认', '是的', '继续', 'sí', 'si', 'confirmar', 'oui', 'confirmer']
const voiceCancelPhrases = ['cancel', 'stop', 'no', 'never mind', 'nevermind', '取消', '停止', '不要', 'no', 'cancelar', 'parar', 'non', 'annuler', 'arreter', 'arrêter']
const voiceStopSpeechPhrases = ['stop talking', 'stop speaking', 'stop reading', 'be quiet', 'quiet', 'shut up', 'cancel speech', 'cancel voice', 'do not read', "don't read", 'pause voice', '停止朗读', '别念', '不要念', '不要读', '停一下', '安静', '闭嘴', 'parar voz', 'silencio', 'arrete de parler', 'arrête de parler']
const voiceEnablePhrases = ['enable', 'select', 'choose', 'pick', 'turn on', 'switch on', 'check', 'tick', 'add', 'use', 'include', '选择', '勾选', '打开', '启用', '加入', '使用', 'seleccionar', 'elige', 'elegir', 'activar', 'agregar', 'usar', 'incluye', 'incluire', 'selectionner', 'sélectionner', 'choisir', 'activer', 'ajouter', 'utiliser', 'inclure']
const voiceDisablePhrases = ['disable', 'unselect', 'deselect', 'cancel', 'turn off', 'switch off', 'uncheck', 'untick', 'remove', 'drop', 'exclude', '取消', '取消勾选', '关闭', '移除', '不要', 'quitar', 'desactivar', 'remover', 'excluir', 'retirer', 'desactiver', 'désactiver', 'enlever', 'exclure']
const voiceOnlyPhrases = ['only', 'only use', '只', '只选', '只用', '仅选择', 'solo', 'solamente', 'seulement', 'uniquement']
const voiceFollowUpPhrases = ['more', 'again', 'keep going', 'continue', 'a little bit more', 'little bit more', 'little more', 'bit more', 'further', 'more please', '再来', '继续', '再来一点', '再一点', '多一点', '再往下', '再往上', 'un poco mas', 'un poco más', 'otra vez', 'continua', 'continúa', 'encore', 'continuez', 'un peu plus']
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
const voiceSpeechMaxCharacters = 160

const activePage = ref('Home')
const appMode = ref('stock')
const uiLanguage = ref('en')
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
const predictionSummaryRef = ref(null)
const matchedPatternsRef = ref(null)

let feedRefreshTimer = null
let beforeInstallHandler = null
let voiceVoicesChangedHandler = null
let voiceRestartTimer = null
let analysisRequestVersion = 0
let voiceSpeechToken = 0
let voiceLastSpeechSignature = ''
let voiceLastSpeechAt = 0

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
const activeMarketSymbol = computed(() => (isCryptoMode.value ? cryptoResponse.value?.stock?.symbol || 'BTC' : activeSymbol.value))
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
  { name: 'S&P 500', level: '5,214.08', change: '+0.42%', tone: 'positive' },
  { name: 'NASDAQ 100', level: '18,102.44', change: '+0.78%', tone: 'positive' },
  { name: 'Dow Jones', level: '39,842.12', change: '+0.19%', tone: 'positive' },
  { name: 'VIX', level: '14.82', change: '-1.14%', tone: 'negative' }
]

const cryptoMarketOverviewCards = [
  { name: 'Bitcoin', level: '$103,420', change: '+2.84%', tone: 'positive' },
  { name: 'Ethereum', level: '$4,920', change: '+2.18%', tone: 'positive' },
  { name: 'Solana', level: '$224.15', change: '+4.31%', tone: 'positive' },
  { name: 'Crypto Vol', level: '61.8', change: '-0.74%', tone: 'negative' }
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
const currentExploreRows = computed(() => {
  if (isCryptoMode.value) {
    return cryptoExploreRows
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
  if (isCryptoMode.value) {
    return cryptoExploreRows
  }

  if (exploreViewMode.value === 'full') {
    return fullMarketBoardRows.value
  }

  return currentExploreRows.value
})
const filteredExploreRows = computed(() => {
  const query = exploreSearchQuery.value.trim().toUpperCase()
  const sourceRows = isCryptoMode.value ? cryptoExploreRows : (query ? allExploreRows.value : visibleExploreRows.value)

  if (!query) {
    return sourceRows
  }

  return sourceRows.filter((row) => {
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
const activeStarredSymbols = computed(() => (isCryptoMode.value ? cryptoStarredSymbols.value : starredSymbols.value))
const starredLookup = computed(() => new Set(activeStarredSymbols.value))
const dashboardWatchlistRows = computed(() => {
  return activeStarredSymbols.value
    .map((symbol) => {
      if (isCryptoMode.value) {
        const cryptoRow = cryptoExploreRows.find((row) => row.symbol === symbol)
        if (cryptoRow) {
          return {
            symbol: cryptoRow.symbol,
            price: cryptoRow.price,
            change: cryptoRow.change,
            tone: cryptoRow.tone,
            note: cryptoRow.category
          }
        }

        return {
          symbol,
          price: '--',
          change: '--',
          tone: 'neutral',
          note: 'Saved crypto'
        }
      }

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
  const providerLabel = activeTradeResponse.value.marketDataProvider || ''

  if (activeTradeResponse.value.dataSource === 'crypto-mock') {
    return {
      label: 'Crypto Preview',
      description: 'Crypto framework placeholder',
      tone: 'mock'
    }
  }

  if (activeTradeResponse.value.dataSource === 'crypto-demo') {
    return {
      label: 'Crypto Replay',
      description: providerLabel || 'Cached crypto replay',
      tone: 'mock'
    }
  }

  if (activeTradeResponse.value.dataSource === 'live') {
    return {
      label: 'Live API',
      description: providerLabel || 'Connected market feed',
      tone: 'live'
    }
  }

  if (activeTradeResponse.value.dataSource === 'cached') {
    return {
      label: 'Live API',
      description: providerLabel || 'Connected market feed',
      tone: 'live'
    }
  }

  if (activeTradeResponse.value.dataSource === 'demo') {
    return {
      label: 'Demo Replay',
      description: providerLabel || 'Cached replay feed',
      tone: 'mock'
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
    { label: 'Best Probability', value: bestMatch ? `${bestMatch.probability.toFixed(2)}%` : '--', note: bestMatch ? `${bestMatch.symbol} is currently the strongest match` : 'Waiting for the next scan result' }
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

  const cryptoRow = cryptoExploreRows.find((row) => row.symbol === symbol)
  if (cryptoRow) {
    return Number(String(cryptoRow.price || '').replace('$', '').replace(',', ''))
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
  recognition.lang = getSpeechLanguage()
  recognition.continuous = true
  recognition.interimResults = true
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
      setVoiceStatus('Microphone permission is blocked. Please allow microphone access for NoobTrade.', { speak: false })
      return
    }

    if (errorName !== 'no-speech' && errorName !== 'aborted') {
      setVoiceStatus(`Voice input paused: ${errorName}. I will keep trying while AI Mode is on.`, { speak: false })
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
  voiceStatus.value = 'I hear you. Go ahead.'
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

  const greeting = 'AI Mode is on. You can talk naturally. Try: Generate AAPL, explain RSI, or open Explore.'
  setVoiceStatus(greeting, { speak: true })
  scheduleVoiceRestart(900)
}

function disableVoiceAssistant() {
  voiceAssistantEnabled.value = false
  voicePendingAction.value = null
  clearVoiceRestartTimer()
  stopVoiceListening()
  stopVoiceSpeech({ restartListening: false })
  voiceStatus.value = 'AI Mode is off. Manual controls stay available.'
}

function startVoiceListening({ silent = false, cancelSpeech = true } = {}) {
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
    if (cancelSpeech) {
      stopVoiceSpeech({ restartListening: false })
    }
    voiceRecognition.value.lang = getSpeechLanguage()
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
    'scrool', 'scroolling', 'lower', 'higher', 'again', 'continue', 'further'
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
    return 'Scrolling down.'
  }

  if (normalizedDirection === 'up') {
    window.scrollBy({ top: -distance, left: 0, behavior: 'smooth' })
    rememberVoiceIntent('scroll', 'up')
    return 'Scrolling up.'
  }

  if (normalizedDirection === 'top') {
    window.scrollTo({ top: 0, behavior: 'smooth' })
    rememberVoiceIntent('scroll', 'up')
    return 'Going to the top.'
  }

  if (normalizedDirection === 'bottom') {
    window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' })
    rememberVoiceIntent('scroll', 'down')
    return 'Going to the bottom.'
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
    return 'Going back.'
  }

  if (includesVoicePhrase(command, ['minimize ai', 'shrink ai', 'hide ai', 'close panel', 'close ai panel'])) {
    minimizeVoiceAssistantPanel()
    return 'AI panel minimized. I can keep listening if AI Mode is still on.'
  }

  if (includesVoicePhrase(command, ['open ai panel', 'show ai panel', 'expand ai', 'open assistant'])) {
    openVoiceAssistantPanel()
    return 'AI panel opened.'
  }

  if (includesVoicePhrase(command, ['turn off ai', 'disable ai mode', 'stop ai mode'])) {
    disableVoiceAssistant()
    return 'AI Mode is off.'
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

  const actionLabel = source === 'generate' ? 'Generating' : 'Searching'
  const workingSymbol = normalizeTradeSymbolInput(symbolInput.value, { isCrypto: activePage.value === 'Crypto Trade' }) || activeSymbol.value
  setVoiceStatus(`${actionLabel} ${workingSymbol}.`, { speak: true, transcript })
  await runSearch(source)

  if (errorMessage.value) {
    setVoiceStatus(getReadableMarketDataError(errorMessage.value, workingSymbol), { speak: true, transcript })
    return
  }

  const finishedSymbol = activeTradeResponse.value?.stock?.symbol || workingSymbol
  const probability = getAnalysisUpsideProbability(activeTradeResponse.value)
  const probabilityText = source === 'generate' && Number.isFinite(probability)
    ? ` Upside probability is ${probability.toFixed(2)}%.`
    : ''
  setVoiceStatus(`${finishedSymbol} is ready.${probabilityText} I loaded the latest analysis workspace for you.`, { speak: true, transcript })
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
  const indicatorExplanation = getIndicatorExplanation(command)

  const replies = {
    zh: {
      greeting: '我在，可以自然说中文。我能回答问题，也能帮你操作页面。',
      wake: '我在。你想让我帮你看行情、切换页面、选择指标，还是运行 Generate？',
      thanks: '不客气。我会继续保持 AI 模式，你也可以随时手动操作。',
      scrollHelp: '我可以控制页面滚动。你可以说：向下滚动、向上滚动、回到顶部、到底部。',
      indicatorHelp: '我可以选择或取消指标。比如：选择 MACD 和布林带，取消 EMA，选择 RSI，移除成交量。',
      generateHelp: '你可以说 Generate AAPL，或者说生成 AAPL，我会切到对应页面并运行分析。',
      capabilities: '我可以聊天、滚动屏幕、切换页面、选择或取消指标、切换周期、搜索股票、扫描自选、运行 Generate。不能语音下单，也不提供投资建议。',
      advice: '我不能提供投资建议，但可以帮你打开分析、解释指标、展示模型结果供你判断。',
      fallback: '我在听，但还不确定你想让我做什么。你可以说：生成 AAPL、打开股票分析、选择 MACD、向下滚动。',
    },
    es: {
      greeting: 'Estoy aquí. Puedes hablar en español; puedo responder o controlar la página.',
      wake: 'Estoy aquí. ¿Quieres que analice, navegue, cambie indicadores o escanee tu lista?',
      thanks: 'Con gusto. Sigo en AI Mode, y también puedes usar la página manualmente.',
      scrollHelp: 'Puedo controlar la pantalla. Prueba: desplaza abajo, sube, ir arriba o ir abajo.',
      indicatorHelp: 'Puedo seleccionar o quitar indicadores. Prueba: selecciona MACD, quita EMA, elige RSI o remueve volumen.',
      generateHelp: 'Di Generate AAPL o analiza AAPL, y abriré el análisis.',
      capabilities: 'Puedo conversar, desplazar la pantalla, abrir páginas, seleccionar indicadores, cambiar intervalos, buscar símbolos, escanear favoritos y ejecutar Generate. No puedo colocar órdenes ni dar asesoría financiera.',
      advice: 'No puedo dar asesoría financiera. Puedo abrir el análisis, explicar indicadores y mostrar el resultado del modelo.',
      fallback: 'Estoy escuchando, pero no estoy segura de la acción. Puedes decir Generate AAPL, abrir Acciones, seleccionar MACD o desplaza abajo.',
    },
    fr: {
      greeting: 'Je suis là. Vous pouvez parler en français; je peux répondre ou contrôler la page.',
      wake: 'Je suis là. Voulez-vous analyser, naviguer, changer des indicateurs ou scanner vos favoris ?',
      thanks: 'Avec plaisir. Je reste en mode IA, et vous pouvez aussi utiliser la page manuellement.',
      scrollHelp: 'Je peux contrôler l’écran. Essayez : défiler vers le bas, monter, aller en haut ou aller en bas.',
      indicatorHelp: 'Je peux sélectionner ou retirer des indicateurs. Essayez : sélectionner MACD, retirer EMA, choisir RSI ou enlever le volume.',
      generateHelp: 'Dites Generate AAPL ou analyser AAPL, et j’ouvrirai l’analyse.',
      capabilities: 'Je peux discuter, faire défiler l’écran, ouvrir des pages, sélectionner des indicateurs, changer d’intervalle, rechercher des symboles, scanner les favoris et lancer Generate. Je ne peux pas passer d’ordres ni donner de conseil financier.',
      advice: 'Je ne peux pas donner de conseil financier. Je peux ouvrir l’analyse, expliquer les indicateurs et montrer le résultat du modèle.',
      fallback: 'J’écoute, mais je ne suis pas sûre de l’action. Vous pouvez dire Generate AAPL, ouvrir Actions, sélectionner MACD ou défiler vers le bas.',
    },
    en: {
      greeting: 'Hi, I am here. You can talk normally, and I will either answer or operate the page for you.',
      wake: 'I am here. What can I help you with? I can analyze, navigate, adjust indicators, or answer questions.',
      thanks: 'Anytime. I am staying in AI Mode, so you can keep talking or use the page manually.',
      scrollHelp: 'I can control the screen. Try saying scroll down, scroll up, go to top, or go to bottom.',
      indicatorHelp: 'I can select or remove indicators. Try select MACD and Bollinger, unselect EMA, choose RSI, or remove volume.',
      generateHelp: 'Say Generate followed by a ticker, like Generate AAPL. I will switch to the right workspace and run it.',
      capabilities: 'I can chat, scroll the screen, open pages, select or unselect indicators, switch intervals, search tickers, scan your starred watchlist, and run Generate. I cannot place trades or give investment advice.',
      advice: 'I cannot give investment advice. I can help you open the analysis, explain indicators, and show the model output so you can review it.',
      fallback: 'I am listening, but I am not sure what action you want. You can ask a question, or say something like Generate AAPL, open Crypto Trade, or enable MACD.',
    }
  }
  const localReplies = replies[uiLanguage.value] || replies.en

  if (indicatorExplanation && includesVoicePhrase(command, ['what is', 'explain', 'tell me about', 'how does'])) {
    return indicatorExplanation
  }

  if (includesVoicePhrase(command, ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'are you there', 'you there', 'noob trade', 'assistant', '你好', '您好', '嗨', '你在吗', '在吗', 'hola', 'bonjour', 'salut'])) {
    return includesVoicePhrase(command, ['hey', 'are you there', 'you there', 'noob trade', 'assistant', '你在吗', '在吗'])
      ? localReplies.wake
      : localReplies.greeting
  }

  if (includesVoicePhrase(command, ['thank you', 'thanks', 'nice', 'great', '谢谢', '感谢', 'gracias', 'merci'])) {
    return localReplies.thanks
  }

  if (includesVoicePhrase(command, ['where am i', 'what page', 'current page', 'where are we'])) {
    return getAssistantContextSummary()
  }

  if (includesVoicePhrase(command, ['scroll', 'scrolling', 'move down', 'move up', 'page down', 'page up', '滚动', '下滑', '上滑', 'desplaza', 'desplazar', 'defiler', 'défiler'])) {
    return localReplies.scrollHelp
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
    return localReplies.generateHelp
  }

  if (includesVoicePhrase(command, ['indicator', 'indicators', 'select', 'unselect', 'choose', 'remove', '指标', '选择', '取消', 'indicador', 'indicadores', 'selecciona', 'quitar', 'indicateur', 'indicateurs', 'selectionner', 'sélectionner', 'retirer'])) {
    return localReplies.indicatorHelp
  }

  if (includesVoicePhrase(command, ['what can you do', 'help', 'commands', '帮助', '帮我', '你会什么', 'ayuda', 'que puedes hacer', 'aide', 'que peux tu faire'])) {
    return localReplies.capabilities
  }

  if (includesVoicePhrase(command, ['financial advice', 'should i buy', 'should i sell', 'recommend', 'advice', '投资建议', '该买吗', '该卖吗', '建议', 'asesoria', 'comprar', 'vender', 'conseil', 'acheter', 'vendre'])) {
    return localReplies.advice
  }

  const maybeSymbol = extractVoiceSymbol(command, { allowLooseTicker: false })
  if (maybeSymbol) {
    return `I heard ${maybeSymbol}. If you want action, say Search ${maybeSymbol} or Generate ${maybeSymbol}.`
  }

  return localReplies.fallback
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
    setVoiceStatus('I did not catch that. Please try again.', { speak: true, transcript: rawTranscript })
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
    setVoiceStatus('Stopped. I am listening.', { speak: false, transcript: rawTranscript })
    return
  }

  if (isVoiceOutputActive()) {
    stopVoiceSpeech({ restartListening: false })
  }

  if (isVoiceCorrectionCommand(command) && voiceLastAssistantPrediction.value) {
    const correctionText = extractVoiceCorrectionText(rawTranscript)
    if (!correctionText) {
      await saveAssistantFeedback({ correctionTranscript: rawTranscript })
      setVoiceStatus('Thanks, I saved that correction for NoobTrade AI training. Please say the command again in the way you want it handled.', {
        speak: true,
        transcript: rawTranscript
      })
      return
    }

    correctionTranscript = correctionText
    effectiveTranscript = correctionText
    command = normalizeVoiceText(correctionText)
    voiceTranscript.value = correctionText
    setVoiceStatus('Thanks, I saved that correction and will use it for NoobTrade AI training. Let me do what you meant now.', {
      speak: true,
      transcript: rawTranscript
    })
  }

  if (includesVoicePhrase(command, ['中文', 'chinese', 'mandarin', '普通话'])) {
    uiLanguage.value = 'zh'
    setVoiceStatus('已切换到中文。我现在可以听中文指令。', { speak: true, transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['spanish', 'espanol', 'español'])) {
    uiLanguage.value = 'es'
    setVoiceStatus('Idioma cambiado a español. Ahora puedo escuchar comandos en español.', { speak: true, transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['french', 'francais', 'français'])) {
    uiLanguage.value = 'fr'
    setVoiceStatus('Langue changée en français. Je peux maintenant écouter les commandes en français.', { speak: true, transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['english', '英语', 'anglais', 'ingles'])) {
    uiLanguage.value = 'en'
    setVoiceStatus('Language switched to English.', { speak: true, transcript: rawTranscript })
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
    setVoiceStatus(buildConversationalReply(command), {
      speak: true,
      transcript: rawTranscript
    })
    return
  }

  if (includesVoicePhrase(command, ['buy ', 'sell ', 'place order', 'submit order', 'market order', 'limit order', 'short ', 'go long', 'go short', '买入', '卖出', '下单', '做空', '做多', 'comprar', 'vender', 'orden', 'acheter', 'vendre', 'ordre'])) {
    setVoiceStatus('Voice trading orders are disabled. I can control analysis and navigation only.', {
      speak: true,
      transcript: rawTranscript
    })
    return
  }

  if (includesVoicePhrase(command, ['sign out', 'log out', 'logout', '退出登录', '登出', 'cerrar sesion', 'cerrar sesión', 'deconnexion', 'déconnexion'])) {
    queueVoiceAction({
      type: 'signOut',
      prompt: 'Confirm sign out? Say confirm to leave your account, or cancel to stay signed in.'
    })
    return
  }

  const requestedPage = findVoicePage(command)
  if (requestedPage && includesVoicePhrase(command, ['open', 'go to', 'show', 'switch to', 'navigate', '打开', '进入', '切换到', '显示', 'abrir', 'ir a', 'mostrar', 'cambiar a', 'ouvrir', 'aller a', 'aller à', 'afficher', 'passer a', 'passer à'])) {
    navigateTo(requestedPage)
    setVoiceStatus(`Opened ${requestedPage}.`, { speak: true, transcript: rawTranscript })
    return
  }

  const screenControlReply = runVoiceScreenControl(command)
  if (screenControlReply) {
    setVoiceStatus(screenControlReply, { speak: true, transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['clear indicators', 'turn off all indicators', 'disable all indicators', '清空指标', '关闭所有指标', '取消所有指标', 'quitar todos los indicadores', 'desactivar todos los indicadores', 'retirer tous les indicateurs', 'desactiver tous les indicateurs'])) {
    indicators.value = indicators.value.map((indicator) => ({ ...indicator, active: false }))
    setVoiceStatus('All indicators are off.', { speak: true, transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['reset indicators', 'default indicators', 'restore indicators', '重置指标', '默认指标', 'restablecer indicadores', 'indicadores predeterminados', 'retablir indicateurs', 'réinitialiser indicateurs'])) {
    const defaultSelected = new Set(['MA', 'EMA', 'MACD', 'BOLL', 'VOL'])
    indicators.value = indicators.value.map((indicator) => ({
      ...indicator,
      active: defaultSelected.has(String(indicator.name).toUpperCase())
    }))
    setVoiceStatus('Indicators reset to the default NoobTrade selection.', { speak: true, transcript: rawTranscript })
    return
  }

  if (includesVoicePhrase(command, ['scan', '扫描', 'escanear', 'scanner']) && includesVoicePhrase(command, ['watchlist', 'starred', 'stars', 'favorites', 'self selected', 'self-selected', '自选', '星标', 'favoritos', 'favoris'])) {
    const threshold = extractVoiceProbability(command)
    watchlistScanThreshold.value = threshold
    navigateTo('Dashboard')
    setVoiceStatus(`Scanning your starred watchlist for probabilities at or above ${threshold.toFixed(0)} percent.`, {
      speak: true,
      transcript: rawTranscript
    })
    await scanStarredWatchlist()
    setVoiceStatus(watchlistScanMessage.value || 'Watchlist scan is complete.', {
      speak: true,
      transcript: rawTranscript
    })
    return
  }

  if (includesVoicePhrase(command, ['select all indicators', 'enable all indicators', 'turn on all indicators', '选择所有指标', '打开所有指标', 'seleccionar todos los indicadores', 'activar todos los indicadores', 'selectionner tous les indicateurs', 'activer tous les indicateurs'])) {
    indicators.value = indicators.value.map((indicator) => ({ ...indicator, active: true }))
    setVoiceStatus('All indicators are on.', { speak: true, transcript: rawTranscript })
    return
  }

  const mentionedIndicators = findVoiceIndicators(command)
  if (mentionedIndicators.length) {
    if (includesVoicePhrase(command, voiceOnlyPhrases)) {
      setOnlyVoiceIndicators(mentionedIndicators)
      setVoiceStatus(`Only ${mentionedIndicators.join(', ')} are selected.`, { speak: true, transcript: rawTranscript })
      return
    }

    if (includesVoicePhrase(command, voiceDisablePhrases)) {
      setIndicatorActive(mentionedIndicators, false)
      setVoiceStatus(`${mentionedIndicators.join(', ')} turned off.`, { speak: true, transcript: rawTranscript })
      return
    }

    if (!includesVoicePhrase(command, voiceEnablePhrases) && !includesVoicePhrase(command, ['indicator', 'indicators'])) {
      const toggledIndicator = toggleVoiceIndicator(mentionedIndicators[0])
      if (toggledIndicator) {
        setVoiceStatus(`${toggledIndicator.name} turned ${toggledIndicator.active ? 'on' : 'off'}.`, { speak: true, transcript: rawTranscript })
        return
      }
    }

    if (includesVoicePhrase(command, voiceEnablePhrases) || includesVoicePhrase(command, ['indicator', 'indicators'])) {
      setIndicatorActive(mentionedIndicators, true)
      setVoiceStatus(`${mentionedIndicators.join(', ')} turned on.`, { speak: true, transcript: rawTranscript })
      return
    }
  }

  const requestedInterval = findVoiceInterval(command)
  if (requestedInterval && includesVoicePhrase(command, ['interval', 'chart', 'time frame', 'timeframe', 'switch', '周期', '图表', '切换', 'intervalo', 'grafico', 'gráfico', 'cambiar', 'intervalle', 'graphique', 'changer'])) {
    selectedChartInterval.value = requestedInterval
    setVoiceStatus(`Chart interval set to ${requestedInterval}.`, { speak: true, transcript: rawTranscript })
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

  setVoiceStatus(buildConversationalReply(command), {
    speak: true,
    transcript: rawTranscript
  })
}

function navigateTo(page) {
  const pageAliases = {
    Analysis: 'Stock Trade',
    Myself: 'Settings'
  }
  const normalizedPage = pageAliases[page] || page

  if (accessiblePages.value.includes(normalizedPage)) {
    activePage.value = normalizedPage
    authMessage.value = ''
    errorMessage.value = ''

    if (normalizedPage === 'Crypto Trade') {
      appMode.value = 'crypto'
      symbolInput.value = cryptoResponse.value.stock.symbol
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
      symbolInput.value = cryptoResponse.value.stock.symbol
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
  if (activePage.value === 'Crypto Trade') {
    cryptoResponse.value = createCryptoWorkspaceResponse(symbol)
    errorMessage.value = ''
    return
  }
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
  const directProbability = Number(data?.patternAnalysis?.probabilityOfIncrease)

  if (Number.isFinite(directProbability)) {
    return directProbability
  }

  const ladder = data?.patternAnalysis?.futureFiveDayProbabilities?.up || []
  const onePercentHit = ladder.find((item) => Number(item.threshold) === 1)
  const ladderProbability = Number(onePercentHit?.probability)

  return Number.isFinite(ladderProbability) ? ladderProbability : 0
}

function formatScanTimestamp(date = new Date()) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

async function runLimitedTasks(items, worker, limit = 4) {
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
  watchlistScanMessage.value = `Scanning ${symbols.length} saved ${isCryptoMode.value ? 'crypto assets' : 'stocks'} together with Generate logic...`

  try {
    const scanResults = await runLimitedTasks(symbols, async (symbol) => {
      const data = isCryptoMode.value
        ? await fetchCryptoAnalysis(symbol, { analysisMode: 'full', compact: true, cacheResult: false })
        : await fetchStockAnalysis(symbol, { analysisMode: 'full', compact: true, cacheResult: false })
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
    }, symbols.length)

    const passedResults = []
    const failedSymbols = []

    scanResults.forEach((result, index) => {
      const symbol = symbols[index]

      if (result?.status !== 'fulfilled') {
        failedSymbols.push(symbol)
        return
      }

      if (result.value.probability >= threshold) {
        passedResults.push(result.value)
      }
    })

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
  appMode.value = 'crypto'
  cryptoResponse.value = createCryptoWorkspaceResponse(cleanedSymbol)
  symbolInput.value = cleanedSymbol
  activePage.value = 'Crypto Trade'
  void runSearch()
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

function buildAnalysisCacheKey(symbol, analysisMode = 'full', assetType = 'stock') {
  return [
    assetType,
    String(symbol || '').trim().toUpperCase(),
    selectedChartInterval.value,
    getSelectedIndicators().join(','),
    analysisMode
  ].join('|')
}

function hasChartSeries(response, interval) {
  const candles = response?.chartData?.series?.[interval]
  return Array.isArray(candles) && candles.length > 0
}

async function fetchStockAnalysis(symbol, { analysisMode = 'full', compact = false, cacheResult = true } = {}) {
  const cleanedSymbol = normalizeTradeSymbolInput(symbol)
  const cacheKey = buildAnalysisCacheKey(cleanedSymbol, analysisMode, 'stock')

  if (cacheResult) {
    const cachedAnalysis = analysisCache.value[cacheKey]
    if (cachedAnalysis && hasChartSeries(cachedAnalysis, selectedChartInterval.value)) {
      return cachedAnalysis
    }

    if (cachedAnalysis) {
      const { [cacheKey]: _staleAnalysis, ...freshCache } = analysisCache.value
      analysisCache.value = freshCache
    }
  }

  const query = new URLSearchParams({
    indicators: getSelectedIndicators().join(','),
    analysis: analysisMode,
  })
  query.set('interval', selectedChartInterval.value)
  if (compact) {
    query.set('compact', '1')
  }

  const requestUrl = `${API_BASE_URL}/stock/${encodeURIComponent(cleanedSymbol)}?${query.toString()}`
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
  if (cacheResult) {
    analysisCache.value = {
      ...analysisCache.value,
      [cacheKey]: data
    }
  }

  return data
}

async function fetchCryptoAnalysis(symbol, { analysisMode = 'full', compact = false, cacheResult = true } = {}) {
  const cleanedSymbol = normalizeTradeSymbolInput(symbol, { isCrypto: true })
  const cacheKey = buildAnalysisCacheKey(cleanedSymbol, analysisMode, 'crypto')

  if (cacheResult) {
    const cachedAnalysis = analysisCache.value[cacheKey]
    if (cachedAnalysis && hasChartSeries(cachedAnalysis, selectedChartInterval.value)) {
      return cachedAnalysis
    }

    if (cachedAnalysis) {
      const { [cacheKey]: _staleAnalysis, ...freshCache } = analysisCache.value
      analysisCache.value = freshCache
    }
  }

  const query = new URLSearchParams({
    indicators: getSelectedIndicators().join(','),
    analysis: analysisMode
  })
  query.set('interval', selectedChartInterval.value)
  if (compact) {
    query.set('compact', '1')
  }

  const requestUrl = `${API_BASE_URL}/crypto/${encodeURIComponent(cleanedSymbol)}?${query.toString()}`
  const response = await secureFetch(requestUrl, {
    timeoutMs: analysisMode === 'search' ? 12000 : 35000
  })

  if (!response.ok) {
    const payload = await parseErrorResponse(
      response,
      `${cleanedSymbol} crypto data is not accessible right now.`
    )
    throw new Error(payload.message || `${cleanedSymbol} crypto data is not accessible right now.`)
  }

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

function applyAnalysisResponse(data, isCryptoPage) {
  if (isCryptoPage) {
    cryptoResponse.value = data
    symbolInput.value = data.stock.symbol
    return
  }

  stockResponse.value = data
  activeSymbol.value = data.stock.symbol
  symbolInput.value = data.stock.symbol
  activePage.value = 'Stock Trade'
}

async function refreshFullGenerateInBackground(symbol, isCryptoPage, requestVersion) {
  try {
    const data = isCryptoPage
      ? await fetchCryptoAnalysis(symbol, { analysisMode: 'full' })
      : await fetchStockAnalysis(symbol, { analysisMode: 'full' })

    if (requestVersion !== analysisRequestVersion) {
      return
    }

    const responseSymbol = String(data?.stock?.symbol || '').toUpperCase()
    if (responseSymbol !== String(symbol || '').toUpperCase()) {
      return
    }

    if (isCryptoPage && activePage.value !== 'Crypto Trade') {
      return
    }
    if (!isCryptoPage && activePage.value !== 'Stock Trade') {
      return
    }

    applyAnalysisResponse(data, isCryptoPage)
  } catch (error) {
    console.warn('Full Generate refresh could not finish.', error)
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
  if (isGenerateAction) {
    isGenerating.value = true
  } else {
    isSearching.value = true
  }
  errorMessage.value = ''

  if (isCryptoPage) {
    try {
      const data = await fetchCryptoAnalysis(cleanedSymbol, {
        analysisMode: 'search'
      })
      applyAnalysisResponse(data, true)
      scrollAnalysisWorkspaceToTop()
      if (isGenerateAction) {
        void refreshFullGenerateInBackground(cleanedSymbol, true, requestVersion)
      }
    } catch (error) {
      errorMessage.value = getReadableMarketDataError(error?.message, cleanedSymbol)
      console.error(error)
    } finally {
      if (isGenerateAction) {
        isGenerating.value = false
      } else {
        isSearching.value = false
      }
    }
    return
  }

  try {
    const data = await fetchStockAnalysis(cleanedSymbol, {
      analysisMode: 'search'
    })

    applyAnalysisResponse(data, false)
    scrollAnalysisWorkspaceToTop()
    if (isGenerateAction) {
      void refreshFullGenerateInBackground(cleanedSymbol, false, requestVersion)
    }
  } catch (error) {
    errorMessage.value = getReadableMarketDataError(error?.message, cleanedSymbol)
    console.error(error)
  } finally {
    if (isGenerateAction) {
      isGenerating.value = false
    } else {
      isSearching.value = false
    }
  }
}

async function handleChartIntervalChange(interval) {
  selectedChartInterval.value = interval

  const isCryptoPage = activePage.value === 'Crypto Trade'
  const responseRef = isCryptoPage ? cryptoResponse : stockResponse
  const symbol = responseRef.value?.stock?.symbol
  const availableSeries = responseRef.value?.chartData?.series || {}

  if (!symbol || availableSeries[interval]?.length) {
    return
  }

  try {
    const data = isCryptoPage
      ? await fetchCryptoAnalysis(symbol, { analysisMode: 'full' })
      : await fetchStockAnalysis(symbol, { analysisMode: 'full' })
    responseRef.value = data
    if (!isCryptoPage) {
      activeSymbol.value = data.stock.symbol
    }
    symbolInput.value = data.stock.symbol
  } catch (error) {
    errorMessage.value = getReadableMarketDataError(error?.message, symbol)
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

function buildCryptoFocusUniverse(symbol, refreshKey) {
  const symbols = cryptoExploreRows.map((row) => row.symbol)
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
    return 'I could not find an available historical match yet.'
  }

  const score = Number(pattern.matchScore)
  const scoreText = Number.isFinite(score) ? `${score.toFixed(1)}% match` : 'matched setup'
  return `Opened a historical window from ${pattern.date || 'the matched period'} with ${scoreText}. Future 5D return was ${formatPercent(pattern.futureReturn5d)}.`
}

function buildAssistantIntentContext() {
  return {
    activePage: activePage.value,
    language: uiLanguage.value,
    symbol: activeTradeResponse.value?.stock?.symbol || activeSymbol.value,
    selectedIndicators: getSelectedIndicators(),
    availablePages: accessiblePages.value,
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
    setVoiceStatus(
      intentPayload.reply || 'Voice trading orders are disabled. I can control analysis and navigation only.',
      { speak: true, transcript: rawTranscript }
    )
    return true
  }

  if (intent === 'navigate' && intentPayload.page) {
    navigateTo(intentPayload.page)
    setVoiceStatus(intentPayload.reply || `Opened ${intentPayload.page}.`, { speak: true, transcript: rawTranscript })
    return true
  }

  if (intent === 'scroll') {
    const reply = executeVoiceScrollIntent(intentPayload.direction, intentPayload.amount)
    if (reply) {
      setVoiceStatus(intentPayload.reply || reply, { speak: true, transcript: rawTranscript })
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
    setVoiceStatus(`Scanning your starred watchlist for probabilities at or above ${watchlistScanThreshold.value.toFixed(0)} percent.`, {
      speak: true,
      transcript: rawTranscript
    })
    await scanStarredWatchlist()
    setVoiceStatus(watchlistScanMessage.value || 'Watchlist scan is complete.', {
      speak: true,
      transcript: rawTranscript
    })
    return true
  }

  if (intent === 'adjust_probability') {
    const snapshot = setVoiceProbabilityThreshold(intentPayload.side, intentPayload.value)
    if (snapshot) {
      setVoiceStatus(`${formatProbabilitySide(snapshot.side)} threshold is now ${snapshot.side === 'down' ? '-' : '+'}${Number(snapshot.threshold).toFixed(1)}%. Probability is ${snapshot.probability}.`, {
        speak: true,
        transcript: rawTranscript
      })
      return true
    }
  }

  if (intent === 'summarize_probability') {
    const snapshot = getVoiceProbabilitySnapshot(intentPayload.side || 'up', intentPayload.value)
    if (snapshot) {
      const thresholdPrefix = snapshot.side === 'down' ? '-' : '+'
      setVoiceStatus(`For ${thresholdPrefix}${Number(snapshot.threshold).toFixed(1)}% ${formatProbabilitySide(snapshot.side)} within 5 trading days, probability is ${snapshot.probability}. The headline +1% upside probability is ${snapshot.headlineProbability}, based on ${snapshot.matchedPatternCount} similar historical setups.`, {
        speak: true,
        transcript: rawTranscript
      })
      return true
    }
  }

  if (intent === 'open_historical_pattern') {
    const index = Number.isFinite(Number(intentPayload.index)) ? Math.max(Number(intentPayload.index) - 1, 0) : 0
    const opened = openVoiceHistoricalPattern(index)
    if (opened) {
      setVoiceStatus(summarizeHistoricalPattern(opened.pattern), {
        speak: true,
        transcript: rawTranscript
      })
      return true
    }

    setVoiceStatus('No historical pattern window is available yet. Run Generate first, then ask me again.', {
      speak: true,
      transcript: rawTranscript
    })
    return true
  }

  if (intent === 'load_more_patterns') {
    matchedPatternsRef.value?.loadMorePatterns?.()
    setVoiceStatus('Loaded more historical matches.', { speak: true, transcript: rawTranscript })
    return true
  }

  if (intent === 'set_star') {
    const targetSymbol = intentPayload.symbol || activeTradeResponse.value?.stock?.symbol || activeSymbol.value
    if (setStarredSymbol(targetSymbol, intentPayload.active !== false)) {
      setVoiceStatus(`${String(targetSymbol).toUpperCase()} ${intentPayload.active === false ? 'removed from' : 'added to'} your starred watchlist.`, {
        speak: true,
        transcript: rawTranscript
      })
      return true
    }
  }

  if (intent === 'clear_indicators') {
    indicators.value = indicators.value.map((indicator) => ({ ...indicator, active: false }))
    setVoiceStatus('All indicators are off.', { speak: true, transcript: rawTranscript })
    return true
  }

  if (intent === 'reset_indicators') {
    const defaultSelected = new Set(['MA', 'EMA', 'MACD', 'BOLL', 'VOL'])
    indicators.value = indicators.value.map((indicator) => ({
      ...indicator,
      active: defaultSelected.has(String(indicator.name).toUpperCase())
    }))
    setVoiceStatus('Indicators reset to the default NoobTrade selection.', { speak: true, transcript: rawTranscript })
    return true
  }

  if (intent === 'select_only_indicators' && Array.isArray(intentPayload.indicators)) {
    const normalizedIndicators = intentPayload.indicators.map(normalizeAssistantIndicatorName).filter(Boolean)
    if (normalizedIndicators.length) {
      setOnlyVoiceIndicators(normalizedIndicators)
      setVoiceStatus(`Only ${normalizedIndicators.join(', ')} are selected.`, { speak: true, transcript: rawTranscript })
      return true
    }
  }

  if (intent === 'set_indicator' && Array.isArray(intentPayload.indicators)) {
    const normalizedIndicators = intentPayload.indicators.map(normalizeAssistantIndicatorName).filter(Boolean)
    if (normalizedIndicators.length) {
      setIndicatorActive(normalizedIndicators, intentPayload.active !== false)
      setVoiceStatus(`${normalizedIndicators.join(', ')} turned ${intentPayload.active === false ? 'off' : 'on'}.`, {
        speak: true,
        transcript: rawTranscript
      })
      return true
    }
  }

  if (intent === 'set_interval' && intentPayload.interval) {
    selectedChartInterval.value = intentPayload.interval
    setVoiceStatus(`Chart interval set to ${intentPayload.interval}.`, { speak: true, transcript: rawTranscript })
    return true
  }

  if (intent === 'sign_out') {
    queueVoiceAction({
      type: 'signOut',
      prompt: 'Confirm sign out? Say confirm to leave your account, or cancel to stay signed in.'
    })
    return true
  }

  if (intent === 'language' && intentPayload.language) {
    uiLanguage.value = intentPayload.language
    setVoiceStatus(intentPayload.reply || `Language switched to ${intentPayload.language}.`, {
      speak: true,
      transcript: rawTranscript
    })
    return true
  }

  if (intent === 'greeting' || intent === 'help' || intent === 'chat') {
    setVoiceStatus(intentPayload.reply || buildConversationalReply(normalizeVoiceText(rawTranscript)), {
      speak: true,
      transcript: rawTranscript
    })
    return true
  }

  return false
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
    authMessage.value = payload.message || `Welcome to NoobTrade, ${payload.user.fullName}.`
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
      const pageAliases = {
        Analysis: 'Stock Trade',
        Myself: 'Settings'
      }
      const normalizedPage = pageAliases[page] || page
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
          <p class="page-subtitle">
            NoobTrade gives unauthenticated visitors a clear story: search-driven stock analysis,
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
          <p class="eyebrow">{{ modeLabel }} Probability Dashboard</p>
          <h1 class="page-title">{{ isCryptoMode ? 'Crypto probability scan center.' : 'Stock probability scan center.' }}</h1>
          <p class="page-subtitle">
            {{ isCryptoMode
              ? 'Scan saved crypto assets by probability, rank the strongest setups, and open the dedicated crypto trade workspace for deeper review.'
              : 'Use your saved watchlist as a probability scanner: set a minimum threshold, run Generate logic, and review only the strongest stock setups.' }}
          </p>
        </div>

        <div class="dashboard-chart-panel">
          <div class="dashboard-chart-copy">
            <span class="section-chip">Probability Workflow</span>
            <span class="dashboard-chart-note">Star symbols, scan probabilities, then open the strongest setup</span>
          </div>

          <div class="task-list">
            <div class="task-row">
              <strong>1. Build Watchlist</strong>
              <span>Star names from Explore so Dashboard has a focused scan universe.</span>
            </div>
            <div class="task-row">
              <strong>2. Set Probability</strong>
              <span>Choose the minimum upside probability you want the Generate logic to pass.</span>
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
          <div v-if="dashboardWatchlistRows.length" class="data-table">
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
              <span class="section-chip">>= {{ watchlistScanThresholdLabel }}</span>
            </div>
            <div class="data-table">
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
          <h2>The normal workflow</h2>
          <div class="task-list guide-task-list">
            <div class="task-row">
              <strong>1. Start in Explore</strong>
              <span>Star the stocks or crypto assets you want NoobTrade to watch. Starred names become the Dashboard scan universe.</span>
            </div>
            <div class="task-row">
              <strong>2. Use Dashboard Scan</strong>
              <span>Choose a minimum upside probability, then run Scan to evaluate all starred names together.</span>
            </div>
            <div class="task-row">
              <strong>3. Open the strongest setup</strong>
              <span>Click a ranked result to open Trade, where you can inspect the chart, indicators, probabilities, and matched historical moments.</span>
            </div>
          </div>
        </article>

        <article class="more-card feature-story-card">
          <p class="eyebrow">Dashboard Scan</p>
          <h2>Scan is batch Generate</h2>
          <p>
            Dashboard Scan runs the same Generate-style analysis across every starred symbol in your current mode. In stock mode it scans only starred stocks;
            in crypto mode it scans only starred crypto assets. Results are filtered by your threshold and sorted from stronger upside probability to weaker.
          </p>
          <p>
            This is meant for fast triage. Use it to find which names deserve attention first, then open Trade for the full review.
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
            The chart, selected indicators, matched setup panel, suggested risk lines, and future probability ladder are there to help users compare context,
            not to replace their own judgment.
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
            Live API data is used where available, while historical context is used to frame probability-style research. If a provider is slow or unavailable,
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
        />

        <MatchedPatterns
          ref="matchedPatternsRef"
          :matched-patterns="activeTradeResponse.patternAnalysis.matchedHistoricalPatterns"
          :high-fit-paths="activeTradeResponse.patternAnalysis.highFitHistoricalPaths"
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
            @click="exploreViewMode = exploreViewMode === 'full' ? 'ranked' : 'full'"
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
                @click="openModeAnalysis(row.symbol)"
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
                :aria-label="isStarredSymbol(row.symbol) ? `Remove ${row.symbol} from starred ${isCryptoMode ? 'crypto' : 'stocks'}` : `Star ${row.symbol}`"
                @click="toggleStarredSymbol(row.symbol)"
              >
                {{ isStarredSymbol(row.symbol) ? '★' : '☆' }}
              </button>
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
              <strong>${{ activeTradeResponse.stock.currentPrice }}</strong>
            </div>
            <div class="spotlight-item">
              <span>52W High</span>
              <strong>${{ activeTradeResponse.stock.week52High }}</strong>
            </div>
            <div class="spotlight-item">
              <span>52W Low</span>
              <strong>${{ activeTradeResponse.stock.week52Low }}</strong>
            </div>
            <div class="spotlight-item">
              <span>Probability</span>
              <strong>{{ activeTradeResponse.patternAnalysis.probabilityOfIncrease }}%</strong>
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
              <small>{{ t('settingsNote') }}</small>
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
          :is-crypto-mode="isCryptoMode"
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
