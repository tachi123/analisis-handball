import { decodePublicReport } from './src/projection.js'
import fs from 'node:fs'

const report = JSON.parse(fs.readFileSync('./public/report.json', 'utf8'))

try {
  const result = decodePublicReport(report)
  console.log('SUCCESS: decodePublicReport completed without error')
  console.log('Players count:', result.players?.length)
  console.log('First player:', result.players?.[0]?.name, 'jersey:', result.players?.[0]?.jersey_number)
  console.log('All player jerseys:')
  result.players?.forEach(p => console.log(' -', p.name, '->', p.jersey_number))
  console.log('Metrics keys:', Object.keys(result.metrics))
  // Check no player: or team: prefixed keys
  const metricKeys = Object.keys(result.metrics)
  const internalKeys = metricKeys.filter(k => /^player:/i.test(k) || /^team:/i.test(k))
  console.log('Internal-looking metric keys (should be empty):', internalKeys)
  if (internalKeys.length === 0) {
    console.log('✓ No internal-looking metric keys in exported report')
  }
} catch (e) {
  console.error('FAILED:', e instanceof Error ? e.message : e)
}