'use client'
import Lenis from 'lenis'
import 'lenis/dist/lenis.css'
import { motion, useReducedMotion, useScroll, useTransform } from 'motion/react'
import { useEffect, useRef } from 'react'
import { BlurText } from '@/components/vendor/blur-text'
import { Lens } from '@/components/vendor/lens'

export interface LensRect { x: number, y: number, r: number }

/** 렌즈 안쪽 면. Lens가 확대본을 한 번 더 그리므로 배경까지 이 안에 둔다 */
function LensFace() {
  return (
    <span className="relative grid h-full w-full place-items-center rounded-full bg-[radial-gradient(circle_at_35%_30%,hsl(var(--card))_0%,hsl(var(--paper))_55%,hsl(var(--secondary))_100%)] shadow-[inset_0_0_60px_hsl(var(--ink)/0.06)]">
      <span aria-hidden className="absolute inset-[7%] rounded-full border border-ink/10" />
      <span className="flex flex-col items-center gap-3">
        <span className="font-serif text-4xl italic md:text-5xl">look closer</span>
        <span className="text-[13px] tracking-wide text-ink/60">눌러서 들여다보기</span>
      </span>
    </span>
  )
}

/**
 * 첫 화면. 로고 하나 → 스크롤하면 로고가 작아지며 위로, 가운데 큰 동그라미(렌즈)가 천천히 떠오른다.
 * 스크롤은 Lenis(darkroomengineering/lenis)로 부드럽게, 스크롤 진행에 따른 변화는 motion의 useScroll.
 */
/** startAtLens: 채팅에서 돌아올 때는 로고가 올라가고 렌즈가 떠 있는 끝 지점에서 바로 보여 준다 */
export function Landing({ onEnter, startAtLens = false }: { onEnter: (lens: LensRect) => void, startAtLens?: boolean }) {
  const trackRef = useRef<HTMLDivElement>(null)
  const lensRef = useRef<HTMLButtonElement>(null)
  const reduce = useReducedMotion()

  useEffect(() => {
    const end = () => Math.max(0, (trackRef.current?.offsetHeight ?? 0) - window.innerHeight)
    if (startAtLens)
      window.scrollTo(0, end())
    if (reduce)
      return
    const lenis = new Lenis({ autoRaf: true, lerp: 0.08 })
    const raf = startAtLens ? requestAnimationFrame(() => lenis.scrollTo(end(), { immediate: true })) : 0
    return () => {
      cancelAnimationFrame(raf)
      lenis.destroy()
    }
  }, [reduce, startAtLens])

  const { scrollYProgress: p } = useScroll({ target: trackRef, offset: ['start start', 'end end'] })
  // 로고: 화면 가운데 큰 글자 → 위쪽 작은 글자
  const logoScale = useTransform(p, [0, 0.45], [1, 0.26])
  const logoY = useTransform(p, [0, 0.45], ['0vh', '-40vh'])
  const hintOpacity = useTransform(p, [0, 0.12], [1, 0])
  // 렌즈: 아래에서 천천히 떠오름
  const lensY = useTransform(p, [0.2, 0.8], ['55vh', '0vh'])
  const lensOpacity = useTransform(p, [0.2, 0.6], [0, 1])
  const lensScale = useTransform(p, [0.2, 0.8], [0.82, 1])
  const captionOpacity = useTransform(p, [0.7, 0.9], [0, 1])

  const enter = () => {
    const rect = lensRef.current?.getBoundingClientRect()
    if (rect)
      onEnter({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2, r: rect.width / 2 })
  }

  return (
    <div ref={trackRef} className="relative h-[280vh]">
      <div className="sticky top-0 flex h-[100svh] items-center justify-center overflow-hidden">
        <motion.h1
          style={{ scale: logoScale, y: logoY }}
          className="pointer-events-none absolute select-none font-serif text-[30vw] leading-none tracking-[-0.03em] md:text-[19vw]"
        >
          <BlurText text="loupe" delay={110} />
        </motion.h1>

        <motion.div style={{ opacity: hintOpacity }} className="absolute bottom-10 flex flex-col items-center gap-2 text-[11px] uppercase tracking-[0.3em] text-ink/50">
          scroll
          <span className="block h-8 w-px bg-ink/30" />
        </motion.div>

        <motion.div style={{ y: lensY, opacity: lensOpacity, scale: lensScale }} className="flex flex-col items-center gap-7">
          <button
            ref={lensRef}
            type="button"
            onClick={enter}
            aria-label="들여다보기 시작"
            className="relative aspect-square w-[min(68vw,420px)] rounded-full border border-ink/80 shadow-[0_30px_80px_-40px_hsl(var(--ink)/0.45)] transition-transform duration-500 ease-out hover:scale-[1.015] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ink focus-visible:ring-offset-8 focus-visible:ring-offset-paper"
          >
            {/* 커서를 올리면 렌즈 안이 살짝 확대돼 보인다 (magicui Lens 기반) */}
            <Lens className="h-full w-full overflow-hidden rounded-full" lensSize={140} zoomFactor={1.4}>
              <LensFace />
            </Lens>
          </button>
          <motion.p style={{ opacity: captionOpacity }} className="max-w-[18rem] text-center text-[13px] leading-relaxed text-ink/60">
            보석과 원단을 들여다보는 둥근 확대경처럼,
            <br />
            숨은 브랜드를 가까이 들여다봐요.
          </motion.p>
        </motion.div>
      </div>
    </div>
  )
}
