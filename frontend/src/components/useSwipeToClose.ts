import { useEffect } from 'react'
import type { RefObject } from 'react'
import { projectMomentum, rubberband, springStep } from '../utils/motion'

const SLOP_PX = 10 // movement before deciding between a horizontal swipe and a vertical scroll
const VELOCITY_WINDOW_MS = 100

/**
 * Touch swipe-left to close a left-edge sheet: tracks the finger 1:1, rubber-bands past the
 * open edge, projects flick momentum to choose open vs closed, and settles on a spring that
 * starts at the finger's velocity. Grabbing the sheet mid-settle picks it up where it is.
 */
export function useSwipeToClose(
  sheetRef: RefObject<HTMLElement>,
  scrimRef: RefObject<HTMLElement>,
  open: boolean,
  onClose: () => void,
) {
  useEffect(() => {
    const sheet = sheetRef.current
    if (!sheet || !open) return
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    let x = 0 // current offset; 0 = open, -width = closed
    let gesture: { id: number; grabX: number; grabY: number; baseX: number; dragging: boolean } | null = null
    let samples: { t: number; x: number }[] = []
    let frame = 0
    let suppressClick = false

    const render = (pos: number) => {
      const width = sheet.offsetWidth
      x = pos > 0 ? rubberband(pos, width) : pos
      sheet.style.transform = `translateX(${x}px)`
      if (scrimRef.current) scrimRef.current.style.opacity = String(Math.max(0, 1 + x / width))
    }
    const clearInline = () => {
      sheet.style.transform = sheet.style.transition = ''
      if (scrimRef.current) scrimRef.current.style.opacity = scrimRef.current.style.transition = ''
    }
    const settle = (target: number, velocity: number) => {
      const start = performance.now()
      const p0 = x - target
      const finish = () => {
        frame = 0
        // Closing: React's closed classes take over at this same position; the effect cleanup clears inline styles
        if (target < 0) onClose()
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

    const onDown = (e: PointerEvent) => {
      if (e.pointerType === 'mouse' || window.innerWidth >= 768) return
      const interrupted = frame !== 0
      cancelAnimationFrame(frame)
      frame = 0
      gesture = { id: e.pointerId, grabX: e.clientX, grabY: e.clientY, baseX: x, dragging: false }
      samples = [{ t: e.timeStamp, x }]
      if (interrupted) startDrag(e.pointerId) // caught mid-flight: it's already a drag
    }
    const startDrag = (pointerId: number) => {
      if (!gesture) return
      gesture.dragging = true
      sheet.setPointerCapture(pointerId)
      sheet.style.transition = 'none'
      if (scrimRef.current) scrimRef.current.style.transition = 'none'
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
      const width = sheet.offsetWidth
      settle(x + projectMomentum(velocity) < -width / 2 ? -width : 0, velocity)
    }
    // A drag that ends over a link must not also follow it
    const onClickCapture = (e: MouseEvent) => {
      if (!suppressClick) return
      suppressClick = false
      e.preventDefault()
      e.stopPropagation()
    }

    sheet.addEventListener('pointerdown', onDown)
    sheet.addEventListener('pointermove', onMove)
    sheet.addEventListener('pointerup', onUp)
    sheet.addEventListener('pointercancel', onUp)
    sheet.addEventListener('click', onClickCapture, true)
    return () => {
      cancelAnimationFrame(frame)
      sheet.removeEventListener('pointerdown', onDown)
      sheet.removeEventListener('pointermove', onMove)
      sheet.removeEventListener('pointerup', onUp)
      sheet.removeEventListener('pointercancel', onUp)
      sheet.removeEventListener('click', onClickCapture, true)
      clearInline()
    }
  }, [sheetRef, scrimRef, open, onClose])
}
