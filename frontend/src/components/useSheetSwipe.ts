import { useEffect } from 'react'
import type { RefObject } from 'react'
import { projectMomentum, rubberband, springStep } from '../utils/motion'

const SLOP_PX = 10 // movement before deciding between a horizontal swipe and a vertical scroll
const VELOCITY_WINDOW_MS = 100

/**
 * Touch swipes for a left-edge sheet on small screens: drag the open sheet left to close it,
 * or drag from the screen-edge strip to pull it open. The sheet tracks the finger 1:1,
 * rubber-bands past the open edge, projects flick momentum to choose open vs closed, and
 * settles on a spring that starts at the finger's velocity. Grabbing it mid-settle picks it
 * up where it is.
 */
export function useSheetSwipe(
  sheetRef: RefObject<HTMLElement>,
  scrimRef: RefObject<HTMLElement>,
  edgeRef: RefObject<HTMLElement>,
  open: boolean,
  setOpen: (open: boolean) => void,
) {
  useEffect(() => {
    const sheet = sheetRef.current
    const source = open ? sheet : edgeRef.current // where a drag can start in this state
    if (!sheet || !source) return
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const closedX = () => -sheet.offsetWidth

    let x = open ? 0 : closedX() // current offset; 0 = open
    let gesture: { id: number; grabX: number; grabY: number; baseX: number; dragging: boolean } | null = null
    let samples: { t: number; x: number }[] = []
    let frame = 0
    let suppressClick = false

    const render = (pos: number) => {
      const width = sheet.offsetWidth
      x = pos > 0 ? rubberband(pos, width) : pos
      sheet.style.transform = `translateX(${x}px)`
      sheet.style.visibility = 'visible' // a closed sheet is visibility:hidden via its class
      if (scrimRef.current) scrimRef.current.style.opacity = String(Math.max(0, 1 + x / width))
    }
    const clearInline = () => {
      sheet.style.transform = sheet.style.transition = sheet.style.visibility = ''
      if (scrimRef.current) scrimRef.current.style.opacity = scrimRef.current.style.transition = ''
    }
    const settle = (target: number, velocity: number) => {
      const start = performance.now()
      const p0 = x - target
      const finish = () => {
        frame = 0
        const willBeOpen = target === 0
        // Changing state: React's classes take over at this same position, and this effect's
        // cleanup clears the inline styles. Staying in the same state: clear them now.
        if (willBeOpen !== open) setOpen(willBeOpen)
        else clearInline()
      }
      if (reducedMotion) { render(target); finish(); return }
      const step = (now: number) => {
        const s = springStep(p0, velocity, (now - start) / 1000)
        render(target + s.position)
        if (Math.abs(s.position) < 0.5 && Math.abs(s.velocity) < 20) { render(target); finish(); return }
        frame = requestAnimationFrame(step)
      }
      frame = requestAnimationFrame(step)
    }

    const startDrag = (pointerId: number) => {
      if (!gesture) return
      gesture.dragging = true
      source.setPointerCapture(pointerId)
      sheet.style.transition = 'none'
      if (scrimRef.current) scrimRef.current.style.transition = 'none'
    }
    const onDown = (e: PointerEvent) => {
      if (e.pointerType === 'mouse' || window.innerWidth >= 768) return
      const interrupted = frame !== 0
      cancelAnimationFrame(frame)
      frame = 0
      gesture = { id: e.pointerId, grabX: e.clientX, grabY: e.clientY, baseX: x, dragging: false }
      samples = [{ t: e.timeStamp, x }]
      if (interrupted) startDrag(e.pointerId) // caught mid-flight: it's already a drag
    }
    const onMove = (e: PointerEvent) => {
      if (!gesture || e.pointerId !== gesture.id) return
      const dx = e.clientX - gesture.grabX
      const dy = e.clientY - gesture.grabY
      if (!gesture.dragging) {
        if (Math.abs(dy) > SLOP_PX && Math.abs(dy) > Math.abs(dx)) { gesture = null; return } // vertical scroll
        if (Math.abs(dx) < SLOP_PX) return
        startDrag(e.pointerId)
      }
      render(gesture.baseX + dx)
      samples.push({ t: e.timeStamp, x })
      samples = samples.filter((s) => e.timeStamp - s.t <= VELOCITY_WINDOW_MS)
    }
    const onUp = (e: PointerEvent) => {
      if (!gesture || e.pointerId !== gesture.id) return
      const wasDragging = gesture.dragging
      gesture = null
      if (!wasDragging) return
      suppressClick = true
      const first = samples[0]
      const last = samples[samples.length - 1]
      const dt = (last.t - first.t) / 1000
      const velocity = dt > 0 ? (last.x - first.x) / dt : 0
      settle(x + projectMomentum(velocity) < closedX() / 2 ? closedX() : 0, velocity)
    }
    // A drag that ends over a link must not also follow it
    const onClickCapture = (e: MouseEvent) => {
      if (!suppressClick) return
      suppressClick = false
      e.preventDefault()
      e.stopPropagation()
    }

    source.addEventListener('pointerdown', onDown)
    source.addEventListener('pointermove', onMove)
    source.addEventListener('pointerup', onUp)
    source.addEventListener('pointercancel', onUp)
    source.addEventListener('click', onClickCapture, true)
    return () => {
      cancelAnimationFrame(frame)
      source.removeEventListener('pointerdown', onDown)
      source.removeEventListener('pointermove', onMove)
      source.removeEventListener('pointerup', onUp)
      source.removeEventListener('pointercancel', onUp)
      source.removeEventListener('click', onClickCapture, true)
      clearInline()
    }
  }, [sheetRef, scrimRef, edgeRef, open, setOpen])
}
