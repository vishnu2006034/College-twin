import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import CampusExplorer from './CampusExplorer'
import { buildings, floors, spaces, linkedRoom, IT_BUILDING, CSE_BUILDING, ECE_BUILDING, LAB_BUILDING, MBA_BUILDING, AIDS_BUILDING, FACILITIES_BUILDING, floorsFor } from './campus'

afterEach(cleanup)
test('hall is centered and opposite facilities building has bank and unconfirmed floor', () => {
  const hall = buildings.find(b => b.id === 'hall')!
  const facility = buildings.find(b => b.id === FACILITIES_BUILDING)!
  expect(hall.position[2]).toBe(0)
  expect(facility.position[2]).toBe(0)
  expect(hall.position[0]).toBeGreaterThan(0)
  expect(facility.position[0]).toBeLessThan(0)
  expect(facility.rotation).toBe(Math.PI / 2)
  render(<CampusExplorer editionId="a" rooms={[]}/>)
  fireEvent.click(screen.getByRole('button', { name: /Facilities \/ Bank building 3 floors/ }))
  fireEvent.click(screen.getByRole('button', { name: 'First · Bank' }))
  fireEvent.click(screen.getByRole('button', { name: 'Bank Bank' }))
  const panel = within(screen.getByRole('complementary', { name: 'Selected space information' }))
  expect(panel.getByRole('heading', { name: 'Bank' })).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Second · Unconfirmed' }))
  expect(screen.getByRole('status')).toHaveTextContent('Second-floor use and rooms are unconfirmed')
})
test('rear lab building preserves structure and has the confirmed floor allocation', () => {
  const rear = buildings.find(b => b.id === AIDS_BUILDING)!
  const front = buildings.find(b => b.id === LAB_BUILDING)!
  expect(rear.position[0]).toBe(front.position[0])
  expect(rear.position[2]).toBeGreaterThan(front.position[2])
  expect(rear.size).toEqual(front.size)
  expect(rear.rotation).toBe(front.rotation)
  const rooms = spaces.filter(s => s.buildingId === AIDS_BUILDING)
  for (const floor of [0, 1, 2]) {
    const labs = rooms.filter(s => s.floor === floor && s.kind === 'lab')
    expect(labs).toHaveLength(2)
    expect(labs.every(s => s.department === [undefined, 'Mechanical', 'AI & DS'][floor])).toBe(true)
  }
  render(<CampusExplorer editionId="a" rooms={[]}/>)
  fireEvent.click(screen.getByRole('button', { name: /AI & DS \/ Mechanical lab building 3 floors/ }))
  fireEvent.click(screen.getByRole('button', { name: 'Second · AI & DS' }))
  fireEvent.click(screen.getByRole('button', { name: 'AI & DS Lab 1 Lab' }))
  const panel = within(screen.getByRole('complementary', { name: 'Selected space information' }))
  expect(panel.getByText('AI & DS / Mechanical lab building')).toBeVisible()
  expect(panel.getByText('AI & DS', { exact: true })).toBeVisible()
  expect(panel.getByText('Provisional')).toBeVisible()
})
test('MBA building sits behind ECE and leaves second-floor room uses unconfirmed', () => {
  const mba = buildings.find(b => b.id === MBA_BUILDING)!
  const ece = buildings.find(b => b.id === ECE_BUILDING)!
  expect(mba.position[0]).toBe(ece.position[0])
  expect(mba.position[2]).toBeGreaterThan(ece.position[2])
  expect(mba.rotation).toBe(ece.rotation)
  expect(mba.size).toEqual(ece.size)
  const rooms = spaces.filter(s => s.buildingId === MBA_BUILDING)
  expect(rooms.filter(s => s.floor === 0).every(s => s.department === 'MBA')).toBe(true)
  expect(rooms.filter(s => s.floor === 1 && s.kind === 'lab')).toHaveLength(2)
  expect(rooms.filter(s => s.floor === 2).every(s => ['stairs', 'restroom'].includes(s.kind) && !s.department)).toBe(true)
  render(<CampusExplorer editionId="a" rooms={[]}/>)
  fireEvent.click(screen.getByRole('button', { name: /MBA \/ Lab building 3 floors/ }))
  fireEvent.click(screen.getByRole('button', { name: 'Second · Unconfirmed' }))
  expect(screen.getByRole('status')).toHaveTextContent('Second-floor use and rooms are unconfirmed')
  expect(screen.queryByRole('button', { name: 'S1 Classroom' })).not.toBeInTheDocument()
})
test('view and label controls preserve selected room and reset restores perspective', () => {
  render(<CampusExplorer editionId="a" rooms={[]}/>)
  fireEvent.click(screen.getByRole('button', { name: 'Explore IT floor →' }))
  fireEvent.click(screen.getByRole('button', { name: 'F3 Staff room' }))
  fireEvent.click(screen.getByRole('button', { name: 'Top view' }))
  expect(screen.getByRole('button', { name: 'Top view' })).toHaveAttribute('aria-pressed', 'true')
  fireEvent.click(screen.getByRole('button', { name: 'Labels on' }))
  expect(screen.getByRole('button', { name: 'Labels off' })).toHaveAttribute('aria-pressed', 'false')
  const panel = within(screen.getByRole('complementary', { name: 'Selected space information' }))
  expect(panel.getByRole('heading', { name: 'F3' })).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Low view' }))
  expect(panel.getByRole('heading', { name: 'F3' })).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Reset view' }))
  expect(screen.getByRole('button', { name: 'Perspective' })).toHaveAttribute('aria-pressed', 'true')
})
test('opposite buildings face the garden and lab floors have their own departments', () => {
  for (const [frontId, oppositeId] of [[IT_BUILDING, ECE_BUILDING], [CSE_BUILDING, LAB_BUILDING]]) {
    const front = buildings.find(b => b.id === frontId)!
    const opposite = buildings.find(b => b.id === oppositeId)!
    expect(opposite.position[0]).toBe(front.position[0])
    expect(opposite.position[2]).toBeGreaterThan(0)
    expect(front.position[2]).toBeLessThan(0)
    expect(opposite.rotation).toBe(Math.PI)
  }
  for (const floor of [0, 1, 2]) {
    const restrooms = spaces.filter(s => s.buildingId === ECE_BUILDING && s.floor === floor && s.kind === 'restroom').sort((a, b) => a.x - b.x)
    expect(restrooms.map(s => s.label)).toEqual(['Boys’ restroom', 'Girls’ restroom'])
    const labs = spaces.filter(s => s.buildingId === LAB_BUILDING && s.floor === floor && s.kind === 'lab').sort((a, b) => a.x - b.x)
    expect(labs.map(s => s.department)).toEqual([['Mechanical', 'Mechanical'], ['CSE', 'MCA'], ['IT', 'AI & DS']][floor])
    expect(labs.every(s => s.provisional)).toBe(true)
  }
  expect(spaces.some(s => s.buildingId === CSE_BUILDING && s.floor === 0 && s.kind === 'lab')).toBe(false)
  expect(spaces.filter(s => s.buildingId === CSE_BUILDING && s.floor === 0 && s.kind === 'classroom')).toHaveLength(5)
})

