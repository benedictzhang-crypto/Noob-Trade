export function resolveMatchedPatternDisplayCount(matchedPatterns, explicitCount) {
  const visibleCount = Array.isArray(matchedPatterns) ? matchedPatterns.length : 0
  const numericExplicitCount = Number(explicitCount)
  const fallbackCount = Number.isFinite(numericExplicitCount) && numericExplicitCount > 0
    ? Math.round(numericExplicitCount)
    : 0

  return Math.max(visibleCount, fallbackCount)
}
