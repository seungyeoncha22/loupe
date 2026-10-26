'use client'
import { Eraser, RotateCcw, X } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { FashionContext, type SaveableBrand } from '@/app/components/fashion/context'
import { brandSaveMessage, ratingMessage } from '@/app/components/fashion/payload'
import { BrandPanel, CandidatePanel } from './brand-panels'
import { type WebCandidate, reloadBrandsData, useBrandsData } from './brands-data'
import { PRODUCT_ZONES, nameCategory } from './category'
import { ChatPanel } from './chat-panel'
import { type KnownProduct, derive } from './derive'
import { type Flight, FLY_DURATION, FlyLayer } from './fly-layer'
import { ProductDialog } from './product-dialog'
import { type MapProduct, domainOf, tasteInput, useMapStore } from './map-store'
import { type DigCandidate, TasteMap, mapNodeScreenPosition } from './taste-map'
import { requestLabel, useBrandRequests } from './use-brand-requests'
import { useLoupeChat } from './use-loupe-chat'

function MapHeader({ products, brands, onReset }: { products: number, brands: number, onReset: () => void }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
      <h2 className="font-serif text-3xl leading-none">
        taste <span className="italic">map</span>
      </h2>
      <div className="flex items-baseline gap-3 text-[12px] text-ink/55">
        <span>{products || brands ? `좋아요 ${products} · 브랜드 ${brands}` : '좋아요·브랜드 저장을 누르면 여기에 취향이 쌓여요'}</span>
        {(products > 0 || brands > 0) && (
          <button type="button" onClick={onReset} className="inline-flex items-center gap-1 text-ink/45 underline-offset-2 hover:text-ink hover:underline">
            <Eraser className="h-3 w-3" strokeWidth={1.5} />
            지도 초기화
          </button>
        )}
      </div>
    </div>
  )
}

