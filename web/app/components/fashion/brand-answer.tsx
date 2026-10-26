'use client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious } from '@/components/ui/carousel'
import { ProductTile } from './product-card'
import { SaveBrandButton } from './save-brand'
import type { BrandCardData, BrandsPayload } from './payload'

// shadcn/ui Card + Carousel을 그대로 쓰고 톤만 loupe(얇은 선, 세리프 브랜드명, 그림자 없음)로 바꿨다
function BrandCard({ brand }: { brand: BrandCardData }) {
  return (
    <Card className="rounded-[4px] border-ink/15 bg-card/70 shadow-none">
      <CardHeader className="space-y-1.5 p-4 pb-3">
        <CardTitle className="flex flex-wrap items-baseline gap-x-2 font-normal">
          <span className="font-serif text-base italic text-ink/40">{brand.rank}</span>
          <a href={brand.url} target="_blank" rel="noopener noreferrer" className="font-serif text-2xl leading-none hover:underline">{brand.ko}</a>
          <span className="text-[10px] uppercase tracking-[0.18em] text-ink/40">{brand.en}</span>
          <span className="ml-auto text-[11px] tabular-nums text-ink/50">
            {brand.score_label}
            {' '}
            {brand.score.toFixed(2)}
          </span>
        </CardTitle>
        <div className="flex items-center justify-between gap-3">
          <div className="text-[12px] text-ink/60">{brand.tags.join(' · ')}</div>
          <SaveBrandButton brand={brand} />
        </div>
        <CardDescription className="text-[12.5px] leading-relaxed text-ink/65">{brand.detail}</CardDescription>
      </CardHeader>
      {brand.products.length > 0 && (
        <CardContent className="p-4 pt-0">
          {/* 대표 상품 캐러셀: 손가락이나 트랙패드로 넘기고, 넓은 화면은 화살표도 쓴다 */}
          <Carousel opts={{ align: 'start', dragFree: true }} className="w-full">
            <CarouselContent className="-ml-2.5">
              {brand.products.map(p => (
                <CarouselItem key={p.url} className="basis-[44%] pl-2.5 sm:basis-1/3">
                  <ProductTile name={p.name} price={p.price} image={p.image} url={p.url} nameInLabel="never" className="border border-ink/10" />
                  <a href={p.url} target="_blank" rel="noopener noreferrer" className="mt-1.5 line-clamp-2 block text-[11.5px] leading-snug text-ink/75 hover:underline">
                    {p.name}
                  </a>
                </CarouselItem>
              ))}
            </CarouselContent>
            <CarouselPrevious className="left-1 top-[38%] hidden h-7 w-7 border-ink/20 bg-paper/90 shadow-none sm:flex" />
            <CarouselNext className="right-1 top-[38%] hidden h-7 w-7 border-ink/20 bg-paper/90 shadow-none sm:flex" />
          </Carousel>
        </CardContent>
      )}
    </Card>
  )
}

export function BrandAnswer({ data }: { data: BrandsPayload }) {
  return (
    <div className="space-y-5">
      {data.groups.map(group => (
        <section key={group.title} className="space-y-3">
          <h2 className="font-serif text-xl leading-snug">{group.title}</h2>
          {group.brands.map(b => <BrandCard key={b.url} brand={b} />)}
        </section>
      ))}
    </div>
  )
}
