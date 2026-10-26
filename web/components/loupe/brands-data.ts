'use client'
import { useEffect, useState } from 'react'

/** public/brands.json — insta-crawler/export_brand_similarity.py가 만드는 수집 브랜드 데이터 (디깅, 발견 진행 표시용) */
export interface SimilarBrand {
  domain: string
  /** 비슷한 이유 (유사도 계산 근거) */
  reason: string
  /** 공통 무드 (겹치는 스타일 태그) */
  mood: string[]
}
export interface BrandInfo {
  ko: string
  en: string
  url: string
  tags: string[]
  products: { name: string, price: number | null, image: string, url: string, category: string }[]
  /** 비슷한 수집 브랜드 (유사도 순) */
  similar: SimilarBrand[]
}
/** total = 수집 브랜드 수 (브랜드를 추가하면 같이 바뀐다) */
export interface BrandsData { total: number, brands: Record<string, BrandInfo> }

/** 웹 검색으로 찾은 미수록 브랜드 후보 (/api/dig) */
export interface WebCandidate { name: string, en: string, url: string, domain: string, instagram: string, reason: string, mood: string[] }

let cache: Promise<BrandsData | null> | null = null
const listeners = new Set<() => void>()

/** 브랜드가 새로 추가됐을 때(자동 추가 대기열) brands.json을 다시 읽는다 */
export function reloadBrandsData() {
  cache = null
  listeners.forEach(fn => fn())
}

export function useBrandsData() {
  const [data, setData] = useState<BrandsData | null>(null)
  const [version, setVersion] = useState(0)
  useEffect(() => {
    const bump = () => setVersion(v => v + 1)
    listeners.add(bump)
    return () => {
      listeners.delete(bump)
    }
  }, [])
  useEffect(() => {
    cache ??= fetch('/brands.json', { cache: 'no-cache' }).then(r => (r.ok ? r.json() : null)).catch(() => null)
    let alive = true
    cache.then(d => alive && d && setData(d))
    return () => {
      alive = false
    }
  }, [version])
  return data
}
