'use client'
import { Ban, Check, Clock, ExternalLink, Instagram, Loader2, Pickaxe, Plus, Send, X } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import type { ReactNode } from 'react'
import { ProductTile } from '@/app/components/fashion/product-card'
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious } from '@/components/ui/carousel'
import type { BrandInfo } from './brands-data'
import { type RequestInfo, requestLabel } from './use-brand-requests'

/** 지도 위 브랜드 패널 틀. 데스크톱은 지도 오른쪽 위, 모바일은 지도 시트 아래쪽 */
function PanelShell({ label, children }: { label: string, children: ReactNode }) {
  const reduce = useReducedMotion()
  return (
    <motion.aside
      aria-label={label}
      className="absolute inset-x-0 bottom-0 z-20 max-h-[72%] overflow-y-auto rounded-[6px] border border-ink/15 bg-paper/95 p-4 shadow-[0_20px_50px_-30px_hsl(var(--ink)/0.5)] backdrop-blur-sm lg:inset-x-auto lg:bottom-auto lg:right-0 lg:top-0 lg:max-h-full lg:w-[330px]"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      transition={{ duration: reduce ? 0 : 0.25, ease: [0.22, 1, 0.36, 1] }}
      onClick={e => e.stopPropagation()}
    >
      {children}
    </motion.aside>
  )
}

function Head({ ko, en, url, external, note, onClose }: { ko: string, en: string, url: string, external?: boolean, note?: ReactNode, onClose: () => void }) {
  return (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
            <a href={url} target="_blank" rel="noopener noreferrer" className="font-serif text-2xl leading-none hover:underline">{ko}</a>
            {external && <span className="rounded-full border border-brass/60 px-1.5 py-px text-[10px] text-brass">미수록</span>}
          </div>
          {en && en.toLowerCase() !== ko.toLowerCase() && <div className="mt-1 text-[10px] uppercase tracking-[0.18em] text-ink/45">{en}</div>}
        </div>
        <button type="button" onClick={onClose} aria-label="패널 닫기" className="-mr-1 -mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full hover:bg-ink/5">
          <X className="h-4 w-4" strokeWidth={1.5} />
        </button>
      </div>
      {note && <div className="mt-1.5 text-[11.5px] text-brass">{note}</div>}
    </>
  )
}

function Products({ info }: { info?: BrandInfo }) {
  const products = info?.products ?? []
  if (!products.length)
    return null
  return (
    <Carousel opts={{ align: 'start', dragFree: true }} className="mt-3 w-full">
      <CarouselContent className="-ml-2">
        {products.map(p => (
          <CarouselItem key={p.url} className="basis-[40%] pl-2 lg:basis-[46%]">
            <ProductTile name={p.name} price={p.price != null ? `${p.price.toLocaleString('ko-KR')}원` : ''} image={p.image} url={p.url} nameInLabel="never" className="border border-ink/10" />
            <a href={p.url} target="_blank" rel="noopener noreferrer" className="mt-1 line-clamp-2 block text-[11px] leading-snug text-ink/70 hover:underline">{p.name}</a>
          </CarouselItem>
        ))}
      </CarouselContent>
      <CarouselPrevious className="left-1 top-[38%] hidden h-7 w-7 border-ink/20 bg-paper/90 shadow-none sm:flex" />
      <CarouselNext className="right-1 top-[38%] hidden h-7 w-7 border-ink/20 bg-paper/90 shadow-none sm:flex" />
    </Carousel>
  )
}

