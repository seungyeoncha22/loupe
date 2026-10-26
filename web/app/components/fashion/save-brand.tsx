'use client'
import { Bookmark } from 'lucide-react'
import { domainOf } from '@/components/loupe/map-store'
import { type SaveableBrand, useFashion } from './context'

/** 브랜드 저장 버튼 (취향 지도의 브랜드 구역에 올라간다). 다시 누르면 저장 취소 */
export function SaveBrandButton({ brand, className = '' }: { brand: SaveableBrand, className?: string }) {
  const { savedBrands, toggleBrand } = useFashion()
  const saved = savedBrands.has(domainOf(brand.url))
  return (
    <button
      type="button"
      onClick={() => toggleBrand(brand)}
      aria-pressed={saved}
      aria-label={saved ? `${brand.ko} 저장 취소` : `${brand.ko} 저장`}
      className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2.5 py-1 text-[11.5px] transition-colors ${saved ? 'border-brass bg-brass text-paper hover:bg-brass/85' : 'border-ink/25 text-ink/70 hover:border-ink hover:text-ink'} ${className}`}
    >
      <Bookmark className="h-3 w-3" strokeWidth={1.75} fill={saved ? 'currentColor' : 'none'} />
      {saved ? '저장됨' : '저장'}
    </button>
  )
}
