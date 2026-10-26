'use client'
import { ArrowUpRight, ThumbsDown, ThumbsUp } from 'lucide-react'
import { CardContent } from '@/components/ui/card'
import { MagicCard } from '@/components/vendor/magic-card'
import { cn } from '@/lib/utils'
import { useFashion } from './context'
import type { ProductCardData } from './payload'

/**
 * 상품 이미지 타일. vercel/commerce의 GridTileImage + Label 구성을 따랐다: 정사각형(aspect-square) 타일에 이미지를
 * object-contain으로 두고, 아래쪽 반투명 블러 알약 안에 상품명과 가격 칩. 색만 loupe 톤(종이·먹)으로 바꿨다.
 */
export function ProductTile({ name, price, image, url, n, className, nameInLabel = 'always' }: {
  name: string
  price?: string
  image: string
  url: string
  n?: number
  className?: string
  /** 라벨 알약에 상품명을 넣을지: 좁은 타일은 이름이 잘리므로 가격 칩만 두고 이름은 타일 아래에 따로 쓴다 */
  nameInLabel?: 'always' | 'never'
}) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn('group/tile relative block aspect-square w-full overflow-hidden bg-card', className)}
    >
      {image
        ? (
          // 여러 쇼핑몰 CDN 이미지라 next/image 도메인 설정 대신 img
          // eslint-disable-next-line @next/next/no-img-element
          <img src={image} alt={name} loading="lazy" className="h-full w-full object-contain transition duration-500 ease-out group-hover/tile:scale-[1.04]" />
        )
        : <div className="grid h-full place-items-center text-xs text-ink/40">이미지 없음</div>}
      {n !== undefined && (
        <span className="absolute left-2.5 top-2.5 font-serif text-xl italic leading-none text-ink">{n}</span>
      )}
      <div className="absolute bottom-0 left-0 flex w-full p-2">
        <div className="flex max-w-full items-center rounded-full border border-ink/10 bg-paper/75 p-1 text-[11px] font-medium text-ink backdrop-blur-md">
          {nameInLabel === 'always' && <h3 className="mr-2 line-clamp-1 grow pl-2 leading-tight">{name}</h3>}
          {price && <p className="flex-none whitespace-nowrap rounded-full bg-ink px-2 py-1 text-paper">{price}</p>}
        </div>
      </div>
    </a>
  )
}

export function RatingButtons({ n, code, withLabel }: { n: number, code: string, withLabel?: boolean }) {
  const { ratings, rate, isResponding } = useFashion()
  const current = ratings[code] || 0
  const base = 'inline-flex h-8 items-center justify-center gap-1.5 rounded-full border text-xs transition-colors disabled:opacity-40'
  const size = withLabel ? 'px-3' : 'w-8'
  // 이미 눌린 버튼을 다시 누르면 평가 취소 (지도에서도 빠진다)
  return (
    <div className="flex gap-1.5">
      <button
        type="button"
        aria-label={current === 1 ? `${n}번 좋아요 취소` : `${n}번 좋아요`}
        aria-pressed={current === 1}
        disabled={isResponding}
        onClick={e => rate(n, code, current === 1 ? 0 : 1, e.currentTarget)}
        className={cn(base, size, current === 1 ? 'border-ink bg-ink text-paper' : 'border-ink/20 text-ink/70 hover:border-ink hover:text-ink')}
      >
        <ThumbsUp className="h-3.5 w-3.5" strokeWidth={1.5} />
        {withLabel && '좋아요'}
      </button>
      <button
        type="button"
        aria-label={current === -1 ? `${n}번 별로 취소` : `${n}번 별로`}
        aria-pressed={current === -1}
        disabled={isResponding}
        onClick={e => rate(n, code, current === -1 ? 0 : -1, e.currentTarget)}
        className={cn(base, size, current === -1 ? 'border-ink/60 bg-ink/10 text-ink' : 'border-ink/20 text-ink/70 hover:border-ink hover:text-ink')}
      >
        <ThumbsDown className="h-3.5 w-3.5" strokeWidth={1.5} />
        {withLabel && '별로'}
      </button>
    </div>
  )
}

export function ProductCard({ item, className }: { item: ProductCardData, className?: string }) {
  return (
    // data-fly-source: 좋아요를 누르면 이 안의 사진이 취향 지도로 날아간다
    <MagicCard className={cn('flex flex-col rounded-[4px]', className)} data-fly-source>
      <ProductTile name={item.name} price={item.price} image={item.image} url={item.url} n={item.n} nameInLabel="never" />
      <CardContent className="flex flex-1 flex-col gap-1.5 border-t border-ink/10 p-3">
        <div className="text-[10px] uppercase tracking-[0.18em] text-ink/50">{item.brand}</div>
        <h3 className="line-clamp-2 text-[13px] font-semibold leading-snug">{item.name}</h3>
        {item.reason && <p className="line-clamp-4 text-[12.5px] leading-relaxed text-ink/70">{item.reason}</p>}
        <div className="mt-auto flex items-center justify-between gap-2 pt-2">
          <RatingButtons n={item.n} code={item.code} />
          <a href={item.url} target="_blank" rel="noopener noreferrer" aria-label={`${item.name} 상품 보러가기`} className="inline-flex items-center gap-0.5 text-[11px] text-ink/60 underline-offset-4 hover:text-ink hover:underline">
            보러가기
            <ArrowUpRight className="h-3 w-3" />
          </a>
        </div>
      </CardContent>
    </MagicCard>
  )
}