/** 미수록 브랜드: 자사몰·인스타 링크 */
function Links({ url, instagram }: { url: string, instagram?: string }) {
  const host = url.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '')
  return (
    <div className="mt-3 space-y-1.5 text-[12.5px]">
      <a href={url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-ink/75 hover:text-ink hover:underline">
        <ExternalLink className="h-3.5 w-3.5 shrink-0" strokeWidth={1.5} />
        자사몰
        {' '}
        <span className="truncate text-ink/50">{host}</span>
      </a>
      {instagram && (
        <a href={instagram} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-ink/75 hover:text-ink hover:underline">
          <Instagram className="h-3.5 w-3.5 shrink-0" strokeWidth={1.5} />
          인스타그램
          {' '}
          <span className="truncate text-ink/50">
            @
            {instagram.replace(/^https?:\/\/(www\.)?instagram\.com\//, '').replace(/\/$/, '')}
          </span>
        </a>
      )}
    </div>
  )
}

/**
 * 미수록 브랜드 "추가 요청"과 그 뒤 상태: 확인 중 → 추가 예정 → 추가됨 / 추가 불가(이유).
 * 요청하면 insta-crawler가 수집 가능 여부를 확인하고, 통과하면 매일 새벽 수집 뒤 자동으로 추가된다.
 */
function RequestStatus({ info, onRequest }: { info?: RequestInfo, onRequest: () => void }) {
  if (!info || info.status === 'error') {
    return (
      <button
        type="button"
        onClick={onRequest}
        className="inline-flex items-center gap-1.5 rounded-full border border-brass/70 px-3.5 py-2 text-[12.5px] text-brass transition-colors hover:bg-brass hover:text-paper"
      >
        <Send className="h-3.5 w-3.5" strokeWidth={1.5} />
        {info?.status === 'error' ? '다시 요청' : '추가 요청'}
      </button>
    )
  }
  const s = info.status
  const tone = s === 'added' ? 'border-ink bg-ink text-paper' : s === 'rejected' || s === 'gave_up' ? 'border-ink/25 text-ink/55' : 'border-brass/70 text-brass'
  const Icon = s === 'added' ? Check : s === 'rejected' || s === 'gave_up' ? Ban : s === 'queued' || s === 'adding' || s === 'failed' ? Clock : Loader2
  return (
    <span className="inline-flex items-center gap-1.5" role="status">
      <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[12px] ${tone}`}>
        <Icon className={`h-3.5 w-3.5 ${Icon === Loader2 ? 'animate-spin' : ''}`} strokeWidth={1.75} />
        {requestLabel(s)}
      </span>
    </span>
  )
}

/** 상태 아래 한 줄 설명 (추가 예정·불가 이유) */
function RequestNote({ info }: { info?: RequestInfo }) {
  if (!info)
    return null
  const text = info.status === 'checking' || info.status === 'sending'
    ? '자사몰에서 상품을 읽을 수 있는지 확인하고 있어요.'
    : info.status === 'queued' || info.status === 'adding'
      ? '매일 새벽 수집이 끝나면 자동으로 추가돼요.'
      : info.status === 'failed'
        ? `추가하다 멈춰서 다음 밤에 한 번 더 시도해요. (${info.reason})`
        : info.status === 'added'
          ? '추가됐어요. 지도에서 일반 브랜드로 바뀌어요.'
          : info.status === 'rejected' || info.status === 'gave_up'
            ? info.reason
            : ''
  return text ? <p className="mt-2 text-[11.5px] leading-relaxed text-ink/55">{text}</p> : null
}

function Why({ reason, mood }: { reason?: string, mood?: string[] }) {
  if (!reason && !mood?.length)
    return null
  return (
    <div className="mt-3 space-y-2 border-l border-brass/50 pl-3">
      {mood && mood.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-ink/50">공통 무드</span>
          {mood.map(m => <span key={m} className="rounded-full bg-ink/[0.06] px-2 py-0.5 text-[11.5px]">{m}</span>)}
        </div>
      )}
      {reason && <p className="text-[12.5px] leading-relaxed text-ink/75">{reason}</p>}
    </div>
  )
}

/** 지도에서 저장한 브랜드를 눌렀을 때: 대표 상품 캐러셀(미수록이면 자사몰·인스타) + 비슷한 브랜드 더 파보기 + 저장 취소 */
export function BrandPanel({ brand, info, external, fromKo, request, onRequest, onDig, digging, onUnsave, onClose }: {
  brand: { ko: string, en: string, url: string, tags: string[], instagram?: string }
  info?: BrandInfo
  external: boolean
  fromKo?: string
  request?: RequestInfo
  onRequest: () => void
  onDig: () => void
  digging: boolean
  onUnsave: () => void
  onClose: () => void
}) {
  return (
    <PanelShell label={`${brand.ko} 브랜드`}>
      <Head ko={brand.ko} en={brand.en} url={brand.url} external={external} note={fromKo && `${fromKo}에서 디깅해 찾은 브랜드`} onClose={onClose} />
      {brand.tags.length > 0 && <div className="mt-2 text-[12px] text-ink/60">{brand.tags.join(' · ')}</div>}
      {external ? <Links url={brand.url} instagram={brand.instagram} /> : <Products info={info} />}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onDig}
          disabled={digging}
          className="inline-flex items-center gap-1.5 rounded-full bg-ink px-4 py-2 text-[12.5px] text-paper transition-opacity hover:bg-ink/85 disabled:opacity-40"
        >
          <Pickaxe className="h-3.5 w-3.5" strokeWidth={1.5} />
          {digging ? '파 보는 중…' : '비슷한 브랜드 더 파보기'}
        </button>
        {external && <RequestStatus info={request} onRequest={onRequest} />}
        <button type="button" onClick={onUnsave} className="rounded-full px-3 py-2 text-[12.5px] text-ink/55 hover:text-ink hover:underline">저장 취소</button>
      </div>
      {external && <RequestNote info={request} />}
    </PanelShell>
  )
}

/**
 * 디깅 후보(점선 동그라미)를 눌렀을 때 미리보기. "지도에 추가"를 눌러야 저장되고, "괜찮아요"·닫기·지도 빈 곳을 누르면 후보가 사라진다.
 * 수집 브랜드는 대표 상품 캐러셀, 미수록 브랜드는 자사몰·인스타 링크와 "추가 요청".
 */
export function CandidatePanel({ ko, en, url, instagram, external, fromKo, info, reason, mood, request, onRequest, onAdd, onDismiss }: {
  ko: string
  en: string
  url: string
  instagram?: string
  external: boolean
  fromKo: string
  info?: BrandInfo
  reason?: string
  mood?: string[]
  request?: RequestInfo
  onRequest: () => void
  onAdd: () => void
  onDismiss: () => void
}) {
  return (
    <PanelShell label={`디깅 후보 ${ko}`}>
      <Head ko={ko} en={en} url={url} external={external} note={`${fromKo}에서 파 본 후보${external ? ' · 웹 검색' : ''}`} onClose={onDismiss} />
      <Why reason={reason} mood={mood} />
      {external ? <Links url={url} instagram={instagram} /> : <Products info={info} />}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button type="button" onClick={onAdd} className="inline-flex items-center gap-1.5 rounded-full bg-ink px-4 py-2 text-[12.5px] text-paper hover:bg-ink/85">
          <Plus className="h-3.5 w-3.5" strokeWidth={1.75} />
          지도에 추가
        </button>
        {external && <RequestStatus info={request} onRequest={onRequest} />}
        <button type="button" onClick={onDismiss} className="rounded-full px-3 py-2 text-[12.5px] text-ink/55 hover:text-ink hover:underline">괜찮아요</button>
      </div>
      {external && <RequestNote info={request} />}
    </PanelShell>
  )
}
