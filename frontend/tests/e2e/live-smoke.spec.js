import { expect, test } from '@playwright/test'

const liveEnabled = process.env.PLAYWRIGHT_LIVE_SMOKE === 'true' && Boolean(process.env.MARKET_DATA_TOKEN)

test.describe('Live API smoke', () => {
  test.skip(!liveEnabled, 'Live smoke requires PLAYWRIGHT_LIVE_SMOKE=true and MARKET_DATA_TOKEN.')

  test('returns healthy and structured live responses', async ({ request }) => {
    const healthResponse = await request.get('/api/health')
    expect(healthResponse.ok()).toBeTruthy()

    const healthJson = await healthResponse.json()
    expect(healthJson).toEqual(
      expect.objectContaining({
        status: 'ok'
      })
    )

    const stockResponse = await request.get('/api/stock/AAPL?lookback=20&interval=daily&indicators=MA,EMA,MACD')
    expect(stockResponse.ok()).toBeTruthy()

    const stockJson = await stockResponse.json()
    expect(stockJson).toEqual(
      expect.objectContaining({
        request: expect.objectContaining({
          symbol: 'AAPL',
          interval: 'daily'
        }),
        stock: expect.objectContaining({
          symbol: 'AAPL'
        }),
        patternAnalysis: expect.any(Object),
        chartData: expect.objectContaining({
          series: expect.any(Object)
        })
      })
    )
  })
})
