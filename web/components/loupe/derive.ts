import type { LoupeMessage } from './use-loupe-chat'
import { BRAND_SAVE_RE, type FashionPayload, type ProductCardData, RATING_BUTTON_RE, splitPayload } from '@/app/components/fashion/payload'

export interface ParsedMessage extends LoupeMessage {
  body: string
  payload: FashionPayload | null
}

export interface KnownProduct extends ProductCardData {
  style: string
  explore: boolean
}

export interface Derived {
  parsed: ParsedMessage[]
  /** 화면에 보일 메시지 (버튼 평가·브랜드 저장 질문, ✓ 답변은 뺀다) */
  visible: ParsedMessage[]
  /** 워크플로가 보낸 최신 평점 표 (코드 → 1/-1) */
  ratings: Record<string, number>
  /** 지금까지 카드로 나온 상품 (코드 → 카드 데이터). 지도 복원에 쓴다 */
  products: Map<string, KnownProduct>
}

export function derive(messages: LoupeMessage[]): Derived {
  const parsed: ParsedMessage[] = messages.map((m) => {
    if (m.role === 'user')
      return { ...m, body: m.text, payload: null }
    const { text, payload } = splitPayload(m.text)
    return { ...m, body: text, payload }
  })

  let ratings: Record<string, number> = {}
  const products = new Map<string, KnownProduct>()
  for (const m of parsed) {
    const p = m.payload
    if (!p)
      continue
    if (p.type === 'products' || p.type === 'rating')
      ratings = p.ratings || {}
    if (p.type === 'products') {
      for (const item of p.items)
        products.set(item.code, { ...item, style: item.style || '', explore: false })
      if (p.explore)
        products.set(p.explore.code, { ...p.explore, style: p.explore.style || p.explore.tag, explore: true })
    }
  }

  const visible: ParsedMessage[] = []
  let afterButtonRating = false
  for (const m of parsed) {
    if (m.role === 'user') {
      afterButtonRating = RATING_BUTTON_RE.test(m.text.trim()) || BRAND_SAVE_RE.test(m.text.trim())
      if (!afterButtonRating)
        visible.push(m)
      continue
    }
    if (m.payload?.type === 'rating')
      continue
    if (afterButtonRating && !m.payload)
      continue // 버튼 평가를 처리하는 중이거나 ✓
    visible.push(m)
  }
  return { parsed, visible, ratings, products }
}

/** 지도에 올릴 좋아요 상품 */
export function likedProducts(d: Derived, ratings: Record<string, number>): KnownProduct[] {
  return [...d.products.values()].filter(p => ratings[p.code] === 1)
}
