import { useEffect, useState } from 'react'
import { api, type Actor, type Edition, type Room } from './api'
import { linkedRoom } from './campus'
import CampusExplorer from './CampusExplorer'
import StateDashboard from './StateDashboard'
import RoomMappingReview, { emptyMapping, type Mapping } from './RoomMappingReview'
import RoomSnapshotPanel from './RoomSnapshotPanel'
import type { Snapshot } from './snapshot'
import M3Workspace from './M3Workspace'
import { simulationHighlights, type SimulationOverlay } from './simulation-map'

export default function M2Workspace({ edition, actor, rooms }: { edition: Edition; actor: Actor; rooms: Room[] }) {
  const [scenario, setScenario] = useState<SimulationOverlay | null>(null)
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [spaceId, setSpace] = useState<string | null>(null)
  const [mapping, setMapping] = useState<Mapping | null>(null)
  const [mappingError, setMappingError] = useState('')
  const [reload, setReload] = useState(0)
  useEffect(() => {
    let active = true
    setMapping(null); setMappingError('')
    api<Mapping>(`/room-mappings/${edition.id}`).then(value => {
      if (value.edition_id !== edition.id || !Array.isArray(value.bindings)) throw new Error('Unable to read room mappings')
      if (active) setMapping(value)
    }).catch(e => { if (active) setMappingError(e.message) })
    return () => { active = false }
  }, [edition.id, reload])
  const links = (mapping ?? emptyMapping(edition.id)).bindings.map(b => ({ spaceId: b.space_id, roomId: b.room_id, editionId: edition.id }))
  const room = spaceId ? linkedRoom(spaceId, edition.id, rooms, links) : undefined
  return <>
    <StateDashboard edition={edition} actor={actor} onSnapshot={setSnapshot}/>
    <M3Workspace key={snapshot?.id ?? "no-snapshot"} snapshot={snapshot} actor={actor} links={links} selectedSpaceId={spaceId} onScenario={setScenario}/>
    <section aria-label="Campus mapping status">
      {mappingError && <p className="error">{mappingError}. Mapped state is unavailable until mappings reload.</p>}
      {!mapping && !mappingError && <p role="status">Loading room mappings…</p>}
      <button className="quiet" onClick={() => setReload(r => r + 1)}>Reload mappings</button>
      {mapping && <RoomMappingReview key={`${mapping.version}-${reload}`} editionId={edition.id} actor={actor} rooms={rooms} mapping={mapping} onSaved={setMapping}/>}
    </section>
    {scenario && <section className="panel" aria-label="Simulation mapping provenance">
      <p>Saved simulation <code>{scenario.runId}</code>. Campus highlights use {mapping ? `current reviewed mapping revision ${mapping.version}` : 'no mapping (loading or unavailable)'}; this mapping is not frozen into the simulation.</p>
      {scenario.editionId !== edition.id && <p>This saved simulation belongs to another edition. Campus highlights are hidden until that edition is selected.</p>}
      {scenario.editionId === edition.id && <p>{Object.keys(simulationHighlights(scenario, edition.id, links)).length} mapped spaces shown. Unmapped closed or destination rooms remain visible by synthetic ID in the comparison.</p>}
    </section>}
    <CampusExplorer highlights={simulationHighlights(scenario, edition.id, links)} editionId={edition.id} rooms={rooms} links={links} onSpaceSelected={setSpace} roomStateRoomId={room?.id}
      roomState={room ? snapshot ? <RoomSnapshotPanel key={`${snapshot.id}-${room.id}`} snapshot={snapshot} room={room} mappingVersion={mapping?.version ?? 0}/> : <p>Create or open a dated snapshot above to see this linked room’s state.</p> : undefined}/>
  </>
}
