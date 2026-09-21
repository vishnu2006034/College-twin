import { useState, type FormEvent } from 'react'
import { api, type Actor, type Room } from './api'
import { buildings, floorsFor, spaces } from './campus'

export type Mapping = { edition_id: string; version: number; bindings: { space_id: string; room_id: string }[]; reviewed_at: string | null; review_note: string | null }
export const emptyMapping = (edition: string): Mapping => ({ edition_id: edition, version: 0, bindings: [], reviewed_at: null, review_note: null })
export const spaceLabel = (id: string) => {
  const space = spaces.find(s => s.id === id)
  return space ? `${buildings.find(b => b.id === space.buildingId)?.label} / ${floorsFor(space.buildingId)[space.floor].label} / ${space.label}` : id
}

export default function RoomMappingReview({ editionId, actor, rooms, mapping, onSaved }: {
  editionId: string; actor: Actor; rooms: Room[]; mapping: Mapping; onSaved: (value: Mapping) => void
}) {
  const [spaceId, setSpace] = useState('')
  const [roomId, setRoom] = useState('')
  const [draft, setDraft] = useState(mapping.bindings)
  const [note, setNote] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const space = spaces.find(s => s.id === spaceId)
  const compatibleRooms = rooms.filter(r => r.kind === space?.kind && !draft.some(b => b.room_id === r.id))
  function add(event: FormEvent) {
    event.preventDefault()
    if (!space || !compatibleRooms.some(r => r.id === roomId) || draft.some(b => b.space_id === spaceId)) return
    setDraft([...draft, { space_id: spaceId, room_id: roomId }]); setConfirmed(false); setSpace(''); setRoom('')
  }
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      onSaved(await api<Mapping>(`/room-mappings/${editionId}`, { expected_version: mapping.version, bindings: draft, review_note: note }))
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to save mapping') }
    finally { setBusy(false) }
  }
  return <details className="panel mapping-review"><summary>Review campus room mappings ({mapping.bindings.length} approved)</summary>
    <p>No links are inferred from labels. Select the physical teaching space and the exact synthetic room, review its type and capacity, then approve. This connects synthetic data for this edition; it does not certify real occupancy or physical capacity.</p>
    <p>Saved mapping revision: {mapping.version}. {mapping.reviewed_at ? `Reviewed ${new Date(mapping.reviewed_at).toLocaleString()}. ${mapping.review_note}` : 'All mappings remain unconfirmed.'}</p>
    {actor.role === 'planner' && <form onSubmit={add} className="snapshot-controls">
      <label>Physical teaching space<select required value={spaceId} disabled={busy} onChange={e => { setSpace(e.target.value); setRoom('') }}>
        <option value="">Choose a physical space</option>{spaces.filter(s => ['classroom', 'lab'].includes(s.kind) && !draft.some(b => b.space_id === s.id)).map(s => <option key={s.id} value={s.id}>{spaceLabel(s.id)}{s.provisional ? ' · provisional' : ''}</option>)}
      </select></label>
      <label>Synthetic room<select required value={roomId} disabled={!space || busy} onChange={e => setRoom(e.target.value)}>
        <option value="">Choose an edition room</option>{compatibleRooms.map(r => <option key={r.id} value={r.id}>{r.code} · {r.lab_type ?? r.kind} · capacity {r.capacity} · {r.id}</option>)}
      </select></label><button disabled={!roomId || busy}>Add to review</button>
    </form>}
    {space?.provisional && <p>The selected physical space has provisional geometry or use. Review this uncertainty before linking it.</p>}
    <ul>{(actor.role === 'planner' ? draft : mapping.bindings).map(b => <li key={b.space_id}>{spaceLabel(b.space_id)} → {rooms.find(r => r.id === b.room_id)?.code ?? b.room_id}
      {actor.role === 'planner' && <button className="quiet" disabled={busy} onClick={() => { setDraft(draft.filter(r => r.space_id !== b.space_id)); setConfirmed(false) }}>Remove {spaces.find(s => s.id === b.space_id)?.label}</button>}</li>)}</ul>
    {actor.role === 'planner' && <form onSubmit={save}>
      <label>Review note<input required minLength={5} maxLength={1000} value={note} disabled={busy} onChange={e => setNote(e.target.value)}/></label>
      <label className="review-confirm"><input type="checkbox" required checked={confirmed} disabled={busy} onChange={e => setConfirmed(e.target.checked)}/>I reviewed these exact links and any provisional space labels for this synthetic edition.</label>
      <button disabled={busy || !confirmed || note.trim().length < 5}>{busy ? 'Saving review…' : 'Approve and save mappings'}</button>
      <p>Draft edits do not affect the campus until saved. To reload after a conflicting review, use “Reload mappings” above; unsaved edits will be discarded.</p>
    </form>}
    {error && <p role="alert" className="error">{error}</p>}
  </details>
}