test('lab building navigation shows lab spaces instead of classroom templates', () => {
  render(<CampusExplorer editionId="a" rooms={[]}/>)
  fireEvent.click(screen.getByRole('button', { name: /Lab building · Block 6 3 floors/ }))
  fireEvent.click(screen.getByRole('button', { name: 'Second · IT / AI & DS labs' }))
  fireEvent.click(screen.getByRole('button', { name: 'AI & DS lab Lab' }))
  const panel = within(screen.getByRole('complementary', { name: 'Selected space information' }))
  expect(panel.getByRole('heading', { name: 'AI & DS lab' })).toBeVisible()
  expect(panel.getByText('Lab building · Block 6')).toBeVisible()
  expect(panel.getByText('Provisional')).toBeVisible()
  expect(screen.queryByRole('button', { name: 'S4 HOD room' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /ECE building 3 floors/ }))
  fireEvent.click(screen.getByRole('button', { name: 'First · ECE' }))
  expect(screen.getByText('← Boys’ side · numbering begins here')).toBeVisible()
})
test('CSE is right of IT and reverses only restroom positions on every floor', () => {
  const cse = buildings.find(b => b.id === CSE_BUILDING)!
  const it = buildings.find(b => b.id === IT_BUILDING)!
  expect(cse.position[0]).toBeGreaterThan(it.position[0])
  expect(cse.position[2]).toBe(it.position[2])
  expect(cse.detailed).toBe(true)
  expect(floorsFor(CSE_BUILDING).map(f => f.label)).toEqual(['Ground · CSE 2nd year', 'First · CSE 3rd year', 'Second · MCA', 'Terrace'])
  for (const floor of [0, 1, 2]) {
    const row = spaces.filter(s => s.buildingId === CSE_BUILDING && s.floor === floor).sort((a, b) => a.x - b.x)
    expect(row[0].label).toBe('Boys’ restroom')
    expect(row[1].label).toBe('Left stairs')
    expect(row.at(-2)?.label).toBe('Right stairs')
    expect(row.at(-1)?.label).toBe('Girls’ restroom')
    expect(row.every(s => s.department === (floor === 2 ? 'MCA' : 'CSE'))).toBe(true)
    for (const room of row.filter(s => s.kind !== 'restroom' && floor > 0)) {
      const original = spaces.find(s => s.id === room.id.replace('cse-', 'it-ece-'))!
      expect([room.x, room.kind, room.label, room.width]).toEqual([original.x, original.kind, original.label, original.width])
    }
  }
})

