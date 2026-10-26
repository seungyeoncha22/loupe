'use client'
import { useCallback, useEffect, useState } from 'react'

/**
 * 취향 지도 저장소. 대화와 분리해 브라우저(localStorage)에 둔다 — 새 대화를 시작해도 남고, '지도 초기화'로만 지운다.
 * - products: 좋아요한 상품
 * - brands: 저장한 브랜드. from이 있으면 그 브랜드에서 디깅해서 찾은 것 (지도의 디깅 경로)
 */
export interface MapProduct {
  code: string
  name: string
  brand: string
  price: string
  image: string
  url: string
  style: string
  category: '상의' | '하의' | '아우터'
  domain: string
  explore: boolean
  likedAt: number
}

export interface MapBrand {
  domain: string
  ko: string
  en: string
  url: string
  tags: string[]
  /** 디깅으로 찾았으면 출발 브랜드 */
  from: string | null
  savedAt: number
  /** 웹 검색으로 찾은 미수록 브랜드의 인스타 주소 (수집 브랜드인지는 brands.json으로 판단한다) */
  instagram?: string
  /** 디깅 후보일 때 보인 비슷한 이유 */
  reason?: string
  /** 미수록일 때 저장해서 아직 워크플로 취향 점수에 반영하지 못함 (수집 브랜드가 되면 반영) */
  botPending?: boolean
}

export interface MapData {
  products: Record<string, MapProduct>
  brands: Record<string, MapBrand>
  /** 지도 저장소가 생기기 전 대화의 좋아요를 한 번 옮겨 왔는지 (초기화 후 다시 옮겨 오지 않게) */
  seeded?: boolean
}

const KEY = 'loupe:map:v1'
const EMPTY: MapData = { products: {}, brands: {} }

function read(): MapData {
  try {
    const raw = localStorage.getItem(KEY)
    const parsed = raw ? JSON.parse(raw) : null
    return parsed && typeof parsed === 'object' ? { products: parsed.products || {}, brands: parsed.brands || {}, seeded: !!parsed.seeded } : EMPTY
  }
  catch {
    return EMPTY
  }
}

export function domainOf(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, '').toLowerCase()
  }
  catch {
    return ''
  }
}

const clamp = (v: number) => Math.max(-3, Math.min(3, Math.round(v * 100) / 100))

/**
 * 새 대화의 첫 메시지에 Dify 입력(taste)으로 넘기는 저장된 취향. 워크플로의 with_taste가 이 값을 바닥에 깐다.
 * 점수는 대화 안의 평가와 같은 규칙: 좋아요한 상품·저장한 브랜드마다 브랜드 +1, 스타일(브랜드 태그) +0.5
 */
export function tasteInput(map: MapData) {
  const brands: Record<string, number> = {}
  const tags: Record<string, number> = {}
  for (const p of Object.values(map.products)) {
    if (p.domain)
      brands[p.domain] = clamp((brands[p.domain] || 0) + 1)
    if (p.style)
      tags[p.style] = clamp((tags[p.style] || 0) + 0.5)
  }
  for (const b of Object.values(map.brands)) {
    brands[b.domain] = clamp((brands[b.domain] || 0) + 1)
    for (const t of b.tags)
      tags[t] = clamp((tags[t] || 0) + 0.5)
  }
  if (!Object.keys(brands).length && !Object.keys(tags).length)
    return ''
  const liked_urls = Object.values(map.products).sort((a, b) => a.likedAt - b.likedAt).map(p => p.url).slice(-30)
  return JSON.stringify({ brands, tags, liked_urls })
}

export function useMapStore() {
  const [map, setMap] = useState<MapData>(EMPTY)
  const [ready, setReady] = useState(false)
  useEffect(() => {
    setMap(read())
    setReady(true)
  }, [])

  const update = useCallback((fn: (prev: MapData) => MapData) => {
    setMap((prev) => {
      const next = fn(prev)
      try {
        localStorage.setItem(KEY, JSON.stringify(next))
      }
      catch {}
      return next
    })
  }, [])

  const addProducts = useCallback((items: MapProduct[]) => update((prev) => {
    const fresh = items.filter(p => !prev.products[p.code])
    if (!fresh.length)
      return prev
    return { ...prev, products: { ...prev.products, ...Object.fromEntries(fresh.map(p => [p.code, p])) } }
  }), [update])
  const removeProducts = useCallback((codes: string[]) => update((prev) => {
    if (!codes.some(c => prev.products[c]))
      return prev
    const products = { ...prev.products }
    codes.forEach(c => delete products[c])
    return { ...prev, products }
  }), [update])
  const saveBrand = useCallback((b: MapBrand) => update(prev => prev.brands[b.domain] ? prev : { ...prev, brands: { ...prev.brands, [b.domain]: b } }), [update])
  const removeBrand = useCallback((domain: string) => update((prev) => {
    if (!prev.brands[domain])
      return prev
    const brands = { ...prev.brands }
    delete brands[domain]
    // 이 브랜드에서 디깅해 찾은 브랜드는 남기되, 출발점이 사라졌으니 경로만 끊는다
    for (const [d, b] of Object.entries(brands)) {
      if (b.from === domain)
        brands[d] = { ...b, from: null }
    }
    return { ...prev, brands }
  }), [update])
  const patchBrand = useCallback((domain: string, patch: Partial<MapBrand>) => update(prev => prev.brands[domain]
    ? { ...prev, brands: { ...prev.brands, [domain]: { ...prev.brands[domain], ...patch } } }
    : prev), [update])
  const markSeeded = useCallback(() => update(prev => prev.seeded ? prev : { ...prev, seeded: true }), [update])
  const reset = useCallback(() => update(() => ({ ...EMPTY, seeded: true })), [update])

  return { map, ready, addProducts, removeProducts, saveBrand, removeBrand, patchBrand, markSeeded, reset }
}
