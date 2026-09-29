import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import M3Workspace from './M3Workspace'
import CampusExplorer from './CampusExplorer'
import M2Workspace from './M2Workspace'
import { spaces, type RoomBinding } from './campus'
import { simulationHighlights, type SimulationOverlay } from './simulation-map'
import { mockSnapshot } from './snapshot.mock'

const actor = { id: 'planner', username: 'planner', role: 'planner' as const }
const baseline = { ...mockSnapshot, as_of: mockSnapshot.window_start, anomalies: [] }
const source = spaces.find(s => s.buildingId === 'academic-it-ece' && s.label === 'F1')!
const target = spaces.find(s => s.buildingId === 'academic-it-ece' && s.label === 'F2')!
const room = { id: 'room-source', code: 'SOURCE', kind: 'classroom' as const, capacity: 40, lab_type: null }
const destination = { ...room, id: 'room-target', code: 'TARGET' }
const links: RoomBinding[] = [{ spaceId: source.id, roomId: room.id, editionId: baseline.edition_id }, { spaceId: target.id, roomId: destination.id, editionId: baseline.edition_id }]
const overlay: SimulationOverlay = { runId: 'run', editionId: baseline.edition_id, closedRoomId: room.id, destinationRoomIds: [destination.id] }
const run = { id: 'run', edition_id: baseline.edition_id, request: { room_id: room.id }, snapshot_id: baseline.id, result: {
  stages: {}, recommendation: { message: 'One move' }, impact: { affected_students: 40, unresolved_students: 0 }, observed_attendance: { label: 'Unchanged' }
} }
const page = { items: [{ id: 's1', starts_at: baseline.window_start, original_room_id: room.id, assigned_room_id: destination.id, allocation_status: 'reassigned' }], total: 1, limit: 200, offset: 0 }
const response = (data: unknown) => ({ ok: true, status: 200, json: async () => data })
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test('only explicit same-edition links can produce highlights; absent links and changed revisions remove them', () => {
  expect(simulationHighlights(overlay, baseline.edition_id, links)).toEqual({ [source.id]: 'closed', [target.id]: 'destination' })
  expect(simulationHighlights(overlay, 'another-edition', links)).toEqual({})
  expect(simulationHighlights(overlay, baseline.edition_id, [])).toEqual({})
  expect(simulationHighlights(overlay, baseline.edition_id, [{ ...links[0], editionId: 'another-edition' }])).toEqual({})
  expect(simulationHighlights(overlay, baseline.edition_id, [{ ...links[0], spaceId: 'unknown-geometry' }])).toEqual({})
  expect(simulationHighlights(overlay, baseline.edition_id, [links[0]])).toEqual({ [source.id]: 'closed' })
})

test('reviewed campus selection submits its exact saved room and never writes mappings', async () => {
  const fetcher = vi.fn(async (url: string) => response(url.endsWith('/rooms') ? { items: [room, destination] } : url.includes('/sessions?') ? page : run))
  vi.stubGlobal('fetch', fetcher)
  render(<M3Workspace snapshot={baseline} actor={actor} links={links} selectedSpaceId={source.id}/>)
  await screen.findByRole('button', { name: /Use selected campus room/ })
  fireEvent.change(screen.getByLabelText('Reviewed campus room'), { target: { value: target.id } })
  expect(screen.getByLabelText('Room to close')).toHaveValue(destination.id)
  fireEvent.click(screen.getByRole('button', { name: /Use selected campus room/ }))
  expect(screen.getByLabelText('Room to close')).toHaveValue(room.id)
  fireEvent.change(screen.getByLabelText('Closure start (IST)'), { target: { value: '2026-01-05T10:00' } })
  fireEvent.change(screen.getByLabelText('Closure end (IST)'), { target: { value: '2026-01-05T11:00' } })
  fireEvent.click(screen.getByText('Simulate closure'))
  await screen.findByText('One move')
  const calls = fetcher.mock.calls as unknown as [string, RequestInit][]
  expect(JSON.parse(calls.find(([url]) => url.endsWith('/simulations'))![1].body as string).room_id).toBe(room.id)
  expect(calls.some(([url]) => url.includes('room-mappings'))).toBe(false)
})

test('mapped rooms absent from the saved inventory stay unavailable and unlinked', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => response({ items: [destination] })))
  render(<M3Workspace snapshot={baseline} actor={actor} links={[links[0]]} selectedSpaceId={source.id}/>)
  await waitFor(() => expect(screen.getByLabelText('Room to close')).toHaveValue(destination.id))
  expect(screen.getByLabelText('Reviewed campus room')).toBeDisabled()
  expect(screen.queryByRole('button', { name: /Use selected campus room/ })).not.toBeInTheDocument()
  expect(screen.getByText(/selected campus space has no reviewed link/)).toBeVisible()
})

