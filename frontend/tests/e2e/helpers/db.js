import pg from 'pg'

const { Client } = pg
const rawDatabaseUrl = process.env.DATABASE_URL_E2E || 'postgresql+psycopg://localhost/stock_pattern_project_e2e'
const connectionString = rawDatabaseUrl.replace('postgresql+psycopg://', 'postgresql://')

async function withClient(callback) {
  const client = new Client({ connectionString })
  await client.connect()

  try {
    return await callback(client)
  } finally {
    await client.end()
  }
}

export async function resetDatabase() {
  await withClient((client) => client.query(`
    TRUNCATE TABLE
      pattern_matches,
      analysis_runs,
      pattern_windows,
      daily_indicators,
      daily_prices,
      symbols
    RESTART IDENTITY CASCADE
  `))
}

export async function getCoreTableCounts() {
  return withClient(async (client) => {
    const tables = [
      'symbols',
      'daily_prices',
      'daily_indicators',
      'pattern_windows',
      'analysis_runs',
      'pattern_matches'
    ]

    const counts = {}

    for (const table of tables) {
      const result = await client.query(`SELECT COUNT(*)::int AS count FROM ${table}`)
      counts[table] = result.rows[0].count
    }

    return counts
  })
}
