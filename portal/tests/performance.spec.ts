import { test, expect } from '@playwright/test'

test.describe('Performance', () => {
  test('should load within acceptable time', async ({ page }) => {
    const startTime = Date.now()
    await page.goto('/')
    const loadTime = Date.now() - startTime

    // Should load in under 3 seconds
    expect(loadTime).toBeLessThan(3000)
  })

  test('should have minimal DOM size', async ({ page }) => {
    await page.goto('/')

    // Count DOM nodes
    const nodeCount = await page.evaluate(() => {
      return document.querySelectorAll('*').length
    })

    // Should have reasonable DOM size (< 1000 nodes for landing page)
    expect(nodeCount).toBeLessThan(1000)
  })

  test('should not have console errors', async ({ page }) => {
    const consoleErrors: string[] = []

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })

    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Should have zero console errors
    expect(consoleErrors).toHaveLength(0)
  })

  test('should not have console warnings', async ({ page }) => {
    const consoleWarnings: string[] = []

    page.on('console', (msg) => {
      if (msg.type() === 'warning') {
        consoleWarnings.push(msg.text())
      }
    })

    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Should have zero console warnings
    expect(consoleWarnings).toHaveLength(0)
  })

  test('should have zero layout shifts', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Check for cumulative layout shift
    const cls = await page.evaluate(() => {
      interface LayoutShiftEntry extends PerformanceEntry {
        value: number
        hadRecentInput: boolean
      }

      return new Promise<number>((resolve) => {
        let clsValue = 0
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.entryType === 'layout-shift') {
              const layoutEntry = entry as unknown as LayoutShiftEntry
              if (!layoutEntry.hadRecentInput) {
                clsValue += layoutEntry.value
              }
            }
          }
        })
        observer.observe({ type: 'layout-shift', buffered: true })

        // Wait a bit for layout shifts to occur
        setTimeout(() => {
          observer.disconnect()
          resolve(clsValue)
        }, 2000)
      })
    })

    // CLS should be less than 0.1 (good score)
    expect(cls).toBeLessThan(0.1)
  })

  test('should load critical resources quickly', async ({ page }) => {
    const resourceTimes: number[] = []

    page.on('response', async (response) => {
      const url = response.url()
      if (url.includes('.js') || url.includes('.css')) {
        // Use request/response lifecycle timing
        const request = response.request()
        const endTime = Date.now()
        resourceTimes.push(endTime)
      }
    })

    const startTime = Date.now()
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    const totalLoadTime = Date.now() - startTime

    // All resources should load in reasonable time
    expect(totalLoadTime).toBeLessThan(5000)
  })

  test('should have small JavaScript bundle size', async ({ page }) => {
    let totalJsSize = 0

    page.on('response', async (response) => {
      const url = response.url()
      if (url.includes('.js') && !url.includes('node_modules')) {
        const buffer = await response.body()
        totalJsSize += buffer.length
      }
    })

    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Total JS should be under 500KB (compressed)
    expect(totalJsSize).toBeLessThan(500 * 1024)
  })
})
