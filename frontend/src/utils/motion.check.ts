// Self-check for the gesture physics (no test runner in this frontend). Run:
//   npx esbuild src/utils/motion.check.ts --bundle --platform=node --log-level=warning | node
import { projectMomentum, rubberband, springStep } from './motion'

const near = (a: number, b: number, tol = 1e-6) => Math.abs(a - b) <= tol
const check = (ok: boolean, what: string) => { if (!ok) throw new Error(`motion check failed: ${what}`) }

// Projection: 1000 px/s with d = 0.998 coasts 1 * 0.998 / 0.002 = 499 px; sign follows velocity
check(near(projectMomentum(1000), 499), 'projectMomentum(1000) = 499')
check(near(projectMomentum(-500), -249.5), 'projectMomentum(-500) = -249.5')
check(projectMomentum(0) === 0, 'no velocity, no coast')

// Rubber band: 100 px over on a 256 px sheet -> 100*256*0.55 / (256 + 55) ≈ 45.27; never exceeds the overshoot
check(near(rubberband(100, 256), 14080 / 311), 'rubberband(100, 256)')
// 1000 px over -> 140800 / 806 ≈ 174.7: resistance grows, and it approaches but never reaches the dimension
check(near(rubberband(1000, 256), 140800 / 806) && rubberband(1e9, 256) < 256, 'rubberband saturates below the dimension')
check(near(rubberband(-100, 256), -rubberband(100, 256)), 'rubberband is symmetric')

// Spring: starts where it was, with the given velocity, and settles to the target
const s0 = springStep(-200, 300, 0)
check(near(s0.position, -200) && near(s0.velocity, 300), 'spring starts at p0 with v0')
const s1 = springStep(-200, 300, 1)
check(Math.abs(s1.position) < 0.5 && Math.abs(s1.velocity) < 20, 'spring settles within 1 s at response 0.3')
// Critically damped from rest never overshoots
for (let t = 0; t <= 1; t += 0.01) check(springStep(-200, 0, t).position <= 1e-9, `no overshoot at t=${t.toFixed(2)}`)

console.log('motion checks passed')
