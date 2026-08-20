import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const readProjectFile = (path) => readFileSync(new URL(`../../${path}`, import.meta.url), 'utf8')

test('publishes the canonical NoobTrade brand and Noob Trade alias', () => {
  const index = readProjectFile('index.html')

  assert.match(index, /<title>NoobTrade \| Stock &amp; Crypto Market Research<\/title>/)
  assert.match(index, /<link rel="canonical" href="https:\/\/www\.noobtrading\.com\/" \/>/)
  assert.match(index, /"alternateName": \["Noob Trade", "NoobTrading"\]/)
  assert.match(index, /"name": "AmpliAlpha, Inc\."/)
})

test('allows search crawlers and points them to the production sitemap', () => {
  const robots = readProjectFile('public/robots.txt')
  const sitemap = readProjectFile('public/sitemap.xml')

  assert.match(robots, /^User-agent: \*$/m)
  assert.match(robots, /^Allow: \/$/m)
  assert.match(robots, /^Sitemap: https:\/\/www\.noobtrading\.com\/sitemap\.xml$/m)
  assert.match(sitemap, /<loc>https:\/\/www\.noobtrading\.com\/<\/loc>/)
})
