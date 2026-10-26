'use client'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useCallback, useEffect, useState } from 'react'
import { PaperGrain } from '@/components/vendor/paper-grain'
import { ChatShell } from './chat-shell'
import { Landing, type LensRect } from './landing'

type Phase = 'landing' | 'opening' | 'chat'

/**
 * 첫 화면 → (렌즈를 누르면 그 자리에서 동그라미가 화면 전체로 퍼지며) → 채팅.
 * 퍼지는 전환은 motion으로 clip-path 원의 반지름을 키운다.
 * 채팅 화면은 한 번 열면 계속 띄워 둔 채 숨기기만 한다 — 로고나 브라우저 뒤로가기로 첫 화면에 돌아갔다가
 * 다시 렌즈를 누르면 하던 대화와 지도가 그대로 이어진다. 채팅에 들어갈 때 기록(history)을 하나 쌓아 뒤로가기가 첫 화면으로 온다.
 */
export function LoupeApp() {
  const [phase, setPhase] = useState<Phase>('landing')
  const [lens, setLens] = useState<LensRect | null>(null)
  const [entered, setEntered] = useState(false)
  const reduce = useReducedMotion()

  useEffect(() => {
    // 뒤로가기 때 브라우저가 예전 스크롤 위치(맨 위)를 되살리지 않게 — 첫 화면은 렌즈가 보이는 곳으로 직접 옮긴다
    history.scrollRestoration = 'manual'
    // 새로고침하면 첫 화면부터 시작하므로, 남아 있는 '채팅' 기록 표시는 지운다
    if (history.state?.loupe === 'chat')
      history.replaceState(null, '')
    const onPop = (e: PopStateEvent) => {
      if (e.state?.loupe === 'chat') {
        setEntered(true)
        setPhase('chat') // 앞으로 가기
      }
      else {
        setPhase('landing')
      }
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const enter = (rect: LensRect) => {
    setLens(rect)
    setPhase('opening')
  }
  const goHome = useCallback(() => {
    if (history.state?.loupe === 'chat')
      history.back() // popstate가 첫 화면으로 돌린다
    else
      setPhase('landing')
  }, [])

  return (
    <main className="relative min-h-[100svh]">
      <PaperGrain />
      <div className="relative z-10">
        {phase !== 'chat' && <Landing onEnter={enter} startAtLens={entered} />}
        {entered && (
          <div hidden={phase !== 'chat'}>
            <ChatShell onHome={goHome} />
          </div>
        )}
      </div>
      <AnimatePresence>
        {phase === 'opening' && lens && (
          <motion.div
            key="opening"
            className="fixed inset-0 z-50 bg-paper"
            initial={{ clipPath: `circle(${lens.r}px at ${lens.x}px ${lens.y}px)` }}
            animate={{ clipPath: `circle(${Math.hypot(window.innerWidth, window.innerHeight)}px at ${lens.x}px ${lens.y}px)` }}
            exit={{ opacity: 0 }}
            transition={{ duration: reduce ? 0.01 : 0.7, ease: [0.65, 0, 0.35, 1] }}
            onAnimationComplete={() => {
              window.scrollTo(0, 0)
              // onAnimationComplete가 두 번 불릴 수 있어, 이미 채팅 기록이면 쌓지 않는다
              if (history.state?.loupe !== 'chat')
                history.pushState({ ...history.state, loupe: 'chat' }, '')
              setEntered(true)
              setPhase('chat')
            }}
          />
        )}
      </AnimatePresence>
    </main>
  )
}