test('highlights collect every affected page, exclude unresolved assignments, and clear on unmount', async () => {
  const onScenario = vi.fn()
  vi.stubGlobal('fetch', vi.fn(async (url: string) => response(url.includes('limit=200') ? (
    url.includes('offset=1') ? { ...page, items: [{ ...page.items[0], assigned_room_id: destination.id }], total: 2, offset: 1 } :
      { ...page, items: [{ ...page.items[0], assigned_room_id: null, allocation_status: 'unresolved' }], total: 2 }
  ) : url.includes('/sessions?') ? page : run)))
  const view = render(<M3Workspace snapshot={null} actor={{ ...actor, role: 'viewer' }} onScenario={onScenario}/>)
  fireEvent.change(screen.getByLabelText('Saved simulation ID'), { target: { value: 'run' } })
  fireEvent.click(screen.getByText('Open saved simulation'))
  await waitFor(() => expect(onScenario).toHaveBeenCalledWith(overlay))
  view.unmount()
  expect(onScenario).toHaveBeenLastCalledWith(null)
})

test('failed highlight page never publishes a misleading partial overlay', async () => {
  const onScenario = vi.fn()
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url.includes('limit=200') && url.includes('offset=1')) throw new Error('Network failure')
    return response(url.includes('limit=200') ? { ...page, total: 2 } : url.includes('/sessions?') ? page : run)
  }))
  render(<M3Workspace snapshot={null} actor={actor} onScenario={onScenario}/>)
  fireEvent.change(screen.getByLabelText('Saved simulation ID'), { target: { value: 'run' } })
  fireEvent.click(screen.getByText('Open saved simulation'))
  expect(await screen.findByText(/Campus highlights unavailable/)).toBeVisible()
  expect(onScenario.mock.calls.every(([value]) => value === null)).toBe(true)
})

test('campus highlight navigation opens the right floor and marks both rooms independently of selection', () => {
  const view = render(<CampusExplorer editionId={baseline.edition_id} rooms={[room, destination]} links={links} highlights={simulationHighlights(overlay, baseline.edition_id, links)}/>)
  fireEvent.click(screen.getByRole('button', { name: /^Reassignment destination: F2/ }))
  expect(screen.getByRole('button', { name: 'F2 Classroom Reassignment destination' })).toHaveAttribute('aria-pressed', 'true')
  expect(screen.getByRole('button', { name: 'F1 Classroom Closed room' })).toHaveClass('simulation-closed')
  expect(within(screen.getByRole('complementary', { name: 'Selected space information' })).getByText('Reassignment destination in saved simulation')).toBeVisible()
  view.rerender(<CampusExplorer editionId={baseline.edition_id} rooms={[room, destination]} links={links} highlights={{}}/>)
  expect(screen.queryByRole('region', { name: 'Simulation campus highlights' })).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'F2 Classroom' })).not.toHaveClass('simulation-destination')
})

test('workspace labels mapping revision and removes existing highlights when mappings are reloaded empty', async () => {
  let revision = 1
  const edition = { id: baseline.edition_id, seed: 42, generator_version: '1', logical_content_hash: 'b', frozen_at: '', config: { start_date: '2026-01-05', weeks: 1, students_per_section: 2 } }
  vi.stubGlobal('fetch', vi.fn(async (url: string) => response(url.includes('/room-mappings/') ? {
    edition_id: edition.id, version: revision, bindings: revision === 1 ? links.map(l => ({ space_id: l.spaceId, room_id: l.roomId })) : []
  } : url.includes('/sessions?') ? page : run)))
  render(<M2Workspace edition={edition} actor={{ ...actor, role: 'viewer' }} rooms={[room, destination]}/>)
  fireEvent.change(screen.getByLabelText('Saved simulation ID'), { target: { value: 'run' } })
  fireEvent.click(screen.getByText('Open saved simulation'))
  await screen.findByText(/current reviewed mapping revision 1/)
  expect(screen.getByRole('region', { name: 'Simulation campus highlights' })).toBeVisible()
  revision = 2
  fireEvent.click(screen.getByText('Reload mappings'))
  await screen.findByText(/current reviewed mapping revision 2/)
  expect(screen.queryByRole('region', { name: 'Simulation campus highlights' })).not.toBeInTheDocument()
  expect(screen.getByText('One move')).toBeVisible()
})
