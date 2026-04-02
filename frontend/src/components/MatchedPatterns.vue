<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  matchedPatterns: {
    type: Array,
    required: true
  },
  highFitPaths: {
    type: Array,
    required: true
  }
})
const emit = defineEmits(['open-replay'])

const selectedPatternKey = ref(null)
const visibleCount = ref(5)

const visiblePatterns = computed(() => props.matchedPatterns.slice(0, visibleCount.value))
const hasMorePatterns = computed(() => props.matchedPatterns.length > visibleCount.value)
const visibleSummary = computed(() => {
  if (!props.matchedPatterns.length) {
    return ''
  }

  return `Showing ${visiblePatterns.value.length} of ${props.matchedPatterns.length}`
})

watch(
  () => props.matchedPatterns,
  (patterns) => {
    visibleCount.value = 5

    if (!patterns.length) {
      selectedPatternKey.value = null
      return
    }

    const existingPattern = patterns.find((pattern) => patternKey(pattern) === selectedPatternKey.value)
    if (!existingPattern) {
      selectedPatternKey.value = patternKey(patterns[0])
    }
  },
  { immediate: true, deep: true }
)

const selectedPattern = computed(() => {
  if (!selectedPatternKey.value) {
    return null
  }

  return props.matchedPatterns.find((pattern) => patternKey(pattern) === selectedPatternKey.value) || null
})

const selectedHistoricalCandles = computed(() => selectedPattern.value?.historicalCandles || [])

const detailPriceRange = computed(() => {
  const candles = selectedHistoricalCandles.value

  if (!candles.length) {
    return { min: 0, max: 1, span: 1 }
  }

  const highs = candles.map((item) => toNumber(item.high))
  const lows = candles.map((item) => toNumber(item.low))
  const min = Math.min(...lows)
  const max = Math.max(...highs)
  const padding = Math.max((max - min) * 0.08, 0.5)

  return createRange(min - padding, max + padding)
})

const detailGeometry = computed(() => {
  const candles = selectedHistoricalCandles.value
  const range = detailPriceRange.value
  const width = getCandleWidth(candles.length)

  return candles.map((candle, index) => {
    const x = toChartX(index, candles.length)
    const open = toNumber(candle.open)
    const close = toNumber(candle.close)
    const high = toNumber(candle.high)
    const low = toNumber(candle.low)
    const bodyTop = toChartY(Math.max(open, close), range)
    const bodyBottom = toChartY(Math.min(open, close), range)

    return {
      key: `${candle.date}-${index}`,
      x,
      rectX: x - (width / 2),
      width,
      wickTop: toChartY(high, range),
      wickBottom: toChartY(low, range),
      bodyTop,
      bodyHeight: Math.max(bodyBottom - bodyTop, 1),
      tone: close >= open ? 'up' : 'down'
    }
  })
})

const detailAxisLabels = computed(() => {
  const range = detailPriceRange.value
  return buildScaleLabels(range, 3)
})

const detailTicks = computed(() => {
  const candles = selectedHistoricalCandles.value

  if (!candles.length) {
    return []
  }

  const desiredCount = Math.min(4, candles.length)
  const step = candles.length <= 1 ? 1 : Math.max(1, Math.floor((candles.length - 1) / Math.max(desiredCount - 1, 1)))

  return Array.from({ length: desiredCount }, (_, index) => {
    const candleIndex = index === desiredCount - 1 ? candles.length - 1 : Math.min(index * step, candles.length - 1)

    return {
      index: candleIndex,
      label: formatDateLabel(candles[candleIndex]?.date ?? ''),
      x: toChartX(candleIndex, candles.length)
    }
  })
})

function patternKey(pattern) {
  return `${pattern.symbol}-${pattern.timeframe}-${pattern.windowSize}-${pattern.date}-${pattern.patternName}`
}

function selectPattern(pattern) {
  selectedPatternKey.value = patternKey(pattern)
  emit('open-replay', pattern)
}

function loadMorePatterns() {
  visibleCount.value = Math.min(visibleCount.value + 5, props.matchedPatterns.length)
}

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return 'TBD'
  }

  const numericValue = Number(value)
  return `${numericValue > 0 ? '+' : ''}${numericValue.toFixed(2)}%`
}

function formatDateLabel(value) {
  if (!value) {
    return '--'
  }

  const parsedDate = new Date(value)

  if (Number.isNaN(parsedDate.getTime())) {
    return value
  }

  return parsedDate.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: parsedDate.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
  })
}

function createRange(min, max) {
  const safeMin = Number.isFinite(min) ? min : 0
  const safeMax = Number.isFinite(max) ? max : 1
  const span = Math.max(safeMax - safeMin, 1)

  return {
    min: safeMin,
    max: safeMax,
    span
  }
}

function buildScaleLabels(range, count) {
  return Array.from({ length: count }, (_, index) => {
    const ratio = count === 1 ? 0 : index / (count - 1)
    const value = range.max - (range.span * ratio)
    return value.toFixed(value >= 100 ? 0 : 2)
  })
}

