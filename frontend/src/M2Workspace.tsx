import { useEffect, useState } from 'react'
import { api, type Actor, type Edition, type Room } from './api'
import { linkedRoom } from './campus'
import CampusExplorer from './CampusExplorer'
import StateDashboard from './StateDashboard'
import RoomMappingReview, { emptyMapping, type Mapping } from './RoomMappingReview'
import RoomSnapshotPanel from './RoomSnapshotPanel'
import type { Snapshot } from './snapshot'

export default function M2Workspace({ edition, actor, rooms }: { edition: Edition; actor: Actor; rooms: Room[] }) {
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
    <section aria-label="Campus mapping status">
      {mappingError && <p className="error">{mappingError}. Mapped state is unavailable until mappings reload.</p>}
      {!mapping && !mappingError && <p role="status">Loading room mappings…</p>}
      <button className="quiet" onClick={() => setReload(r => r + 1)}>Reload mappings</button>
      {mapping && <RoomMappingReview key={`${mapping.version}-${reload}`} editionId={edition.id} actor={actor} rooms={rooms} mapping={mapping} onSaved={setMapping}/>}
    </section>
    <CampusExplorer editionId={edition.id} rooms={rooms} links={links} onSpaceSelected={setSpace} roomStateRoomId={room?.id}
      roomState={room ? snapshot ? <RoomSnapshotPanel key={`${snapshot.id}-${room.id}`} snapshot={snapshot} room={room} mappingVersion={mapping?.version ?? 0}/> : <p>Create or open a dated snapshot above to see this linked room’s state.</p> : undefined}/>
  </>
}
