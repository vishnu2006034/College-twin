import { useRef, useState, type FormEvent } from 'react'
import type { Actor, Edition } from './api'
import { snapshotClient, type Snapshot, type SnapshotClient } from './snapshot'

const percent = (value: number | null) => value === null ? 'Unknown' : `${(value * 100).toFixed(1)}%`
const localTime = (value: string) => new Date(value).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })

export default function StateDashboard({ edition, actor, client = snapshotClient, onSnapshot }: { edition: Edition; actor: Actor; client?: SnapshotClient; onSnapshot?: (snapshot: Snapshot | null) => void }) {
  const [date, setDate] = useState(edition.config.start_date ?? '')
  const [cutoff, setCutoff] = useState('17:00')
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [savedId, setSavedId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const pending = useRef<{ body: string; key: string } | null>(null)

  async function run(event: FormEvent, saved = false) {
    event.preventDefault(); setBusy(true); setError(''); setSnapshot(null); onSnapshot?.(null)
    try {
      let result: Snapshot
      if (saved) result = await client.get(savedId.trim())
      else {
        const body = { edition_id: edition.id, as_of: `${date}T${cutoff}:00+05:30`, window_start: `${date}T00:00:00+05:30`, window_end: `${new Date(Date.parse(`${date}T00:00:00Z`) + 86400000).toISOString().slice(0, 10)}T00:00:00+05:30` }
        const serialized = JSON.stringify(body)
        if (pending.current?.body !== serialized) pending.current = { body: serialized, key: crypto.randomUUID() }
        result = await client.create(body, pending.current.key)
      }
      if (result.edition_id !== edition.id) throw new Error('This snapshot belongs to another dataset. Select its edition first.')
      setSnapshot(result)
      onSnapshot?.(result)
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to load snapshot') }
    finally { setBusy(false) }
  }

  return <section className="panel state-dashboard" aria-labelledby="state-heading">
    <p className="eyebrow">M2 / DATED STATE · SYNTHETIC DATA</p><h2 id="state-heading">State & anomalies</h2>
    <p>Select a synthetic date. Times use Asia/Kolkata; room use is scheduled, not measured presence.</p>
    {actor.role === 'planner' ? <form onSubmit={e => run(e)} className="snapshot-controls">
      <label>Synthetic date<input type="date" required value={date} onChange={e => setDate(e.target.value)}/></label>
      <label>Cutoff time (IST)<input type="time" required value={cutoff} onChange={e => setCutoff(e.target.value)}/></label>
      <button disabled={busy}>Create dated snapshot</button>
    </form> : <p>A planner creates snapshots. Open a saved snapshot below to inspect its state.</p>}
    <form onSubmit={e => run(e, true)} className="snapshot-controls">
      <label>Saved snapshot ID<input required value={savedId} onChange={e => setSavedId(e.target.value)}/></label>
      <button disabled={busy}>Open saved snapshot</button>
    </form>
    {busy && <p role="status">Loading snapshot…</p>}{error && <p role="alert" className="error">{error}</p>}
    {snapshot && <>
      <p>State at {localTime(snapshot.as_of)} IST · Saved snapshot <code>{snapshot.id}</code></p>
      <p>Window: {localTime(snapshot.window_start)} – {localTime(snapshot.window_end)} IST</p>
      <div className="stats">
        <div><strong>{snapshot.metrics.scheduled_classes}</strong><span>Scheduled classes</span></div>
        <div><strong>{snapshot.metrics.scheduled_occupied_rooms}</strong><span>Scheduled occupied rooms at cutoff</span></div>
        <div><strong>{snapshot.metrics.available_rooms}</strong><span>Available rooms at cutoff</span></div>
        <div><strong>{percent(snapshot.metrics.room_utilization)}</strong><span>Scheduled room utilization</span></div>
        <div><strong>{percent(snapshot.metrics.attendance_rate)}</strong><span>Recorded attendance rate</span></div>
        <div><strong>{percent(snapshot.coverage.attendance_ratio)}</strong><span>Attendance coverage</span></div>
      </div>
      <p>{snapshot.metrics.booked_room_minutes} booked room minutes / {snapshot.metrics.available_room_minutes} available teaching minutes (weekdays 09:00–17:00).</p>
      <p>{snapshot.metrics.attendance_present} present / {snapshot.metrics.attendance_recorded} recorded / {snapshot.metrics.attendance_expected} expected. {snapshot.coverage.missing_attendance} missing records are unknown.</p>
      <h3>Detected anomalies ({snapshot.anomalies.length})</h3>
      {snapshot.anomalies.length === 0 ? <p>No conflicts or suitability violations in this window.</p> : <div className="table-wrap"><table>
        <thead><tr><th>Rule</th><th>Resource</th><th>Sessions</th><th>Interval (IST)</th></tr></thead>
        <tbody>{snapshot.anomalies.map((a, i) => <tr key={i}><td>{a.rule.replaceAll('_', ' ')}</td><td>{a.resource_id}</td><td>{a.session_ids.join(', ')}</td><td>{localTime(a.starts_at)} – {localTime(a.ends_at)}</td></tr>)}</tbody>
      </table></div>}
      <details><summary>Faculty scheduled teaching workload</summary><ul>{snapshot.metrics.faculty_workload.map(f => <li key={f.faculty_id}>{f.faculty_id}: {f.scheduled_minutes} minutes</li>)}</ul></details>
      <details><summary>Snapshot provenance</summary><p className="hash">Schema {snapshot.schema_version} · Input hash <code>{snapshot.input_hash}</code> · Edition hash <code>{snapshot.edition_hash}</code></p></details>
    </>}
  </section>
}