function toNumber(value) {
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? numericValue : 0
}

function toChartX(index, total) {
  const left = 6
  const right = 95

  if (total <= 1) {
    return (left + right) / 2
  }

  return left + ((right - left) * index) / (total - 1)
}

function toChartY(value, range) {
  const top = 8
  const bottom = 80
  const ratio = (value - range.min) / range.span
  return bottom - ((bottom - top) * ratio)
}

function getCandleWidth(count) {
  if (count >= 60) {
    return 0.72
  }

  if (count >= 40) {
    return 1.05
  }

  if (count >= 24) {
    return 1.6
  }

  return 2.2
}
</script>

<template>
  <div class="inner-card matched-card">
    <div class="section-header">Matched Historical Patterns</div>

    <div v-if="matchedPatterns.length" class="match-table">
      <article
        v-for="pattern in visiblePatterns"
        :key="patternKey(pattern)"
        class="match-row match-row--interactive"
        :class="{ 'match-row--active': patternKey(pattern) === selectedPatternKey }"
        role="button"
        tabindex="0"
        @click="selectPattern(pattern)"
        @keydown.enter.prevent="selectPattern(pattern)"
        @keydown.space.prevent="selectPattern(pattern)"
      >
        <div class="match-main">
          <div>
            <p class="match-name">{{ pattern.patternName }}</p>
            <p class="match-meta">
              {{ pattern.symbol }} · {{ pattern.timeframe }} · {{ pattern.windowSize }} bars
            </p>
          </div>
          <strong class="match-score">{{ pattern.matchScore }}%</strong>
        </div>

        <div class="match-stats">
          <span>End Date: {{ pattern.date }}</span>
          <span>Return: {{ formatPercent(pattern.returnPct) }}</span>
          <span>Drawdown: {{ formatPercent(pattern.maxDrawdown) }}</span>
        </div>
      </article>

      <div v-if="hasMorePatterns || matchedPatterns.length > 5" class="match-load-more-row">
        <span class="match-load-more__status">{{ visibleSummary }}</span>
        <button
          v-if="hasMorePatterns"
          type="button"
          class="match-load-more"
          @click="loadMorePatterns"
        >
          <span>Load more</span>
          <span class="match-load-more__arrow" aria-hidden="true">↓</span>
        </button>
      </div>
    </div>
    <div v-else class="empty-state">
      Historical pattern matches will appear here once more comparable windows are stored.
    </div>

    <div v-if="selectedPattern" class="match-detail-card">
      <div class="match-detail-header">
        <div>
          <p class="match-detail-eyebrow">Selected Historical Window</p>
          <h3>{{ selectedPattern.patternName }}</h3>
          <p class="match-detail-meta">
            {{ selectedPattern.symbol }} · {{ selectedPattern.timeframe }} · {{ selectedPattern.windowSize }} bars
          </p>
        </div>
        <strong class="match-detail-score">{{ selectedPattern.matchScore }}%</strong>
      </div>

      <div class="match-detail-stats">
        <span>End Date {{ selectedPattern.date }}</span>
        <span>Return {{ formatPercent(selectedPattern.returnPct) }}</span>
        <span>Drawdown {{ formatPercent(selectedPattern.maxDrawdown) }}</span>
        <span>Future 5D {{ formatPercent(selectedPattern.futureReturn5d) }}</span>
      </div>

      <div v-if="selectedHistoricalCandles.length" class="match-detail-chart">
        <div class="match-detail-price-axis">
          <span v-for="label in detailAxisLabels" :key="label">{{ label }}</span>
        </div>

        <div class="match-detail-plot">
          <svg viewBox="0 0 100 88" preserveAspectRatio="none" class="match-detail-svg">
            <g class="match-detail-grid">
              <line x1="6" y1="8" x2="95" y2="8" />
              <line x1="6" y1="44" x2="95" y2="44" />
              <line x1="6" y1="80" x2="95" y2="80" />
            </g>

            <g class="match-detail-candles">
              <g v-for="candle in detailGeometry" :key="candle.key">
                <line
                  class="detail-wick"
                  :class="`detail-wick--${candle.tone}`"
                  :x1="candle.x"
                  :x2="candle.x"
                  :y1="candle.wickTop"
                  :y2="candle.wickBottom"
                />
                <rect
                  class="detail-body"
                  :class="`detail-body--${candle.tone}`"
                  :x="candle.rectX"
                  :y="candle.bodyTop"
                  :width="candle.width"
                  :height="candle.bodyHeight"
                  rx="0.25"
                />
              </g>
            </g>
          </svg>

          <div class="match-detail-time-axis">
            <span
              v-for="tick in detailTicks"
              :key="`${tick.index}-${tick.label}`"
              :style="{ left: `${tick.x}%` }"
            >
              {{ tick.label }}
            </span>
          </div>
        </div>
      </div>
      <div v-else class="empty-state empty-state--compact">
        Historical candles are not available for this matched window yet.
      </div>
    </div>
  </div>
</template>