test('CSE search, floor selection and inspector stay isolated from IT rooms', () => {
  render(<CampusExplorer editionId="a" rooms={[]}/>)
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'F3' } })
  fireEvent.click(screen.getByRole('button', { name: /F3 · Staff room.*CSE · Block 5/ }))
  const panel = within(screen.getByRole('complementary', { name: 'Selected space information' }))
  expect(panel.getByText('CSE · Block 5')).toBeVisible()
  expect(panel.getByText('First · CSE 3rd year')).toBeVisible()
  expect(panel.getByText('CSE', { exact: true })).toBeVisible()
  const floorView = within(screen.getByRole('region', { name: 'Building floors' }))
  expect(floorView.getAllByRole('button', { name: 'F3 Staff room' })).toHaveLength(1)
  expect(floorView.getByText('← Boys’ side · numbering begins here')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Second · MCA' }))
  fireEvent.click(screen.getByRole('button', { name: 'S4 HOD room' }))
  expect(panel.getByRole('heading', { name: 'S4' })).toBeVisible()
  expect(panel.getByText('No linked dataset record')).toBeVisible()
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: '' } })
  fireEvent.click(screen.getByRole('button', { name: /IT \/ ECE · Block 3 3 floors/ }))
  fireEvent.click(screen.getByRole('button', { name: 'First · IT' }))
  expect(floorView.getByText('← Girls’ side · numbering begins here')).toBeVisible()
  expect(panel.queryByRole('heading', { name: 'S4' })).not.toBeInTheDocument()
})

test('confirmed layout has three enclosed floors, a terrace, and correct room functions and direction', () => {
  expect(floors.map(f => f.level)).toEqual([0, 1, 2, 3])
  expect(new Set([...buildings, ...spaces].map(s => s.id)).size).toBe(buildings.length + spaces.length)
  expect(spaces.filter(s => s.buildingId === IT_BUILDING && s.kind === 'lab')).toHaveLength(2)
  expect(spaces.filter(s => s.kind === 'lab').every(s => s.provisional)).toBe(true)
  for (const floor of [0, 1, 2]) {
    const row = spaces.filter(s => s.buildingId === IT_BUILDING && s.floor === floor).sort((a, b) => a.x - b.x)
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
  fireEvent.click(screen.getByRole('button', { name: /F4 · HOD room.*IT \/ ECE/ }))
  const panel = within(screen.getByRole('complementary', { name: 'Selected space information' }))
  expect(panel.getByRole('heading', { name: 'F4' })).toBeVisible()
  rerender(<CampusExplorer editionId="b" rooms={[{ id: 'synthetic', code: 'F4', kind: 'classroom', capacity: 99, lab_type: null }]}/>)
  expect(panel.getByText('No linked dataset record')).toBeVisible()
  expect(panel.queryByText(/99/)).not.toBeInTheDocument()
  expect(buildings.find(b => b.id === IT_BUILDING)?.detailed).toBe(true)
})
