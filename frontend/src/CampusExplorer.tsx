import { Component, lazy, Suspense, useState, type ReactNode } from 'react'
import type { Room } from './api'
import { buildings, floorsFor, spaces, IT_BUILDING, kindLabels, linkedRoom } from './campus'
import './campus.css'

const CampusScene = lazy(() => import('./CampusScene'))
class SceneBoundary extends Component<{ children: ReactNode; fallback: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() { return this.state.failed ? this.props.fallback : this.props.children }
}
function supportsWebGL() {
  if (typeof window === 'undefined' || !window.WebGL2RenderingContext) return false
  try { const canvas = document.createElement('canvas'); const gl = canvas.getContext('webgl2'); gl?.getExtension('WEBGL_lose_context')?.loseContext(); return !!gl } catch { return false }
}
export default function CampusExplorer({ editionId, rooms }: { editionId: string; rooms: Room[] }) {
  const [buildingId, setBuilding] = useState<string | null>(null)
  const [floor, setFloor] = useState<number | null>(null)
  const [spaceId, setSpace] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [reset, setReset] = useState(0)
  const [view, setView] = useState<'perspective' | 'plan' | 'ground'>('perspective')
  const [labels, setLabels] = useState(true)
  const [webgl, setWebgl] = useState(supportsWebGL)
  const building = buildings.find(b => b.id === buildingId)
  const floors = floorsFor(buildingId ?? IT_BUILDING)
  const buildingSpaces = spaces.filter(s => s.buildingId === buildingId)
  const spaceMatches = (s: (typeof spaces)[number]) => `${s.label} ${s.department ?? ''} ${kindLabels[s.kind]} ${buildings.find(b => b.id === s.buildingId)?.label ?? ''}`.toLowerCase().includes(term)
  const floorSpaces = buildingSpaces.filter(s => s.floor === floor).sort((a, b) => a.x - b.x)
  const leftRestroom = floorSpaces.find(s => s.kind === 'restroom')?.label.replace(' restroom', '') ?? 'Left'
  const rightRestroom = [...floorSpaces].reverse().find(s => s.kind === 'restroom')?.label.replace(' restroom', '') ?? 'Right'
  const space = spaces.find(s => s.id === spaceId)
  const record = space ? linkedRoom(space.id, editionId, rooms) : undefined
  const term = query.trim().toLowerCase()
  function selectBuilding(id: string) { setBuilding(id); setFloor(null); setSpace(null) }
  function selectSpace(id: string) { const target = spaces.find(s => s.id === id); if (target) { setBuilding(target.buildingId); setFloor(target.floor); setSpace(id) } }
  function resetView() { setBuilding(null); setFloor(null); setSpace(null); setQuery(''); setView('perspective'); setReset(r => r + 1) }
  const fallback = <div className="scene-fallback"><span className="eyebrow">CAMPUS DIRECTORY AVAILABLE</span><h3>Explore without 3D</h3><p>3D rendering is unavailable on this device. Select a building and floor below or use the directory to inspect every room.</p><button onClick={() => selectBuilding(IT_BUILDING)}>Explore IT / ECE</button></div>
  return <section className="campus-workspace" aria-label="Interactive campus twin">
    <div className="campus-heading"><div><p className="eyebrow">JEPPIAAR ENGINEERING COLLEGE</p><h1>Your campus, connected.</h1><p>Explore the campus. Step into a floor. Understand each space.</p></div><span className="model-badge"><i/> Architectural model · v2</span></div>
    <div className="explorer-grid">
      <aside className="campus-directory"><p className="eyebrow">EXPLORE SPACES</p><label htmlFor="campus-search">Find a building or room</label><input id="campus-search" type="search" placeholder="Search IT, F3, lab…" value={query} onChange={e => setQuery(e.target.value)}/>
        <div className="directory-list"><p className="directory-caption">CAMPUS BUILDINGS</p>{buildings.filter(b => b.label.toLowerCase().includes(term)).map(b => <button key={b.id} className={`directory-item ${b.id === buildingId ? 'selected' : ''}`} aria-pressed={b.id === buildingId} onClick={() => selectBuilding(b.id)}><span>{b.label}</span><small>{b.detailed ? '3 floors + terrace ↗' : 'Exterior model'}</small></button>)}
        {term && <><p className="directory-caption">ROOMS & FACILITIES</p>{spaces.filter(spaceMatches).map(s => <button className="directory-item" key={s.id} onClick={() => selectSpace(s.id)}><span>{s.label} · {kindLabels[s.kind]}</span><small>{buildings.find(b => b.id === s.buildingId)?.label} · {floorsFor(s.buildingId)[s.floor].label}</small></button>)}{!spaces.some(spaceMatches) && <p>No matching rooms.</p>}</>}
        </div><div className="directory-note">Based on campus references.<br/>Dimensions are approximate.</div>
      </aside>
      <div className="campus-main"><div className="scene-toolbar"><nav aria-label="Campus breadcrumbs"><button onClick={resetView}>Campus</button>{building && <><span>/</span><button onClick={() => selectBuilding(building.id)}>{building.label}</button></>}{floor !== null && <span>/ {floors[floor].label}</span>}</nav><button className="quiet" onClick={resetView}>Reset view</button></div>
        <div className="model-controls" aria-label="Model presentation"><div>{([['perspective', 'Perspective'], ['plan', 'Top view'], ['ground', 'Low view']] as const).map(([value, label]) => <button key={value} aria-pressed={view === value} onClick={() => setView(value)}>{label}</button>)}</div><button aria-pressed={labels} onClick={() => setLabels(value => !value)}>Labels {labels ? 'on' : 'off'}</button></div>
        <div className="scene-viewport" role="region" aria-label="3D campus viewer"><SceneBoundary fallback={fallback}><Suspense fallback={<div className="scene-fallback" role="status">Loading campus geometry…</div>}>{webgl ? <CampusScene view={view} labels={labels} buildingId={buildingId} floor={floor} spaceId={spaceId} reset={reset} onBuilding={selectBuilding} onSpace={selectSpace} onFailure={() => setWebgl(false)}/> : fallback}</Suspense></SceneBoundary><div className="scene-caption">{floor === null ? 'CAMPUS MODEL' : floor === 3 ? 'OPEN TERRACE' : 'FLOOR CUTAWAY'}<span>Approximate geometry</span></div></div>
        <div className="viewer-help">Drag to orbit · Scroll / pinch to zoom · Right-drag to pan <span>Or use the directory and floor controls</span></div>
        {building?.detailed && <section className="floor-explorer" aria-label="Building floors"><div className="floor-heading"><h2>Inside {building.label}</h2><span>Garden-facing corridor</span></div><div className="floor-tabs">{floors.map(f => <button key={f.level} aria-pressed={floor === f.level} onClick={() => { setFloor(f.level); setSpace(null) }}>{f.label}</button>)}</div>
          {floor === null ? <p>Select a floor to reveal its rooms.</p> : floor === 3 ? <p>Open terrace with a parapet and access from the left and right stairs. Dimensions and access structures are approximate.</p> : <>{floors[floor].label.includes('Unconfirmed') && <p role="status">Second-floor use and rooms are unconfirmed. Only provisional stairs and restrooms are shown.</p>}<div className="floor-orientation"><span>← {leftRestroom} side · numbering begins here</span><span>{rightRestroom} side →</span></div><div className="room-strip">{floorSpaces.map(s => <button key={s.id} aria-pressed={spaceId === s.id} className={`room-cell ${s.kind}`} onClick={() => selectSpace(s.id)}><strong>{s.label}</strong><small>{kindLabels[s.kind]}</small></button>)}</div><div className="corridor-strip">Single corridor · faces the central garden</div></>}
        </section>}
      </div>
      <aside className="space-inspector" aria-label="Selected space information" aria-live="polite"><p className="eyebrow">SPACE DETAILS</p>{space ? <><h2>{space.label}</h2><span className={`function-chip ${space.kind}`}>{kindLabels[space.kind]}</span><dl><dt>Building</dt><dd>{building?.label}</dd><dt>Floor</dt><dd>{floors[space.floor].label}</dd><dt>Department</dt><dd>{space.department ?? 'Not confirmed'}</dd><dt>Assignment</dt><dd>{space.provisional ? 'Provisional' : 'User-confirmed'}</dd><dt>Geometry</dt><dd>Approximate</dd></dl><div className="data-link"><p className="eyebrow">DATA CONNECTION</p>{record ? <><p>Synthetic dataset record</p><strong>{record.code}</strong><p>Capacity: {record.capacity}</p>{record.lab_type && <p>Lab type: {record.lab_type}</p>}</> : <><h3>No linked dataset record</h3><p>This physical space has not been mapped to a room in the selected synthetic dataset.</p></>}</div></> : building ? <><h2>{building.label}</h2><p>{building.detailed ? 'Select a floor, then a room to inspect its function and data connection.' : 'Exterior geometry is available. Interior details have not been confirmed.'}</p><dl><dt>Reference</dt><dd>{building.confidence === 'provisional' ? 'Identity unconfirmed' : 'Campus imagery / user description'}</dd><dt>Dimensions</dt><dd>Approximate</dd></dl>{building.detailed && <button onClick={() => { setFloor(1); setSpace(null) }}>Explore {buildingId === IT_BUILDING ? 'IT' : building.label} floor →</button>}</> : <><div className="inspector-symbol">⌘</div><h2>A place for every insight.</h2><p>Select a building to begin. IT / ECE, CSE, ECE and the lab building include explorable floors, classrooms, offices, labs, and facilities.</p><button onClick={() => { selectBuilding(IT_BUILDING); setFloor(1) }}>Explore IT floor →</button><div className="inspector-stat"><strong>3 + roof</strong><span>Levels per detailed building</span></div></>}
        <div className="inspector-disclaimer">Approximate architecture and illustrative furnishings. Synthetic data remains separate. Live occupancy and simulations are not connected.</div>
      </aside>
    </div>
  </section>
}
