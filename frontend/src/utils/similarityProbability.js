const DEFAULT_SAMPLE_LIMIT = 20
const COMPLETE_INDICATOR_SET = ['MA', 'EMA', 'MACD', 'BOLL', 'RSI', 'VOL', 'KDJ', 'OI', 'OBV']
const TOP_MATCH_WEIGHT = 0.6
const TOP_TEN_WEIGHT = 0.4
const CONFIDENCE_FLOOR = 0.92
const CONFIDENCE_RANGE = 0.03

function toFiniteNumber(value) {
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? numericValue : null
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value))
}

function round(value, digits = 1) {
  const multiplier = 10 ** digits
  return Math.round((value + Number.EPSILON) * multiplier) / multiplier
}

export function hasCompleteIndicatorSet(indicatorNames) {
  const selected = new Set((indicatorNames || []).map((name) => String(name || '').trim().toUpperCase()))
  return COMPLETE_INDICATOR_SET.every((name) => selected.has(name))
}

function buildCalibrationMetadata({ sampleSize, top1Similarity, top10AverageSimilarity, samples = [] }) {
  const normalizedSampleSize = Math.max(0, Math.round(toFiniteNumber(sampleSize) ?? 0))
  const normalizedTop1 = clamp(toFiniteNumber(top1Similarity) ?? 0, 0, 100) / 100
  const normalizedTop10Average = clamp(toFiniteNumber(top10AverageSimilarity) ?? 0, 0, 100) / 100

  if (!normalizedSampleSize || normalizedTop1 <= 0 || normalizedTop10Average <= 0) {
    return null
  }

  const similarityQuality = (normalizedTop1 * TOP_MATCH_WEIGHT) + (normalizedTop10Average * TOP_TEN_WEIGHT)
  const confidenceFactor = clamp(
    CONFIDENCE_FLOOR + (CONFIDENCE_RANGE * similarityQuality),
    CONFIDENCE_FLOOR,
    CONFIDENCE_FLOOR + CONFIDENCE_RANGE,
  )

  return {
    method: 'similarity_weighted_v2',
    sampleLimit: DEFAULT_SAMPLE_LIMIT,
    sampleSize: normalizedSampleSize,
    top1Similarity: round(normalizedTop1 * 100, 2),
    top10AverageSimilarity: round(normalizedTop10Average * 100, 2),
    similarityQuality: round(similarityQuality * 100, 2),
    confidenceFactor: round(confidenceFactor, 4),
    confidenceFactorPercent: round(confidenceFactor * 100, 2),
    samples,
  }
}

function getSimilarityPercent(match) {
  const selectedPercent = toFiniteNumber(match?.quantSelectedPercent)
  const matchScore = toFiniteNumber(match?.matchScore)
  return clamp(selectedPercent ?? matchScore ?? 0, 0, 100)
}

function normalizeProbabilitySample(match) {
  const futureStats = match?.futureStats5d || {}
  const maxUpPct = toFiniteNumber(futureStats.maxUpPct) ?? toFiniteNumber(match?.futureReturn5d)
  const maxDownPct = toFiniteNumber(futureStats.maxDownPct) ?? toFiniteNumber(match?.futureDrawdown5d)
  const similarityPercent = getSimilarityPercent(match)

  if (similarityPercent <= 0 || (maxUpPct === null && maxDownPct === null)) {
    return null
  }

  return {
    similarity: similarityPercent / 100,
    similarityPercent,
    maxUpPct,
    maxDownPct,
  }
}

export function calculateSimilarityAdjustedProbability(samples, side, threshold, confidenceFactor) {
  const safeThreshold = Math.max(0, toFiniteNumber(threshold) ?? 0)
  const safeConfidenceFactor = clamp(toFiniteNumber(confidenceFactor) ?? 0, 0, 1)
  let totalWeight = 0
  let hitWeight = 0
  let hitCount = 0
  let usableCount = 0

  for (const sample of samples || []) {
    const outcome = side === 'down'
      ? toFiniteNumber(sample?.maxDownPct)
      : toFiniteNumber(sample?.maxUpPct)
    const weight = clamp(toFiniteNumber(sample?.similarity) ?? 0, 0, 1)

    if (outcome === null || weight <= 0) {
      continue
    }

    const isHit = side === 'down' ? outcome <= -safeThreshold : outcome >= safeThreshold
    usableCount += 1
    totalWeight += weight
    if (isHit) {
      hitCount += 1
      hitWeight += weight
    }
  }

  if (!usableCount || totalWeight <= 0) {
    return null
  }

  const rawProbability = (hitCount / usableCount) * 100
  const similarityWeightedProbability = (hitWeight / totalWeight) * 100
  const probability = rawProbability * safeConfidenceFactor

  return {
    probability: round(clamp(probability, 0, 100), 1),
    rawProbability: round(rawProbability, 2),
    similarityWeightedProbability: round(similarityWeightedProbability, 2),
    hitCount,
    sampleSize: usableCount,
  }
}

