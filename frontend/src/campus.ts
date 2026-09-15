import type { Room } from './api'

export type Vec3 = [number, number, number]
export type SpaceKind = 'classroom' | 'lab' | 'staff' | 'hod' | 'restroom' | 'stairs' | 'facility' | 'bank' | 'auditorium' | 'chamber' | 'library' | 'principal' | 'exam' | 'passage'
export type Space = { id: string; buildingId: string; label: string; kind: SpaceKind; floor: number; department?: string; x: number; width: number; provisional: boolean; z?: number; depth?: number; wing?: 'front' | 'left' | 'right' | 'rear'; note?: string }
export type Building = { id: string; label: string; position: Vec3; size: Vec3; rotation?: number; detailed?: boolean; confidence: 'reference-derived' | 'provisional' }
export type RoomBinding = { spaceId: string; editionId: string; roomId: string }
export const IT_BUILDING = 'academic-it-ece'
export const CSE_BUILDING = 'cse'
export const ECE_BUILDING = 'north-west'
export const LAB_BUILDING = 'mechanical'
export const MBA_BUILDING = 'north-west-outer'
export const AIDS_BUILDING = 'north-east'
export const FACILITIES_BUILDING = 'east-wing'
export const HALL_BUILDING = 'hall'
export const geometry = { width: 84, depth: 15, floorHeight: 4, corridorDepth: 3.5, roomDepth: 10, wall: .22, facilityWidth: 6 }
// +X runs left to right when looking from the garden (+Z). CSE reverses restrooms only.
export const buildings: Building[] = [
  { id: IT_BUILDING, label: 'IT / ECE · Block 3', position: [-46, 0, -57], size: [geometry.width, geometry.floorHeight * 3, geometry.depth], detailed: true, confidence: 'reference-derived' },
  { id: 'civil', label: 'Civil block', position: [-46, 0, -79], size: [84, 12, 15], confidence: 'reference-derived' },
  { id: CSE_BUILDING, label: 'CSE · Block 5', position: [46, 0, -57], size: [geometry.width, geometry.floorHeight * 3, geometry.depth], detailed: true, confidence: 'reference-derived' },
  { id: 'south-east', label: 'Academic block A', position: [46, 0, -79], size: [84, 12, 15], confidence: 'provisional' },
  { id: ECE_BUILDING, label: 'ECE building', position: [-46, 0, 55], size: [geometry.width, geometry.floorHeight * 3, geometry.depth], rotation: Math.PI, detailed: true, confidence: 'reference-derived' },
  { id: MBA_BUILDING, label: 'MBA / Lab building', position: [-46, 0, 78], size: [geometry.width, geometry.floorHeight * 3, geometry.depth], rotation: Math.PI, detailed: true, confidence: 'reference-derived' },
  { id: LAB_BUILDING, label: 'Lab building · Block 6', position: [46, 0, 55], size: [geometry.width, geometry.floorHeight * 3, geometry.depth], rotation: Math.PI, detailed: true, confidence: 'reference-derived' },
  { id: AIDS_BUILDING, label: 'AI & DS / Mechanical lab building', position: [46, 0, 78], size: [geometry.width, geometry.floorHeight * 3, geometry.depth], rotation: Math.PI, detailed: true, confidence: 'reference-derived' },
  { id: HALL_BUILDING, label: 'Central hall', position: [117, 0, 0], size: [65, 10, 35], rotation: -Math.PI / 2, detailed: true, confidence: 'reference-derived' },
  { id: FACILITIES_BUILDING, label: 'Facilities / Bank building', position: [-105, 0, 0], size: [74, 12, 13], rotation: Math.PI / 2, detailed: true, confidence: 'reference-derived' },
  { id: 'courtyard-north', label: 'Courtyard complex · north', position: [-46, 0, 114], size: [84, 12, 14], confidence: 'provisional' },
  { id: 'courtyard-west', label: 'Courtyard complex · west', position: [-81, 0, 144], size: [14, 12, 48], confidence: 'provisional' },
  { id: 'courtyard-east', label: 'Courtyard complex · east', position: [-11, 0, 144], size: [14, 12, 48], confidence: 'provisional' },
  { id: 'courtyard-south', label: 'Courtyard complex · south', position: [-46, 0, 174], size: [84, 12, 14], confidence: 'provisional' },
]
export const floors = [{ level: 0, label: 'Ground · Labs' }, { level: 1, label: 'First · IT' }, { level: 2, label: 'Second · ECE' }, { level: 3, label: 'Terrace' }]
export function floorsFor(buildingId: string) {
  const labels: Record<string, string[]> = {
    [HALL_BUILDING]: ['Ground · Chambers & library', 'First · Auditorium & courtyard', 'Terrace'],
    [CSE_BUILDING]: ['Ground · CSE 2nd year', 'First · CSE 3rd year', 'Second · MCA', 'Terrace'],
    [ECE_BUILDING]: ['Ground · ECE', 'First · ECE', 'Second · ECE', 'Terrace'],
    [LAB_BUILDING]: ['Ground · Mechanical labs', 'First · CSE / MCA labs', 'Second · IT / AI & DS labs', 'Terrace'],
    [MBA_BUILDING]: ['Ground · MBA', 'First · Labs', 'Second · Unconfirmed', 'Terrace'],
    [AIDS_BUILDING]: ['Ground · Labs', 'First · Mechanical labs', 'Second · AI & DS', 'Terrace'],
    [FACILITIES_BUILDING]: ['Ground · College facilities', 'First · Bank', 'Second · Unconfirmed', 'Terrace'],
  }
  return labels[buildingId]?.map((label, level) => ({ level, label })) ?? floors
}
const itSpaces: Space[] = [0, 1, 2].flatMap(floor => {
  const department = floor === 1 ? 'IT' : floor === 2 ? 'ECE' : undefined
  const roomSpan = geometry.width - 4 * geometry.facilityWidth
  const rooms: Space[] = floor === 0 ? [0, 1].map(i => ({ id: `it-ece-l0-room-${i + 1}`, buildingId: IT_BUILDING, label: `Lab ${i + 1}`, kind: 'lab', floor, x: -roomSpan / 4 + i * roomSpan / 2, width: roomSpan / 2, provisional: true })) :
    Array.from({ length: 7 }, (_, i) => ({ id: `it-ece-l${floor}-room-${i + 1}`, buildingId: IT_BUILDING, label: `${floor === 1 ? 'F' : 'S'}${i + 1}`, kind: i === 2 ? 'staff' : i === 3 ? 'hod' : 'classroom', floor, department, x: -roomSpan / 2 + (i + .5) * roomSpan / 7, width: roomSpan / 7, provisional: false }))
  return [...rooms, ...([-1, 1] as const).flatMap(side => [
    { id: `it-ece-l${floor}-${side < 0 ? 'girls' : 'boys'}`, buildingId: IT_BUILDING, label: `${side < 0 ? 'Girls’' : 'Boys’'} restroom`, kind: 'restroom' as const, floor, x: side * (geometry.width / 2 - geometry.facilityWidth / 2), width: geometry.facilityWidth, provisional: false },
    { id: `it-ece-l${floor}-stairs-${side < 0 ? 'left' : 'right'}`, buildingId: IT_BUILDING, label: `${side < 0 ? 'Left' : 'Right'} stairs`, kind: 'stairs' as const, floor, x: side * (geometry.width / 2 - geometry.facilityWidth * 1.5), width: geometry.facilityWidth, provisional: false },
  ])]
})
const cseSpaces: Space[] = itSpaces.filter(s => !(s.floor === 0 && s.kind === 'lab')).map(space => ({
  ...space,
  id: space.id.replace('it-ece-', 'cse-'),
  buildingId: CSE_BUILDING,
  department: space.floor === 2 ? 'MCA' : 'CSE',
  // Restroom identity follows its gender; only its position is mirrored.
  x: space.kind === 'restroom' ? -space.x : space.x,
}))
// The second-year floor uses the upper-floor classroom template until its exact layout is supplied.
cseSpaces.push(...itSpaces.filter(s => s.floor === 1 && ['classroom', 'staff', 'hod'].includes(s.kind)).map(s => ({
  ...s, id: s.id.replace('it-ece-l1-', 'cse-l0-'), buildingId: CSE_BUILDING,
  floor: 0, label: s.label.replace('F', 'G'), department: 'CSE', provisional: true,
})))
const eceSpaces: Space[] = itSpaces.map(s => ({
  ...s, id: s.id.replace('it-ece-', 'ece-'), buildingId: ECE_BUILDING, department: 'ECE',
  x: s.kind === 'restroom' ? -s.x : s.x, provisional: true,
}))
// ECE's restroom/stair arrangement is confirmed; its room contents remain illustrative.
eceSpaces.filter(s => s.kind === 'restroom' || s.kind === 'stairs').forEach(s => { s.provisional = false })
const labDepartments = [['Mechanical', 'Mechanical'], ['CSE', 'MCA'], ['IT', 'AI & DS']]
const labSpaces: Space[] = [0, 1, 2].flatMap(floor => itSpaces.filter(s => s.floor === 0).map(s => {
  const index = s.x < 0 ? 0 : 1
  const department = s.kind === 'lab' ? labDepartments[floor][index] : undefined
  return { ...s, id: s.id.replace('it-ece-l0-', `labs-l${floor}-`), buildingId: LAB_BUILDING, floor,
    department, label: s.kind === 'lab' ? `${department} lab${floor === 0 ? ` ${index + 1}` : ''}` : s.label,
    provisional: true }
}))
const mbaSpaces: Space[] = eceSpaces.filter(s => s.kind === 'restroom' || s.kind === 'stairs').map(s => ({
  ...s, id: s.id.replace('ece-', 'mba-'), buildingId: MBA_BUILDING,
  department: s.floor === 0 ? 'MBA' : undefined, provisional: true,
}))
mbaSpaces.push(...itSpaces.filter(s => s.floor === 1 && ['classroom', 'staff', 'hod'].includes(s.kind)).map(s => ({
  ...s, id: s.id.replace('it-ece-l1-', 'mba-l0-'), buildingId: MBA_BUILDING, floor: 0,
  label: s.label.replace('F', 'G'), department: 'MBA', provisional: true,
})))
mbaSpaces.push(...itSpaces.filter(s => s.floor === 0 && s.kind === 'lab').map(s => ({
  ...s, id: s.id.replace('it-ece-l0-', 'mba-l1-'), buildingId: MBA_BUILDING, floor: 1, provisional: true,
})))
// No room functions are invented for the unconfirmed second floor.
const aidsSpaces: Space[] = labSpaces.map(s => {
  const department = s.floor === 1 ? 'Mechanical' : s.floor === 2 ? 'AI & DS' : undefined
  const number = s.x < 0 ? 1 : 2
  return { ...s, id: s.id.replace('labs-', 'aids-'), buildingId: AIDS_BUILDING, department,
    label: s.kind === 'lab' ? `${department ? `${department} ` : ''}Lab ${number}` : s.label,
    provisional: true }
})
const facilitySpaces: Space[] = itSpaces.filter(s => s.kind === 'stairs' || s.kind === 'restroom').map(s => ({
  ...s, id: s.id.replace('it-ece-', 'facilities-'), buildingId: FACILITIES_BUILDING, department: undefined, provisional: true,
}))
facilitySpaces.push(
  { id: 'facilities-l0-service-area', buildingId: FACILITIES_BUILDING, label: 'College facilities / visiting services', kind: 'facility', floor: 0, x: 0, width: 60, provisional: true },
  { id: 'facilities-l1-bank', buildingId: FACILITIES_BUILDING, label: 'Bank', kind: 'bank', floor: 1, x: 0, width: 60, provisional: true },
)
// Hall coordinates: garden at +Z, rear at -Z; dimensions and door widths are illustrative.
function hallSpace(id: string, label: string, kind: SpaceKind, floor: number, x: number, z: number, width: number, depth: number, wing: Space['wing'], provisional = false): Space {
  return { id: `hall-${id}`, buildingId: HALL_BUILDING, label, kind, floor, x, z, width, depth, wing, provisional,
    note: 'Dimensions, furnishings and door positions are approximate. Room labels are descriptive, not official room numbers.' }
}
export const hallSpaces: Space[] = [
  ...[-1, 1].flatMap(side => [0, 1].map(i => hallSpace(`g-chamber-${side < 0 ? 'left' : 'right'}-${i + 1}`, `${side < 0 ? 'Left' : 'Right'} entrance chamber ${i + 1}`, 'chamber', 0, side * 12.5, 7.5 + i * 14, 19, 14, 'front'))),
  hallSpace('g-entry', 'Main entrance to courtyard', 'passage', 0, 0, 14.5, 6, 28, 'front'),
  hallSpace('g-left', 'Large chamber', 'chamber', 0, -27, -12.5, 10, 24, 'left'),
  hallSpace('g-rear', 'Rear chamber', 'chamber', 0, 0, -29, 44, 7, 'rear'),
  hallSpace('g-library', 'Library', 'library', 0, 27, -12.5, 10, 24, 'right'),
  hallSpace('f-auditorium', 'Auditorium', 'auditorium', 1, 0, 14.5, 38, 28, 'front'),
  ...[0, 1].flatMap(floor => [
    hallSpace(`${floor}-stairs-left`, 'Left stairs · boys side', 'stairs', floor, -27, 26.5, 10, 4, 'left'),
    hallSpace(`${floor}-boys`, 'Boys’ restroom', 'restroom', floor, -27, 22.5, 10, 4, 'left', floor === 0),
    hallSpace(`${floor}-stairs-right`, 'Right stairs · girls side', 'stairs', floor, 27, 26.5, 10, 4, 'right'),
    hallSpace(`${floor}-girls`, 'Girls’ restroom', 'restroom', floor, 27, 22.5, 10, 4, 'right', true),
    hallSpace(`${floor}-front-corridor`, 'Front corridor · both stairs', 'passage', floor, 0, 30.5, 64, 4, 'front'),
  ]),
  ...[0, 1, 2, 3].map(i => hallSpace(`f-class-${i + 1}`, `Auditorium-side classroom ${i + 1}`, 'classroom', 1, -27, 18.5 - i * 4, 10, 4, 'left')),
  hallSpace('f-left-staff', 'Auditorium-side staff room', 'staff', 1, -27, 2.5, 10, 4, 'left'),
  hallSpace('f-principal', 'Principal room', 'principal', 1, -24, -29, 16, 7, 'rear'),
  hallSpace('f-hod', 'HOD room', 'hod', 1, -8, -29, 16, 7, 'rear'),
  hallSpace('f-staff', 'Rear staff room', 'staff', 1, 8, -29, 16, 7, 'rear'),
  hallSpace('f-exam', 'Exam cell', 'exam', 1, 24, -29, 16, 7, 'rear'),
  hallSpace('f-entry', 'Right wing auditorium entrance', 'passage', 1, 27, 10.5, 10, 20, 'right'),
  // Retain existing space IDs while correcting their floor assignment.
  ...[0, 1, 2].map(i => hallSpace(`s-left-class-${i + 1}`, `Courtyard left classroom ${i + 1}`, 'classroom', 1, -27, -4.5 - i * 8, 10, 8, 'left')),
  ...[0, 1].map(i => hallSpace(`s-right-class-${i + 1}`, `Courtyard right classroom ${i + 1}`, 'classroom', 1, 27, -6.5 - i * 12, 10, 12, 'right')),
  { ...hallSpace('s-terrace-stairs', 'Courtyard stairs to terrace', 'stairs', 1, -14, -20, 10, 5, 'left'), note: 'Courtyard sketch marker 7: stairs from the first floor to the upper terrace. Dimensions and landings are approximate.' },
]

