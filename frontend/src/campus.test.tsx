import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import CampusExplorer from './CampusExplorer'
import { buildings, floors, spaces, linkedRoom, IT_BUILDING } from './campus'

afterEach(cleanup)
test('confirmed layout has three enclosed floors, a terrace, and correct room functions and direction', () => {
  expect(floors.map(f => f.level)).toEqual([0, 1, 2, 3])
  expect(new Set([...buildings, ...spaces].map(s => s.id)).size).toBe(buildings.length + spaces.length)
  expect(spaces.filter(s => s.kind === 'lab')).toHaveLength(2)
  expect(spaces.filter(s => s.kind === 'lab').every(s => s.provisional)).toBe(true)
  for (const floor of [0, 1, 2]) {
    const row = spaces.filter(s => s.floor === floor).sort((a, b) => a.x - b.x)
    expect(row[0].label).toBe('Girls’ restroom')
    expect(row[1].label).toBe('Left stairs')
    expect(row.at(-2)?.label).toBe('Right stairs')
    expect(row.at(-1)?.label).toBe('Boys’ restroom')
    if (floor > 0) {
      const prefix = floor === 1 ? 'F' : 'S'
      const rooms = row.filter(s => ['classroom', 'staff', 'hod'].includes(s.kind))
      expect(rooms.map(s => s.label)).toEqual([1, 2, 3, 4, 5, 6, 7].map(n => `${prefix}${n}`))
      expect(rooms.filter(s => s.kind === 'classroom')).toHaveLength(5)
      expect(rooms[2].kind).toBe('staff')
      expect(rooms[3].kind).toBe('hod')
    }
  }
})
test('bindings never infer matches and never cross dataset editions', () => {
  const rooms = [{ id: 'r1', code: 'F1', capacity: 60, kind: 'classroom' as const, lab_type: null }]
  expect(linkedRoom('physical', 'a', rooms)).toBeUndefined()
  const links = [{ spaceId: 'physical', editionId: 'a', roomId: 'r1' }]
  expect(linkedRoom('physical', 'a', rooms, links)?.capacity).toBe(60)
  expect(linkedRoom('physical', 'b', rooms, links)).toBeUndefined()
  expect(linkedRoom('physical', 'a', [], links)).toBeUndefined()
})
test('directory fallback supports building, floor, room, terrace, and reset navigation', () => {
  render(<CampusExplorer editionId="a" rooms={[]}/>)
  expect(screen.getByText('Explore without 3D')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: /IT \/ ECE · Block 3 3 floors/ }))
  fireEvent.click(screen.getByRole('button', { name: 'First · IT' }))
  fireEvent.click(screen.getByRole('button', { name: 'F3 Staff room' }))
  const panel = within(screen.getByRole('complementary', { name: 'Selected space information' }))
  expect(panel.getByRole('heading', { name: 'F3' })).toBeVisible()
  expect(panel.getByText('Staff room')).toBeVisible()
  expect(panel.getByText('No linked dataset record')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Second · ECE' }))
  fireEvent.click(screen.getByRole('button', { name: 'S4 HOD room' }))
  expect(panel.getByRole('heading', { name: 'S4' })).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Terrace' }))
  expect(screen.queryByRole('button', { name: 'S4 HOD room' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Reset view' }))
  expect(screen.queryByRole('region', { name: 'Building floors' })).not.toBeInTheDocument()
  expect(panel.getByText('A place for every insight.')).toBeVisible()
})
test('search finds a room directly; dataset changes keep physical selection without invented metrics', () => {
  const { rerender } = render(<CampusExplorer editionId="a" rooms={[]}/>)
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'F4' } })
  fireEvent.click(screen.getByRole('button', { name: /F4 · HOD room/ }))
  const panel = within(screen.getByRole('complementary', { name: 'Selected space information' }))
  expect(panel.getByRole('heading', { name: 'F4' })).toBeVisible()
  rerender(<CampusExplorer editionId="b" rooms={[{ id: 'synthetic', code: 'F4', kind: 'classroom', capacity: 99, lab_type: null }]}/>)
  expect(panel.getByText('No linked dataset record')).toBeVisible()
  expect(panel.queryByText(/99/)).not.toBeInTheDocument()
  expect(buildings.find(b => b.id === IT_BUILDING)?.detailed).toBe(true)
})
