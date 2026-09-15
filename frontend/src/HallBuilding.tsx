import { Html } from '@react-three/drei'
import { Blocks, type Block } from './SceneArchitecture'
import { hallSpaces, spaceColors, type Space } from './campus'

function HallRoom({ room, active, labels, onSpace }: { room: Space; active: boolean; labels: boolean; onSpace: (id: string) => void }) {
  const w = room.width, d = room.depth!, wall = '#e9dfcd'
  const items: Block[] = [{ at: [0, .12, 0], size: [w, .24, d], color: active ? '#efa650' : spaceColors[room.kind] }]
  if (room.kind !== 'passage') {
    // Every room opens toward the circulation route. Auditorium opens on its right side.
    const eastDoor = room.wing === 'left' || room.kind === 'auditorium' || (room.wing === 'front' && room.x < 0)
    const westDoor = room.wing === 'right' || (room.wing === 'front' && room.x > 0)
    for (const side of [-1, 1]) {
      const door = side === 1 ? eastDoor : westDoor
      if (door && room.kind === 'auditorium') items.push({ at: [side * w / 2, 1.6, 1], size: [.18, 3, d - 2], color: wall })
      else if (door) for (const sign of [-1, 1]) items.push({ at: [side * w / 2, 1.6, sign * (d / 4 + .6)], size: [.18, 3, d / 2 - 1.2], color: wall })
      else items.push({ at: [side * w / 2, 1.6, 0], size: [.18, 3, d], color: wall })
    }
    items.push({ at: [0, 1.6, -d / 2], size: [w, 3, .18], color: wall })
    if (room.wing === 'rear' || room.kind === 'stairs') for (const side of [-1, 1]) items.push({ at: [side * (w / 4 + .6), 1.6, d / 2], size: [w / 2 - 1.2, 3, .18], color: wall })
    else items.push({ at: [0, 1.6, d / 2], size: [w, 3, .18], color: wall })
  }
  if (room.kind === 'auditorium') {
    items.push({ at: [-14, .55, 0], size: [6, 1, 8], color: '#776452' })
    for (let row = 0; row < 7; row++) for (const z of [-3, -1.7, 1.7, 3]) items.push({ at: [-8 + row * 3.5, .75, z], size: [1.2, 1.2, .9], color: '#775a56' })
  }
  if (room.kind === 'stairs') for (let i = 0; i < 12; i++) items.push({ at: [-4 + i * .7, .25 + i * .19, 0], size: [.7, .3 + i * .38, 2.8], color: '#a6aaa4' })
  if (room.kind === 'library') for (let i = 0; i < 5; i++) items.push({ at: [1, 1.3, -6 + i * 3], size: [6, 2.4, .65], color: '#8a7257' })
  return <group position={[room.x, room.floor * 5, room.z!]} onClick={e => { e.stopPropagation(); onSpace(room.id) }}>
    <Blocks items={items}/>
    {labels && <Html position={[0, 3.5, 0]} center zIndexRange={[20, 0]}><button className={`space-tag ${active ? 'active' : ''}`} onClick={e => { e.stopPropagation(); onSpace(room.id) }}>{room.label}</button></Html>}
  </group>
}

export default function HallBuilding({ floor, spaceId, labels, onSpace }: { floor: number | null; spaceId: string | null; labels: boolean; onSpace: (id: string) => void }) {
  const structure: Block[] = []
  // Logical plan is 65 x 65; Z is compressed to the reference-derived 35 m footprint below.
  const wings = [{ x: 0, z: 14.5, w: 44, d: 28 }, { x: 0, z: -29, w: 64, d: 7 }, { x: -27, z: 1.5, w: 10, d: 54 }, { x: 27, z: 1.5, w: 10, d: 54 }]
  for (let level = 0; level <= Math.min(floor ?? 1, 1); level++) {
    for (const wing of wings) structure.push({ at: [wing.x, level * 5, wing.z], size: [wing.w, .22, wing.d], color: '#d2c4ac' })
    structure.push({ at: [0, level * 5, 30.5], size: [64, .24, 4], color: '#d8ceb9' })
    for (const x of [-20.5, 20.5]) structure.push({ at: [x, level * 5 + .03, 1.5], size: [3, .24, 54], color: '#d8ceb9' })
    for (const z of [-24, -1]) structure.push({ at: [0, level * 5 + .03, z], size: [44, .24, 3], color: '#d8ceb9' })
    if (level > 0) for (const x of [-19, 19]) structure.push({ at: [x, level * 5 + .65, -12.5], size: [.15, 1.1, 20], color: '#b6b4a4' })
  }
  structure.push({ at: [0, 4.45, 28.5], size: [6, 1.1, .35], color: '#dfd1b5' })
  if (floor === null || floor === 2) for (const wing of wings) {
    structure.push({ at: [wing.x, 10, wing.z], size: [wing.w + .4, .35, wing.d + .4], color: '#a99e89' })
    for (const side of [-1, 1]) structure.push({ at: [wing.x, 10.55, wing.z + side * wing.d / 2], size: [wing.w, .8, .2], color: '#d9ceb9' })
  }

  return <group scale={[1, 1, 35 / 65]}><Blocks items={structure}/>{hallSpaces.filter(s => s.floor <= Math.min(floor ?? 1, 1)).map(room => <HallRoom key={room.id} room={room} active={room.id === spaceId} labels={labels && (room.floor === floor || (floor === 2 && room.id === 'hall-s-terrace-stairs'))} onSpace={onSpace}/>)}</group>
}
