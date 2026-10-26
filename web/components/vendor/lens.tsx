'use client'
/**
 * Lens — magicui(magicuidesign/magicui, apps/www/registry/magicui/lens.tsx)를 다듬은 것. MIT (THIRD_PARTY_NOTICES.md 참고)
 *
 * 원본처럼 같은 내용을 한 번 더 그려 확대(scale)하고, 커서 위치의 원 모양 마스크로 그 부분만 보이게 한다.
 * 바꾼 점:
 * - 커서 위치를 React 상태 대신 motion value로 다뤄 마우스가 움직여도 리렌더가 없다 (마스크 위치만 바뀜)
 * - 렌즈 가장자리에 얇은 링을 그려 확대경처럼 보이게 했다
 * - 마우스에서만 동작 (터치·펜에서는 꺼짐), prefers-reduced-motion이면 꺼짐
 * - static/defaultPosition 모드는 뺐다
 */
import { AnimatePresence, motion, useMotionTemplate, useMotionValue, useReducedMotion, useTransform } from 'motion/react'
import { useState } from 'react'
import { cn } from '@/lib/utils'

interface LensProps {
  children: React.ReactNode
  zoomFactor?: number
  lensSize?: number
  className?: string
  /** 렌즈 가장자리 링 색 */
  ringColor?: string
}

export function Lens({ children, zoomFactor = 1.35, lensSize = 150, className, ringColor = 'hsl(var(--brass) / 0.8)' }: LensProps) {
  const reduce = useReducedMotion()
  const [hovering, setHovering] = useState(false)
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const r = lensSize / 2
  const mask = useMotionTemplate`radial-gradient(circle ${r}px at ${x}px ${y}px, black 100%, transparent 100%)`
  const origin = useMotionTemplate`${x}px ${y}px`
  const ringX = useTransform(x, v => v - r)
  const ringY = useTransform(y, v => v - r)

  const onMove = (e: React.PointerEvent<HTMLSpanElement>) => {
    if (e.pointerType !== 'mouse')
      return
    const rect = e.currentTarget.getBoundingClientRect()
    x.set(e.clientX - rect.left)
    y.set(e.clientY - rect.top)
  }

  return (
    // 버튼 안에도 넣을 수 있게 span(블록)으로 그린다
    <span
      className={cn('relative block', className)}
      onPointerEnter={e => e.pointerType === 'mouse' && !reduce && setHovering(true)}
      onPointerLeave={() => setHovering(false)}
      onPointerMove={onMove}
    >
      {children}
      <AnimatePresence>
        {hovering && (
          <>
            <motion.span
              aria-hidden
              className="pointer-events-none absolute inset-0 block overflow-hidden rounded-[inherit]"
              style={{ maskImage: mask, WebkitMaskImage: mask }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
            >
              <motion.span className="absolute inset-0 block" style={{ scale: zoomFactor, transformOrigin: origin }}>
                {children}
              </motion.span>
            </motion.span>
            <motion.span
              aria-hidden
              className="pointer-events-none absolute left-0 top-0 rounded-full"
              style={{ width: lensSize, height: lensSize, x: ringX, y: ringY, boxShadow: `0 0 0 1px ${ringColor}, 0 8px 24px -12px hsl(var(--ink) / 0.35)` }}
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.18 }}
            />
          </>
        )}
      </AnimatePresence>
    </span>
  )
}
