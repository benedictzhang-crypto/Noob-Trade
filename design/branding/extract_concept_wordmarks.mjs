import { createRequire } from 'node:module'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(fileURLToPath(import.meta.url))
const require = createRequire(resolve(root, '../../frontend/package.json'))
const { chromium } = require('playwright')

const sourcePath = resolve(root, 'noobtrade-logo-concept-v2.png')
const exportsDirectory = resolve(root, 'exports')
const frontendBrandDirectory = resolve(root, '../../frontend/public/brand')
const launcherAssetsDirectory = resolve(root, '../../launcher/assets')
const sourceData = (await readFile(sourcePath)).toString('base64')

await mkdir(exportsDirectory, { recursive: true })
await mkdir(frontendBrandDirectory, { recursive: true })
await mkdir(launcherAssetsDirectory, { recursive: true })

const browser = await chromium.launch({ headless: true })
try {
  const page = await browser.newPage()
  await page.setContent(`<img id="source" src="data:image/png;base64,${sourceData}" hidden>`)

  const images = await page.evaluate(async () => {
    const image = document.querySelector('#source')
    await image.decode()

    const sourceCanvas = document.createElement('canvas')
    sourceCanvas.width = image.naturalWidth
    sourceCanvas.height = image.naturalHeight
    const sourceContext = sourceCanvas.getContext('2d')
    sourceContext.drawImage(image, 0, 0)

    const source = sourceContext.getImageData(0, 0, sourceCanvas.width, sourceCanvas.height)
    let minX = sourceCanvas.width
    let minY = 520
    let maxX = 0
    let maxY = 0

    for (let y = 80; y < 520; y += 1) {
      for (let x = 0; x < sourceCanvas.width; x += 1) {
        const index = (y * sourceCanvas.width + x) * 4
        const red = source.data[index]
        const green = source.data[index + 1]
        const blue = source.data[index + 2]
        const luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
        const orange = red > 180 && red > green * 1.15 && green > 50 && green < 210 && blue < 140

        if (luminance < 220 || orange) {
          minX = Math.min(minX, x)
          minY = Math.min(minY, y)
          maxX = Math.max(maxX, x)
          maxY = Math.max(maxY, y)
        }
      }
    }

    const marginX = 18
    const marginY = 14
    const cropX = minX - marginX
    const cropY = minY - marginY
    const cropWidth = maxX - minX + 1 + marginX * 2
    const cropHeight = maxY - minY + 1 + marginY * 2
    const cropped = sourceContext.getImageData(cropX, cropY, cropWidth, cropHeight)

    const render = (foreground, background = null) => {
      const canvas = document.createElement('canvas')
      canvas.width = cropWidth
      canvas.height = cropHeight
      const context = canvas.getContext('2d')
      const output = context.createImageData(cropWidth, cropHeight)

      for (let index = 0; index < cropped.data.length; index += 4) {
        const red = cropped.data[index]
        const green = cropped.data[index + 1]
        const blue = cropped.data[index + 2]
        const luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
        const orange = red > 180 && red > green * 1.15 && green > 50 && green < 210 && blue < 150
        let alpha

        if (orange) {
          alpha = Math.max((255 - green) / 117, (255 - blue) / 255)
          output.data[index] = 255
          output.data[index + 1] = 138
          output.data[index + 2] = 0
        } else {
          alpha = (255 - luminance) / 238
          output.data[index] = foreground
          output.data[index + 1] = foreground
          output.data[index + 2] = foreground
        }

        alpha = alpha < 0.08 ? 0 : alpha
        output.data[index + 3] = Math.max(0, Math.min(255, Math.round(alpha * 255)))
      }

      context.putImageData(output, 0, 0)
      if (background) {
        const foregroundCanvas = document.createElement('canvas')
        foregroundCanvas.width = cropWidth
        foregroundCanvas.height = cropHeight
        foregroundCanvas.getContext('2d').putImageData(output, 0, 0)
        context.fillStyle = background
        context.fillRect(0, 0, cropWidth, cropHeight)
        context.drawImage(foregroundCanvas, 0, 0)
      }
      return canvas.toDataURL('image/png')
    }

    return {
      blackTransparent: render(17),
      whiteTransparent: render(255),
      blackOnWhite: render(17, '#ffffff'),
      whiteOnBlack: render(255, '#111111'),
    }
  })

  const decode = (dataUrl) => Buffer.from(dataUrl.split(',')[1], 'base64')
  const black = decode(images.blackTransparent)
  const white = decode(images.whiteTransparent)
  const svg = (title, png) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1451 273" role="img" aria-label="${title}">
  <image width="1451" height="273" href="data:image/png;base64,${png.toString('base64')}" />
</svg>
`
  const blackSvg = svg('NoobTrade', black)
  const whiteSvg = svg('NoobTrade', white)

  await Promise.all([
    writeFile(resolve(exportsDirectory, 'noobtrade-wordmark-black-transparent.png'), black),
    writeFile(resolve(exportsDirectory, 'noobtrade-wordmark-white-transparent.png'), white),
    writeFile(resolve(exportsDirectory, 'noobtrade-wordmark-black-on-white.png'), decode(images.blackOnWhite)),
    writeFile(resolve(exportsDirectory, 'noobtrade-wordmark-white-on-black.png'), decode(images.whiteOnBlack)),
    writeFile(resolve(exportsDirectory, 'noobtrade-wordmark-black.svg'), blackSvg),
    writeFile(resolve(exportsDirectory, 'noobtrade-wordmark-white.svg'), whiteSvg),
    writeFile(resolve(frontendBrandDirectory, 'noobtrade-wordmark.png'), black),
    writeFile(resolve(frontendBrandDirectory, 'noobtrade-wordmark-dark.png'), white),
    writeFile(resolve(frontendBrandDirectory, 'noobtrade-wordmark.svg'), blackSvg),
    writeFile(resolve(frontendBrandDirectory, 'noobtrade-wordmark-dark.svg'), whiteSvg),
    writeFile(resolve(launcherAssetsDirectory, 'noobtrade_wordmark.svg'), blackSvg),
  ])
} finally {
  await browser.close()
}
