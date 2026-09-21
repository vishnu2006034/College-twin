import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import StateDashboard from './StateDashboard'
import { mockSnapshot, mockSnapshotClient } from './snapshot.mock'
import { snapshotClient } from './snapshot'

const edition = { id: mockSnapshot.edition_id, seed: 42, generator_version: '1', logical_content_hash: 'b', frozen_at: '', config: { start_date: '2026-01-05', weeks: 1, students_per_section: 2 } }
const actor = { id: 'planner', username: 'planner', role: 'planner' as const }
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test('mock contract renders hand-calculated metrics, coverage and conflicts', async () => {
  render(<StateDashboard edition={edition} actor={actor} client={mockSnapshotClient}/>)
  fireEvent.click(screen.getByText('Create dated snapshot'))
  expect(await screen.findByText('9.4%')).toBeVisible()
  expect(screen.getByText('50.0%')).toBeVisible()
  expect(screen.getByText('room overlap')).toBeVisible()
  expect(screen.getByText(/1 missing records are unknown/)).toBeVisible()
})

test('real adapter sends contract, CSRF and idempotency header', async () => {
  document.cookie = 'twin_csrf=test-token'
  const fetcher = vi.fn().mockResolvedValue({ ok: true, status: 201, json: async () => mockSnapshot })
  vi.stubGlobal('fetch', fetcher)
  render(<StateDashboard edition={edition} actor={actor} client={snapshotClient}/>)
  fireEvent.click(screen.getByText('Create dated snapshot'))
  await screen.findByText('9.4%')
  const [url, options] = fetcher.mock.calls[0]
  expect(url).toBe('/api/v1/snapshots')
  expect(options.headers['Idempotency-Key']).toBeTruthy()
  expect(options.headers['X-CSRF-Token']).toBe('test-token')
  expect(JSON.parse(options.body)).toMatchObject({ edition_id: edition.id, as_of: '2026-01-05T17:00:00+05:30' })
})

test('failure shows error and retry reuses key without substituting mock values', async () => {
  const create = vi.fn().mockRejectedValue(new Error('Database unavailable'))
  render(<StateDashboard edition={edition} actor={actor} client={{ ...mockSnapshotClient, create }}/>)
  fireEvent.click(screen.getByText('Create dated snapshot'))
  expect(await screen.findByRole('alert')).toHaveTextContent('Database unavailable')
  expect(screen.queryByText('9.4%')).not.toBeInTheDocument()
  fireEvent.click(screen.getByText('Create dated snapshot'))
  await screen.findByRole('alert')
  expect(create.mock.calls[0][1]).toBe(create.mock.calls[1][1])
})

test('viewer opens saved snapshot and empty or unknown states are explicit', async () => {
  render(<StateDashboard edition={edition} actor={{ ...actor, role: 'viewer' }} client={{ ...mockSnapshotClient, get: async () => ({ ...mockSnapshot, anomalies: [], metrics: { ...mockSnapshot.metrics, attendance_rate: null } }) }}/>)
  expect(screen.queryByText('Create dated snapshot')).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Saved snapshot ID'), { target: { value: mockSnapshot.id } })
  fireEvent.click(screen.getByText('Open saved snapshot'))
  expect(await screen.findByText('Unknown')).toBeVisible()
  expect(screen.getByText(/No conflicts or suitability/)).toBeVisible()
})
