'use client'
/**
 * BlurText — react-bits(DavidHDev/react-bits, src/ts-tailwind/TextAnimations/BlurText)의 'blur' 효과를 다듬은 것.
 * Copyright (c) 2026 David Haz. MIT + Commons Clause (THIRD_PARTY_NOTICES.md 참고)
 *
 * 바꾼 점: 효과 5종·트리거 4종·exit 애니메이션을 빼고, 로고처럼 짧은 단어를 글자 단위로 흐림 → 선명하게 한 번 등장시키는
 * 'blur' 효과만 남겼다. prefers-reduced-motion이면 바로 선명한 상태가 된다.
 */
import { motion, useReducedMotion } from 'motion/react'
import { useMemo } from 'react'

interface BlurTextProps {
  text: string
  className?: string
  /** 글자 사이 간격(ms) */
  delay?: number
  /** 한 단계 길이(s). 흐림 → 반쯤 → 선명 세 단계 */
  stepDuration?: number
  /** 시작 위치(px). 아래에서 위로 */
  distance?: number
  blur?: number
}

export function BlurText({ text, className, delay = 90, stepDuration = 0.35, distance = 18, blur = 10 }: BlurTextProps) {
  const reduce = useReducedMotion()
  const letters = useMemo(() => Array.from(text), [text])
  // react-bits 'blur' 효과의 스냅샷: from → steps[0] → steps[1]
  const from = { filter: `blur(${blur}px)`, opacity: 0, y: distance }
  const to = {
    filter: [`blur(${blur}px)`, `blur(${blur / 2}px)`, 'blur(0px)'],
    opacity: [0, 0.5, 1],
    y: [distance, -distance / 10, 0],
  }
  return (
    <span className={className} aria-label={text}>
      {letters.map((ch, i) => (
        <motion.span
          key={i}
          aria-hidden
          className="inline-block will-change-[transform,filter,opacity]"
          initial={from}
          // 줄인 동작이어도 최종 상태로는 간다 (첫 렌더에는 설정을 아직 몰라 흐린 상태로 시작하므로) — 시간만 0
          animate={reduce ? { filter: 'blur(0px)', opacity: 1, y: 0 } : to}
          transition={reduce ? { duration: 0 } : { duration: stepDuration * 2, times: [0, 0.5, 1], delay: (i * delay) / 1000, ease: 'easeOut' }}
        >
          {ch === ' ' ? ' ' : ch}
        </motion.span>
      ))}
    </span>
  )
}
