import { useEffect, useLayoutEffect, useMemo, useRef } from 'react'
import { CanvasTexture, Color, InstancedMesh, Matrix4, RepeatWrapping, SRGBColorSpace } from 'three'
import type { Building, Space, Vec3 } from './campus'

export type Block = { at: Vec3; size: Vec3; color: string }
// Repeated architectural elements share one draw call per batch.
export function Blocks({ items, roughness = .8 }: { items: Block[]; roughness?: number }) {
  const ref = useRef<InstancedMesh>(null)
  useLayoutEffect(() => {
    const matrix = new Matrix4()
    items.forEach((item, i) => {
      matrix.makeScale(...item.size).setPosition(...item.at)
      ref.current!.setMatrixAt(i, matrix)
      ref.current!.setColorAt(i, new Color(item.color))
    })
    ref.current!.instanceMatrix.needsUpdate = true
    if (ref.current!.instanceColor) ref.current!.instanceColor.needsUpdate = true
    ref.current!.computeBoundingSphere()
  }, [items])
  return <instancedMesh ref={ref} args={[undefined, undefined, items.length]} castShadow receiveShadow><boxGeometry/><meshStandardMaterial roughness={roughness}/></instancedMesh>
}

export function useSurface(kind: 'plaster' | 'roof' | 'grass' | 'road' | 'paving' | 'water') {
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas'); canvas.width = canvas.height = 128
    const ctx = canvas.getContext('2d')!
    const palette = { plaster: [217, 206, 184], roof: [148, 139, 118], grass: [104, 125, 65], road: [87, 91, 88], paving: [189, 176, 151], water: [55, 99, 83] }
    const rgb = palette[kind]
    const pixels = ctx.createImageData(128, 128)
    let seed = 91231
    for (let i = 0; i < pixels.data.length; i += 4) {
      seed = (Math.imul(seed, 1664525) + 1013904223) | 0
      const grain = ((seed >>> 0) / 4294967296 - .5) * (kind === 'grass' ? 40 : 19)
      for (let c = 0; c < 3; c++) pixels.data[i + c] = rgb[c] + grain
      pixels.data[i + 3] = 255
    }
    ctx.putImageData(pixels, 0, 0)
    if (kind === 'roof' || kind === 'paving') {
      ctx.strokeStyle = kind === 'roof' ? '#68665655' : '#6b685e45'; ctx.lineWidth = 1
      for (let i = 0; i <= 128; i += 32) { ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, 128); ctx.moveTo(0, i); ctx.lineTo(128, i); ctx.stroke() }
    }
    if (kind === 'water') {
      ctx.strokeStyle = '#9fae8c30'
      for (let i = 4; i < 128; i += 9) { ctx.beginPath(); ctx.moveTo(0, i); ctx.bezierCurveTo(30, i - 4, 90, i + 4, 128, i); ctx.stroke() }
    }
    const result = new CanvasTexture(canvas)
    result.wrapS = result.wrapT = RepeatWrapping
    result.repeat.set(kind === 'grass' ? 45 : kind === 'road' ? 14 : 6, kind === 'grass' ? 45 : 6)
    result.colorSpace = SRGBColorSpace
    return result
  }, [kind])
  useEffect(() => () => texture.dispose(), [texture])
  return texture
}

