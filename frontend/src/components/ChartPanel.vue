<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  activeSymbol: {
    type: String,
    required: true
  },
  activeIndicators: {
    type: Array,
    required: true
  },
  chartIntervals: {
    type: Array,
    required: true
  },
  chartData: {
    type: Object,
    required: true
  },
  companyName: {
    type: String,
    required: true
  },
  sector: {
    type: String,
    required: true
  },
  industry: {
    type: String,
    required: true
  },
  selectedInterval: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['update:selected-interval'])

const PRICE_LEFT = 3
const PRICE_RIGHT = 96
const PRICE_TOP = 5
const PRICE_BOTTOM = 92
const DEFAULT_VISIBLE_BARS = {
  daily: 30,
  '5day': 30,
  weekly: 30,
  '2week': 28,
  monthly: 30
}
const MIN_VISIBLE_BARS = {
  daily: 10,
  '5day': 10,
  weekly: 10,
  '2week': 8,
  monthly: 6
}
const MAX_VISIBLE_BARS = {
  daily: 260,
  '5day': 220,
  weekly: 220,
  '2week': 180,
  monthly: 160
}

const stackedIndicatorNames = ['Vol', 'RSI', 'KDJ', 'MACD', 'OBV', 'OI']

const chartViewportRef = ref(null)
const visibleBarCount = ref(60)
const viewStartIndex = ref(0)
const isDragging = ref(false)
const dragState = ref({ startX: 0, startIndex: 0, width: 1 })

const fullCandles = computed(() => {
  const series = props.chartData?.series || {}
  return series[props.selectedInterval] || []
})

watch(
  () => [props.selectedInterval, fullCandles.value.length],
  () => resetViewport(),
  { immediate: true }
)

const activeCandles = computed(() => {
  const candles = fullCandles.value

  if (!candles.length) {
    return []
  }

  const start = clamp(viewStartIndex.value, 0, Math.max(candles.length - visibleBarCount.value, 0))
  return candles.slice(start, start + visibleBarCount.value)
})

const closeSeries = computed(() => activeCandles.value.map((item) => toNumber(item.close)))
const highSeries = computed(() => activeCandles.value.map((item) => toNumber(item.high)))
const lowSeries = computed(() => activeCandles.value.map((item) => toNumber(item.low)))
const volumeSeries = computed(() => activeCandles.value.map((item) => toNumber(item.volume)))

const selectedNames = computed(() => props.activeIndicators.map((item) => item.name))
const overlayNames = computed(() => selectedNames.value.filter((name) => ['MA', 'EMA', 'BOLL'].includes(name)))
const stackedNames = computed(() => selectedNames.value.filter((name) => stackedIndicatorNames.includes(name)))
const visibleDensity = computed(() => visibleBarCount.value)
const isDenseView = computed(() => visibleDensity.value >= 120)
const isVeryDenseView = computed(() => visibleDensity.value >= 200)

const latestCandle = computed(() => activeCandles.value[activeCandles.value.length - 1] || null)

const xTicks = computed(() => {
  const candles = activeCandles.value

  if (!candles.length) {
    return []
  }

  const desiredCount = Math.min(6, candles.length)
  const step = candles.length <= 1 ? 1 : Math.max(1, Math.floor((candles.length - 1) / Math.max(desiredCount - 1, 1)))

  return Array.from({ length: desiredCount }, (_, index) => {
    const candleIndex = index === desiredCount - 1 ? candles.length - 1 : Math.min(index * step, candles.length - 1)

    return {
      index: candleIndex,
      x: toChartX(candleIndex, candles.length),
      label: formatDateLabel(candles[candleIndex]?.date ?? '')
    }
  })
})

const priceRange = computed(() => {
  const candles = activeCandles.value

  if (!candles.length) {
    return { min: 0, max: 1, span: 1 }
  }

  const lows = candles.map((item) => toNumber(item.low))
  const highs = candles.map((item) => toNumber(item.high))
  const min = Math.min(...lows)
  const max = Math.max(...highs)
  const padding = Math.max((max - min) * 0.06, 0.5)

  return createRange(min - padding, max + padding)
})

const priceAxisLabels = computed(() => buildScaleLabels(priceRange.value, 4, formatPrice))

