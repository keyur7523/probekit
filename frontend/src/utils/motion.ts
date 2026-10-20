// Gesture physics from Apple's "Designing Fluid Interfaces" (WWDC 2018), in px and seconds.

/** Where a flick at `velocity` px/s would come to rest (scroll-style exponential deceleration). */
export function projectMomentum(velocity: number, decelerationRate = 0.998): number {
  return ((velocity / 1000) * decelerationRate) / (1 - decelerationRate)
}

/** Progressive resistance for `overshoot` px past a boundary on a `dimension`-px element. */
export function rubberband(overshoot: number, dimension: number, constant = 0.55): number {
  return (overshoot * dimension * constant) / (dimension + constant * Math.abs(overshoot))
}

/**
 * Critically damped spring (damping ratio 1.0): offset from the target and velocity after
 * `t` seconds, starting `p0` px away with velocity `v0` px/s. `response` is Apple's response.
 */
export function springStep(p0: number, v0: number, t: number, response = 0.3) {
  const omega = (2 * Math.PI) / response
  const decay = Math.exp(-omega * t)
  const c = v0 + omega * p0
  return { position: (p0 + c * t) * decay, velocity: (v0 - omega * c * t) * decay }
}
