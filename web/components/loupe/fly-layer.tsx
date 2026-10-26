'use client'
import { AnimatePresence, motion } from 'motion/react'

export interface Flight {
  id: number
  image: string
  from: { x: number, y: number, size: number }
  to: { x: number, y: number, size: number }
}

export const FLY_DURATION = 0.75

/**
 * 좋아요를 누르면 카드 사진이 둥글게 접히며 곡선을 그려 취향 지도의 그 상품 자리로 날아간다 (motion).
 * transform(x, y, scale)과 border-radius만 바꿔서 레이아웃을 다시 계산하지 않는다.
 */
export function FlyLayer({ flights, onDone }: { flights: Flight[], onDone: (id: number) => void }) {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-50">
      <AnimatePresence>
        {flights.map((f) => {
          const dx = f.to.x - f.from.x
          const dy = f.to.y - f.from.y
          const lift = Math.min(160, Math.abs(dx) * 0.25 + 60) // 위로 살짝 솟았다가 내려앉는 곡선
          return (
            <motion.img
              key={f.id}
              src={f.image}
              alt=""
              className="absolute object-cover shadow-[0_12px_30px_-12px_hsl(var(--ink)/0.5)]"
              style={{ left: f.from.x - f.from.size / 2, top: f.from.y - f.from.size / 2, width: f.from.size, height: f.from.size }}
              initial={{ x: 0, y: 0, scale: 1, borderRadius: '6%', opacity: 1 }}
              animate={{
                x: [0, dx * 0.45, dx],
                y: [0, dy * 0.45 - lift, dy],
                scale: [1, 0.75, f.to.size / f.from.size],
                borderRadius: ['6%', '50%', '50%'],
                opacity: [1, 1, 0.9],
              }}
              exit={{ opacity: 0, transition: { duration: 0.15 } }}
              transition={{ duration: FLY_DURATION, times: [0, 0.45, 1], ease: [0.45, 0, 0.2, 1] }}
              onAnimationComplete={() => onDone(f.id)}
            />
          )
        })}
      </AnimatePresence>
    </div>
  )
}
