import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, type Actor, type Page, type Room } from './api'
import type { Snapshot } from './snapshot'
import { buildings, floorsFor, spaces, type RoomBinding } from './campus'
import type { SimulationOverlay } from './simulation-map'
type Stage = { assigned_classes: number; unassigned_classes: number; booked_room_minutes: number; available_room_minutes: number; room_utilization: number | null }
export type Run = {
  id: string; edition_id: string; request: { room_id: string }; snapshot_id: string; baseline_input_hash: string; algorithm_version: string;
  result: { stages: Record<string, Stage>; impact: { affected_students: number; unresolved_students: number };
    recommendation: { message: string }; observed_attendance: { label: string; attendance_present: number; attendance_recorded: number } }
}
type Row = { id: string; starts_at: string; original_room_id: string; assigned_room_id: string | null; allocation_status: string; reason_code: string | null; candidate_summary: Record<string, number> | null }
const time = (value: string) => new Date(value).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })
export default function M3Workspace({ snapshot, actor, links = [], selectedSpaceId, onScenario }: {
  snapshot: Snapshot | null; actor: Actor; links?: RoomBinding[]; selectedSpaceId?: string | null;
  onScenario?: (value: SimulationOverlay | null) => void;
}) {
  const [rooms, setRooms] = useState<Room[]>([])
  const [room, setRoom] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [savedId, setSavedId] = useState('')
  const [run, setRun] = useState<Run | null>(null)
  const [rows, setRows] = useState<Page<Row> | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [mapError, setMapError] = useState('')
  const pending = useRef<{ body: string; key: string } | null>(null)
  useEffect(() => {
    let active = true
    setRooms([]); setRoom(''); setRun(null); setRows(null); setError('')
    if (snapshot) api<{ items: Room[] }>(`/snapshots/${snapshot.id}/rooms`).then(page => {
      if (!Array.isArray(page.items)) throw new Error('Unable to read saved room inventory')
      if (active) { setRooms(page.items); setRoom(page.items[0]?.id ?? '') }
    }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [snapshot?.id])
  useEffect(() => {
    let active = true
    onScenario?.(null); setMapError('')
    if (run && onScenario) {
      const value = run
      async function collectDestinations() {
        const destinations = new Set<string>()
        let offset = 0
        while (true) {
          const page = await api<Page<Row>>(`/simulations/${value.id}/sessions?stage=reassigned&affected_only=true&limit=200&offset=${offset}`)
          if (!active) return
          for (const row of page.items) if (row.allocation_status === 'reassigned' && row.assigned_room_id) destinations.add(row.assigned_room_id)
          offset += page.items.length
          if (offset >= page.total) break
          if (!page.items.length) throw new Error('Incomplete affected-session results')
        }
        if (active) onScenario?.({ runId: value.id, editionId: value.edition_id,
          closedRoomId: value.request.room_id, destinationRoomIds: [...destinations].sort() })
      }
      collectDestinations().catch(() => { if (active) setMapError('Campus highlights unavailable. Reopen the saved simulation to retry; comparison results remain available.') })
    }
    return () => { active = false; onScenario?.(null) }
  }, [run, onScenario])
  const mappedChoices = links.filter(link => link.editionId === snapshot?.edition_id && rooms.some(r => r.id === link.roomId) && spaces.some(s => s.id === link.spaceId))
  const selectedLink = mappedChoices.find(link => link.spaceId === selectedSpaceId)
  function spaceLabel(id: string) {
    const space = spaces.find(s => s.id === id)!
    return `${space.label} / ${buildings.find(b => b.id === space.buildingId)?.label} / ${floorsFor(space.buildingId)[space.floor].label}`
  }
  async function loadRows(id: string, offset = 0) {
    const page = await api<Page<Row>>(`/simulations/${id}/sessions?stage=reassigned&affected_only=true&limit=50&offset=${offset}`)
    setRows(page)
  }
  async function submit(event: FormEvent, saved = false) {
    event.preventDefault(); setBusy(true); setError(''); setRun(null); setRows(null)
    try {
      let value: Run
      if (saved) value = await api<Run>(`/simulations/${encodeURIComponent(savedId.trim())}`)
      else {
        const body = { snapshot_id: snapshot!.id, type: 'room_unavailability', room_id: room,
          closure_start: `${start}:00+05:30`, closure_end: `${end}:00+05:30` }
        const serialized = JSON.stringify(body)
        if (pending.current?.body !== serialized) pending.current = { body: serialized, key: crypto.randomUUID() }
        value = await api<Run>('/simulations', body, { 'Idempotency-Key': pending.current.key })
      }
      setRun(value); setSavedId(value.id); await loadRows(value.id)
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to load simulation') }
    finally { setBusy(false) }
  }
  async function paginate(offset: number) {
    setBusy(true); setError('')
    try { await loadRows(run!.id, offset) } catch (e) { setError(e instanceof Error ? e.message : 'Unable to load sessions') }
    finally { setBusy(false) }
  }
  const suitable = snapshot && Date.parse(snapshot.as_of) === Date.parse(snapshot.window_start) && snapshot.anomalies.length === 0
  return <section className="panel state-dashboard simulation-workspace" aria-labelledby="simulation-heading">
    <p className="eyebrow">M3 / ROOM CLOSURE · SYNTHETIC DATA</p><h2 id="simulation-heading">Compare a room closure</h2>
    <p>Fixed class times. Saved baseline and observed attendance remain unchanged. Rooms use saved synthetic IDs; campus selections use reviewed links only. Unmapped spaces remain unconfirmed.</p>
    {snapshot && <p>Baseline {snapshot.id} · {time(snapshot.window_start)} – {time(snapshot.window_end)} IST</p>}
    {!suitable && <p>Create or open a conflict-free planning snapshot above with cutoff 00:00 (window start). Active classes must fit entirely within the window.</p>}
    {actor.role === 'planner' && suitable && <form className="snapshot-controls" onSubmit={e => submit(e)}>
      <label>Reviewed campus room<select disabled={busy || !mappedChoices.length} value={mappedChoices.find(link => link.roomId === room)?.spaceId ?? ''} onChange={e => {
        const link = mappedChoices.find(item => item.spaceId === e.target.value)
        if (link) setRoom(link.roomId)
      }}><option value="">Select a reviewed campus room</option>{mappedChoices.map(link => <option key={link.spaceId} value={link.spaceId}>{spaceLabel(link.spaceId)}</option>)}</select></label>
      {!mappedChoices.length && <p>No reviewed campus links for this saved room inventory. Select a synthetic room below.</p>}
      {selectedLink && <button type="button" disabled={busy} onClick={() => setRoom(selectedLink.roomId)}>Use selected campus room: {spaceLabel(selectedLink.spaceId)}</button>}
      {selectedSpaceId && !selectedLink && <p>The selected campus space has no reviewed link in this saved inventory.</p>}
      <label>Room to close<select required value={room} onChange={e => setRoom(e.target.value)}>{rooms.map(r => <option key={r.id} value={r.id}>{r.code ?? r.id} · {r.kind} · {r.capacity} seats</option>)}</select></label>
      <label>Closure start (IST)<input required type="datetime-local" value={start} onChange={e => setStart(e.target.value)}/></label>
      <label>Closure end (IST)<input required type="datetime-local" value={end} onChange={e => setEnd(e.target.value)}/></label>
      <button disabled={busy || !room}>Simulate closure</button>
    </form>}
    {actor.role === 'viewer' && <p>Viewer access: open saved simulations below.</p>}
    <form className="snapshot-controls" onSubmit={e => submit(e, true)}>
      <label>Saved simulation ID<input required value={savedId} onChange={e => setSavedId(e.target.value)}/></label><button disabled={busy}>Open saved simulation</button>
    </form>
    {mapError && <p role="alert">{mapError}</p>}
    {busy && <p role="status">Loading simulation…</p>}{error && <p role="alert">{error}</p>}
    {run && <>
      <p>Saved run <code>{run.id}</code> · {run.algorithm_version}</p>
      <p>Baseline <code>{run.snapshot_id}</code> · input checksum <code>{run.baseline_input_hash}</code></p>
      <p>{run.result.recommendation.message}</p>
      <p>{run.result.impact.affected_students} distinct affected students; {run.result.impact.unresolved_students} students with unresolved classes.</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label="Stage comparison"><table><caption>Baseline, disrupted and reassigned comparison</caption><thead><tr><th>Stage</th><th>Assigned</th><th>Unassigned demand</th><th>Booked / available room-minutes</th><th>Utilization</th></tr></thead>
        <tbody>{Object.entries(run.result.stages).map(([name, s]) => <tr key={name}><th>{name}</th><td>{s.assigned_classes}</td><td>{s.unassigned_classes}</td><td>{s.booked_room_minutes} / {s.available_room_minutes}</td><td>{s.room_utilization === null ? 'Unknown (zero availability)' : `${(s.room_utilization * 100).toFixed(2)}%`}</td></tr>)}</tbody></table></div>
      <p>{run.result.observed_attendance.label}: {run.result.observed_attendance.attendance_present} present / {run.result.observed_attendance.attendance_recorded} recorded.</p>
      {rows && <><h3>Affected sessions ({rows.total})</h3>{rows.total === 0 && <p>No sessions affected by this closure.</p>}
        <div className="table-wrap" tabIndex={0} role="region" aria-label="Affected session assignments"><table><thead><tr><th>Session / start IST</th><th>Original room</th><th>Assigned room</th><th>Outcome / candidate constraints</th></tr></thead>
          <tbody>{rows.items.map(row => <tr key={row.id}><td>{row.id}<br/>{time(row.starts_at)}</td><td>{row.original_room_id}</td><td>{row.assigned_room_id ?? 'Unassigned'}</td><td>{row.allocation_status}{row.reason_code && <p>No room found by this heuristic ({row.reason_code}).</p>}{row.candidate_summary && <dl>{Object.entries(row.candidate_summary).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{value}</dd></div>)}</dl>}</td></tr>)}</tbody></table></div>
        <button disabled={busy || rows.offset === 0} onClick={() => paginate(Math.max(0, rows.offset - 50))}>Previous sessions</button>
        <button disabled={busy || rows.offset + rows.limit >= rows.total} onClick={() => paginate(rows.offset + 50)}>Next sessions</button>
      </>}
    </>}
  </section>
}