const maSeries = computed(() => buildMovingAverageSeries(closeSeries.value, 20))
const emaSeries = computed(() => buildExponentialSeries(closeSeries.value, 12))
const bollSeries = computed(() => buildBollingerSeries(closeSeries.value, 20))
const macdSeries = computed(() => buildMacdSnapshot(closeSeries.value))
const rsiSeries = computed(() => buildRsiSeries(closeSeries.value, 14))
const kdjSeries = computed(() => buildKdjSeries(highSeries.value, lowSeries.value, closeSeries.value, 9))
const obvSeries = computed(() => buildObvSeries(closeSeries.value, volumeSeries.value))
const oiSeries = computed(() => buildOiSeries(activeCandles.value.length, closeSeries.value))

const mainOverlays = computed(() => {
  const overlays = []

  if (overlayNames.value.includes('MA')) {
    overlays.push({
      key: 'ma',
      label: 'MA(20)',
      className: 'ma',
      points: buildLinePoints(maSeries.value, priceRange.value)
    })
  }

  if (overlayNames.value.includes('EMA')) {
    overlays.push({
      key: 'ema',
      label: 'EMA(12)',
      className: 'ema',
      points: buildLinePoints(emaSeries.value, priceRange.value)
    })
  }

  if (overlayNames.value.includes('BOLL')) {
    overlays.push(
      {
        key: 'boll-upper',
        label: 'BOLL Upper',
        className: 'boll',
        points: buildLinePoints(bollSeries.value.upper, priceRange.value)
      },
      {
        key: 'boll-mid',
        label: 'BOLL Mid',
        className: 'boll-mid',
        points: buildLinePoints(bollSeries.value.mid, priceRange.value)
      },
      {
        key: 'boll-lower',
        label: 'BOLL Lower',
        className: 'boll',
        points: buildLinePoints(bollSeries.value.lower, priceRange.value)
      }
    )
  }

  return overlays.filter((item) => item.points)
})

const candleGeometry = computed(() => {
  const candles = activeCandles.value
  const width = getCandleWidth(candles.length)

  return candles.map((candle, index) => {
    const x = toChartX(index, candles.length)
    const open = toNumber(candle.open)
    const close = toNumber(candle.close)
    const high = toNumber(candle.high)
    const low = toNumber(candle.low)
    const bodyTop = toPriceY(Math.max(open, close), priceRange.value)
    const bodyBottom = toPriceY(Math.min(open, close), priceRange.value)
    const wickTop = toPriceY(high, priceRange.value)
    const wickBottom = toPriceY(low, priceRange.value)

    return {
      key: `${candle.date}-${index}`,
      x,
      rectX: x - (width / 2),
      width,
      wickTop,
      wickBottom,
      bodyTop,
      bodyHeight: Math.max(bodyBottom - bodyTop, isDenseView.value ? 0.45 : 0.62),
      tone: close >= open ? 'up' : 'down'
    }
  })
})

