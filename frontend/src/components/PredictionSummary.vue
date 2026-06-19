<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  requestData: {
    type: Object,
    required: true
  },
  stockData: {
    type: Object,
    required: true
  },
  analysisData: {
    type: Object,
    required: true
  },
  formatPercent: {
    type: Function,
    required: true
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  loadingTitle: {
    type: String,
    default: 'Generating probabilities'
  },
  loadingMessage: {
    type: String,
    default: 'Loading matched history and probability ranges.'
  }
})

const upsideThreshold = ref(1)
const downsideThreshold = ref(1)

function getSignalLabel(signal) {
  return signal || 'Bullish Bias'
}

function formatProbabilityLabel(value) {
  if (value === null || value === undefined || value === '') {
    return '--'
  }

  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) {
    return '--'
  }

  return `${numericValue.toFixed(0)}%`
}

function formatPrice(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return 'TBD'
  }

  return '$' + Number(value).toFixed(2)
}

function formatValue(value) {
  if (value === null || value === undefined || value === '') {
    return 'TBD'
  }

  return value
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

function findThresholdProbability(side, threshold) {
  const ladder = props.analysisData.futureFiveDayProbabilities?.[side] || []
  const matched = ladder.find((item) => Number(item.threshold) === Number(threshold))

  if (!matched || matched.probability === null || matched.probability === undefined) {
    return calculateDynamicProbability(side, threshold).replace(/\.0%$/, '%')
  }

  return Number(matched.probability).toFixed(0) + '%'
}

function getNumericProbability(value) {
  if (value === null || value === undefined || value === '') {
    return null
  }

  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? numericValue : null
}

function getLadderProbability(side, threshold) {
  const ladder = props.analysisData.futureFiveDayProbabilities?.[side] || []
  const matched = ladder.find((item) => Number(item.threshold) === Number(threshold))
  return getNumericProbability(matched?.probability)
}

const matchedPatterns = computed(() => props.analysisData.matchedHistoricalPatterns || [])
const matchedPatternCount = computed(() => {
  const explicitCount = Number(props.analysisData.matchedPatternsCount)

  if (Number.isFinite(explicitCount) && explicitCount > 0) {
    return explicitCount
  }

  return matchedPatterns.value.length
})
const headlineProbabilityValue = computed(() => (
  getNumericProbability(props.analysisData.probabilityOfIncrease)
    ?? getLadderProbability('up', 1)
))
const hasHeadlineProbability = computed(() => {
  return headlineProbabilityValue.value !== null
})
const headlineProbabilityLabel = computed(() => formatProbabilityLabel(headlineProbabilityValue.value))
const currentPrice = computed(() => {
  const value = Number(props.stockData?.currentPrice)
  return Number.isFinite(value) ? value : null
})
const projectedTargetPrice = computed(() => {
  const basePrice = currentPrice.value
  const avgReturn = Number(props.analysisData?.avgReturn)

  if (!Number.isFinite(basePrice) || !Number.isFinite(avgReturn)) {
    return null
  }

  return basePrice * (1 + (avgReturn / 100))
})
const projectedRiskLine = computed(() => {
  const basePrice = currentPrice.value
  const avgDrawdown = Number(props.analysisData?.maxDrawdown)

  if (!Number.isFinite(basePrice) || !Number.isFinite(avgDrawdown)) {
    return null
  }

  return basePrice * (1 + (avgDrawdown / 100))
})

function formatThreshold(value) {
  return Number(value || 0).toFixed(1)
}

function calculateDynamicProbability(side, threshold) {
  const safeThreshold = Math.max(1, Number(threshold) || 1)
  const totalWeight = matchedPatterns.value.reduce((sum, match) => {
    const weight = Number(match.quantSelectedPercent || match.matchScore || 0)
    return sum + Math.max(weight, 0)
  }, 0)

  if (!totalWeight) {
    return '--'
  }

  const hitWeight = matchedPatterns.value.reduce((sum, match) => {
    const stats = match.futureStats5d || {}
    const weight = Math.max(Number(match.quantSelectedPercent || match.matchScore || 0), 0)

    if (side === 'up') {
      return sum + (Number(stats.maxUpPct || 0) >= safeThreshold ? weight : 0)
    }

    return sum + (Number(stats.maxDownPct || 0) <= -safeThreshold ? weight : 0)
  }, 0)

  return ((hitWeight / totalWeight) * 100).toFixed(1) + '%'
}

function normalizeThreshold(value) {
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) {
    return 1
  }

  return Math.min(100, Math.max(1, numericValue))
}

function setProbabilityThreshold(side, value) {
  const normalizedValue = normalizeThreshold(value)

  if (side === 'down') {
    downsideThreshold.value = normalizedValue
    return {
      side: 'down',
      threshold: normalizedValue,
      probability: calculateDynamicProbability('down', normalizedValue)
    }
  }

  upsideThreshold.value = normalizedValue
  return {
    side: 'up',
    threshold: normalizedValue,
    probability: calculateDynamicProbability('up', normalizedValue)
  }
}

