// Export stable teaching-space identities for backend mapping validation.
import { readFileSync, writeFileSync } from 'node:fs'
import { buildings, spaces, floorsFor } from '../frontend/src/campus.ts'
const path = new URL('../backend/app/campus_catalog.json', import.meta.url)
const data = JSON.stringify(spaces.filter(s => ['classroom', 'lab'].includes(s.kind)).map(s => ({
  id: s.id, label: s.label, kind: s.kind, provisional: s.provisional,
  building: buildings.find(b => b.id === s.buildingId).label,
  floor: floorsFor(s.buildingId)[s.floor].label,
})).sort((a, b) => a.id.localeCompare(b.id)), null, 2) + '\n'
if (process.argv.includes('--check')) {
  if (readFileSync(path, 'utf8') !== data) throw new Error('Campus catalog drift: run node scripts/sync_campus_catalog.mjs')
} else writeFileSync(path, data)