const stackedPanels = computed(() => {
  const panels = []

  if (stackedNames.value.includes('Vol')) {
    const range = createValueRange(volumeSeries.value, { minFallback: 0 })
    panels.push({
      key: 'vol',
      title: 'VOL',
      summary: `VOL ${formatCompactNumber(lastValid(volumeSeries.value))}`,
      range,
      axisLabels: buildScaleLabels(range, 2, formatCompactNumber),
      guides: [],
      bars: buildBars(volumeSeries.value, range, closeSeries.value),
      lines: []
    })
  }

  if (stackedNames.value.includes('RSI')) {
    const range = createRange(0, 100)
    panels.push({
      key: 'rsi',
      title: 'RSI(14)',
      summary: `RSI ${formatNumber(lastValid(rsiSeries.value))}`,
      range,
      axisLabels: ['100', '50', '0'],
      guides: [70, 50, 30],
      bars: [],
      lines: [
        { key: 'rsi-line', className: 'rsi', points: buildPanelLine(rsiSeries.value, range) }
      ]
    })
  }

  if (stackedNames.value.includes('KDJ')) {
    const range = createRange(0, 100)
    panels.push({
      key: 'kdj',
      title: 'KDJ(9,3,3)',
      summary: `K ${formatNumber(lastValid(kdjSeries.value.k))} · D ${formatNumber(lastValid(kdjSeries.value.d))} · J ${formatNumber(lastValid(kdjSeries.value.j))}`,
      range,
      axisLabels: ['80', '50', '20'],
      guides: [80, 50, 20],
      bars: [],
      lines: [
        { key: 'kdj-k', className: 'kdj-k', points: buildPanelLine(kdjSeries.value.k, range) },
        { key: 'kdj-d', className: 'kdj-d', points: buildPanelLine(kdjSeries.value.d, range) },
        { key: 'kdj-j', className: 'kdj-j', points: buildPanelLine(kdjSeries.value.j, range) }
      ]
    })
  }

  if (stackedNames.value.includes('MACD')) {
    const range = createValueRange(
      [
        ...macdSeries.value.histogram,
        ...macdSeries.value.macdLine,
        ...macdSeries.value.signalLine
      ],
      { symmetric: true }
    )

    panels.push({
      key: 'macd',
      title: 'MACD(12,26,9)',
      summary: `DIF ${formatSigned(lastValid(macdSeries.value.macdLine))} · DEA ${formatSigned(lastValid(macdSeries.value.signalLine))} · STICK ${formatSigned(lastValid(macdSeries.value.histogram))}`,
      range,
      axisLabels: buildScaleLabels(range, 2, formatSigned),
      guides: [0],
      bars: buildCenteredBars(macdSeries.value.histogram, range),
      lines: [
        { key: 'macd-line', className: 'macd', points: buildPanelLine(macdSeries.value.macdLine, range) },
        { key: 'signal-line', className: 'signal', points: buildPanelLine(macdSeries.value.signalLine, range) }
      ]
    })
  }

  if (stackedNames.value.includes('OBV')) {
    const range = createValueRange(obvSeries.value, {})
    panels.push({
      key: 'obv',
      title: 'OBV',
      summary: `OBV ${formatCompactNumber(lastValid(obvSeries.value))}`,
      range,
      axisLabels: buildScaleLabels(range, 2, formatCompactNumber),
      guides: [],
      bars: [],
      lines: [
        { key: 'obv-line', className: 'pbv', points: buildPanelLine(obvSeries.value, range) }
      ]
    })
  }

  if (stackedNames.value.includes('OI')) {
    const range = createValueRange(oiSeries.value, {})
    panels.push({
      key: 'oi',
      title: 'OI',
      summary: `OI ${formatCompactNumber(lastValid(oiSeries.value))}`,
      range,
      axisLabels: buildScaleLabels(range, 2, formatCompactNumber),
      guides: [],
      bars: [],
      lines: [
        { key: 'oi-line', className: 'oi', points: buildPanelLine(oiSeries.value, range) }
      ]
    })
  }

  return panels
})

