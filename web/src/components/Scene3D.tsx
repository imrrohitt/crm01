import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js'

export type SceneVariant = 'hero' | 'banner' | 'mini'

/**
 * A glossy 3D chat-bubble emblem (the product's symbol) with orbiting pearls and a chrome ring.
 * Lazy-loaded so three.js stays out of the main bundle. Falls back to nothing if WebGL is missing.
 */
export default function Scene3D({ variant = 'hero' }: { variant?: SceneVariant }) {
  const host = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = host.current
    if (!el) return
    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' })
    } catch {
      return
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.05
    el.appendChild(renderer.domElement)
    renderer.domElement.style.cssText = 'width:100%;height:100%;display:block'

    const scene = new THREE.Scene()
    const pmrem = new THREE.PMREMGenerator(renderer)
    const env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
    scene.environment = env

    const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100)
    camera.position.set(0, 0.1, variant === 'mini' ? 7.2 : 8.2)

    const key = new THREE.DirectionalLight(0xffffff, 2.2)
    key.position.set(3, 4, 5)
    const rimA = new THREE.PointLight(0xff4fa3, 60, 20)
    rimA.position.set(-4, -1, 3)
    const rimB = new THREE.PointLight(0x6d8bff, 55, 20)
    rimB.position.set(4, 2, -2)
    scene.add(key, rimA, rimB)

    const group = new THREE.Group()
    scene.add(group)

    // --- bubble emblem
    const bodyMat = new THREE.MeshPhysicalMaterial({
      color: 0x6a45ff, metalness: 0.2, roughness: 0.16, clearcoat: 1, clearcoatRoughness: 0.08,
      iridescence: 0.9, iridescenceIOR: 1.4, sheen: 1, sheenColor: new THREE.Color(0xff7ac8), envMapIntensity: 1.25,
    })
    const bubble = new THREE.Group()
    const body = new THREE.Mesh(new RoundedBoxGeometry(2.6, 1.8, 0.9, 10, 0.55), bodyMat)
    const tail = new THREE.Mesh(new THREE.ConeGeometry(0.42, 0.7, 4, 1), bodyMat)
    tail.position.set(-0.75, -1.12, 0)
    tail.rotation.set(0, Math.PI / 4, Math.PI)
    tail.scale.set(1, 1, 0.9)
    const pearl = new THREE.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.12, metalness: 0.05, clearcoat: 1, envMapIntensity: 1.6 })
    const dots = [-0.62, 0, 0.62].map((x) => {
      const d = new THREE.Mesh(new THREE.SphereGeometry(0.21, 48, 48), pearl)
      d.position.set(x, 0.02, 0.5)
      return d
    })
    bubble.add(body, tail, ...dots)
    bubble.rotation.set(0.12, -0.35, 0.06)
    group.add(bubble)

    // --- chrome ring + orbiting pearls
    const ringMat = new THREE.MeshPhysicalMaterial({ color: 0xf6d9c4, metalness: 1, roughness: 0.14, envMapIntensity: 1.5 })
    const ring = new THREE.Mesh(new THREE.TorusGeometry(2.45, 0.055, 32, 220), ringMat)
    ring.rotation.set(Math.PI / 2.35, 0.25, 0)
    if (variant !== 'mini') group.add(ring)

    const orbiters: { mesh: THREE.Mesh; r: number; speed: number; phase: number; tilt: number }[] = []
    const colors = [0xff6aa8, 0xffb86b, 0x8aa4ff, 0xffffff, 0xc4a8ff]
    const count = variant === 'hero' ? 9 : variant === 'banner' ? 5 : 0
    for (let i = 0; i < count; i++) {
      const size = 0.07 + (i % 3) * 0.05
      const mesh = new THREE.Mesh(
        new THREE.SphereGeometry(size, 32, 32),
        new THREE.MeshPhysicalMaterial({ color: colors[i % colors.length], roughness: 0.14, metalness: i % 2 ? 0.8 : 0.1, clearcoat: 1, envMapIntensity: 1.4 }),
      )
      group.add(mesh)
      orbiters.push({ mesh, r: 2.2 + (i % 4) * 0.45, speed: 0.18 + (i % 5) * 0.05, phase: (i / count) * Math.PI * 2, tilt: (i % 3) * 0.5 - 0.5 })
    }

    const pointer = { x: 0, y: 0 }
    const onMove = (e: PointerEvent) => {
      const r = el.getBoundingClientRect()
      pointer.x = ((e.clientX - r.left) / r.width - 0.5) * 2
      pointer.y = ((e.clientY - r.top) / r.height - 0.5) * 2
    }
    window.addEventListener('pointermove', onMove, { passive: true })

    const resize = () => {
      const w = el.clientWidth || 1
      const h = el.clientHeight || 1
      renderer.setSize(w, h, false)
      camera.aspect = w / h
      // keep the emblem fully visible on narrow containers
      const fit = Math.max(1, 1.35 / camera.aspect)
      camera.position.z = (variant === 'mini' ? 7.2 : 8.2) * (variant === 'hero' ? Math.min(fit, 1.6) : Math.min(fit, 1.3))
      camera.updateProjectionMatrix()
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(el)

    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let visible = true
    const io = new IntersectionObserver(([entry]) => (visible = entry.isIntersecting))
    io.observe(el)

    const clock = new THREE.Clock()
    let raf = 0
    const frame = () => {
      raf = requestAnimationFrame(frame)
      if (!visible && !reduce) return
      const t = reduce ? 0 : clock.getElapsedTime()
      group.rotation.y += ((pointer.x * 0.45) - group.rotation.y) * 0.05
      group.rotation.x += ((pointer.y * 0.25) - group.rotation.x) * 0.05
      bubble.position.y = Math.sin(t * 0.9) * 0.14
      bubble.rotation.y = -0.35 + Math.sin(t * 0.5) * 0.18
      bubble.rotation.z = 0.06 + Math.sin(t * 0.7) * 0.03
      ring.rotation.z = t * 0.12
      dots.forEach((d, i) => (d.position.y = 0.02 + Math.sin(t * 2.2 + i * 0.9) * 0.05))
      orbiters.forEach((o) => {
        const a = t * o.speed + o.phase
        o.mesh.position.set(Math.cos(a) * o.r, Math.sin(a * 1.3) * 0.9 + o.tilt, Math.sin(a) * o.r * 0.55)
      })
      renderer.render(scene, camera)
    }
    frame()
    if (reduce) cancelAnimationFrame(raf)

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      io.disconnect()
      window.removeEventListener('pointermove', onMove)
      scene.traverse((o) => {
        const m = o as THREE.Mesh
        m.geometry?.dispose()
        const mat = m.material as THREE.Material | THREE.Material[] | undefined
        if (Array.isArray(mat)) mat.forEach((x) => x.dispose())
        else mat?.dispose()
      })
      env.dispose()
      pmrem.dispose()
      renderer.dispose()
      renderer.domElement.remove()
    }
  }, [variant])

  return <div ref={host} className={`scene3d scene3d-${variant}`} aria-hidden="true" />
}