/** 지도 초기화 확인창. 지도만 지우고 대화는 그대로 둔다 */
function ResetDialog({ open, onCancel, onConfirm }: { open: boolean, onCancel: () => void, onConfirm: () => void }) {
  const reduce = useReducedMotion()
  useEffect(() => {
    if (!open)
      return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onCancel()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onCancel])
  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-[60] grid place-items-center bg-ink/25 p-5" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: reduce ? 0 : 0.2 }} onClick={onCancel}>
          <motion.div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="reset-title"
            className="w-full max-w-[340px] rounded-[6px] border border-ink/15 bg-paper p-6"
            initial={{ y: 12, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 8, opacity: 0 }}
            transition={{ duration: reduce ? 0 : 0.25, ease: [0.22, 1, 0.36, 1] }}
            onClick={e => e.stopPropagation()}
          >
            <h3 id="reset-title" className="font-serif text-2xl leading-tight">지도를 비울까요?</h3>
            <p className="mt-2 text-[13px] leading-relaxed text-ink/65">좋아요한 상품, 저장한 브랜드, 디깅 경로가 모두 지워져요. 대화는 그대로 남아요.</p>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" autoFocus onClick={onCancel} className="rounded-full border border-ink/25 px-4 py-2 text-[13px] hover:border-ink">취소</button>
              <button type="button" onClick={onConfirm} className="rounded-full bg-ink px-4 py-2 text-[13px] text-paper hover:bg-ink/85">지도 초기화</button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

/** 브랜드 데이터 중 몇 개를 찾았는지 */
function Progress({ found, total }: { found: number, total: number }) {
  return (
    <div className="pointer-events-none absolute bottom-0 left-0 z-10 flex items-center gap-2 text-[11.5px] text-ink/55" aria-live="polite">
      <span className="relative h-1 w-16 overflow-hidden rounded-full bg-ink/10">
        <span className="absolute inset-y-0 left-0 rounded-full bg-brass transition-[width] duration-500" style={{ width: `${(found / total) * 100}%` }} />
      </span>
      <span className="tabular-nums">
        {total}개 브랜드 중
        {' '}
        <b className="font-semibold text-ink">{found}</b>
        개 발견
      </span>
    </div>
  )
}

function toMapProduct(p: KnownProduct): MapProduct {
  return {
    code: p.code,
    name: p.name,
    brand: p.brand,
    price: p.price,
    image: p.image,
    url: p.url,
    style: p.style,
    explore: p.explore,
    category: (PRODUCT_ZONES as string[]).includes(p.category || '') ? p.category as MapProduct['category'] : nameCategory(p.name, ''),
    domain: p.domain || domainOf(p.url),
    likedAt: Date.now(),
  }
}

/** 채팅 화면. 데스크톱: 취향 지도 + 채팅 패널, 모바일: 채팅이 기본이고 상단 작은 동그라미로 지도를 펼친다 */
export function ChatShell({ onHome }: { onHome: () => void }) {
  const [openCode, setOpenCode] = useState<string | null>(null)
  const store = useMapStore()
  const { map } = store
  const mapRef = useRef(map)
  mapRef.current = map
  const brandsData = useBrandsData()
  // 새 대화의 첫 메시지에 저장된 취향을 넘긴다 (새 대화 첫 추천부터 반영)
  const chat = useLoupeChat(() => {
    const taste = tasteInput(mapRef.current)
    return taste ? { taste } : {} as Record<string, string>
  })
  const d = useMemo(() => derive(chat.messages), [chat.messages])

  // 버튼을 누른 즉시 카드·지도에 반영하고, 워크플로의 새 평점 표가 오면 그걸로 대체한다
  const [local, setLocal] = useState<Record<string, number>>({})
  // derive는 메시지가 바뀔 때마다 새 객체를 만들므로, 평점 표 '내용'이 바뀔 때만 로컬 상태를 비운다
  const serverKey = useMemo(() => JSON.stringify(d.ratings), [d.ratings])
  useEffect(() => setLocal({}), [serverKey])
  const ratings = useMemo(() => {
    const merged = { ...d.ratings, ...local }
    for (const k of Object.keys(merged)) {
      if (!merged[k])
        delete merged[k]
    }
    return merged
  }, [d.ratings, local])

  // 지도 저장소 동기화. 대화의 평점 표에서 '바뀐 것'만 반영한다 — 새 대화(평점 없음)나 초기화 뒤에도 지도가 되살아나거나 지워지지 않게.
  // 처음 한 번은 지도 저장소가 생기기 전 대화의 좋아요를 옮겨 온다
  const prevServer = useRef<Record<string, number> | null>(null)
  const dRef = useRef(d)
  dRef.current = d
  const { ready, addProducts, removeProducts, markSeeded } = store
  useEffect(() => {
    if (chat.restoring || !ready)
      return
    const { ratings: cur, products } = dRef.current
    const prev = prevServer.current
    prevServer.current = cur
    const pick = (codes: string[]) => codes.map(c => products.get(c)).filter((p): p is KnownProduct => !!p).map(toMapProduct)
    if (prev === null) {
      if (!mapRef.current.seeded) {
        addProducts(pick(Object.keys(cur).filter(c => cur[c] === 1)))
        markSeeded()
      }
      return
    }
    addProducts(pick(Object.keys(cur).filter(c => cur[c] === 1 && prev[c] !== 1)))
    removeProducts(Object.keys(cur).filter(c => cur[c] === -1 && prev[c] !== -1))
  }, [serverKey, chat.restoring, ready, addProducts, removeProducts, markSeeded])

  const mapProducts = useMemo(() => Object.values(map.products).sort((a, b) => a.likedAt - b.likedAt), [map.products])
  const mapBrands = useMemo(() => Object.values(map.brands).sort((a, b) => a.savedAt - b.savedAt), [map.brands])
  const mapCount = mapProducts.length + mapBrands.length

  const { send } = chat
  const reduce = useReducedMotion()
  const [flights, setFlights] = useState<Flight[]>([])
  const [arriving, setArriving] = useState<string | null>(null)
  const flightId = useRef(0)
  const isDesktopRef = useRef(false)

  /** 좋아요: 누른 카드의 사진을 지도의 그 상품 자리(모바일은 상단 지도 동그라미)로 날린다 */
  const launch = useCallback((code: string, source?: HTMLElement) => {
    const img = source?.closest('[data-fly-source]')?.querySelector('img')
    if (reduce || !img)
      return
    const r = img.getBoundingClientRect()
    const from = { x: r.left + r.width / 2, y: r.top + r.height / 2, size: Math.min(r.width, r.height) }
    setArriving(code)
    // 지도에 새 동그라미가 그려진 다음 프레임에 도착 위치를 잰다
    requestAnimationFrame(() => requestAnimationFrame(() => {
      let to = isDesktopRef.current ? mapNodeScreenPosition(code) : null
      if (!to) {
        const badge = document.querySelector('[data-map-badge]')?.getBoundingClientRect()
        if (!badge)
          return
        to = { x: badge.left + badge.width / 2, y: badge.top + badge.height / 2, size: 30 }
      }
      setFlights(prev => [...prev, { id: ++flightId.current, image: img.currentSrc || img.src, from, to }])
    }))
  }, [reduce])

  // 브랜드 저장: 지도에 올리고, 숨은 메시지로 워크플로 취향 점수에도 반영한다 (답변 중이면 끝난 뒤 보낸다)
  // 미수록 브랜드(웹에서 찾은 곳)는 워크플로가 모르므로 지도에만 올린다
  const saveBrand = useCallback((b: SaveableBrand, from: string | null = null, extra: { instagram?: string, reason?: string } = {}) => {
    const domain = domainOf(b.url)
    if (!domain)
      return
    const info = brandsData?.brands[domain]
    store.saveBrand({ domain, ko: b.ko, en: b.en, url: b.url, tags: b.tags.length ? b.tags : info?.tags ?? [], from, savedAt: Date.now(), ...extra, botPending: !info })
    if (info)
      send(brandSaveMessage(domain, true), { queue: true })
  }, [brandsData, store, send])
  const unsaveBrand = useCallback((domain: string) => {
    store.removeBrand(domain)
    if (brandsData?.brands[domain])
      send(brandSaveMessage(domain, false), { queue: true })
  }, [brandsData, store, send])

  const savedBrands = useMemo(() => new Set(Object.keys(map.brands)), [map.brands])
  const fashion = useMemo(() => ({
    ratings,
    isResponding: chat.responding,
    send,
    rate: (n: number, code: string, v: 1 | -1 | 0, source?: HTMLElement) => {
      setLocal(prev => ({ ...prev, [code]: v }))
      send(ratingMessage(n, code, v))
      const p = d.products.get(code)
      if (v === 1 && p)
        addProducts([toMapProduct(p)])
      else
        removeProducts([code])
      if (v === 1)
        launch(code, source)
    },
    savedBrands,
    toggleBrand: (b: SaveableBrand) => {
      const domain = domainOf(b.url)
      if (savedBrands.has(domain))
        unsaveBrand(domain)
      else
        saveBrand(b)
    },
  }), [ratings, chat.responding, send, launch, d.products, addProducts, removeProducts, savedBrands, saveBrand, unsaveBrand])

  // 브랜드 디깅. "더 파보기" = 수집 브랜드 중 비슷한 곳 2개(유사도 순) + 웹 검색으로 찾은 미수록 브랜드 1~2개.
  // 웹 결과가 없으면 수집 브랜드를 하나 더 보여 준다. 후보는 눌러서 미리 본 뒤 "지도에 추가"해야 저장된다.
  // "괜찮아요"로 거절한 브랜드는 같은 출발 브랜드의 디깅에서 다시 나오지 않는다 (이 화면을 띄워 둔 동안).
  const [selected, setSelected] = useState<string | null>(null)
  const [dig, setDig] = useState<{ from: string, web: WebCandidate[] | null } | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [rejected, setRejected] = useState<Record<string, string[]>>({})
  const collected = useMemo(() => brandsData ? new Set(Object.keys(brandsData.brands)) : null, [brandsData])
  const webCache = useRef(new Map<string, WebCandidate[]>())

  const dbCandidates = useMemo(() => {
    if (!dig || !brandsData)
      return []
    const skip = new Set(rejected[dig.from] ?? [])
    const all = (brandsData.brands[dig.from]?.similar ?? []).filter(s => brandsData.brands[s.domain] && !map.brands[s.domain] && !skip.has(s.domain))
    return all.slice(0, dig.web?.length === 0 ? 3 : 2)
  }, [dig, brandsData, map.brands, rejected])
  const webCandidates = useMemo(() => {
    if (!dig?.web)
      return []
    const skip = new Set(rejected[dig.from] ?? [])
    return dig.web.filter(c => !map.brands[c.domain] && !skip.has(c.domain) && !collected?.has(c.domain)).slice(0, 2)
  }, [dig, map.brands, rejected, collected])
  const candidates = useMemo<DigCandidate[]>(() => {
    if (!dig || !map.brands[dig.from])
      return []
    return [
      ...dbCandidates.map(s => ({ domain: s.domain, ko: brandsData?.brands[s.domain]?.ko ?? s.domain, from: dig.from, external: false })),
      ...webCandidates.map(c => ({ domain: c.domain, ko: c.name, from: dig.from, external: true })),
    ]
  }, [dig, map.brands, dbCandidates, webCandidates, brandsData])

  const startDig = useCallback((from: string) => {
    const b = map.brands[from]
    if (!b)
      return
    const cached = webCache.current.get(from)
    setDig({ from, web: cached ?? null })
    setSelected(null) // 패널을 닫아 지도에서 뻗어 나온 후보가 보이게
    setPreview(null)
    if (cached)
      return
    fetch('/api/dig', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: from, brand: `${b.ko} / ${b.en}`, tags: b.tags.join(', ') }),
    })
      .then(r => r.json())
      .catch(() => ({ candidates: [] }))
      .then((res) => {
        const list: WebCandidate[] = Array.isArray(res?.candidates) ? res.candidates : []
        webCache.current.set(from, list)
        setDig(prev => prev?.from === from ? { from, web: list } : prev)
      })
  }, [map.brands])

  // 미리보기를 거절: 이번 디깅 후보에서 빼고 다시 내지 않는다
  const dismissPreview = useCallback(() => {
    if (preview && dig)
      setRejected(prev => ({ ...prev, [dig.from]: [...(prev[dig.from] ?? []), preview] }))
    setPreview(null)
  }, [preview, dig])

  // 미수록 브랜드 추가 요청과 자동 추가 대기열 상태 (저장한 미수록 브랜드 + 웹 후보)
  const externalDomains = useMemo(() => [
    ...Object.keys(map.brands).filter(d => collected && !collected.has(d)),
    ...webCandidates.map(c => c.domain),
  ], [map.brands, collected, webCandidates])
  const { states: requests, request: requestBrand } = useBrandRequests(externalDomains)
  // 지도 동그라미의 '미수록' 자리에 상태를 보여 준다
  const externalNotes = useMemo(() => Object.fromEntries(Object.entries(requests).map(([d, r]) => [d, requestLabel(r.status)])), [requests])
  // 대기열에서 추가가 끝난 브랜드가 있으면 brands.json을 다시 읽는다 → 일반 브랜드 동그라미로 바뀐다
  useEffect(() => {
    if (collected && Object.entries(requests).some(([d, r]) => r.status === 'added' && !collected.has(d)))
      reloadBrandsData()
  }, [requests, collected])
  // 미수록일 때 저장한 브랜드가 수집 브랜드가 되면, 그때 워크플로 취향 점수에 반영한다 (브랜드 저장과 같은 숨은 메시지)
  const { patchBrand } = store
  useEffect(() => {
    if (!collected)
      return
    for (const b of Object.values(map.brands)) {
      if ((b.botPending ?? b.instagram !== undefined) && collected.has(b.domain) && b.botPending !== false) {
        // 이름·태그도 수집 데이터 기준으로 바꿔 일반 브랜드 동그라미가 된다
        const info = brandsData?.brands[b.domain]
        patchBrand(b.domain, { botPending: false, ...(info ? { ko: info.ko, en: info.en, tags: info.tags, url: info.url } : {}) })
        send(brandSaveMessage(b.domain, true), { queue: true })
      }
    }
  }, [collected, brandsData, map.brands, patchBrand, send])

  const selectedBrand = selected ? map.brands[selected] : undefined
  const previewDb = preview ? dbCandidates.find(s => s.domain === preview) : undefined
  const previewWeb = preview ? webCandidates.find(c => c.domain === preview) : undefined
  // 진행 표시: 수집 브랜드(brands.json, 브랜드를 추가하면 같이 늘어남) 중 저장한 수
  const found = collected ? Object.keys(map.brands).filter(b => collected.has(b)).length : 0

  const [confirmReset, setConfirmReset] = useState(false)
  const doReset = useCallback(() => {
    store.reset()
    setSelected(null)
    setDig(null)
    setPreview(null)
    setConfirmReset(false)
  }, [store])
  const cancelReset = useCallback(() => setConfirmReset(false), [])

  const fromKo = dig ? map.brands[dig.from]?.ko ?? '' : ''
  const mapArea = (desktop: boolean) => (
    <div className="relative min-h-0 flex-1">
      <TasteMap
        products={mapProducts}
        brands={mapBrands}
        candidates={candidates}
        loadingFrom={dig && dig.web === null ? dig.from : null}
        collected={collected}
        externalNotes={externalNotes}
        selectedBrand={preview ?? selected ?? dig?.from ?? null}
        onOpen={setOpenCode}
        onBrand={(domain) => {
          if (preview)
            dismissPreview()
          setSelected(prev => prev === domain ? null : domain)
        }}
        onCandidate={(domain) => {
          setSelected(null)
          setPreview(domain)
        }}
        onBackground={() => {
          if (preview)
            dismissPreview()
          else
            setSelected(null)
        }}
        arriving={desktop ? arriving : null}
        arriveDelay={reduce ? 0 : FLY_DURATION * 0.8}
        className="h-full"
      />
      {brandsData && <Progress found={found} total={brandsData.total} />}
      <AnimatePresence>
        {selectedBrand && !preview && (
          <BrandPanel
            key={selectedBrand.domain}
            brand={selectedBrand}
            info={brandsData?.brands[selectedBrand.domain]}
            external={!!collected && !collected.has(selectedBrand.domain)}
            fromKo={selectedBrand.from ? map.brands[selectedBrand.from]?.ko : undefined}
            request={requests[selectedBrand.domain]}
            onRequest={() => requestBrand({ domain: selectedBrand.domain, name: selectedBrand.ko, en: selectedBrand.en, url: selectedBrand.url, instagram: selectedBrand.instagram, from: selectedBrand.from ? map.brands[selectedBrand.from]?.ko : undefined })}
            digging={dig?.from === selectedBrand.domain && dig.web === null}
            onDig={() => startDig(selectedBrand.domain)}
            onUnsave={() => {
              unsaveBrand(selectedBrand.domain)
              setSelected(null)
            }}
            onClose={() => setSelected(null)}
          />
        )}
        {dig && previewDb && brandsData?.brands[previewDb.domain] && (
          <CandidatePanel
            key={previewDb.domain}
            ko={brandsData.brands[previewDb.domain].ko}
            en={brandsData.brands[previewDb.domain].en}
            url={brandsData.brands[previewDb.domain].url}
            external={false}
            fromKo={fromKo}
            info={brandsData.brands[previewDb.domain]}
            reason={previewDb.reason}
            mood={previewDb.mood}
            onRequest={() => {}}
            onAdd={() => {
              const info = brandsData.brands[previewDb.domain]
              saveBrand({ ko: info.ko, en: info.en, url: info.url, tags: info.tags }, dig.from, { reason: previewDb.reason })
              setPreview(null)
            }}
            onDismiss={dismissPreview}
          />
        )}
        {dig && previewWeb && (
          <CandidatePanel
            key={previewWeb.domain}
            ko={previewWeb.name}
            en={previewWeb.en}
            url={previewWeb.url}
            instagram={previewWeb.instagram}
            external
            fromKo={fromKo}
            reason={previewWeb.reason}
            mood={previewWeb.mood}
            request={requests[previewWeb.domain]}
            onRequest={() => requestBrand({ domain: previewWeb.domain, name: previewWeb.name, en: previewWeb.en, url: previewWeb.url, instagram: previewWeb.instagram, from: fromKo })}
            onAdd={() => {
              saveBrand({ ko: previewWeb.name, en: previewWeb.en, url: previewWeb.url, tags: previewWeb.mood }, dig.from, { instagram: previewWeb.instagram, reason: previewWeb.reason })
              setPreview(null)
            }}
            onDismiss={dismissPreview}
          />
        )}
      </AnimatePresence>
    </div>
  )

  const openProduct = openCode ? d.products.get(openCode) ?? map.products[openCode] ?? null : null
  const closeProduct = useCallback(() => setOpenCode(null), [])
  const [mapOpen, setMapOpen] = useState(false)
  // 지도는 화면에 보이는 한 곳에만 그린다 (보이지 않는 쪽의 d3 배치 계산을 하지 않도록)
  const [isDesktop, setIsDesktop] = useState(false)
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)')
    const update = () => {
      setIsDesktop(mq.matches)
      isDesktopRef.current = mq.matches
    }
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  return (
    <FashionContext.Provider value={fashion}>
      <div className="flex h-[100svh] flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-ink/10 px-5">
          {/* 로고를 누르면 첫 화면으로 (대화와 지도는 그대로) */}
          <motion.button
            type="button"
            onClick={onHome}
            aria-label="첫 화면으로"
            className="group relative -ml-2 flex items-baseline gap-2 rounded-full px-2 py-1 outline-none focus-visible:ring-1 focus-visible:ring-ink"
            whileHover={reduce ? undefined : { scale: 1.06 }}
            whileTap={reduce ? undefined : { scale: 0.97 }}
            transition={{ type: 'spring', stiffness: 400, damping: 22 }}
          >
            <span className="font-serif text-2xl leading-none transition-[font-style] group-hover:italic">loupe</span>
            <span className="text-[11px] text-ink/0 transition-colors duration-300 group-hover:text-ink/45 group-focus-visible:text-ink/45">← 처음으로</span>
          </motion.button>
          <div className="flex items-center gap-3">
            <button type="button" onClick={chat.reset} disabled={chat.responding} className="inline-flex items-center gap-1.5 text-[12px] text-ink/55 hover:text-ink disabled:opacity-40">
              <RotateCcw className="h-3.5 w-3.5" strokeWidth={1.5} />
              새 대화
            </button>
            {/* 모바일: 작은 동그라미 = 취향 지도 열기 (좋아요 수). 좋아요한 사진이 여기로 날아와 내려앉는다 */}
            <motion.button
              key={mapCount}
              type="button"
              data-map-badge
              onClick={() => setMapOpen(true)}
              aria-label={`취향 지도 열기 (좋아요·브랜드 ${mapCount}개)`}
              initial={reduce ? false : { scale: 1 }}
              animate={{ scale: [1, 1.25, 1] }}
              transition={{ duration: 0.4, delay: reduce ? 0 : FLY_DURATION * 0.85 }}
              className="grid h-9 w-9 place-items-center rounded-full border border-ink bg-ink text-[12px] tabular-nums text-paper lg:hidden"
            >
              {mapCount}
            </motion.button>
          </div>
        </header>

        <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,1fr)_minmax(400px,34vw)]">
          {isDesktop && (
            <section className="relative flex min-h-0 flex-col gap-4 p-8">
              <MapHeader products={mapProducts.length} brands={mapBrands.length} onReset={() => setConfirmReset(true)} />
              {mapArea(true)}
            </section>
          )}
          <section className="min-h-0 border-ink/10 lg:border-l">
            <ChatPanel messages={d.visible} responding={chat.responding} restoring={chat.restoring} onSend={send} />
          </section>
        </div>
      </div>

      <AnimatePresence>
        {mapOpen && !isDesktop && (
          <motion.div
            className="fixed inset-0 z-40 flex flex-col bg-paper p-5 lg:hidden"
            initial={{ clipPath: 'circle(18px at calc(100% - 38px) 28px)' }}
            animate={{ clipPath: 'circle(150% at calc(100% - 38px) 28px)' }}
            exit={{ clipPath: 'circle(18px at calc(100% - 38px) 28px)' }}
            transition={{ duration: reduce ? 0 : 0.45, ease: [0.65, 0, 0.35, 1] }}
          >
            <div className="flex items-start justify-between">
              <MapHeader products={mapProducts.length} brands={mapBrands.length} onReset={() => setConfirmReset(true)} />
              <button type="button" onClick={() => setMapOpen(false)} aria-label="지도 닫기" className="-mr-1 -mt-1 grid h-9 w-9 place-items-center rounded-full border border-ink/30">
                <X className="h-4 w-4" strokeWidth={1.5} />
              </button>
            </div>
            <div className="mt-4 flex min-h-0 flex-1 flex-col">{mapArea(false)}</div>
          </motion.div>
        )}
      </AnimatePresence>

      <ResetDialog open={confirmReset} onCancel={cancelReset} onConfirm={doReset} />
      <ProductDialog
        product={openProduct}
        onClose={closeProduct}
        onRemove={openCode && !d.products.has(openCode)
          ? () => {
              removeProducts([openCode])
              setOpenCode(null)
            }
          : undefined}
      />
      <FlyLayer flights={flights} onDone={id => setFlights(prev => prev.filter(f => f.id !== id))} />
    </FashionContext.Provider>
  )
}
