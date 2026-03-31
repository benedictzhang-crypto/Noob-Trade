import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import pg from 'pg'

const { Client } = pg
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '..')
const schemaPath = path.resolve(projectRoot, '../backend/db/init.sql')
const rawDatabaseUrl = process.env.DATABASE_URL_E2E || 'postgresql+psycopg://localhost/stock_pattern_project_e2e'
const normalizedDatabaseUrl = rawDatabaseUrl.replace('postgresql+psycopg://', 'postgresql://')
const targetUrl = new URL(normalizedDatabaseUrl)
const databaseName = targetUrl.pathname.replace(/^\//, '')

if (!/^[a-zA-Z0-9_]+$/.test(databaseName)) {
  throw new Error(`Unsupported e2e database name: ${databaseName}`)
}

const adminUrl = new URL(normalizedDatabaseUrl)
adminUrl.pathname = '/postgres'

const adminClient = new Client({ connectionString: adminUrl.toString() })
await adminClient.connect()

const existingDatabase = await adminClient.query(
  'SELECT 1 FROM pg_database WHERE datname = $1',
  [databaseName]
)

if (existingDatabase.rowCount === 0) {
  await adminClient.query(`CREATE DATABASE ${databaseName}`)
}

await adminClient.end()

const schemaSql = fs.readFileSync(schemaPath, 'utf8')
const schemaClient = new Client({ connectionString: normalizedDatabaseUrl })
await schemaClient.connect()
await schemaClient.query(schemaSql)
await schemaClient.end()