function getProbabilitySnapshot(side = 'up', value = null) {
  const normalizedSide = side === 'down' ? 'down' : 'up'
  const threshold = value === null || value === undefined
    ? (normalizedSide === 'down' ? downsideThreshold.value : upsideThreshold.value)
    : normalizeThreshold(value)

  return {
    side: normalizedSide,
    threshold,
    probability: calculateDynamicProbability(normalizedSide, threshold),
    onePercentUp: findThresholdProbability('up', 1),
    onePercentDown: findThresholdProbability('down', 1),
    headlineProbability: headlineProbabilityLabel.value,
    matchedPatternCount: matchedPatternCount.value
  }
}

defineExpose({
  getProbabilitySnapshot,
  setProbabilityThreshold
})
</script>

<template>
  <div class="inner-card">
    <div class="section-header">Prediction Summary</div>
    <div v-if="isLoading" class="prediction-loading-card" role="status" aria-live="polite">
      <span class="prediction-loading-spinner" aria-hidden="true"></span>
      <div class="prediction-loading-copy">
        <strong>{{ loadingTitle }}</strong>
        <small>{{ loadingMessage }}</small>
      </div>
    </div>
    <div v-else class="stats-list">
      <div class="summary-hero">
        <div>
          <p class="summary-label">5D Probability Of Reaching +1%</p>
          <h3>{{ headlineProbabilityLabel }}</h3>
          <p v-if="hasHeadlineProbability" class="summary-disclaimer">
            This result is based on the {{ matchedPatternCount }} most similar historical setups. We measure how often price touched upside and
            downside thresholds within the following 5 trading days. The upside and downside probabilities can both be
            triggered by the same 5-day path.
          </p>
          <p v-else class="summary-disclaimer">
            Search loads live market data only. Generate to score probabilities and matched historical setups.
          </p>
        </div>
        <span class="summary-badge">{{ getSignalLabel(analysisData.signalClassification) }}</span>
      </div>

      <div class="probability-stack">
        <div class="probability-ladder">
          <p class="summary-label">5D Upside Reach</p>
          <div class="suggestion-row">
            <span>Probability of +1%</span>
            <strong class="positive">{{ findThresholdProbability('up', 1) }}</strong>
          </div>
          <div class="suggestion-row">
            <span>Probability of +5%</span>
            <strong class="positive">{{ findThresholdProbability('up', 5) }}</strong>
          </div>
          <div class="suggestion-row">
            <span>Probability of +10%</span>
            <strong class="positive">{{ findThresholdProbability('up', 10) }}</strong>
          </div>
          <div class="probability-slider-card">
            <div class="suggestion-row">
              <span>Custom upside threshold</span>
              <strong class="positive">+{{ formatThreshold(upsideThreshold) }}%</strong>
            </div>
            <input
              v-model="upsideThreshold"
              class="probability-slider"
              type="range"
              min="1"
              max="100"
              step="0.1"
            >
            <div class="suggestion-row">
              <span>Probability of reaching +{{ formatThreshold(upsideThreshold) }}%</span>
              <strong class="positive">{{ calculateDynamicProbability('up', upsideThreshold) }}</strong>
            </div>
          </div>
        </div>

        <div class="probability-ladder">
          <p class="summary-label">5D Downside Reach</p>
          <div class="suggestion-row">
            <span>Probability of -1%</span>
            <strong class="negative">{{ findThresholdProbability('down', 1) }}</strong>
          </div>
          <div class="suggestion-row">
            <span>Probability of -5%</span>
            <strong class="negative">{{ findThresholdProbability('down', 5) }}</strong>
          </div>
          <div class="suggestion-row">
            <span>Probability of -10%</span>
            <strong class="negative">{{ findThresholdProbability('down', 10) }}</strong>
          </div>
          <div class="probability-slider-card">
            <div class="suggestion-row">
              <span>Custom downside threshold</span>
              <strong class="negative">-{{ formatThreshold(downsideThreshold) }}%</strong>
            </div>
            <input
              v-model="downsideThreshold"
              class="probability-slider"
              type="range"
              min="1"
              max="100"
              step="0.1"
            >
            <div class="suggestion-row">
              <span>Probability of reaching -{{ formatThreshold(downsideThreshold) }}%</span>
              <strong class="negative">{{ calculateDynamicProbability('down', downsideThreshold) }}</strong>
            </div>
          </div>
        </div>
      </div>

      <div class="suggestion-row">
        <span>Average 5D High Touch</span>
        <strong>{{ formatPercent(analysisData.avgReturn) }}</strong>
      </div>
      <div class="suggestion-row">
        <span>Average 5D Low Touch</span>
        <strong class="negative">{{ formatPercent(analysisData.maxDrawdown) }}</strong>
      </div>
      <div class="suggestion-row">
        <span>Target Price</span>
        <strong class="positive">{{ formatPrice(projectedTargetPrice) }}</strong>
      </div>
      <div class="suggestion-row">
        <span>Risk Line</span>
        <strong class="negative">{{ formatPrice(projectedRiskLine) }}</strong>
      </div>
      <div class="suggestion-row">
        <span>Matched Patterns</span>
        <strong>{{ analysisData.matchedPatternsCount }}</strong>
      </div>
      <div class="suggestion-row">
        <span>Timeframe</span>
        <strong>{{ formatIntervalLabel(requestData.interval) }}</strong>
      </div>
      <div class="suggestion-row">
        <span>Historical Target Window</span>
        <strong>{{ formatValue(analysisData.recommendedSellDate) }}</strong>
      </div>
    </div>
  </div>
</template>
