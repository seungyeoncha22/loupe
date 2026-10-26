'use client'
import { ArrowRight } from 'lucide-react'
import { ProductCard, ProductTile, RatingButtons } from './product-card'
import { useFashion } from './context'
import { SaveBrandButton } from './save-brand'
import { NEXT_MESSAGE, type ProductsPayload } from './payload'

export function ProductAnswer({ data }: { data: ProductsPayload }) {
  const { send, isResponding } = useFashion()
  return (
    <div className="space-y-5">
      {data.notice.length > 0 && (
        <div className="space-y-1 border-l border-ink/30 pl-3">
          {data.notice.map(text => <p key={text} className="text-[12.5px] leading-relaxed text-ink/60">{text}</p>)}
        </div>
      )}
      {data.intro && <p className="text-[14px] leading-relaxed">{data.intro}</p>}

      {data.items.length > 0 && (
        <div className="grid grid-cols-2 gap-3 xl:grid-cols-3">
          {data.items.map(item => <ProductCard key={item.code} item={item} />)}
        </div>
      )}

      {data.explore && (
        <section className="border border-brass/70 bg-card/60 p-4" data-fly-source>
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <h4 className="text-[13px] font-semibold">🔎 이런 스타일은 어때요?</h4>
            <span className="font-serif text-lg italic text-brass">{data.explore.style || data.explore.tag}</span>
          </div>
          <div className="flex gap-4">
            <ProductTile name={data.explore.name} price={data.explore.price} image={data.explore.image} url={data.explore.url} n={data.explore.n} nameInLabel="never" className="w-32 shrink-0 border border-ink/10" />
            <div className="flex min-w-0 flex-1 flex-col gap-1.5">
              <div className="text-[10px] uppercase tracking-[0.18em] text-ink/50">{data.explore.brand}</div>
              <div className="line-clamp-2 text-[13px] font-semibold leading-snug">{data.explore.name}</div>
              <p className="text-[12.5px] leading-relaxed text-ink/70">{data.explore.why}</p>
              <div className="mt-auto pt-1"><RatingButtons n={data.explore.n} code={data.explore.code} withLabel /></div>
            </div>
          </div>
        </section>
      )}

      {data.more_brands.length > 0 && (
        <section>
          <h4 className="mb-2 text-[12px] font-medium text-ink/55">이 스타일 브랜드 더 보기</h4>
          <ul className="divide-y divide-ink/10 border-y border-ink/10">
            {data.more_brands.map(b => (
              <li key={b.url} className="flex items-center gap-3 py-2.5">
                {b.product?.image && (
                  <a href={b.product.url} target="_blank" rel="noopener noreferrer" className="shrink-0">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={b.product.image} alt={b.product.name} loading="lazy" className="h-12 w-12 rounded-full border border-ink/10 bg-card object-cover" />
                  </a>
                )}
                <div className="min-w-0 flex-1">
                  <a href={b.url} target="_blank" rel="noopener noreferrer" className="font-serif text-lg leading-none hover:underline">{b.ko}</a>
                  <span className="ml-2 text-[11px] uppercase tracking-[0.15em] text-ink/40">{b.en}</span>
                  <div className="mt-1 truncate text-[12px] text-ink/60">{b.tags.join(' · ')}</div>
                </div>
                <SaveBrandButton brand={b} />
              </li>
            ))}
          </ul>
        </section>
      )}

      {data.next && (
        <button
          type="button"
          disabled={isResponding}
          onClick={() => send(NEXT_MESSAGE)}
          className="group inline-flex items-center gap-2 rounded-full border border-ink px-5 py-2.5 text-[13px] transition-colors hover:bg-ink hover:text-paper disabled:opacity-40"
        >
          다음 추천 보기
          <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" strokeWidth={1.5} />
        </button>
      )}
    </div>
  )
}
