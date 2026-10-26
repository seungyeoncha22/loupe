// 워크플로가 답변 끝에 붙이는 숨은 JSON 블록(<!--fashion-ui {...} -->)의 형식과 해석.
// 블록은 Dify Code 노드("추가 제안", "유사 브랜드", "평가 기록")가 만든다. 마크다운은 읽지 않는다.

export interface ProductCardData {
  n: number
  code: string
  name: string
  brand: string
  price: string
  image: string
  url: string
  reason?: string
  /** 대표 스타일 1개 (취향 지도의 스타일 동그라미) */
  style?: string
  /** 상의/하의/아우터 (워크플로가 상품명으로 재확인한 값). 예전 답변에는 없다 */
  category?: string
  /** 브랜드 도메인. 예전 답변에는 없다 */
  domain?: string
}

export interface ExploreCardData extends ProductCardData {
  tag: string
  seed: string
  why: string
}

export interface MoreBrand {
  ko: string
  en: string
  url: string
  tags: string[]
  product: { name: string, url: string, image: string, price: string } | null
}

export interface ProductsPayload {
  v: 1
  type: 'products'
  notice: string[]
  intro: string
  items: ProductCardData[]
  explore: ExploreCardData | null
  more_brands: MoreBrand[]
  next: boolean
  ratings: Record<string, number>
}

export interface BrandProduct { name: string, price: string, image: string, url: string }
export interface BrandCardData {
  rank: number
  ko: string
  en: string
  url: string
  score_label: string
  score: number
  tags: string[]
  detail: string
  products: BrandProduct[]
}

export interface BrandsPayload {
  v: 1
  type: 'brands'
  mode: 'similar' | 'style'
  groups: { title: string, brands: BrandCardData[] }[]
}

export interface RatingPayload {
  v: 1
  type: 'rating'
  ratings: Record<string, number>
}

/** 맞는 상품이 없을 때 (검색 준비: 모르는 브랜드 / 후보 정리: 후보 0개). 웹 디깅 버튼을 보여 준다 */
export interface NoMatchPayload {
  v: 1
  type: 'no_match'
  reason: 'brand' | 'empty'
  /** 모르는 브랜드 이름 (reason=brand) */
  brand: string
  styles: string[]
  category?: string
  text: string
}

export type FashionPayload = ProductsPayload | BrandsPayload | RatingPayload | NoMatchPayload

const MARKER = '<!--fashion-ui '
const BLOCK_RE = /<!--fashion-ui (\{[\s\S]*\}) -->\s*$/

/** 답변 텍스트를 (보이는 텍스트, 데이터)로 나눈다. 스트리밍 중 아직 덜 온 블록은 텍스트에서만 숨긴다. */
export function splitPayload(content: string): { text: string, payload: FashionPayload | null } {
  const at = content.indexOf(MARKER)
  if (at < 0)
    return { text: content, payload: null }
  const text = content.slice(0, at).trimEnd()
  const m = content.match(BLOCK_RE)
  if (!m)
    return { text, payload: null }
  try {
    const payload = JSON.parse(m[1]) as FashionPayload
    return { text, payload: payload?.v === 1 ? payload : null }
  }
  catch {
    return { text, payload: null }
  }
}

/** 카드 버튼이 보내는 평가 메시지 ("1번 좋아 #k3f9"). 워크플로의 평가 기록 노드가 #코드로 정확한 상품을 찾는다.
 *  0은 이미 눌린 버튼을 다시 눌러 평가를 취소하는 것 ("1번 취소 #k3f9") */
export const ratingMessage = (n: number, code: string, v: 1 | -1 | 0) => `${n}번 ${v > 0 ? '좋아' : v < 0 ? '별로' : '취소'} #${code}`
export const RATING_BUTTON_RE = /^\d+번 (좋아|별로|취소) #[0-9a-z]{4}$/
/** 브랜드 저장 버튼이 보내는 숨은 메시지. 워크플로의 평가 기록 노드가 브랜드 좋아요와 같게 점수에 반영한다 */
export const brandSaveMessage = (domain: string, save: boolean) => `브랜드 저장${save ? '' : ' 취소'} @${domain}`
export const BRAND_SAVE_RE = /^브랜드 저장( 취소)? @[0-9a-z.-]+$/
export const NEXT_MESSAGE = '다음 추천 보기'
