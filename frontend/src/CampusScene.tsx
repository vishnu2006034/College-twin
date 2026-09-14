import { useEffect, useRef } from 'react'
import { Canvas, useThree, type ThreeEvent } from '@react-three/fiber'
import { Html, OrbitControls } from '@react-three/drei'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { buildings, geometry, spaces, spaceColors, type Vec3, type Space } from './campus'

export type SceneProps = { buildingId: string | null; floor: number | null; spaceId: string | null; reset: number; onBuilding: (id: string) => void; onSpace: (id: string) => void; onFailure: () => void }
function Box({ at, size, color, onClick }: { at: Vec3; size: Vec3; color: string; onClick?: (e: ThreeEvent<MouseEvent>) => void }) {
  return <mesh position={at} onClick={onClick} castShadow receiveShadow><boxGeometry args={size}/><meshStandardMaterial color={color} roughness={.85}/></mesh>
}
function CameraRig({ buildingId, floor, reset }: Pick<SceneProps, 'buildingId' | 'floor' | 'reset'>) {
  const { camera, invalidate, size } = useThree()
  const controls = useRef<OrbitControlsImpl>(null)
  useEffect(() => {
    const building = buildings.find(b => b.id === buildingId)
    const [x, , z] = building?.position ?? [0, 0, 15]
    const y = floor === null ? 4 : floor * geometry.floorHeight
    const framing = Math.max(1, 1.55 / (size.width / size.height))
    camera.position.set(x + (building ? 0 : 235) * framing, (building ? 54 : 280) * framing, z + (building ? 65 * Math.cos(building.rotation ?? 0) : 300) * framing)
    controls.current?.target.set(x, y, z)
    controls.current?.update()
    invalidate()
  }, [buildingId, floor, reset, camera, invalidate, size.width, size.height])
  return <OrbitControls ref={controls} makeDefault enableDamping={false} minDistance={22} maxDistance={650} maxPolarAngle={Math.PI / 2.08}/>
}
function RoomShape({ room, active, onSelect }: { room: Space; active: boolean; onSelect: () => void }) {
  const h = geometry.floorHeight
  const color = active ? '#efa650' : spaceColors[room.kind]
  const depth = geometry.roomDepth
  return <group position={[room.x, room.floor * h + .25, -geometry.corridorDepth / 2]} onClick={e => { e.stopPropagation(); onSelect() }}>
    <Box at={[0, .03, 0]} size={[room.width - .25, .16, depth]} color={color}/>
    <Box at={[-room.width / 2, 1.2, 0]} size={[geometry.wall, 2.4, depth]} color="#eeeee4"/>
    <Box at={[0, 1.2, -depth / 2]} size={[room.width, 2.4, geometry.wall]} color="#e8e5d8"/>
    <Box at={[room.width * .16, 1.2, depth / 2]} size={[room.width * .65, 2.4, geometry.wall]} color="#eeeee4"/>
    {room.kind === 'stairs' ? Array.from({ length: 10 }, (_, i) => <Box key={i} at={[0, .12 + i * .16, -3.5 + i * .65]} size={[3.8, .25 + i * .32, .65]} color="#989f98"/>) : null}
    <Html position={[0, 2.9, room.kind === 'restroom' ? -2 : room.kind === 'stairs' ? 2 : 0]} center zIndexRange={[20, 0]}><button aria-label={room.label} title={room.label} className={`space-tag ${active ? 'active' : ''}`} onClick={e => { e.stopPropagation(); onSelect() }}>{room.kind === 'restroom' ? room.label.replace(' restroom', ' WC') : room.kind === 'stairs' ? room.label.replace(' stairs', ' ↑') : room.label}</button></Html>
  </group>
}
function DetailedBuilding({ buildingId, floor, spaceId, onSpace }: Pick<SceneProps, 'buildingId' | 'floor' | 'spaceId' | 'onSpace'>) {
  const top = floor ?? 3
  const { width: w, depth: d, floorHeight: h, corridorDepth: c, roomDepth: rd } = geometry
  const stairsX = w / 2 - geometry.facilityWidth * 1.5
  return <group>
    {[0, 1, 2].filter(level => level <= top).map(level => <group key={level}>
      <Box at={[0, level * h + .12, 0]} size={[w, .24, d]} color="#e6e1d2"/>
      <Box at={[0, level * h + .3, d / 2 - c / 2]} size={[w, .15, c]} color="#d5c7aa"/>
      {floor === level ? spaces.filter(s => s.buildingId === buildingId && s.floor === level).map(room => <RoomShape key={room.id} room={room} active={spaceId === room.id} onSelect={() => onSpace(room.id)}/>) : <>
        <Box at={[0, level * h + h / 2, -c / 2]} size={[w, h - .4, rd + .7]} color="#e6dfce"/>
        {Array.from({ length: 22 }, (_, i) => <group key={i}>
          <Box at={[-w / 2 + 2 + i * (w - 4) / 21, level * h + h / 2, (rd + .7 - c) / 2 + .05]} size={[1.9, 1.6, .15]} color="#607d7b"/>
          <Box at={[-w / 2 + 1 + i * (w - 2) / 21, level * h + h / 2, d / 2 - .4]} size={[.3, h - .2, .3]} color="#f0eadb"/>
        </group> )}
        <Box at={[0, level * h + .9, d / 2 - .3]} size={[w, 1.1, .2]} color="#cfc9b8"/>
      </>}
    </group>)}
    {top === 3 && <>
      <Box at={[0, h * 3 + .15, 0]} size={[w, .3, d]} color="#b7b5a7"/>
      {[-1, 1].map(side => <group key={side}>
        <Box at={[0, h * 3 + .8, side * (d / 2 - .1)]} size={[w, 1.2, .25]} color="#dbd6c6"/>
        <Box at={[side * (w / 2 - .2), h * 3 + .8, 0]} size={[.25, 1.2, d]} color="#dbd6c6"/>
        <Box at={[side * stairsX, h * 3 + 1.5, -c / 2]} size={[geometry.facilityWidth - 1, 2.7, 6]} color="#ddd7c7"/>
        <Box at={[side * stairsX, h * 3 + 1.1, -c / 2 + 3.05]} size={[1.4, 2, .1]} color="#647b73"/>
      </group>)}
    </>}
  </group>
}
function Landscape() {
  return <group>
    <Box at={[10, -1.4, 25]} size={[340, 2.5, 390]} color="#c7d0b4"/>
    <Box at={[0, -.04, 0]} size={[185, .15, 92]} color="#ddd8c4"/>
    {[-1, 1].flatMap(side => [0, 1, 2, 3].map(i => <Box key={`${side}-${i}`} at={[side * (15 + i * 21), .1, 0]} size={[13, .25, 76]} color="#92ad7c"/>))}
    <Box at={[0, .26, 0]} size={[180, .1, 6]} color="#eee6cd"/>
    <Box at={[0, .28, 0]} size={[8, .1, 90]} color="#eee6cd"/>
    <Box at={[0, .8, 0]} size={[14, 1, 14]} color="#cec5af"/>
    {[-96, 96].map(x => <Box key={x} at={[x, -.05, 25]} size={[7, .2, 315]} color="#b4b4a5"/>)}
    {[-94, 94, 188].map(z => <Box key={z} at={[0, -.04, z]} size={[200, .2, 7]} color="#b4b4a5"/>)}
    <Box at={[0, -.03, -126]} size={[170, .2, 48]} color="#c3b395"/>
    <Box at={[54, .12, -125]} size={[42, .18, 24]} color="#58866a"/>
    <Box at={[-9, .12, -125]} size={[24, .18, 37]} color="#af7860"/>
    <Box at={[-46, .12, 145]} size={[29, .18, 21]} color="#9b8b72"/>
    {[-9, -46, 54].map((x, i) => <group key={x} position={[x, .24, i === 1 ? 145 : -125]}>
      <Box at={[0, 0, 0]} size={[.2, .04, i === 0 ? 36 : 20]} color="#eee9ce"/>
      {[-1, 1].map(side => <Box key={side} at={[0, 0, side * (i === 0 ? 18 : 10)]} size={[i === 2 ? 40 : 24, .04, .2]} color="#eee9ce"/>)}
    </group>)}
    <mesh position={[117, -.05, 119]} rotation={[-Math.PI / 2, 0, -.25]} scale={[1, 1.65, 1]}><circleGeometry args={[26, 36]}/><meshStandardMaterial color="#6e9990" roughness={.45}/></mesh>
    {Array.from({ length: 95 }, (_, i) => {
      const edge = i % 2 === 0
      const x = edge ? (i % 4 === 0 ? -128 : 147) + Math.sin(i * 8) * 8 : -85 + (i * 37 % 170)
      const z = edge ? -147 + i * 3.5 : (i % 3 === 0 ? 91 : -91) + Math.sin(i) * 2
      return <group key={i} position={[x, 0, z]}><Box at={[0, 1.2, 0]} size={[.65, 2.4, .65]} color="#7d7960"/><mesh position={[0, 3.9, 0]} castShadow><icosahedronGeometry args={[2.6 + i % 3 * .4, 1]}/><meshStandardMaterial color={i % 2 ? '#607c58' : '#759163'}/></mesh></group>
    })}
  </group>
}
export default function CampusScene(props: SceneProps) {
  return <Canvas shadows="percentage" dpr={[1, 1.5]} frameloop="demand" camera={{ position: [210, 245, 285], fov: 43, near: .5, far: 1500 }} fallback={<p>3D is unavailable. Use the campus directory to explore every space.</p>} onCreated={({ gl }) => { gl.domElement.addEventListener('webglcontextlost', props.onFailure, { once: true }) }}>
    <color attach="background" args={['#e7ebdf']}/><ambientLight intensity={1.5}/><directionalLight position={[80, 180, 90]} intensity={2.5} castShadow shadow-mapSize={[2048, 2048]} shadow-camera-left={-230} shadow-camera-right={230} shadow-camera-top={230} shadow-camera-bottom={-230} shadow-camera-far={500} shadow-bias={-.001}/>
    <Landscape/>
    {buildings.map(building => <group key={building.id} position={building.position} rotation={[0, building.rotation ?? 0, 0]} onClick={e => { e.stopPropagation(); props.onBuilding(building.id) }}>
      {building.detailed && props.buildingId === building.id ? <DetailedBuilding {...props}/> : <>
        <Box at={[0, building.size[1] / 2, 0]} size={building.size} color={props.buildingId === building.id ? '#d4ad69' : building.detailed ? '#a9bca3' : '#ddd9c9'}/>
        <Box at={[0, building.size[1] + .15, 0]} size={[building.size[0] + .5, .3, building.size[2] + .5]} color="#b5b4a5"/>
        {[0, 1, 2].map(level => <Box key={level} at={[0, 2 + level * 4, building.size[2] / 2 + .05]} size={[building.size[0] - 2, 1.3, .12]} color="#6f8480"/>)}
      </>}
      {(building.detailed || props.buildingId === building.id) && <Html position={[0, building.size[1] + 4, 0]} center zIndexRange={[15, 0]}><button className="building-tag" onClick={() => props.onBuilding(building.id)}>{building.label}</button></Html>}
    </group>)}
    <CameraRig {...props}/>
  </Canvas>
}
