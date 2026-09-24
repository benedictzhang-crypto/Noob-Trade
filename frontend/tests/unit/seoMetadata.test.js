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

test('publishes the NoobTrade wordmark and bird-only install icons', () => {
  const index = readProjectFile('index.html')
  const app = readProjectFile('src/App.vue')
  const styles = readProjectFile('src/style.css')
  const manifest = JSON.parse(readProjectFile('public/manifest.webmanifest'))
  const wordmark = readProjectFile('public/brand/noobtrade-wordmark.svg')
  const appIcon = readProjectFile('public/icons/noobtrade-app-icon-v4.svg')

  assert.match(index, /noobtrade-app-icon-v4\.svg/)
  assert.match(index, /favicon-v4\.ico/)
  assert.match(app, /noobtrade-wordmark\.png/)
  assert.match(app, /noobtrade-wordmark-dark\.png/)
  assert.match(styles, /aspect-ratio: 1960 \/ 384;/)
  assert.match(wordmark, /aria-label="NoobTrade"/)
  assert.match(wordmark, /data:image\/png;base64,/)
  assert.match(appIcon, /NoobTrade app icon/)
  assert.deepEqual(
    manifest.icons.map(({ src, sizes }) => [src, sizes]),
    [
      ['/icons/noobtrade-192-v4.png', '192x192'],
      ['/icons/noobtrade-512-v4.png', '512x512'],
      ['/icons/noobtrade-maskable-512-v4.png', '512x512'],
      ['/icons/apple-touch-icon-v4.png', '180x180'],
    ]
  )
})
