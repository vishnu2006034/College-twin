import { useEffect, useRef } from 'react'
import { Canvas, useThree, type ThreeEvent } from '@react-three/fiber'
import { Html, OrbitControls } from '@react-three/drei'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { BuildingExterior, RoomFurniture } from './SceneArchitecture'
import SceneLandscape from './SceneLandscape'
import { buildings, geometry, spaces, spaceColors, type Vec3, type Space } from './campus'

export type SceneProps = { view: 'perspective' | 'plan' | 'ground'; labels: boolean; buildingId: string | null; floor: number | null; spaceId: string | null; reset: number; onBuilding: (id: string) => void; onSpace: (id: string) => void; onFailure: () => void }
function Box({ at, size, color, onClick }: { at: Vec3; size: Vec3; color: string; onClick?: (e: ThreeEvent<MouseEvent>) => void }) {
  return <mesh position={at} onClick={onClick} castShadow receiveShadow><boxGeometry args={size}/><meshStandardMaterial color={color} roughness={.85}/></mesh>
}
function CameraRig({ buildingId, floor, reset, view }: Pick<SceneProps, 'buildingId' | 'floor' | 'reset' | 'view'>) {
  const { camera, invalidate, size } = useThree()
  const controls = useRef<OrbitControlsImpl>(null)
  useEffect(() => {
    const building = buildings.find(b => b.id === buildingId)
    const [x, , z] = building?.position ?? [0, 0, 15]
    const y = floor === null ? 4 : floor * geometry.floorHeight
    const framing = Math.max(1, 1.55 / (size.width / size.height))
    camera.position.set(x + (building ? 0 : 235) * framing, (building ? 54 : 280) * framing, z + (building ? 65 * Math.cos(building.rotation ?? 0) : 300) * framing)
    if (view === 'plan') camera.position.set(x, (building ? 85 : 460) * framing, z + (building?.rotation ? -.01 : .01))
    if (view === 'ground') camera.position.set(x + (building ? 20 : 100), y + (building ? 10 : 32), z + (building ? 65 * Math.cos(building.rotation ?? 0) : 145) * framing)
    controls.current?.target.set(x, y, z)
    controls.current?.update()
    invalidate()
  }, [buildingId, floor, reset, camera, invalidate, size.width, size.height, view])
  return <OrbitControls ref={controls} makeDefault enableDamping={false} minDistance={22} maxDistance={650} maxPolarAngle={Math.PI / 2.08}/>
}
function RoomShape({ room, active, onSelect, labels }: { room: Space; active: boolean; onSelect: () => void; labels: boolean }) {
  const h = geometry.floorHeight
  const color = active ? '#efa650' : spaceColors[room.kind]
  const depth = geometry.roomDepth
  return <group position={[room.x, room.floor * h + .25, -geometry.corridorDepth / 2]} onClick={e => { e.stopPropagation(); onSelect() }}>
    <Box at={[0, .03, 0]} size={[room.width - .25, .16, depth]} color={color}/>
    <Box at={[-room.width / 2, 1.2, 0]} size={[geometry.wall, 2.4, depth]} color="#eeeee4"/>
    <Box at={[0, 1.2, -depth / 2]} size={[room.width, 2.4, geometry.wall]} color="#e8e5d8"/>
    <Box at={[room.width * .16, 1.2, depth / 2]} size={[room.width * .65, 2.4, geometry.wall]} color="#eeeee4"/>
    {room.kind === 'stairs' ? Array.from({ length: 10 }, (_, i) => <Box key={i} at={[0, .12 + i * .16, -3.5 + i * .65]} size={[3.8, .25 + i * .32, .65]} color="#989f98"/>) : null}
    <RoomFurniture room={room}/>
    {labels && <Html position={[0, 2.9, room.kind === 'restroom' ? -2 : room.kind === 'stairs' ? 2 : 0]} center zIndexRange={[20, 0]}><button aria-label={room.label} title={room.label} className={`space-tag ${active ? 'active' : ''}`} onClick={e => { e.stopPropagation(); onSelect() }}>{room.kind === 'restroom' ? room.label.replace(' restroom', ' WC') : room.kind === 'stairs' ? room.label.replace(' stairs', ' ↑') : room.label}</button></Html>}
  </group>
}
function DetailedBuilding({ buildingId, floor, spaceId, onSpace, labels }: Pick<SceneProps, 'buildingId' | 'floor' | 'spaceId' | 'onSpace' | 'labels'>) {
  const building = buildings.find(b => b.id === buildingId)!
  if (floor === null || floor === 3) return <BuildingExterior building={building} selected/>
  const { width: w, depth: d, floorHeight: h, corridorDepth: c } = geometry
  return <group>
    {floor > 0 && <BuildingExterior building={building} levels={floor} roof={false}/>}
    <Box at={[0, floor * h + .12, 0]} size={[w, .24, d]} color="#d6c7a9"/>
    <Box at={[0, floor * h + .3, d / 2 - c / 2]} size={[w, .15, c]} color="#cbbd9d"/>
    <Box at={[0, floor * h + 1, d / 2]} size={[w, 1.1, .2]} color="#dbcfb2"/>
    <Box at={[w / 2, floor * h + 1.45, -c / 2]} size={[.22, 2.4, geometry.roomDepth]} color="#e4d9bc"/>
    {spaces.filter(s => s.buildingId === buildingId && s.floor === floor).map(room => <RoomShape key={room.id} room={room} active={spaceId === room.id} labels={labels} onSelect={() => onSpace(room.id)}/>)}
  </group>
}
export default function CampusScene(props: SceneProps) {
  return <Canvas shadows="percentage" dpr={[1, 1.5]} frameloop="demand" camera={{ position: [210, 245, 285], fov: 43, near: .5, far: 1500 }} fallback={<p>3D is unavailable. Use the campus directory to explore every space.</p>} onCreated={({ gl }) => { gl.domElement.addEventListener('webglcontextlost', props.onFailure, { once: true }) }}>
    <color attach="background" args={['#c7d6d6']}/><fog attach="fog" args={['#c7d6d6', 440, 950]}/><hemisphereLight args={['#d1e1ed', '#797052', 1.1]}/><ambientLight intensity={.35}/><directionalLight color="#fff0d4" position={[-130, 150, 110]} intensity={3.2} castShadow shadow-mapSize={[2048, 2048]} shadow-camera-left={-230} shadow-camera-right={230} shadow-camera-top={230} shadow-camera-bottom={-230} shadow-camera-far={500} shadow-bias={-.001}/>
    <SceneLandscape/>
    {buildings.map(building => <group key={building.id} position={building.position} rotation={[0, building.rotation ?? 0, 0]} onClick={e => { e.stopPropagation(); props.onBuilding(building.id) }}>
      {building.detailed && props.buildingId === building.id ? <DetailedBuilding {...props}/> : <BuildingExterior building={building} selected={props.buildingId === building.id}/>}
      {props.labels && (building.detailed || props.buildingId === building.id) && <Html position={[0, building.size[1] + 4, 0]} center zIndexRange={[15, 0]}><button className="building-tag" onClick={() => props.onBuilding(building.id)}>{building.label}</button></Html>}
    </group>)}
    <CameraRig {...props}/>
  </Canvas>
}
