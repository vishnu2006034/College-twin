import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import RoomMappingReview, { emptyMapping } from './RoomMappingReview'
import M2Workspace from './M2Workspace'
import RoomSnapshotPanel from './RoomSnapshotPanel'
import { mockSnapshot } from './snapshot.mock'
import { spaces } from './campus'

const actor = { id: 'planner', username: 'planner', role: 'planner' as const }
const room = { id: 'room-a', code: 'ROOM-A', kind: 'classroom' as const, capacity: 30, lab_type: null }
const space = spaces.find(s => s.buildingId === 'academic-it-ece' && s.label === 'F1')!
const edition = { id: mockSnapshot.edition_id, seed: 42, generator_version: '1', logical_content_hash: 'b', frozen_at: '', config: { start_date: '2026-01-05', weeks: 1, students_per_section: 2 } }
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test('review starts empty and requires explicit selections, acknowledgement and a note', async () => {
  const saved = vi.fn()
  const fetcher = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ ...emptyMapping(edition.id), version: 1, bindings: [{ space_id: space.id, room_id: room.id }] }) })
  vi.stubGlobal('fetch', fetcher)
  render(<RoomMappingReview editionId={edition.id} actor={actor} rooms={[room]} mapping={emptyMapping(edition.id)} onSaved={saved}/>)
  fireEvent.click(screen.getByText(/Review campus room mappings/))
  expect(screen.getByText(/All mappings remain unconfirmed/)).toBeVisible()
  fireEvent.change(screen.getByLabelText('Physical teaching space'), { target: { value: space.id } })
  fireEvent.change(screen.getByLabelText('Synthetic room'), { target: { value: room.id } })
  fireEvent.click(screen.getByText('Add to review'))
  expect(fetcher).not.toHaveBeenCalled()
  expect(screen.getByText('Approve and save mappings')).toBeDisabled()
  fireEvent.change(screen.getByLabelText('Review note'), { target: { value: 'Reviewed synthetic demo link' } })
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByText('Approve and save mappings'))
  await waitFor(() => expect(saved).toHaveBeenCalled())
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ expected_version: 0, bindings: [{ space_id: space.id, room_id: room.id }], review_note: 'Reviewed synthetic demo link' })
})

test('viewer can inspect links but cannot edit or approve', () => {
  render(<RoomMappingReview editionId={edition.id} actor={{ ...actor, role: 'viewer' }} rooms={[room]} mapping={emptyMapping(edition.id)} onSaved={vi.fn()}/>)
  fireEvent.click(screen.getByText(/Review campus room mappings/))
  expect(screen.queryByText('Approve and save mappings')).not.toBeInTheDocument()
  expect(screen.queryByLabelText('Synthetic room')).not.toBeInTheDocument()
})

test('mapped selection shares snapshot identity and resets on a different edition', async () => {
  const data = { ...mockSnapshot, snapshot_id: mockSnapshot.id, room }
  const fetcher = vi.fn().mockImplementation((url: string) => Promise.resolve({ ok: true, status: 200, json: async () =>
    url.includes('/room-mappings/') ? { ...emptyMapping(url.endsWith(edition.id) ? edition.id : 'edition-b'), version: 1, bindings: url.endsWith(edition.id) ? [{ space_id: space.id, room_id: room.id }] : [] } :
      url.endsWith('/rooms') ? { items: [room] } : url.includes('/sessions?') ? { items: [], total: 0, limit: 10, offset: 0 } : url.includes('/rooms/') ? data : mockSnapshot,
  }))
  vi.stubGlobal('fetch', fetcher)
  const view = render(<M2Workspace key={edition.id} edition={edition} actor={actor} rooms={[room]}/>)
  await screen.findByText(/Review campus room mappings \(1 approved\)/)
  fireEvent.click(screen.getByText('Create dated snapshot'))
  await screen.findByText('9.4%')
  fireEvent.click(screen.getByRole('button', { name: 'Explore IT floor →' }))
  fireEvent.click(screen.getByRole('button', { name: 'F1 Classroom' }))
  expect(await screen.findByRole('region', { name: 'Selected room snapshot' })).toBeVisible()
  expect(await screen.findByText(/No sessions for this room/)).toBeVisible()
  expect(fetcher.mock.calls.some(([url]) => url === `/api/v1/snapshots/${mockSnapshot.id}/rooms/${room.id}`)).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: 'F2 Classroom' }))
  expect(screen.queryByRole('region', { name: 'Selected room snapshot' })).not.toBeInTheDocument()
  expect(screen.getByText('No linked dataset record')).toBeVisible()
  view.rerender(<M2Workspace key="edition-b" edition={{ ...edition, id: 'edition-b' }} actor={actor} rooms={[]}/>)
  await screen.findByText(/Review campus room mappings \(0 approved\)/)
  expect(screen.queryByText('9.4%')).not.toBeInTheDocument()
})

test('room timetable consumes subsequent pages and exposes failures', async () => {
  const fetcher = vi.fn().mockImplementation((url: string) => Promise.resolve({ ok: true, status: 200, json: async () =>
    url.includes('/rooms/') ? { ...mockSnapshot, snapshot_id: mockSnapshot.id, room } :
      { items: Array.from({ length: url.includes('offset=10') ? 1 : 10 }, (_, i) => ({ id: `session-${url.includes('offset=10') ? 10 : i}`, room_id: room.id, faculty_id: 'f', section_id: 's', starts_at: mockSnapshot.window_start, ends_at: mockSnapshot.as_of, status: 'held' })), total: 11, limit: 10, offset: url.includes('offset=10') ? 10 : 0 },
  }))
  vi.stubGlobal('fetch', fetcher)
  render(<RoomSnapshotPanel snapshot={mockSnapshot} room={room} mappingVersion={1}/>)
  fireEvent.click(await screen.findByText('Next sessions'))
  expect(await screen.findByText('Session session-10')).toBeVisible()
  expect(screen.queryByText('Session session-0')).not.toBeInTheDocument()
  const panel = within(screen.getByRole('region', { name: 'Selected room snapshot' }))
  expect(panel.getByText('Next sessions')).toBeDisabled()
})