function resetViewport() {
  const candles = fullCandles.value
  const total = candles.length

  if (!total) {
    visibleBarCount.value = 0
    viewStartIndex.value = 0
    return
  }

  const defaultBars = DEFAULT_VISIBLE_BARS[props.selectedInterval] ?? 60
  visibleBarCount.value = Math.min(defaultBars, total)
  viewStartIndex.value = Math.max(total - visibleBarCount.value, 0)
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

function getMinimumVisibleBars() {
  return MIN_VISIBLE_BARS[props.selectedInterval] ?? 8
}

function getMaximumVisibleBars() {
  const total = fullCandles.value.length
  const intervalCap = MAX_VISIBLE_BARS[props.selectedInterval] ?? total
  return Math.min(intervalCap, total)
}

function updateViewport(nextVisibleCount, anchorRatio = 0.5) {
  const total = fullCandles.value.length

  if (!total) {
    return
  }

  const clampedVisible = clamp(Math.round(nextVisibleCount), getMinimumVisibleBars(), getMaximumVisibleBars())
  const currentVisible = Math.max(visibleBarCount.value, 1)
  const currentStart = clamp(viewStartIndex.value, 0, Math.max(total - currentVisible, 0))
  const anchorIndex = currentStart + Math.round((currentVisible - 1) * anchorRatio)
  const nextStart = clamp(
    Math.round(anchorIndex - ((clampedVisible - 1) * anchorRatio)),
    0,
    Math.max(total - clampedVisible, 0)
  )

  visibleBarCount.value = clampedVisible
  viewStartIndex.value = nextStart
}

function handleWheel(event) {
  const total = fullCandles.value.length

  if (!total || !chartViewportRef.value) {
    return
  }

  event.preventDefault()

  const rect = chartViewportRef.value.getBoundingClientRect()
  const ratio = clamp((event.clientX - rect.left) / rect.width, 0, 1)
  const zoomStep = Math.max(1, Math.round(visibleBarCount.value * 0.12))
  const nextVisibleCount = event.deltaY < 0
    ? visibleBarCount.value - zoomStep
    : visibleBarCount.value + zoomStep

  updateViewport(nextVisibleCount, ratio)
}

function zoomIn() {
  updateViewport(visibleBarCount.value * 0.84, 0.5)
}

function zoomOut() {
  updateViewport(visibleBarCount.value * 1.16, 0.5)
}

function resetView() {
  resetViewport()
}

function handlePointerDown(event) {
  if (!chartViewportRef.value || fullCandles.value.length <= visibleBarCount.value) {
    return
  }

  event.preventDefault()
  const rect = chartViewportRef.value.getBoundingClientRect()
  isDragging.value = true
  dragState.value = {
    startX: event.clientX,
    startIndex: viewStartIndex.value,
    width: rect.width
  }
}

function handlePointerMove(event) {
  if (!isDragging.value) {
    return
  }

  const total = fullCandles.value.length
  const deltaX = event.clientX - dragState.value.startX
  const barsPerPixel = visibleBarCount.value / Math.max(dragState.value.width, 1)
  const shiftBars = Math.trunc(deltaX * barsPerPixel)

  viewStartIndex.value = clamp(
    dragState.value.startIndex - shiftBars,
    0,
    Math.max(total - visibleBarCount.value, 0)
  )
}

function stopDragging() {
  isDragging.value = false
}

onMounted(() => {
  window.addEventListener('pointermove', handlePointerMove)
  window.addEventListener('pointerup', stopDragging)
  window.addEventListener('pointercancel', stopDragging)
  window.addEventListener('blur', stopDragging)
})

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', handlePointerMove)
  window.removeEventListener('pointerup', stopDragging)
  window.removeEventListener('pointercancel', stopDragging)
  window.removeEventListener('blur', stopDragging)
})

function toNumber(value) {
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? numericValue : 0
}

function createRange(min, max) {
  const safeMin = Number.isFinite(min) ? min : 0
  const safeMax = Number.isFinite(max) ? max : 1
  const span = Math.max(safeMax - safeMin, 1)
  return { min: safeMin, max: safeMax, span }
}

function createValueRange(values, options = {}) {
  const validValues = values.filter((value) => value !== null && value !== undefined && Number.isFinite(Number(value))).map(Number)

  if (!validValues.length) {
    return createRange(options.minFallback ?? -1, options.maxFallback ?? 1)
  }

  let min = Math.min(...validValues)
  let max = Math.max(...validValues)

  if (options.symmetric) {
    const maxAbs = Math.max(Math.abs(min), Math.abs(max), 1)
    return createRange(-maxAbs, maxAbs)
  }

  if (options.minFallback !== undefined) {
    min = Math.min(min, options.minFallback)
  }

  if (options.maxFallback !== undefined) {
    max = Math.max(max, options.maxFallback)
  }

  const padding = Math.max((max - min) * 0.08, 0.0001)
  return createRange(min - padding, max + padding)
}

function buildScaleLabels(range, steps, formatter) {
  return Array.from({ length: steps + 1 }, (_, index) => {
    const value = range.max - ((range.span / steps) * index)
    return formatter(value)
  })
}

function toChartX(index, length) {
  if (length <= 1) {
    return (PRICE_LEFT + PRICE_RIGHT) / 2
  }

  return PRICE_LEFT + ((PRICE_RIGHT - PRICE_LEFT) * index) / (length - 1)
}

function toPriceY(value, range) {
  return PRICE_TOP + ((range.max - value) / range.span) * (PRICE_BOTTOM - PRICE_TOP)
}

function toPanelY(value, range) {
  return 8 + ((range.max - value) / range.span) * 84
}

function getCandleWidth(length) {
  if (length <= 1) {
    return 2.2
  }

  const slots = Math.max(length - 1, 1)
  const spacing = (PRICE_RIGHT - PRICE_LEFT) / slots

  if (length >= 140) {
    return Math.max(Math.min(spacing * 0.3, 0.46), 0.14)
  }

  if (length >= 90) {
    return Math.max(Math.min(spacing * 0.34, 0.56), 0.16)
  }

  if (length >= 50) {
    return Math.max(Math.min(spacing * 0.4, 0.7), 0.2)
  }

  if (length >= 30) {
    return Math.max(Math.min(spacing * 0.46, 0.9), 0.24)
  }

  return Math.max(Math.min(spacing * 0.56, 1.18), 0.3)
}

