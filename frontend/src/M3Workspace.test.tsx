import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import M3Workspace from './M3Workspace'
import { mockSnapshot } from './snapshot.mock'

const actor = { id: 'planner', username: 'planner', role: 'planner' as const }
const baseline = { ...mockSnapshot, as_of: mockSnapshot.window_start, anomalies: [] }
const stage = { assigned_classes: 2, unassigned_classes: 0, booked_room_minutes: 120, available_room_minutes: 1800, room_utilization: 120 / 1800 }
const run = { id: 'saved-run', snapshot_id: baseline.id, baseline_input_hash: 'frozen-hash', algorithm_version: 'greedy_room_v1', result: {
  stages: { baseline: { ...stage, available_room_minutes: 1920, room_utilization: 120 / 1920 }, disrupted: { ...stage, assigned_classes: 1, unassigned_classes: 1, booked_room_minutes: 60, room_utilization: 60 / 1800 }, reassigned: stage },
  impact: { affected_students: 40, unresolved_students: 0 }, recommendation: { message: '1 affected class; 1 reassigned.' }, observed_attendance: { label: 'Observed at baseline cutoff; unchanged by simulation', attendance_present: 0, attendance_recorded: 0 }
} }
const response = (data: unknown) => ({ ok: true, status: 200, json: async () => data })
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test('planner retries identical input with same key and displays independent comparison arithmetic', async () => {
  let creates = 0
  const fetcher = vi.fn(async (url: string) => {
    if (url.endsWith('/rooms')) return response({ items: [{ id: 'room', code: 'R1', kind: 'classroom', capacity: 40 }] })
    if (url.includes('/sessions?')) return response({ items: [], total: 0, offset: 0, limit: 50 })
    if (++creates === 1) return { ok: false, status: 503, json: async () => ({ message: 'Retry database request' }) }
    return response(run)
  })
  vi.stubGlobal('fetch', fetcher)
  render(<M3Workspace snapshot={baseline} actor={actor}/> )
  await waitFor(() => expect(screen.getByText('Simulate closure')).toBeEnabled())
  fireEvent.change(screen.getByLabelText('Closure start (IST)'), { target: { value: '2026-01-05T10:00' } })
  fireEvent.change(screen.getByLabelText('Closure end (IST)'), { target: { value: '2026-01-05T12:00' } })
  fireEvent.click(screen.getByText('Simulate closure'))
  expect(await screen.findByRole('alert')).toHaveTextContent('Retry database request')
  fireEvent.click(screen.getByText('Simulate closure'))
  expect(await screen.findByText('6.25%')).toBeVisible()
  expect(screen.getByText('6.67%')).toBeVisible()
  expect(screen.getByText('120 / 1920')).toBeVisible()
  const calls = fetcher.mock.calls as unknown as [string, RequestInit][]
  const posts = calls.filter(([url]) => url === '/api/v1/simulations')
  expect(posts).toHaveLength(2)
  expect(posts[0][1].headers).toEqual(posts[1][1].headers)
  expect(JSON.parse(posts[0][1].body as string)).toMatchObject({ snapshot_id: baseline.id, closure_start: '2026-01-05T10:00:00+05:30' })
})

test('viewer opens unresolved saved run and sees rejection reasons without create controls', async () => {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => response(url.includes('/sessions?') ? {
    items: [{ id: 'session', starts_at: '2026-01-05T04:30:00Z', original_room_id: 'old', assigned_room_id: null, allocation_status: 'unresolved', reason_code: 'no_feasible_candidate', candidate_summary: { rejected_capacity: 1, rejected_room_busy: 1, rejected_closure: 1, feasible_count: 0 } }], total: 1, limit: 50, offset: 0
  } : { ...run, result: { ...run.result, impact: { affected_students: 40, unresolved_students: 40 } } })))
  render(<M3Workspace snapshot={null} actor={{ ...actor, role: 'viewer' }}/>)
  expect(screen.queryByText('Simulate closure')).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Saved simulation ID'), { target: { value: 'saved-run' } })
  fireEvent.click(screen.getByText('Open saved simulation'))
  expect(await screen.findByText(/No room found by this heuristic/)).toBeVisible()
  expect(screen.getByText('rejected capacity')).toBeVisible()
  expect(screen.getByText('Unassigned')).toBeVisible()
})

test('historical snapshot explains planning baseline requirement', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => response({ items: [] })))
  render(<M3Workspace snapshot={{ ...baseline, as_of: '2026-01-05T17:00:00+05:30' }} actor={actor}/>)
  expect(screen.queryByText('Simulate closure')).not.toBeInTheDocument()
  expect(screen.getByText(/cutoff 00:00/)).toBeVisible()
  await waitFor(() => expect(fetch).toHaveBeenCalled())
})
