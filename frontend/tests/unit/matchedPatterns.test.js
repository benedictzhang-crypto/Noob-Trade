import assert from 'node:assert/strict'
import test from 'node:test'

import { resolveMatchedPatternDisplayCount } from '../../src/utils/matchedPatterns.js'

test('shows all 30 displayed matches when probability calibration uses 20 samples', () => {
  const displayedMatches = Array.from({ length: 30 }, (_, index) => ({ id: index }))

  assert.equal(resolveMatchedPatternDisplayCount(displayedMatches, 20), 30)
})

test('falls back to the API count while matched details are not included', () => {
  assert.equal(resolveMatchedPatternDisplayCount([], 20), 20)
})
