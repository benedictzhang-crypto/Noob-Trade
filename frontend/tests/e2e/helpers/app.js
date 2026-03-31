export async function warmApplication() {
  const warmupUrl = 'http://127.0.0.1:4173/api/stock/AAPL?lookback=20&interval=daily&indicators=MA,EMA,MACD'

  for (let attempt = 1; attempt <= 8; attempt += 1) {
    try {
      const response = await fetch(warmupUrl)

      if (response.ok) {
        return
      }
    } catch (error) {
      // Keep retrying while the local stack warms up.
    }

    await new Promise((resolve) => setTimeout(resolve, attempt * 250))
  }

  throw new Error('Could not warm the stock API before running the UI tests.')
}
