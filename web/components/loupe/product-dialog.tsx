'use client'
import { X } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect } from 'react'
import { FashionContext, useFashion } from '@/app/components/fashion/context'
import { ProductCard } from '@/app/components/fashion/product-card'
import type { ProductCardData } from '@/app/components/fashion/payload'

type DialogProduct = Omit<ProductCardData, 'n'> & { n?: number, style: string, explore: boolean }

/**
 * 지도에서 상품 동그라미를 누르면 그 상품 카드를 다시 연다 (👍/👎도 그대로 동작).
 * 지금 대화에 없는 상품(예전 대화에서 좋아요한 것)은 워크플로가 그 상품을 모르므로, 버튼은 지도에서 빼는 데만 쓴다 (onRemove)
 */
export function ProductDialog({ product, onClose, onRemove }: { product: DialogProduct | null, onClose: () => void, onRemove?: () => void }) {
  const fashion = useFashion()
  useEffect(() => {
    if (!product)
      return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [product, onClose])

  return (
    <AnimatePresence>
      {product && (
        <motion.div
          className="fixed inset-0 z-50 grid place-items-center bg-ink/30 p-6 backdrop-blur-[2px]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={product.name}
            className="relative w-full max-w-[300px]"
            initial={{ y: 12, scale: 0.98 }}
            animate={{ y: 0, scale: 1 }}
            exit={{ y: 8, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
            onClick={e => e.stopPropagation()}
          >
            <button type="button" onClick={onClose} aria-label="닫기" className="absolute -right-3 -top-3 z-10 grid h-8 w-8 place-items-center rounded-full bg-ink text-paper">
              <X className="h-4 w-4" strokeWidth={1.5} />
            </button>
            {product.style && <p className="mb-2 text-center font-serif text-lg italic text-paper drop-shadow">{product.style}</p>}
            {onRemove
              ? (
                <FashionContext.Provider value={{ ...fashion, ratings: { [product.code]: 1 }, rate: (_n, _c, v) => v !== 1 && onRemove() }}>
                  <ProductCard item={{ ...product, n: product.n ?? 0 }} className={product.explore ? 'border-brass' : undefined} />
                </FashionContext.Provider>
              )
              : <ProductCard item={{ ...product, n: product.n ?? 0 }} className={product.explore ? 'border-brass' : undefined} />}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