function buildLinePoints(values, range) {
  const points = values
    .map((value, index) => {
      if (value === null || value === undefined || !Number.isFinite(Number(value))) {
        return null
      }

      return `${toChartX(index, values.length)},${toPriceY(Number(value), range)}`
    })
    .filter(Boolean)

  return points.length > 1 ? points.join(' ') : ''
}

function buildPanelLine(values, range) {
  const points = values
    .map((value, index) => {
      if (value === null || value === undefined || !Number.isFinite(Number(value))) {
        return null
      }

      return `${toChartX(index, values.length)},${toPanelY(Number(value), range)}`
    })
    .filter(Boolean)

  return points.length > 1 ? points.join(' ') : ''
}

function buildBars(values, range, closes = []) {
  const width = getCandleWidth(values.length)

  return values.map((value, index) => {
    const numericValue = Number(value || 0)
    const x = toChartX(index, values.length)
    const y = toPanelY(numericValue, range)
    const previousClose = closes[index - 1] ?? closes[index] ?? 0
    const currentClose = closes[index] ?? previousClose

    return {
      key: `bar-${index}`,
      x: x - (width / 2),
      y,
      width,
      height: Math.max(92 - y, 0.8),
      className: currentClose >= previousClose ? 'positive' : 'negative'
    }
  })
}

function buildCenteredBars(values, range) {
  const width = getCandleWidth(values.length)
  const zeroY = toPanelY(0, range)

  return values.map((value, index) => {
    const numericValue = Number(value || 0)
    const y = numericValue >= 0 ? toPanelY(numericValue, range) : zeroY
    const bottom = numericValue >= 0 ? zeroY : toPanelY(numericValue, range)

    return {
      key: `center-bar-${index}`,
      x: toChartX(index, values.length) - (width / 2),
      y,
      width,
      height: Math.max(Math.abs(bottom - zeroY), 0.8),
      className: numericValue >= 0 ? 'positive' : 'negative'
    }
  })
}

function buildMovingAverageSeries(values, period) {
  return values.map((_, index) => calcSimpleMovingAverage(values.slice(0, index + 1), period))
}

function buildExponentialSeries(values, period) {
  const results = []
  const multiplier = 2 / (period + 1)
  let previousEma = null

  values.forEach((value, index) => {
    if (index + 1 < period) {
      results.push(null)
      return
    }

    if (previousEma === null) {
      previousEma = values.slice(0, period).reduce((sum, item) => sum + item, 0) / period
      results.push(previousEma)
      return
    }

    previousEma = ((value - previousEma) * multiplier) + previousEma
    results.push(previousEma)
  })

  return results
}

function buildBollingerSeries(values, period) {
  const upper = []
  const mid = []
  const lower = []

  values.forEach((_, index) => {
    if (index + 1 < period) {
      upper.push(null)
      mid.push(null)
      lower.push(null)
      return
    }

    const window = values.slice(index + 1 - period, index + 1)
    const average = window.reduce((sum, value) => sum + value, 0) / period
    const variance = window.reduce((sum, value) => sum + (value - average) ** 2, 0) / period
    const deviation = Math.sqrt(variance)

    upper.push(average + deviation * 2)
    mid.push(average)
    lower.push(average - deviation * 2)
  })

  return { upper, mid, lower }
}

function buildRsiSeries(values, period) {
  return values.map((_, index) => calcRsi(values.slice(0, index + 1), period))
}

function buildKdjSeries(highs, lows, closes, period) {
  const k = []
  const d = []
  const j = []
  let previousK = 50
  let previousD = 50

  closes.forEach((_, index) => {
    if (index + 1 < period) {
      k.push(null)
      d.push(null)
      j.push(null)
      return
    }

    const recentHigh = Math.max(...highs.slice(index + 1 - period, index + 1))
    const recentLow = Math.min(...lows.slice(index + 1 - period, index + 1))
    const close = closes[index]
    const rsv = recentHigh === recentLow ? 50 : ((close - recentLow) / (recentHigh - recentLow)) * 100
    const nextK = ((2 * previousK) + rsv) / 3
    const nextD = ((2 * previousD) + nextK) / 3
    const nextJ = (3 * nextK) - (2 * nextD)

    k.push(nextK)
    d.push(nextD)
    j.push(nextJ)
    previousK = nextK
    previousD = nextD
  })

  return { k, d, j }
}

