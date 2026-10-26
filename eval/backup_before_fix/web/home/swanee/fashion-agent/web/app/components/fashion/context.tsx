'use client'
import { createContext, useContext } from 'react'

/** 브랜드 저장 버튼이 넘기는 브랜드 정보 */
export interface SaveableBrand { ko: string, en: string, url: string, tags: string[] }

export interface FashionContextValue {
  /** 상품 코드 → 평점(1/-1). 워크플로가 내보낸 최신 평점 표 + 방금 누른 버튼 */
  ratings: Record<string, number>
  /** 1 좋아요, -1 별로, 0 취소(이미 눌린 버튼을 다시 누름). source는 누른 버튼 (좋아요 때 카드 사진이 지도로 날아가는 출발점) */
  rate: (n: number, code: string, v: 1 | -1 | 0, source?: HTMLElement) => void
  send: (message: string) => void
  isResponding: boolean
  /** 취향 지도에 저장한 브랜드 도메인 */
  savedBrands: Set<string>
  /** 브랜드 저장/저장 취소 */
  toggleBrand: (brand: SaveableBrand) => void
}

export const FashionContext = createContext<FashionContextValue>({
  ratings: {},
  rate: () => {},
  send: () => {},
  isResponding: false,
  savedBrands: new Set(),
  toggleBrand: () => {},
})

export const useFashion = () => useContext(FashionContext)