export function BuildingExterior({ building, levels = 3, roof = true, selected = false }: { building: Building; levels?: number; roof?: boolean; selected?: boolean }) {
  const [w, totalHeight, d] = building.size
  const h = totalHeight / 3
  const plaster = useSurface('plaster')
  const roofMap = useSurface('roof')
  const facade = useMemo(() => {
    const items: Block[] = []
    const add = (at: Vec3, size: Vec3, color: string) => items.push({ at, size, color })
    const bays = Math.max(3, Math.floor(w / 3.8))
    const step = w / bays
    const wallZ = d / 2 - Math.min(3.5, d / 4)
    for (let level = 0; level < levels; level++) {
      const y = level * h
      add([0, y + .16, 0], [w + .6, .32, d + .6], '#d7d0bb')
      add([0, y + h - .3, wallZ + 1.6], [w, .3, 3.3], '#c7bc9d')
      for (let i = 0; i < bays; i++) {
        const x = -w / 2 + (i + .5) * step
        for (const z of [wallZ + .08, -d / 2 - .04]) {
          add([x, y + 2.05, z], [step * .68, 1.7, .16], '#b9b6a5')
          add([x, y + 2.05, z + (z > 0 ? .1 : -.1)], [step * .59, 1.47, .05], i % 4 === 0 ? '#567676' : '#3e6062')
          add([x, y + 2.05, z + (z > 0 ? .15 : -.15)], [.07, 1.55, .08], '#d0ccbb')
          add([x, y + 2.1, z + (z > 0 ? .15 : -.15)], [step * .65, .06, .08], '#d0ccbb')
          add([x, y + 3.05, z], [step * .82, .14, .8], '#d4cab1')
        }
        add([x - step / 2, y + h / 2, d / 2 - .2], [.32, h, .38], '#e2d7bb')
        if (level > 0) {
          add([x, y + .65, d / 2], [step - .3, .85, .2], '#d4c9ae')
          add([x, y + 1.16, d / 2], [step, .12, .26], '#f0e5cb')
          for (const dx of [-.8, 0, .8]) add([x + dx, y + 1.35, d / 2], [.045, .35, .07], '#767d72')
        }
      }
      // A shaded entrance opening at both stair ends, rather than a solid ribbon facade.
      for (const side of [-1, 1]) {
        const x = side * (w / 2 - Math.min(9, w / 4))
        add([x, y + 1.45, wallZ + .2], [1.8, 2.6, .15], '#555d51')
        add([x, y + 2.94, wallZ + .32], [2.1, .12, .5], '#c9bea2')
      }
    }
    for (const side of [-1, 1]) {
      const x = side * (w / 2 - Math.min(9, w / 4))
      for (let stair = 0; stair < 3; stair++) add([x, .12 + stair * .1, d / 2 + 1.2 - stair * .35], [4.4, .2, 1.5 - stair * .3], '#b9b29f')
      add([x, 3.5, d / 2 + 1], [5, .22, 2.8], '#c0b698')
    }
    if (roof) {
      const y = levels * h
      for (const side of [-1, 1]) {
        add([0, y + .65, side * d / 2], [w + .3, 1.1, .22], '#c8bfa7')
        add([side * w / 2, y + .65, 0], [.22, 1.1, d], '#c8bfa7')
        const x = side * (w / 2 - Math.min(9, w / 4))
        add([x, y + 1.4, -1.5], [4.7, 2.7, 5.2], '#d8ccb0')
        add([x, y + 2.84, -1.5], [5.1, .2, 5.6], '#b9b19b')
        add([x, y + 1.05, 1.14], [1.4, 2.1, .08], '#667068')
      }
      if (w > 40) {
        for (let i = 0; i < 4; i++) add([-9 + i * 5, y + .7, -d / 2 + 2], [3.4, .35, 1.7], '#354e5b')
      }
    }
    if (selected) add([0, .12, d / 2 + 2.5], [w, .15, .3], '#c18e3d')
    return items
  }, [w, d, h, levels, roof, selected])
  return <group>
    {levels > 0 && <mesh position={[0, levels * h / 2, -1.7]} castShadow receiveShadow><boxGeometry args={[w, levels * h, d - 3.4]}/><meshStandardMaterial map={plaster} roughness={.95}/></mesh>}
    <Blocks items={facade}/>
    {roof && <mesh position={[0, levels * h + .05, 0]} castShadow receiveShadow><boxGeometry args={[w + .3, .25, d + .3]}/><meshStandardMaterial map={roofMap} roughness={.95}/></mesh>}
  </group>
}

export function RoomFurniture({ room }: { room: Space }) {
  const items = useMemo(() => {
    const result: Block[] = []
    const add = (at: Vec3, size: Vec3, color: string) => result.push({ at, size, color })
    const desk = (x: number, z: number, computer = false) => {
      add([x, .85, z], [1.65, .12, .8], '#997953')
      for (const dx of [-.66, .66]) add([x + dx, .43, z], [.06, .8, .5], '#50584e')
      add([x, .48, z + .7], [.6, .1, .6], '#466460')
      add([x, .88, z + .98], [.62, .73, .08], '#466460')
      if (computer) { add([x, 1.22, z - .12], [.75, .48, .08], '#2e3e42'); add([x, .97, z + .18], [.65, .025, .2], '#454b48') }
    }
    if (room.kind === 'classroom' || room.kind === 'lab') {
      add([0, 1.6, -4.82], [Math.min(4, room.width - 1), 1.1, .07], '#315951')
      const cols = Math.min(6, Math.max(2, Math.floor((room.width - 2) / 2.3)))
      for (let col = 0; col < cols; col++) for (let row = 0; row < 3; row++) desk((col - (cols - 1) / 2) * 2.2, -1.8 + row * 1.9, room.kind === 'lab' && room.department !== 'Mechanical')
      desk(0, -3.8)
      if (room.kind === 'lab' && room.department === 'Mechanical') {
        for (const x of [-room.width / 3, room.width / 3]) { add([x, .8, -3.5], [2.2, 1.4, 1.4], '#6d897a'); add([x, 1.7, -3.5], [.6, .8, .8], '#465b52') }
      }
    } else if (room.kind === 'hod' || room.kind === 'staff') {
      desk(-1.3, -2, true)
      if (room.kind === 'staff') { desk(1.3, -2, true); desk(-1.3, 1.5, true); desk(1.3, 1.5, true) }
      else { add([1.4, .5, 1.4], [1.7, .5, .7], '#7f7861'); add([1.4, .95, 1.7], [1.7, .7, .12], '#7f7861') }
      add([room.width / 2 - .6, 1.15, -2.6], [.7, 2.2, 2.2], '#b2a188')
    } else if (room.kind === 'restroom') {
      for (let i = 0; i < 3; i++) { add([0, 1, -3.4 + i * 2.2], [room.width - .6, 2, .1], '#dedbd0'); add([1.3, .45, -2.6 + i * 2.2], [.65, .7, .85], '#eeeae0') }
      add([-1.7, .9, 3.4], [1.6, .15, .75], '#e7e2d6')
    }
    return result
  }, [room])
  return items.length ? <Blocks items={items}/> : null
}
