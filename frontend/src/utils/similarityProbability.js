const DEFAULT_SAMPLE_LIMIT = 20
const TOP_MATCH_WEIGHT = 0.6
const TOP_TEN_WEIGHT = 0.4
const CONFIDENCE_FLOOR = 0.5
const CONFIDENCE_RANGE = 0.45

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
  const similarityQuality = (top1Similarity * TOP_MATCH_WEIGHT) + (top10AverageSimilarity * TOP_TEN_WEIGHT)
  const confidenceFactor = clamp(
    CONFIDENCE_FLOOR + (CONFIDENCE_RANGE * similarityQuality),
    CONFIDENCE_FLOOR,
    CONFIDENCE_FLOOR + CONFIDENCE_RANGE,
  )

  return {
    method: 'similarity_weighted_v1',
    sampleLimit: Math.max(1, sampleLimit),
    sampleSize: samples.length,
    top1Similarity: round(top1Similarity * 100, 2),
    top10AverageSimilarity: round(top10AverageSimilarity * 100, 2),
    similarityQuality: round(similarityQuality * 100, 2),
    confidenceFactor: round(confidenceFactor, 4),
    confidenceFactorPercent: round(confidenceFactor * 100, 2),
    samples,
  }
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