export const spaces: Space[] = [...itSpaces, ...cseSpaces, ...eceSpaces, ...labSpaces, ...mbaSpaces, ...aidsSpaces, ...facilitySpaces, ...hallSpaces]
export const bindings: RoomBinding[] = []
export function linkedRoom(spaceId: string, editionId: string, rooms: Room[], links = bindings) {
  const binding = links.find(item => item.spaceId === spaceId && item.editionId === editionId)
  return binding ? rooms.find(room => room.id === binding.roomId) : undefined
}
export const kindLabels: Record<SpaceKind, string> = { classroom: 'Classroom', lab: 'Lab', staff: 'Staff room', hod: 'HOD room', restroom: 'Restroom', stairs: 'Stairs', facility: 'College facility', bank: 'Bank', auditorium: 'Auditorium', chamber: 'Chamber', library: 'Library', principal: 'Principal office', exam: 'Exam cell', passage: 'Entrance / passage' }
export const spaceColors: Record<SpaceKind, string> = { classroom: '#bbd8cf', lab: '#afc9dc', staff: '#e6cca2', hod: '#dcb694', restroom: '#c6c5da', stairs: '#b7bdbb', facility: '#c4d9cc', bank: '#d8c9a9', auditorium: '#d8a995', chamber: '#d5c7ad', library: '#a9c8d9', principal: '#e2c594', exam: '#c4b6d8', passage: '#e6ddc8' }
