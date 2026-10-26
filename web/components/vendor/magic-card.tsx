'use client'
/**
 * MagicCard — magicui(magicuidesign/magicui, apps/www/registry/magicui/magic-card.tsx)를 다듬은 것. MIT (THIRD_PARTY_NOTICES.md 참고)
 *
 * 바꾼 점: next-themes 다크 테마 분기와 orb 모드를 빼고, 'gradient' 모드의 테두리 하이라이트만 남겼다.
 * 커서를 따라 카드 테두리가 은은하게 황동색으로 비치는 정도의 마이크로 인터랙션 (터치 기기에서는 효과 없음).
 */
import { motion, useMotionTemplate, useMotionValue } from 'motion/react'
import { useCallback } from 'react'
import { cn } from '@/lib/utils'

interface MagicCardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'style' | 'onPointerMove' | 'onPointerLeave' | 'onAnimationStart' | 'onDrag' | 'onDragStart' | 'onDragEnd'> {
  children?: React.ReactNode
  className?: string
  gradientSize?: number
  /** 하이라이트 색 (기본 brass) */
  gradientFrom?: string
}

export function MagicCard({ children, className, gradientSize = 220, gradientFrom = 'hsl(var(--brass) / 0.55)', ...rest }: MagicCardProps) {
  const mouseX = useMotionValue(-gradientSize)
  const mouseY = useMotionValue(-gradientSize)
  const reset = useCallback(() => {
    mouseX.set(-gradientSize)
    mouseY.set(-gradientSize)
  }, [mouseX, mouseY, gradientSize])
  const onMove = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    if (e.pointerType !== 'mouse')
      return
    const rect = e.currentTarget.getBoundingClientRect()
    mouseX.set(e.clientX - rect.left)
    mouseY.set(e.clientY - rect.top)
  }, [mouseX, mouseY])

  return (
    <motion.div
      {...rest}
      className={cn('group relative isolate overflow-hidden border border-transparent', className)}
      onPointerMove={onMove}
      onPointerLeave={reset}
      style={{
        // magicui gradient 모드: 안쪽은 카드 배경, 테두리(border-box)만 커서 위치의 방사형 그라디언트
        background: useMotionTemplate`
          linear-gradient(hsl(var(--card)) 0 0) padding-box,
          radial-gradient(${gradientSize}px circle at ${mouseX}px ${mouseY}px, ${gradientFrom}, hsl(var(--border)) 100%) border-box
        `,
      }}
    >
      {children}
    </motion.div>
  )
}