function buildMacdSnapshot(values) {
  const ema12 = buildExponentialSeries(values, 12)
  const ema26 = buildExponentialSeries(values, 26)
  const macdLine = values.map((_, index) => {
    if (ema12[index] === null || ema26[index] === null) {
      return null
    }

    return ema12[index] - ema26[index]
  })

  const signalLine = []
  const multiplier = 2 / (9 + 1)
  let previousSignal = null

  macdLine.forEach((value, index) => {
    if (value === null) {
      signalLine.push(null)
      return
    }

    const validValues = macdLine.slice(0, index + 1).filter((item) => item !== null)

    if (validValues.length < 9) {
      signalLine.push(null)
      return
    }

    if (previousSignal === null) {
      previousSignal = validValues.slice(0, 9).reduce((sum, item) => sum + item, 0) / 9
      signalLine.push(previousSignal)
      return
    }

    previousSignal = ((value - previousSignal) * multiplier) + previousSignal
    signalLine.push(previousSignal)
  })

  const histogram = macdLine.map((value, index) => {
    if (value === null || signalLine[index] === null) {
      return 0
    }

    return value - signalLine[index]
  })

  return {
    macdLine,
    signalLine,
    histogram
  }
}

function buildObvSeries(closes, volumes) {
  let running = 0

  return closes.map((close, index) => {
    const previousClose = closes[index - 1] ?? close
    const volume = volumes[index] ?? 0
    running += close >= previousClose ? volume : -volume
    return running
  })
}

function buildOiSeries(length, closes) {
  let running = 120000

  return Array.from({ length }, (_, index) => {
    const previousClose = closes[index - 1] ?? closes[index] ?? 0
    const currentClose = closes[index] ?? previousClose
    const drift = currentClose >= previousClose ? 640 : -420
    running += drift + ((index % 5) - 2) * 55
    return running
  })
}

function calcSimpleMovingAverage(values, period) {
  if (values.length < period) {
    return null
  }

  const window = values.slice(-period)
  return window.reduce((sum, value) => sum + value, 0) / period
}

function calcRsi(values, period) {
  if (values.length <= period) {
    return null
  }

  const gains = []
  const losses = []

  for (let index = 1; index < values.length; index += 1) {
    const delta = values[index] - values[index - 1]
    gains.push(Math.max(delta, 0))
    losses.push(Math.abs(Math.min(delta, 0)))
  }

  const recentGains = gains.slice(-period)
  const recentLosses = losses.slice(-period)
  const avgGain = recentGains.reduce((sum, value) => sum + value, 0) / recentGains.length
  const avgLoss = recentLosses.reduce((sum, value) => sum + value, 0) / recentLosses.length

  if (avgLoss === 0) {
    return 100
  }

  const rs = avgGain / avgLoss
  return 100 - (100 / (1 + rs))
}

function lastValid(values) {
  return [...values].reverse().find((value) => value !== null && value !== undefined && Number.isFinite(Number(value))) ?? null
}

function formatIntervalLabel(interval) {
  const labels = {
    daily: 'Daily',
    '5day': '5 Days',
    weekly: 'Weekly',
    '2week': '2 Weeks',
    monthly: 'Monthly'
  }

  return labels[interval] || interval
}

function formatPrice(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return 'TBD'
  }

  return Number(value).toFixed(2)
}

function formatNumber(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return 'TBD'
  }

  return Number(value).toFixed(2)
}

function formatSigned(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return 'TBD'
  }

  const numericValue = Number(value)
  return `${numericValue > 0 ? '+' : ''}${numericValue.toFixed(2)}`
}

function formatCompactNumber(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return 'TBD'
  }

  return Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 2
  }).format(value)
}

