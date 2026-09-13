import type { Room } from './api'

export type Vec3 = [number, number, number]
export type SpaceKind = 'classroom' | 'lab' | 'staff' | 'hod' | 'restroom' | 'stairs'
export type Space = { id: string; label: string; kind: SpaceKind; floor: number; department?: string; x: number; width: number; provisional: boolean }
export type Building = { id: string; label: string; position: Vec3; size: Vec3; detailed?: boolean; confidence: 'reference-derived' | 'provisional' }
export type RoomBinding = { spaceId: string; editionId: string; roomId: string }
export const IT_BUILDING = 'academic-it-ece'
export const geometry = { width: 84, depth: 15, floorHeight: 4, corridorDepth: 3.5, roomDepth: 10, wall: .22, facilityWidth: 6 }
// +X runs from girls to boys when looking from the garden (+Z) toward this block.
export const buildings: Building[] = [
  { id: IT_BUILDING, label: 'IT / ECE · Block 3', position: [-46, 0, -57], size: [geometry.width, geometry.floorHeight * 3, geometry.depth], detailed: true, confidence: 'reference-derived' },
  { id: 'civil', label: 'Civil block', position: [-46, 0, -79], size: [84, 12, 15], confidence: 'reference-derived' },
  { id: 'cse', label: 'CSE · Block 5', position: [46, 0, -57], size: [84, 12, 15], confidence: 'reference-derived' },
  { id: 'south-east', label: 'Academic block A', position: [46, 0, -79], size: [84, 12, 15], confidence: 'provisional' },
  { id: 'north-west', label: 'Academic block B', position: [-46, 0, 55], size: [84, 12, 15], confidence: 'provisional' },
  { id: 'north-west-outer', label: 'Academic block C', position: [-46, 0, 78], size: [84, 12, 15], confidence: 'provisional' },
  { id: 'mechanical', label: 'Mechanical · Block 6', position: [46, 0, 55], size: [84, 12, 15], confidence: 'reference-derived' },
  { id: 'north-east', label: 'Academic block D', position: [46, 0, 78], size: [84, 12, 15], confidence: 'provisional' },
  { id: 'hall', label: 'Large hall · unconfirmed', position: [117, 0, 15], size: [35, 10, 65], confidence: 'provisional' },
  { id: 'east-wing', label: 'East wing · unconfirmed', position: [-105, 0, -8], size: [13, 12, 74], confidence: 'provisional' },
  { id: 'courtyard-north', label: 'Courtyard complex · north', position: [-46, 0, 114], size: [84, 12, 14], confidence: 'provisional' },
  { id: 'courtyard-west', label: 'Courtyard complex · west', position: [-81, 0, 144], size: [14, 12, 48], confidence: 'provisional' },
  { id: 'courtyard-east', label: 'Courtyard complex · east', position: [-11, 0, 144], size: [14, 12, 48], confidence: 'provisional' },
  { id: 'courtyard-south', label: 'Courtyard complex · south', position: [-46, 0, 174], size: [84, 12, 14], confidence: 'provisional' },
]
export const floors = [{ level: 0, label: 'Ground · Labs' }, { level: 1, label: 'First · IT' }, { level: 2, label: 'Second · ECE' }, { level: 3, label: 'Terrace' }]
export const spaces: Space[] = [0, 1, 2].flatMap(floor => {
  const department = floor === 1 ? 'IT' : floor === 2 ? 'ECE' : undefined
  const roomSpan = geometry.width - 4 * geometry.facilityWidth
  const rooms: Space[] = floor === 0 ? [0, 1].map(i => ({ id: `it-ece-l0-room-${i + 1}`, label: `Lab ${i + 1}`, kind: 'lab', floor, x: -roomSpan / 4 + i * roomSpan / 2, width: roomSpan / 2, provisional: true })) :
    Array.from({ length: 7 }, (_, i) => ({ id: `it-ece-l${floor}-room-${i + 1}`, label: `${floor === 1 ? 'F' : 'S'}${i + 1}`, kind: i === 2 ? 'staff' : i === 3 ? 'hod' : 'classroom', floor, department, x: -roomSpan / 2 + (i + .5) * roomSpan / 7, width: roomSpan / 7, provisional: false }))
  return [...rooms, ...([-1, 1] as const).flatMap(side => [
    { id: `it-ece-l${floor}-${side < 0 ? 'girls' : 'boys'}`, label: `${side < 0 ? 'Girls’' : 'Boys’'} restroom`, kind: 'restroom' as const, floor, x: side * (geometry.width / 2 - geometry.facilityWidth / 2), width: geometry.facilityWidth, provisional: false },
    { id: `it-ece-l${floor}-stairs-${side < 0 ? 'left' : 'right'}`, label: `${side < 0 ? 'Left' : 'Right'} stairs`, kind: 'stairs' as const, floor, x: side * (geometry.width / 2 - geometry.facilityWidth * 1.5), width: geometry.facilityWidth, provisional: false },
  ])]
})
export const bindings: RoomBinding[] = []
export function linkedRoom(spaceId: string, editionId: string, rooms: Room[], links = bindings) {
  const binding = links.find(item => item.spaceId === spaceId && item.editionId === editionId)
  return binding ? rooms.find(room => room.id === binding.roomId) : undefined
}
export const kindLabels: Record<SpaceKind, string> = { classroom: 'Classroom', lab: 'Lab', staff: 'Staff room', hod: 'HOD room', restroom: 'Restroom', stairs: 'Stairs' }
export const spaceColors: Record<SpaceKind, string> = { classroom: '#bbd8cf', lab: '#afc9dc', staff: '#e6cca2', hod: '#dcb694', restroom: '#c6c5da', stairs: '#b7bdbb' }
