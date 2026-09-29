import { spaces, type RoomBinding } from './campus'

export type SimulationMark = 'closed' | 'destination'
export type SimulationHighlights = Record<string, SimulationMark>
export type SimulationOverlay = {
  runId: string
  editionId: string
  closedRoomId: string
  destinationRoomIds: string[]
}
export const simulationLabels = { closed: 'Closed room', destination: 'Reassignment destination' }
export const simulationColors = { closed: '#d96a65', destination: '#668bdd' }

// Geometry is joined only through reviewed, edition-scoped IDs. Never infer links.
export function simulationHighlights(overlay: SimulationOverlay | null, editionId: string, links: RoomBinding[]): SimulationHighlights {
  if (!overlay || overlay.editionId !== editionId) return {}
  const result: SimulationHighlights = {}
  const destinations = new Set(overlay.destinationRoomIds)
  for (const link of links) {
    if (link.editionId !== editionId || !spaces.some(s => s.id === link.spaceId)) continue
    if (link.roomId === overlay.closedRoomId) result[link.spaceId] = 'closed'
    else if (destinations.has(link.roomId)) result[link.spaceId] = 'destination'
  }
  return result
}
