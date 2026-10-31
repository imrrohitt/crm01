import { lazy, Suspense } from 'react'
import type { SceneVariant } from './Scene3D'

const Scene3D = lazy(() => import('./Scene3D'))

export function Scene({ variant = 'hero' }: { variant?: SceneVariant }) {
  return (
    <Suspense fallback={<div className={`scene3d scene3d-${variant}`} aria-hidden="true" />}>
      <Scene3D variant={variant} />
    </Suspense>
  )
}
