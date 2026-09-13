import { useEffect, useState, type FormEvent } from 'react'
import { api, ApiError, type Actor, type Edition, type Page, type Room } from './api'
import CampusExplorer from './CampusExplorer'

export default function App() {
  const [actor, setActor] = useState<Actor | null>(null)
  const [checking, setChecking] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [editions, setEditions] = useState<Edition[]>([])
  const [selected, setSelected] = useState('')
  const [rooms, setRooms] = useState<Room[]>([])
  const [loading, setLoading] = useState(false)
  const [roomsEdition, setRoomsEdition] = useState('')

  useEffect(() => {
    api<Actor>('/auth/me').then(setActor).catch(e => {
      if (!(e instanceof ApiError && e.status === 401)) setError('Unable to reach the server. Try again shortly.')
    }).finally(() => setChecking(false))
  }, [])

  useEffect(() => {
    if (!actor) return
    let active = true
    setLoading(true)
    api<Page<Edition>>('/datasets').then(data => {
      if (active) { setEditions(data.items); setSelected(data.items[0]?.id ?? '') }
    }).catch(e => { if (active) setError(e.message) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [actor])

  useEffect(() => {
    setRooms([])
    setRoomsEdition('')
    if (!selected || !actor) return
    let active = true
    async function loadRooms() {
      const all: Room[] = []
      let offset = 0
      while (true) {
        const page = await api<Page<Room>>(`/rooms?edition_id=${selected}&offset=${offset}&limit=100`)
        if (!active) return
        all.push(...page.items)
        offset += page.items.length
        if (offset >= page.total || page.items.length === 0) break
      }
      return all
    }
    loadRooms().then(data => {
      if (active && data) { setRooms(data); setRoomsEdition(selected) }
    }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [selected, actor])

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const data = new FormData(event.currentTarget)
    try { setActor(await api<Actor>('/auth/login', { username: data.get('username'), password: data.get('password') })) }
    catch (e) { setError(e instanceof Error ? e.message : 'Sign-in failed') }
    finally { setBusy(false) }
  }

  async function logout() {
    setBusy(true); setError('')
    try {
      await api('/auth/logout', {})
      setActor(null); setEditions([]); setSelected(''); setRooms([])
    } catch (e) { setError(e instanceof Error ? e.message : 'Sign-out failed') }
    finally { setBusy(false) }
  }

  const edition = editions.find(item => item.id === selected)
  return <main>
    <header><a className="brand" href="/">CT<span>College Twin</span></a><span className="badge">SYNTHETIC DATA PROTOTYPE</span>
      {actor && <button className="quiet" disabled={busy} onClick={logout}>Sign out</button>}</header>
    {!actor && <section className="intro"><p className="eyebrow">OPERATIONS LAB / M1 FOUNDATION</p>
      <h1>A shared foundation.<br/><span>A college you can explore.</span></h1>
      <p>Reproducible college data, ready for state analysis and simulation.</p></section>}
    {error && <div role="alert" className="error">{error}</div>}
    {checking ? <p role="status">Checking your session…</p> : !actor ?
      <form className="panel login" onSubmit={login}><h2>Enter the workspace</h2><p>Use your locally configured planner or viewer account.</p>
        <label>Username<input name="username" autoComplete="username" required maxLength={80}/></label>
        <label>Password<input name="password" type="password" autoComplete="current-password" required maxLength={256}/></label>
        <button disabled={busy}>{busy ? 'Signing in…' : 'Sign in →'}</button></form> :
      <><CampusExplorer editionId={selected} rooms={roomsEdition === selected ? rooms : []}/><details className="dataset-details"><summary>Dataset workspace & room inventory</summary><div className="workspace"><section className="panel">
        <div className="section-title"><h2>Dataset workspace</h2><span className="badge">{actor.role}</span></div>
        {loading ? <p role="status">Loading editions…</p> : editions.length === 0 ?
          <p>No frozen datasets are available. Run the documented bootstrap command to create one.</p> : <>
          <label>Dataset edition<select value={selected} onChange={event => setSelected(event.target.value)}>
            {editions.map(item => <option key={item.id} value={item.id}>Seed {item.seed} · {item.config.weeks} weeks · {item.id.slice(0, 8)}</option>)}
          </select></label>
          <div className="stats"><div><strong>{rooms.length}</strong><span>Rooms in edition</span></div>
            <div><strong>{edition?.config.weeks}</strong><span>Synthetic weeks</span></div>
            <div><strong>{edition?.generator_version}</strong><span>Generator version</span></div></div>
          <p className="hash">Content hash <code>{edition?.logical_content_hash}</code></p>
          <div className="table-wrap"><table><caption>Room inventory — scheduled and actual occupancy are not yet available</caption>
            <thead><tr><th>Room</th><th>Type</th><th>Capacity</th></tr></thead><tbody>
              {rooms.map(room => <tr key={room.id}><td>{room.code}</td><td>{room.kind === 'lab' ? `${room.lab_type} lab` : 'Classroom'}</td><td>{room.capacity}</td></tr>)}
            </tbody></table></div></>}
      </section><aside className="panel roadmap"><p className="eyebrow">WHAT COMES NEXT</p><h2>From records to decisions</h2>
        <ol><li><strong>State & anomalies</strong><span>Weeks 4–5 · planned</span></li><li><strong>Room-closure simulation</strong><span>Weeks 6–7 · planned</span></li>
          <li><strong>Attendance-risk prediction</strong><span>Weeks 6–8 · planned</span></li></ol>
        <p>Frontend work begins with mocked API responses in week 4. Integration replaces the mocks as backend capabilities become ready.</p></aside></div></details></>}
    <footer>College Twin · Synthetic-data digital-twin prototype · No live campus connection</footer>
  </main>
}