function formatDateLabel(rawDate) {
  if (!rawDate) {
    return ''
  }

  if (/^\d{4}-\d{2}-\d{2}$/.test(rawDate)) {
    const date = new Date(`${rawDate}T12:00:00`)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: '2-digit'
    })
  }

  if (/^\d{4}-\d{2}$/.test(rawDate)) {
    const date = new Date(`${rawDate}-01T12:00:00`)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      year: '2-digit'
    })
  }

  return rawDate
}

function getPriceOverlayStrokeWidth(className) {
  if (className === 'boll') {
    return isVeryDenseView.value ? 0.46 : isDenseView.value ? 0.56 : 0.72
  }

  if (className === 'boll-mid') {
    return isVeryDenseView.value ? 0.38 : isDenseView.value ? 0.48 : 0.62
  }

  return isVeryDenseView.value ? 0.62 : isDenseView.value ? 0.74 : 0.9
}

function getPriceOverlayOpacity(className) {
  if (className === 'boll') {
    return isVeryDenseView.value ? 0.72 : isDenseView.value ? 0.8 : 0.88
  }

  if (className === 'boll-mid') {
    return isVeryDenseView.value ? 0.62 : isDenseView.value ? 0.72 : 0.82
  }

  return isVeryDenseView.value ? 0.82 : isDenseView.value ? 0.9 : 0.98
}

function getWickStrokeWidth() {
  if (isVeryDenseView.value) {
    return 0.42
  }

  if (isDenseView.value) {
    return 0.5
  }

  return 0.58
}

function getIndicatorStrokeWidth() {
  if (isVeryDenseView.value) {
    return 0.82
  }

  if (isDenseView.value) {
    return 0.96
  }

  return 1.14
}

function getIndicatorOpacity(className) {
  if (className === 'signal') {
    return isVeryDenseView.value ? 0.82 : 0.9
  }

  if (className === 'kdj-j') {
    return isVeryDenseView.value ? 0.7 : 0.82
  }

  return isVeryDenseView.value ? 0.84 : isDenseView.value ? 0.9 : 0.98
}

function getBarOpacity() {
  if (isVeryDenseView.value) {
    return 0.72
  }

  if (isDenseView.value) {
    return 0.8
  }

  return 0.9
}
</script>

