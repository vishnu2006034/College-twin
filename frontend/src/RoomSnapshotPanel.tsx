import { useEffect, useState } from 'react'
import { api, type Page, type Room } from './api'
import type { Snapshot } from './snapshot'

export type SavedSession = { id: string; room_id: string; faculty_id: string; section_id: string; starts_at: string; ends_at: string; status: string }
export type RoomState = Pick<Snapshot, 'edition_id' | 'as_of' | 'window_start' | 'window_end' | 'schema_version' | 'synthetic_data_only' | 'input_hash' | 'metrics' | 'coverage' | 'anomalies'> & { snapshot_id: string; room: Room }
const percent = (n: number | null) => n === null ? 'Unknown' : `${(100 * n).toFixed(1)}%`
const time = (t: string) => new Date(t).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })

export default function RoomSnapshotPanel({ snapshot, room, mappingVersion }: { snapshot: Snapshot; room: Room; mappingVersion: number }) {
  const [data, setData] = useState<RoomState | null>(null)
  const [page, setPage] = useState<Page<SavedSession> | null>(null)
  const [offset, setOffset] = useState(0)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    let active = true
    setData(null); setError('')
    api<RoomState>(`/snapshots/${snapshot.id}/rooms/${room.id}`).then(value => {
      if (value.snapshot_id !== snapshot.id || value.edition_id !== snapshot.edition_id || value.room.id !== room.id) throw new Error('Room state does not match the selected snapshot')
      if (active) setData(value)
    }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [snapshot.id, snapshot.edition_id, room.id, retry])
  useEffect(() => {
    let active = true
    setPage(null)
    api<Page<SavedSession>>(`/snapshots/${snapshot.id}/sessions?room_id=${room.id}&limit=10&offset=${offset}`).then(value => { if (active) setPage(value) }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [snapshot.id, room.id, offset, retry])
  return <section className="room-state" aria-label="Selected room snapshot">
    <h3>{room.code} · dated state</h3><p>Snapshot {snapshot.id} · {time(snapshot.as_of)} IST. Current mapping revision {mappingVersion}.</p>
    {error ? <><p role="alert">{error}</p><button onClick={() => { setError(''); setRetry(r => r + 1) }}>Retry room state</button></> : <>
      {!data ? <p role="status">Loading room state…</p> : <>
        <p>{data.metrics.scheduled_occupied_rooms ? 'Scheduled occupied' : 'Scheduled available'} at cutoff. This is planned use.</p>
        <p>{data.metrics.scheduled_classes} scheduled classes · {percent(data.metrics.room_utilization)} utilization ({data.metrics.booked_room_minutes}/{data.metrics.available_room_minutes} room minutes).</p>
        <p>Attendance {percent(data.metrics.attendance_rate)}; coverage {percent(data.coverage.attendance_ratio)} ({data.metrics.attendance_recorded}/{data.metrics.attendance_expected} records).</p>
        <h4>Room-related anomalies ({data.anomalies.length})</h4>
        {data.anomalies.length ? <ul>{data.anomalies.map((a, i) => <li key={i}>{a.rule.replaceAll('_', ' ')}: {a.session_ids.join(', ')} · {time(a.starts_at)}–{time(a.ends_at)}</li>)}</ul> : <p>No anomalies involving this room.</p>}
      </>}
      <h4>Saved timetable</h4>{!page ? <p role="status">Loading timetable…</p> : <>
        {page.total === 0 ? <p>No sessions for this room in the selected window.</p> : <ul>{page.items.map(s => <li key={s.id}>{time(s.starts_at)}–{time(s.ends_at)} IST · {s.status}<br/><small>Session {s.id}</small></li>)}</ul>}
        <p>{page.total} sessions · {page.total ? offset + 1 : 0}–{offset + page.items.length} shown</p>
        <button className="quiet" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 10))}>Previous sessions</button>
        <button className="quiet" disabled={offset + page.items.length >= page.total} onClick={() => setOffset(offset + 10)}>Next sessions</button>
      </>}
    </>}
  </section>
}
