import { useLayoutEffect, useMemo, useRef } from 'react'
import { Color, InstancedMesh, Matrix4, Shape } from 'three'
import { Blocks, useSurface, type Block } from './SceneArchitecture'
import type { Vec3 } from './campus'

function Surface({ at, size, kind }: { at: Vec3; size: Vec3; kind: Parameters<typeof useSurface>[0] }) {
  const map = useSurface(kind)
  return <mesh position={at} receiveShadow><boxGeometry args={size}/><meshStandardMaterial map={map} roughness={kind === 'water' ? .26 : .96}/></mesh>
}
function Trees() {
  const ref = useRef<InstancedMesh>(null)
  const positions = useMemo(() => {
    const points: Vec3[] = []
    for (let i = 0; i < 63; i++) {
      const z = -157 + i * 5.5
      for (const side of [-1, 1]) points.push([side * (141 + Math.sin(i * 7) * 8), 0, z])
    }
    for (let i = 0; i < 36; i++) {
      points.push([-88 + i * 5, 0, -91], [-88 + i * 5, 0, 93])
    }
    for (const x of [-87, 87]) for (const z of [-33, -15, 15, 33]) points.push([x, 0, z])
    return points
  }, [])
  const trunks = useMemo(() => positions.map((at): Block => ({ at: [at[0], 2, at[2]], size: [.55, 4, .55], color: '#625b40' })), [positions])
  useLayoutEffect(() => {
    const matrix = new Matrix4()
    positions.forEach(([x, , z], i) => {
      const size = 2.5 + (i % 4) * .28
      for (let j = 0; j < 3; j++) {
        matrix.makeScale(size, size * (j === 0 ? 1.05 : .8), size).setPosition(x + Math.cos(j * 2.1) * 1.1, 4.4 + (j === 0 ? 1 : 0), z + Math.sin(j * 2.1))
        ref.current!.setMatrixAt(i * 3 + j, matrix)
        ref.current!.setColorAt(i * 3 + j, new Color(['#426043', '#567347', '#6a7c48', '#3e604b'][i % 4]))
      }
    })
    ref.current!.instanceMatrix.needsUpdate = true
    ref.current!.instanceColor!.needsUpdate = true
    ref.current!.computeBoundingSphere()
  }, [positions])
  return <><Blocks items={trunks}/><instancedMesh ref={ref} args={[undefined, undefined, positions.length * 3]} castShadow receiveShadow><icosahedronGeometry args={[1, 2]}/><meshStandardMaterial roughness={1}/></instancedMesh></>
}
function Pond() {
  const map = useSurface('water')
  const shape = useMemo(() => {
    const s = new Shape()
    s.moveTo(-17, -38); s.bezierCurveTo(-34, -18, -27, 24, -12, 39); s.bezierCurveTo(10, 53, 28, 29, 27, 5); s.bezierCurveTo(34, -23, 13, -49, -17, -38)
    return s
  }, [])
  return <group position={[111, .04, 129]} rotation={[-Math.PI / 2, 0, -.2]}>
    <mesh receiveShadow scale={[1.12, 1.1, 1]}><shapeGeometry args={[shape, 32]}/><meshStandardMaterial color="#8e9570" roughness={1}/></mesh>
    <mesh position={[0, 0, .06]} receiveShadow><shapeGeometry args={[shape, 32]}/><meshStandardMaterial map={map} color="#c4cdaa" roughness={.26} metalness={.18}/></mesh>
  </group>
}
function Palm({ x, z }: { x: number; z: number }) {
  return <group position={[x, 0, z]}>
    <mesh position={[0, 3, 0]} castShadow><cylinderGeometry args={[.19, .35, 6, 7]}/><meshStandardMaterial color="#8d8360"/></mesh>
    {Array.from({ length: 7 }, (_, i) => <group key={i} position={[0, 6, 0]} rotation={[0, i * Math.PI * 2 / 7, .15]}><mesh position={[1.5, .1, 0]} rotation={[0, 0, -.18]} castShadow scale={[3, .15, .52]}><sphereGeometry args={[1, 8, 4]}/><meshStandardMaterial color={i % 2 ? '#54774a' : '#6d8746'}/></mesh></group>)}
  </group>
}
export default function SceneLandscape() {
  const details = useMemo(() => {
    const list: Block[] = []
    const add = (at: Vec3, size: Vec3, color: string) => list.push({ at, size, color })
    // Curbs, lanes and crossing marks.
    for (const x of [-97, 97]) {
      for (const side of [-1, 1]) add([x + side * 4.2, .12, 42], [.35, .3, 301], '#c5bfa9')
      for (let z = -97; z < 190; z += 12) add([x, .05, z], [.16, .04, 4.5], '#e2d9bc')
    }
    for (const z of [-99, 98, 188]) for (let x = -92; x <= 92; x += 12) add([x, .05, z], [4.5, .04, .16], '#e2d9bc')
    for (const x of [-97, 97]) for (let i = 0; i < 7; i++) add([x - 2.9 + i, .08, 0], [.6, .05, 4.2], '#e5dcc6')
    // Split lawn beds follow the garden's cross axes, with low hedge edging.
    for (const side of [-1, 1]) for (let i = 0; i < 4; i++) for (const z of [-22, 22]) {
      const x = side * (15 + i * 20)
      add([x, .18, z], [13.8, .3, 33.8], '#b8b79b')
      add([x, .36, z], [13, .15, 33], '#7f9853')
      add([x, .64, z - 16.1], [12.5, .6, .6], '#5b753e')
      for (const dx of [-6.25, 6.25]) add([x + dx, .64, z], [.6, .6, 32], '#5b753e')
    }
    // Benches and lamps along the central promenade.
    for (const x of [-69, -43, 43, 69]) for (const z of [-6, 6]) {
      add([x, .8, z], [3, .16, .75], '#826948')
      add([x, 1.3, z + (z > 0 ? .35 : -.35)], [3, .8, .09], '#826948')
      for (const dx of [-1, 1]) add([x + dx, .35, z], [.15, .7, .55], '#545b50')
    }
    for (const x of [-91, 91]) for (const z of [-42, 0, 42, 95, 179]) {
      add([x, 2.6, z], [.11, 5.2, .11], '#424f49'); add([x + .45, 5.1, z], [1, .12, .32], '#e1d7b4')
    }
    // Campus perimeter, entry gate and guard shelter: illustrative architectural details.
    for (const x of [-156, 166]) add([x, .85, 28], [.5, 1.7, 363], '#c0b497')
    add([5, .85, 209], [322, 1.7, .5], '#c0b497')
    for (const x of [-91, 91]) add([x, .85, -161], [142, 1.7, .5], '#c0b497')
    for (const x of [-16, 16]) { add([x, 2.4, -161], [1.2, 4.8, 1.2], '#ded0ad'); add([x, 4.9, -161], [1.7, .25, 1.7], '#a3987c') }
    add([0, 4.1, -161], [31, .8, .6], '#667653')
    add([24, 1.6, -156], [5, 3.2, 4], '#cdbd97'); add([24, 3.35, -156], [5.6, .25, 4.6], '#817d68'); add([24, 1.9, -158.1], [2.3, 1.2, .06], '#4e7273')
    // Marked parking with several illustrative parked cars.
    for (let i = 0; i < 9; i++) {
      const x = -82 + i * 6
      add([x, .02, -145], [.1, .05, 9], '#d6cdb1')
      if (i % 3 !== 0) {
        add([x + 2.8, .65, -144.5], [2.3, .9, 4.3], ['#d9d7c9', '#637b7f', '#8a6b54'][i % 3])
        add([x + 2.8, 1.25, -144.3], [2.05, .6, 2.35], '#40565b')
        for (const dx of [-1.1, 1.1]) for (const dz of [-1.25, 1.25]) add([x + 2.8 + dx, .32, -144.5 + dz], [.22, .52, .7], '#323b35')
      }
    }
    // Sports pitches, complete boundary markings, goals, and court nets.
    for (const [x, z, w, d] of [[53, -123, 46, 26], [-17, -120, 23, 34], [-46, 145, 28, 19]]) {
      add([x, .14, z], [w + 3, .2, d + 3], '#b3a180')
      add([x, .27, z], [w, .1, d], x === -17 ? '#a9664b' : '#547e58')
      for (const side of [-1, 1]) { add([x + side * (w / 2 - .6), .34, z], [.12, .04, d - 1.2], '#e4e0c8'); add([x, .34, z + side * (d / 2 - .6)], [w - 1.2, .04, .12], '#e4e0c8') }
      add([x, .34, z], [.12, .04, d - 1.2], '#e4e0c8')
      if (x === 53) for (const side of [-1, 1]) {
        add([x + side * w / 2, 2.05, z], [.1, .1, 6], '#e3e1cf')
        for (const dz of [-3, 3]) add([x + side * w / 2, 1.1, z + dz], [.1, 2.2, .1], '#e3e1cf')
      }
      if (x === -17) { add([x, 1.1, z], [w, .04, .06], '#d7d5c7'); for (let i = 0; i < 24; i++) add([x - w / 2 + i, .7, z], [.04, .85, .04], '#8b8c7d') }
    }
    return list
  }, [])
  return <group>
    <Surface at={[5, -1.25, 25]} size={[345, 2, 390]} kind="grass"/>
    <Surface at={[0, -.08, 0]} size={[185, .3, 92]} kind="paving"/>
    <Surface at={[0, -.14, -125]} size={[187, .18, 58]} kind="paving"/>
    <Surface at={[-58, -.01, -145]} size={[64, .1, 12]} kind="road"/>
    {[-97, 97].map(x => <Surface key={x} at={[x, -.08, 42]} size={[8, .18, 301]} kind="road"/>)}
    {[-99, 98, 188].map(z => <Surface key={z} at={[0, -.08, z]} size={[202, .18, 8]} kind="road"/>)}
    <Surface at={[0, -.06, -129]} size={[10, .2, 66]} kind="road"/>
    <Surface at={[-46, -.08, 145]} size={[70, .2, 49]} kind="paving"/>
    <Blocks items={details}/>
    <Trees/><Pond/>
    {[-70, -35, 35, 70].flatMap(x => [-10, 10].map(z => <Palm key={`${x}-${z}`} x={x} z={z}/>))}
    <mesh position={[0, .3, 0]} receiveShadow><cylinderGeometry args={[7, 7, .4, 48]}/><meshStandardMaterial color="#c8b88f"/></mesh>
    <mesh position={[0, .6, 0]} receiveShadow><cylinderGeometry args={[5.7, 5.7, .25, 48]}/><meshStandardMaterial color="#667f71" roughness={.3}/></mesh>
    <mesh position={[0, 1.6, 0]} castShadow><cylinderGeometry args={[1.9, 2.8, 1.8, 32]}/><meshStandardMaterial color="#c6b995"/></mesh>
    <mesh position={[0, 2.55, 0]} castShadow><cylinderGeometry args={[3.2, 1.9, .2, 32]}/><meshStandardMaterial color="#dbccac"/></mesh>
  </group>
}