export function buildSimilarityProbabilityCalibration(matches, { sampleLimit = DEFAULT_SAMPLE_LIMIT } = {}) {
  const samples = (matches || [])
    .map(normalizeProbabilitySample)
    .filter(Boolean)
    .sort((left, right) => right.similarity - left.similarity)
    .slice(0, Math.max(1, sampleLimit))

  if (!samples.length) {
    return null
  }

  const topTenSamples = samples.slice(0, Math.min(10, samples.length))
  const top1Similarity = samples[0].similarity
  const top10AverageSimilarity = topTenSamples.reduce((sum, sample) => sum + sample.similarity, 0) / topTenSamples.length
  const calibration = buildCalibrationMetadata({
    sampleSize: samples.length,
    top1Similarity: top1Similarity * 100,
    top10AverageSimilarity: top10AverageSimilarity * 100,
    samples,
  })

  return calibration ? { ...calibration, sampleLimit: Math.max(1, sampleLimit) } : null
}

export function buildSimilarityProbabilityCalibrationFromSummary(summary) {
  return buildCalibrationMetadata({
    sampleSize: summary?.sampleSize,
    top1Similarity: summary?.top1Similarity,
    top10AverageSimilarity: summary?.top10AverageSimilarity,
  })
}

function calibrateRawProbability(rawProbability, confidenceFactor) {
  const probability = toFiniteNumber(rawProbability)
  if (probability === null) {
    return null
  }

  return round(clamp(probability, 0, 100) * confidenceFactor, 1)
}

function buildCalibratedProbabilityLadder(calibration, side, rawLadder, thresholds = [1, 5, 10]) {
  return thresholds.map((threshold) => {
    const sampleResult = calculateSimilarityAdjustedProbability(
      calibration.samples,
      side,
      threshold,
      calibration.confidenceFactor,
    )
    const rawLadderProbability = toFiniteNumber(
      (rawLadder || []).find((item) => Number(item?.threshold) === threshold)?.probability,
    )
    const rawProbability = rawLadderProbability ?? sampleResult?.rawProbability ?? null

    return {
      threshold,
      ...(sampleResult || {}),
      rawProbability,
      probability: calibrateRawProbability(rawProbability, calibration.confidenceFactor),
    }
  })
}

export function applySimilarityProbabilityCalibration(patternAnalysis, matches, options = {}) {
  const calibration = buildSimilarityProbabilityCalibration(matches, options)
    ?? buildSimilarityProbabilityCalibrationFromSummary(patternAnalysis?.probabilityCalibrationSummary)
  if (!calibration) {
    return patternAnalysis
  }

  const rawLadders = patternAnalysis?.futureFiveDayProbabilities || {}
  const up = buildCalibratedProbabilityLadder(calibration, 'up', rawLadders.up)
  const down = buildCalibratedProbabilityLadder(calibration, 'down', rawLadders.down)
  const calibratedIncrease = calibrateRawProbability(patternAnalysis?.probabilityOfIncrease, calibration.confidenceFactor)
  const calibratedDecrease = calibrateRawProbability(patternAnalysis?.probabilityOfDecrease, calibration.confidenceFactor)

  return {
    ...patternAnalysis,
    rawProbabilityOfIncrease: patternAnalysis?.probabilityOfIncrease,
    rawProbabilityOfDecrease: patternAnalysis?.probabilityOfDecrease,
    rawFutureFiveDayProbabilities: patternAnalysis?.futureFiveDayProbabilities,
    probabilityOfIncrease: calibratedIncrease ?? up[0]?.probability ?? patternAnalysis?.probabilityOfIncrease,
    probabilityOfDecrease: calibratedDecrease ?? down[0]?.probability ?? patternAnalysis?.probabilityOfDecrease,
    futureFiveDayProbabilities: { up, down },
    matchedPatternsCount: calibration.sampleSize,
    probabilityCalibration: calibration,
  }
}

export function applySimilarityProbabilityCalibrationForIndicators(patternAnalysis, matches, indicatorNames, options = {}) {
  if (hasCompleteIndicatorSet(indicatorNames)) {
    if (patternAnalysis?.probabilityCalibration?.method === 'similarity_weighted_v2') {
      return patternAnalysis
    }
    return applySimilarityProbabilityCalibration(patternAnalysis, matches, options)
  }

  if (!patternAnalysis?.probabilityCalibration) {
    return patternAnalysis
  }

  const {
    probabilityCalibration: _probabilityCalibration,
    rawProbabilityOfIncrease,
    rawProbabilityOfDecrease,
    rawFutureFiveDayProbabilities,
    ...uncalibratedAnalysis
  } = patternAnalysis

  return {
    ...uncalibratedAnalysis,
    probabilityOfIncrease: rawProbabilityOfIncrease ?? uncalibratedAnalysis.probabilityOfIncrease,
    probabilityOfDecrease: rawProbabilityOfDecrease ?? uncalibratedAnalysis.probabilityOfDecrease,
    futureFiveDayProbabilities: rawFutureFiveDayProbabilities ?? uncalibratedAnalysis.futureFiveDayProbabilities,
  }
}