<template>
  <div class="inner-card chart-shell">
    <div class="chart-meta">
      <div class="chart-title-group">
        <span>Ticker: <strong>{{ activeSymbol }}</strong></span>
        <span class="chart-interval-label">{{ formatIntervalLabel(selectedInterval) }} Candles</span>
      </div>

      <div class="interval-toggle">
        <button
          v-for="interval in chartIntervals"
          :key="interval"
          class="interval-button"
          :class="{ active: selectedInterval === interval }"
          @click="emit('update:selected-interval', interval)"
        >
          {{ formatIntervalLabel(interval) }}
        </button>
      </div>
    </div>

    <div class="stock-overview chart-header-copy">
      <span>{{ companyName }}</span>
      <span>{{ sector }} / {{ industry }}</span>
    </div>

    <div class="chart-legend">
      <span class="legend-chip price">Price</span>
      <span v-for="overlay in mainOverlays" :key="overlay.key" class="legend-chip indicator">
        {{ overlay.label }}
      </span>
      <span v-for="name in stackedNames" :key="name" class="legend-chip macd">
        {{ name }}
      </span>
    </div>

    <div class="chart-interaction-hint">
      <span>{{ activeCandles.length }} bars in view</span>
      <div class="chart-toolbar">
        <span class="chart-toolbar-hint">Wheel to zoom, drag to pan</span>
        <button class="chart-toolbar-button" @click="zoomIn">+</button>
        <button class="chart-toolbar-button" @click="zoomOut">-</button>
        <button class="chart-toolbar-button reset" @click="resetView">Reset</button>
      </div>
    </div>

    <div v-if="latestCandle" class="ohlc-bar">
      <span>O {{ formatPrice(latestCandle.open) }}</span>
      <span>H {{ formatPrice(latestCandle.high) }}</span>
      <span>L {{ formatPrice(latestCandle.low) }}</span>
      <span>C {{ formatPrice(latestCandle.close) }}</span>
      <span>Vol {{ Number(latestCandle.volume || 0).toLocaleString() }}</span>
    </div>

    <div class="chart-stack">
      <div
        ref="chartViewportRef"
        class="chart-main-shell"
        :class="{ dragging: isDragging }"
        @wheel.prevent="handleWheel"
        @pointerdown="handlePointerDown"
      >
        <div class="chart-placeholder trading-price-chart">
        <svg class="chart-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
          <g>
            <line
              v-for="label in priceAxisLabels"
              :key="`price-grid-${label}`"
              class="chart-grid-line"
              vector-effect="non-scaling-stroke"
              shape-rendering="crispEdges"
              x1="0"
              x2="100"
              :y1="toPriceY(Number(label), priceRange)"
              :y2="toPriceY(Number(label), priceRange)"
            />

            <line
              v-for="tick in xTicks"
              :key="`x-grid-${tick.index}`"
              class="chart-grid-line chart-grid-line--vertical"
              vector-effect="non-scaling-stroke"
              shape-rendering="crispEdges"
              :x1="tick.x"
              :x2="tick.x"
              y1="0"
              y2="100"
            />
          </g>

          <polyline
            v-for="overlay in mainOverlays"
            :key="overlay.key"
            :class="['price-line-overlay', overlay.className]"
            fill="none"
            :points="overlay.points"
            vector-effect="non-scaling-stroke"
            stroke-linecap="round"
            stroke-linejoin="round"
            :stroke-width="getPriceOverlayStrokeWidth(overlay.className)"
            :stroke-opacity="getPriceOverlayOpacity(overlay.className)"
          />

          <g v-for="candle in candleGeometry" :key="candle.key">
            <line
              :class="['price-wick', candle.tone]"
              vector-effect="non-scaling-stroke"
              shape-rendering="crispEdges"
              :x1="candle.x"
              :x2="candle.x"
              :y1="candle.wickTop"
              :y2="candle.wickBottom"
              :stroke-width="getWickStrokeWidth()"
            />
            <rect
              :class="['price-candle', candle.tone]"
              :x="candle.rectX"
              :y="candle.bodyTop"
              :width="candle.width"
              :height="candle.bodyHeight"
              :rx="isDenseView ? 0.05 : 0.12"
              shape-rendering="crispEdges"
            />
          </g>
        </svg>

        <div class="price-axis">
          <span v-for="label in priceAxisLabels" :key="`axis-${label}`" class="price-label">
            {{ label }}
          </span>
        </div>
        </div>

        <div class="shared-time-axis">
          <span v-for="tick in xTicks" :key="`label-${tick.index}`">{{ tick.label }}</span>
        </div>
      </div>

      <div
        v-for="panel in stackedPanels"
        :key="panel.key"
        class="indicator-stack-panel"
      >
        <div class="indicator-stack-header">
          <strong>{{ panel.title }}</strong>
          <span>{{ panel.summary }}</span>
        </div>

        <div class="indicator-stack-canvas">
          <svg viewBox="0 0 100 100" preserveAspectRatio="none">
            <line
              v-for="tick in xTicks"
              :key="`${panel.key}-tick-${tick.index}`"
              class="chart-grid-line chart-grid-line--vertical"
              vector-effect="non-scaling-stroke"
              shape-rendering="crispEdges"
              :x1="tick.x"
              :x2="tick.x"
              y1="0"
              y2="100"
            />

            <line
              v-for="guide in panel.guides"
              :key="`${panel.key}-guide-${guide}`"
              class="indicator-guide-line"
              vector-effect="non-scaling-stroke"
              x1="0"
              x2="100"
              :y1="toPanelY(guide, panel.range)"
              :y2="toPanelY(guide, panel.range)"
            />

            <rect
              v-for="bar in panel.bars"
              :key="bar.key"
              :class="['indicator-bar', bar.className]"
              :x="bar.x"
              :y="bar.y"
              :width="bar.width"
              :height="bar.height"
              :rx="isDenseView ? 0.04 : 0.12"
              :opacity="getBarOpacity()"
              shape-rendering="crispEdges"
            />

            <polyline
              v-for="line in panel.lines"
              :key="line.key"
              :class="['indicator-line', line.className]"
              fill="none"
              :points="line.points"
              vector-effect="non-scaling-stroke"
              stroke-linecap="round"
              stroke-linejoin="round"
              :stroke-width="getIndicatorStrokeWidth()"
              :stroke-opacity="getIndicatorOpacity(line.className)"
            />
          </svg>

          <div class="indicator-axis-right">
            <span v-for="label in panel.axisLabels" :key="`${panel.key}-${label}`">
              {{ label }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
