import assert from 'node:assert/strict'
import test from 'node:test'

import {
  applySimilarityProbabilityCalibration,
  applySimilarityProbabilityCalibrationForIndicators,
  buildSimilarityProbabilityCalibration,
  buildSimilarityProbabilityCalibrationFromSummary,
  calculateSimilarityAdjustedProbability,
  hasCompleteIndicatorSet,
} from '../../src/utils/similarityProbability.js'

function makeMatch(score, { maxUpPct = 2, maxDownPct = -0.5 } = {}) {
  return {
    matchScore: score,
    quantSelectedPercent: score,
    futureStats5d: { maxUpPct, maxDownPct },
  }
}

test('maps the proposed 70 top match and 50 top-ten average to a gentle 93.86% confidence factor', () => {
  const topTen = [70, ...Array(9).fill(430 / 9)]
  const matches = [...topTen, ...Array(10).fill(40)].map((score) => makeMatch(score))
  const calibration = buildSimilarityProbabilityCalibration(matches)
  const result = calculateSimilarityAdjustedProbability(
    calibration.samples,
    'up',
    1,
    calibration.confidenceFactor,
  )

  assert.equal(calibration.top1Similarity, 70)
  assert.equal(calibration.top10AverageSimilarity, 50)
  assert.equal(calibration.confidenceFactorPercent, 93.86)
  assert.equal(result.rawProbability, 100)
  assert.equal(result.probability, 93.9)
})

test('discounts the existing hit rate while retaining weighted outcomes for audit', () => {
  const samples = [
    makeMatch(90, { maxUpPct: 2 }),
    makeMatch(80, { maxUpPct: 2 }),
    makeMatch(70, { maxUpPct: 2 }),
    makeMatch(60, { maxUpPct: 0.2 }),
  ]
  const calibration = buildSimilarityProbabilityCalibration(samples)
  const result = calculateSimilarityAdjustedProbability(
    calibration.samples,
    'up',
    1,
    calibration.confidenceFactor,
  )

  assert.equal(result.rawProbability, 75)
  assert.equal(result.similarityWeightedProbability, 80)
  assert.equal(result.probability, 70.9)
})

test('uses only the 20 most similar matches even when 30 are displayed', () => {
  const matches = Array.from({ length: 30 }, (_, index) => makeMatch(100 - index))
  const calibration = buildSimilarityProbabilityCalibration(matches)

  assert.equal(calibration.sampleSize, 20)
  assert.equal(calibration.samples.at(-1).similarityPercent, 81)
})

test('calibrates compact scan probabilities from the lightweight summary', () => {
  const summary = {
    sampleSize: 20,
    top1Similarity: 70,
    top10AverageSimilarity: 50,
  }
  const calibration = buildSimilarityProbabilityCalibrationFromSummary(summary)
  const calibrated = applySimilarityProbabilityCalibration({
    probabilityOfIncrease: 95,
    probabilityOfDecrease: 40,
    matchedPatternsCount: 20,
    matchedHistoricalPatterns: [],
    probabilityCalibrationSummary: summary,
    futureFiveDayProbabilities: {
      up: [{ threshold: 1, probability: 95 }],
      down: [{ threshold: 1, probability: 40 }],
    },
  }, [])

  assert.equal(calibration.confidenceFactorPercent, 93.86)
  assert.equal(calibrated.probabilityOfIncrease, 89.2)
  assert.equal(calibrated.probabilityCalibration.samples.length, 0)
})

test('recognizes only the complete nine-indicator selection', () => {
  assert.equal(hasCompleteIndicatorSet(['MA', 'EMA', 'MACD', 'BOLL', 'RSI', 'Vol', 'KDJ', 'OI', 'OBV']), true)
  assert.equal(hasCompleteIndicatorSet(['MA', 'EMA', 'MACD', 'BOLL', 'RSI', 'Vol', 'KDJ', 'OBV']), false)
})

test('keeps the prior weighted probability when any indicator is not selected', () => {
  const rawAnalysis = {
    probabilityOfIncrease: 87.35,
    probabilityOfDecrease: 42.2,
    futureFiveDayProbabilities: {
      up: [{ threshold: 1, probability: 87.35 }],
      down: [{ threshold: 1, probability: 42.2 }],
    },
    probabilityCalibrationSummary: {
      sampleSize: 20,
      top1Similarity: 70,
      top10AverageSimilarity: 50,
    },
  }
  const matches = Array(20).fill(null).map(() => makeMatch(70))
  const partialIndicators = ['MA', 'EMA', 'MACD', 'BOLL', 'RSI', 'Vol', 'KDJ', 'OBV']
  const fullIndicators = [...partialIndicators, 'OI']

  const unchanged = applySimilarityProbabilityCalibrationForIndicators(rawAnalysis, matches, partialIndicators)
  const calibrated = applySimilarityProbabilityCalibrationForIndicators(rawAnalysis, matches, fullIndicators)

  assert.equal(unchanged.probabilityOfIncrease, 87.35)
  assert.equal(unchanged.probabilityCalibration, undefined)
  assert.equal(calibrated.probabilityOfIncrease, 82.2)
})

test('applies calibrated ladders without mutating the raw analysis', () => {
  const original = {
    probabilityOfIncrease: 100,
    probabilityOfDecrease: 50,
    futureFiveDayProbabilities: {
      up: [{ threshold: 1, probability: 100 }],
      down: [{ threshold: 1, probability: 50 }],
    },
  }
  const matches = [
    makeMatch(90, { maxUpPct: 3, maxDownPct: -2 }),
    makeMatch(80, { maxUpPct: 0.5, maxDownPct: -0.2 }),
  ]
  const calibrated = applySimilarityProbabilityCalibration(original, matches)

  assert.equal(original.probabilityOfIncrease, 100)
  assert.equal(calibrated.rawProbabilityOfIncrease, 100)
  assert.notEqual(calibrated.probabilityOfIncrease, 100)
  assert.equal(calibrated.futureFiveDayProbabilities.up[0].rawProbability, 100)
  assert.equal(calibrated.futureFiveDayProbabilities.up.length, 3)
  assert.equal(calibrated.matchedPatternsCount, 2)
})
