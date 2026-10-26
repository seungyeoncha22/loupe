'use client'
import { forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY, type SimulationLinkDatum, type SimulationNodeDatum } from 'd3-force'
import { select } from 'd3-selection'
import 'd3-transition'
import { type ZoomBehavior, zoom, zoomIdentity } from 'd3-zoom'
import { Maximize2 } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { type MouseEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { Zone } from './category'
import type { MapBrand, MapProduct } from './map-store'

/**
 * 취향 지도. 가운데 큰 동그라미 = 사용자. 지도는 상의 · 하의 · 아우터 · 브랜드 4구역으로 나뉜다.
 * - 상품 구역(상의/하의/아우터): 상품(사진이 든 작은 동그라미)이 대표 스타일 동그라미에 붙어 뭉친다.
 *   구역이 달라도 같은 스타일은 흐린 점선으로 잇는다.
 * - 브랜드 구역: 저장한 브랜드 동그라미만 촘촘히 모인다. 브랜드 사이에는 디깅 경로(황동색 선)만 남는다.
 *   "더 파보기"의 후보는 출발 브랜드에서 뻗어 나온 흐린 점선 동그라미 (웹에서 찾은 미수록 브랜드는 '미수록' 표시).
 * - 배치: d3-force(d3/d3-force). 구역 중심으로 끌어당기는 힘 + 링크 + 충돌 방지 + 약한 반발력. 그리기 전에 미리 돌려 고정한다.
 * - 확대·이동: d3-zoom(d3/d3-zoom). 휠·핀치로 확대, 드래그로 이동, '전체 보기'로 처음 화면. 글자는 확대 배율과 상관없이
 *   화면에서 10.5~17px 사이로 보이게 크기를 맞춘다.
 * - 움직임: motion. 새 동그라미는 커지며 등장하고, 배치가 바뀌면 기존 동그라미·선이 새 위치로 옮겨 간다.
 * - 렌즈: 상품 동그라미에 마우스를 대면 커지며 사진이 한 번 더 확대되고, 상품명·브랜드가 보인다. 누르면 카드를 다시 연다.
 */
type Kind = 'user' | 'style' | 'product' | 'brand' | 'candidate' | 'loading'
interface MapNode extends SimulationNodeDatum {
  id: string
  kind: Kind
  zone?: Zone
  r: number
  label: string
  product?: MapProduct
  domain?: string
  /** 수집하지 않은(웹에서 찾은) 브랜드 */
  external?: boolean
}
type EdgeKind = 'tree' | 'cross' | 'dig' | 'candidate'

export interface DigCandidate { domain: string, ko: string, from: string, external: boolean }

const USER_R = 46
const PRODUCT_R = 24
const BRAND_R = 32
const LENS_SCALE = 1.7 // 마우스를 댔을 때 상품 동그라미 크기 배율
const PHOTO_ZOOM = 1.25 // 그 안의 사진을 한 번 더 확대
const Z = 220 // 구역 중심까지의 거리
const MIN_FONT = 10.5 // 화면에서 보이는 글자 크기 (px) 범위
const MAX_FONT = 17
const zonesFor = (tall: boolean): [Zone, number, number][] => {
  // 세로로 긴 화면(모바일 지도 시트)은 구역을 위아래로 벌려 빈 공간 없이 채운다
  const [zx, zy] = tall ? [150, 280] : [Z, Z]
  return [['상의', -zx, -zy], ['아우터', zx, -zy], ['하의', -zx, zy], ['브랜드', zx, zy]]
}
// 긴 브랜드 이름은 두 줄로 (띄어쓰기에서, 없으면 가운데에서 자른다)
function nameLines(name: string): string[] {
  const chars = [...name]
  if (chars.length <= 8)
    return [name]
  // 띄어쓰기가 없으면 TheColdestMoment처럼 대문자가 시작되는 곳을 단어 경계로 본다
  const words = (/\s/.test(name) ? name : name.replace(/([a-z])([A-Z])/g, '$1 $2')).split(/\s+/)
  if (words.length > 1) {
    let best = 1
    let bestDiff = Infinity
    for (let i = 1; i < words.length; i++) {
      const diff = Math.abs(words.slice(0, i).join(' ').length - words.slice(i).join(' ').length)
      if (diff < bestDiff) {
        best = i
        bestDiff = diff
      }
    }
    const sep = /\s/.test(name) ? ' ' : ''
    return [words.slice(0, best).join(sep), words.slice(best).join(sep)]
  }
  const half = Math.ceil(chars.length / 2)
  return [chars.slice(0, half).join(''), chars.slice(half).join('')]
}
// 브랜드 동그라미는 이름(가장 긴 줄)이 다 들어가게 조금 키운다. 글자 폭은 한글 1, 영문·숫자 0.6 (11px 기준)
const lineWidth = (line: string) => [...line].reduce((w, ch) => w + (/[\x20-\x7E]/.test(ch) ? 0.6 : 1), 0) * 11
// labelScale: 지도가 작게 그려져 글자를 최소 크기로 키울 때(모바일)의 배율. 그만큼 동그라미도 키운다
const brandR = (name: string, base = BRAND_R, labelScale = 1) => Math.max(base, Math.max(...nameLines(name).map(lineWidth)) * labelScale / 2 + 12)

function layout(products: MapProduct[], brands: MapBrand[], candidates: DigCandidate[], loadingFrom: string | null, collected: Set<string> | null, tall: boolean, labelScale: number) {
  const ZONES = zonesFor(tall)
  const zoneCenter = (z: Zone) => ZONES.find(([n]) => n === z)!.slice(1) as [number, number]
  const nodes: MapNode[] = [{ id: 'user', kind: 'user', r: USER_R, label: 'you', fx: 0, fy: 0 }]
  const pairs: [string, string, EdgeKind][] = []
  const byId = new Map<string, MapNode>()
  const add = (n: MapNode) => {
    nodes.push(n)
    byId.set(n.id, n)
  }
  const near = (z: Zone, i: number, d = 70) => {
    const [cx, cy] = zoneCenter(z)
    return { x: cx + Math.cos(i * 2.4) * d, y: cy + Math.sin(i * 2.4) * d }
  }

  // 상품 구역의 스타일 동그라미 (상품 대표 스타일)
  const styleCount = new Map<string, number>()
  products.forEach(p => styleCount.set(`${p.category}:${p.style || '기타'}`, (styleCount.get(`${p.category}:${p.style || '기타'}`) || 0) + 1))
  ;[...styleCount].forEach(([key, count], i) => {
    const z = key.slice(0, key.indexOf(':')) as Zone
    const label = key.slice(z.length + 1)
    const r = Math.max(26 + Math.min(count, 6) * 3, lineWidth(label) * (13 / 11) * labelScale / 2 + 8)
    add({ id: `s:${key}`, kind: 'style', zone: z, r, label, ...near(z, i, 40) })
    pairs.push(['user', `s:${key}`, 'tree'])
  })
  products.forEach((p, i) => {
    const sid = `s:${p.category}:${p.style || '기타'}`
    const st = byId.get(sid)!
    add({ id: `p:${p.code}`, kind: 'product', zone: p.category, r: PRODUCT_R, label: p.name, product: p, x: st.x! + Math.cos(i) * 40, y: st.y! + Math.sin(i) * 40 })
    pairs.push([sid, `p:${p.code}`, 'tree'])
  })
  // 브랜드 구역: 브랜드 동그라미만. 디깅으로 찾은 브랜드는 출발 브랜드 옆에서 시작한다
  brands.forEach((b, i) => {
    const src = b.from ? byId.get(`b:${b.from}`) : undefined
    const at = src ? { x: src.x! + Math.cos(i * 2.4) * 60, y: src.y! + Math.sin(i * 2.4) * 60 } : near('브랜드', i, 50)
    add({ id: `b:${b.domain}`, kind: 'brand', zone: '브랜드', r: brandR(b.ko || b.en, BRAND_R, labelScale), label: b.ko || b.en, domain: b.domain, external: collected ? !collected.has(b.domain) : false, ...at })
  })
  brands.forEach((b) => {
    if (b.from && byId.has(`b:${b.from}`))
      pairs.push([`b:${b.from}`, `b:${b.domain}`, 'dig'])
  })
  const shoot = (src: MapNode, i: number, d = 95) => ({ x: src.x! + Math.cos(i * 2.1 + 0.4) * d, y: src.y! + Math.sin(i * 2.1 + 0.4) * d })
  candidates.forEach((c, i) => {
    const src = byId.get(`b:${c.from}`)
    if (!src || byId.has(`b:${c.domain}`))
      return
    add({ id: `c:${c.domain}`, kind: 'candidate', zone: '브랜드', r: brandR(c.ko, BRAND_R - 2, labelScale), label: c.ko, domain: c.domain, external: c.external, ...shoot(src, i) })
    pairs.push([`b:${c.from}`, `c:${c.domain}`, 'candidate'])
  })
  // 웹 검색 중: 출발 브랜드에서 '찾는 중' 점선 동그라미가 하나 뻗어 있다
  const loadingSrc = loadingFrom ? byId.get(`b:${loadingFrom}`) : undefined
  if (loadingSrc) {
    add({ id: `l:${loadingFrom}`, kind: 'loading', zone: '브랜드', r: BRAND_R - 4, label: '웹에서 찾는 중', ...shoot(loadingSrc, candidates.length) })
    pairs.push([`b:${loadingFrom}`, `l:${loadingFrom}`, 'candidate'])
  }

  // forceLink는 계산하면서 source/target을 노드 객체로 바꿔 놓으므로 ID 쌍을 따로 둔다
  const links = pairs.map(([source, target, kind]) => ({ source, target, kind }))
  const zx = (d: MapNode) => d.zone ? zoneCenter(d.zone)[0] : 0
  const zy = (d: MapNode) => d.zone ? zoneCenter(d.zone)[1] : 0
  const inBrandZone = (d: MapNode) => d.kind === 'brand' || d.kind === 'candidate' || d.kind === 'loading'
  const pull = (d: MapNode) => d.kind === 'product' ? 0.04 : d.kind === 'user' ? 0 : inBrandZone(d) ? 0.22 : 0.1
  forceSimulation(nodes)
    .force('link', forceLink<MapNode, SimulationLinkDatum<MapNode>>(links as any).id(d => d.id)
      .distance((l: any) => l.kind === 'dig' || l.kind === 'candidate' ? l.source.r + l.target.r + 22 : l.source.kind === 'user' ? 150 : l.source.r + l.target.r + 12)
      .strength((l: any) => l.source.kind === 'user' ? 0.01 : l.kind === 'tree' && l.target.kind === 'product' ? 0.9 : 0.5))
    // 브랜드끼리는 반발력을 약하게 해서 촘촘히 모이게 한다
    .force('charge', forceManyBody<MapNode>().strength(d => d.kind === 'product' ? -40 : inBrandZone(d) ? -45 : -260))
    .force('collide', forceCollide<MapNode>(d => d.r + (d.kind === 'product' ? 4 : d.kind === 'user' ? 40 : inBrandZone(d) ? 5 : 10)).iterations(3))
    .force('x', forceX<MapNode>(zx).strength(pull))
    .force('y', forceY<MapNode>(zy).strength(pull))
    .stop()
    .tick(320)

  // 구역이 달라도 같은 스타일은 흐린 점선으로 잇는다 (구역 순서대로 사슬처럼)
  const styleZones = new Map<string, string[]>()
  for (const n of nodes) {
    if (n.kind === 'style')
      styleZones.set(n.label, [...(styleZones.get(n.label) || []), n.id])
  }
  for (const ids of styleZones.values()) {
    for (let i = 1; i < ids.length; i++)
      pairs.push([ids[i - 1], ids[i], 'cross'])
  }
  const edges = pairs.map(([a, b, kind]) => ({ id: `${a}>${b}`, kind, a: byId.get(a) ?? nodes[0], b: byId.get(b)! }))

  // 구역 이름: 그 구역 동그라미들 위쪽 가운데. 비어 있는 구역은 구역 중심에
  const zoneLabels = ZONES.map(([z, cx, cy]) => {
    const own = nodes.filter(n => n.zone === z)
    if (!own.length)
      return { zone: z, x: cx, y: cy, empty: true }
    const top = Math.min(...own.map(n => n.y! - n.r))
    const xs = own.map(n => n.x!)
    return { zone: z, x: (Math.min(...xs) + Math.max(...xs)) / 2, y: top - 16, empty: false }
  })

  const pad = 30
  const xs = [...nodes.flatMap(n => [n.x! - n.r, n.x! + n.r]), ...zoneLabels.flatMap(l => [l.x - 50, l.x + 50])]
  const ys = [...nodes.flatMap(n => [n.y! - n.r, n.y! + n.r]), ...zoneLabels.flatMap(l => [l.y - 20, l.y + 20])]
  const minX = Math.min(...xs) - pad
  const maxX = Math.max(...xs) + pad
  const minY = Math.min(...ys) - pad
  const maxY = Math.max(...ys) + pad
  const w = Math.max(maxX - minX, 380)
  const h = Math.max(maxY - minY, 380)
  const cx = (minX + maxX) / 2
  const cy = (minY + maxY) / 2
  return { nodes, edges, zoneLabels, viewBox: `${cx - w / 2} ${cy - h / 2} ${w} ${h}` }
}

const ease = [0.22, 1, 0.36, 1] as const

function ProductNode({ n, hovered, onHover, onOpen, reduce, delay }: {
  n: MapNode
  delay: number
  hovered: boolean
  onHover: (id: string | null) => void
  onOpen: (code: string) => void
  reduce: boolean | null
}) {
  const p = n.product!
  const r = hovered ? n.r * LENS_SCALE : n.r
  const photo = r * 2 * (hovered ? PHOTO_ZOOM : 1)
  const t = { duration: reduce ? 0 : 0.28, ease }
  return (
    <motion.g
      data-code={p.code}
      data-x={n.x}
      data-y={n.y}
      role="button"
      tabIndex={0}
      aria-label={`${p.name} · ${p.brand}`}
      className="cursor-pointer outline-none"
      initial={{ x: n.x, y: n.y, scale: 0, opacity: 0 }}
      animate={{ x: n.x, y: n.y, scale: 1, opacity: 1 }}
      exit={{ scale: 0, opacity: 0 }}
      transition={{ duration: reduce ? 0 : 0.6, ease, scale: { duration: reduce ? 0 : 0.45, delay }, opacity: { duration: reduce ? 0 : 0.3, delay } }}
      onPointerEnter={() => onHover(n.id)}
      onPointerLeave={() => onHover(null)}
      onFocus={() => onHover(n.id)}
      onBlur={() => onHover(null)}
      onClick={() => onOpen(p.code)}
      onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && onOpen(p.code)}
    >
      <clipPath id={`clip-${p.code}`}>
        <motion.circle cx={0} cy={0} initial={false} animate={{ r }} transition={t} />
      </clipPath>
      {hovered && <circle r={r + 10} fill="hsl(var(--ink) / 0.06)" />}
      <motion.circle cx={0} cy={0} initial={false} animate={{ r }} transition={t} fill="hsl(var(--card))" />
      {p.image && (
        <motion.image
          href={p.image}
          preserveAspectRatio="xMidYMid slice"
          clipPath={`url(#clip-${p.code})`}
          initial={false}
          animate={{ attrX: -photo / 2, attrY: -photo / 2, width: photo, height: photo }}
          transition={t}
        />
      )}
      <motion.circle
        cx={0}
        cy={0}
        fill="none"
        initial={false}
        animate={{ r, strokeWidth: hovered ? 1.5 : p.explore ? 2.5 : 1 }}
        transition={t}
        stroke={p.explore ? 'hsl(var(--brass))' : hovered ? 'hsl(var(--ink))' : 'hsl(var(--ink) / 0.55)'}
      />
    </motion.g>
  )
}

function BrandNode({ n, selected, onClick, reduce, font, note }: {
  n: MapNode
  /** 미수록 브랜드 아래 작은 글씨 (기본 '미수록') */
  note?: string
  selected: boolean
  onClick: () => void
  reduce: boolean | null
  font: (base: number) => number
}) {
  const ghost = n.kind !== 'brand' // 디깅 후보, 찾는 중
  const lines = n.kind === 'loading' ? [n.label] : nameLines(n.label)
  const fontSize = font(lines.length === 1 && [...n.label].length <= 4 ? 13 : 11)
  const lineH = fontSize * 1.15
  const top = -((lines.length - 1) * lineH) / 2 - (n.external ? fontSize * 0.35 : 0)
  return (
    <motion.g
      data-brand={n.kind === 'loading' ? undefined : n.domain}
      role={n.kind === 'loading' ? undefined : 'button'}
      tabIndex={n.kind === 'loading' ? undefined : 0}
      aria-label={n.kind === 'loading' ? '웹에서 비슷한 브랜드 찾는 중' : n.kind === 'candidate' ? `${n.label} 미리보기 (디깅 후보${n.external ? ', 미수록' : ''})` : `${n.label} 브랜드 보기`}
      className={n.kind === 'loading' ? 'pointer-events-none' : 'cursor-pointer outline-none'}
      initial={{ x: n.x, y: n.y, scale: 0, opacity: 0 }}
      animate={{ x: n.x, y: n.y, scale: 1, opacity: ghost && !selected ? 0.75 : 1 }}
      exit={{ scale: 0, opacity: 0 }}
      whileHover={n.kind === 'loading' ? undefined : { scale: 1.08, opacity: 1 }}
      transition={{ duration: reduce ? 0 : 0.6, ease }}
      onClick={(e) => {
        e.stopPropagation()
        onClick()
      }}
      onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && onClick()}
    >
      {selected && <circle r={n.r + 9} fill="none" stroke="hsl(var(--brass) / 0.5)" strokeWidth={1} />}
      <circle
        r={n.r}
        fill={ghost ? 'hsl(var(--paper))' : 'hsl(var(--card))'}
        stroke={ghost ? 'hsl(var(--ink) / 0.45)' : 'hsl(var(--brass))'}
        strokeWidth={ghost ? 1 : selected ? 2.5 : 1.5}
        strokeDasharray={ghost ? '4 4' : undefined}
      >
        {n.kind === 'loading' && !reduce && <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="6s" repeatCount="indefinite" />}
      </circle>
      <text textAnchor="middle" dominantBaseline="central" className={ghost ? 'fill-ink/80' : 'fill-ink'} fontSize={n.kind === 'loading' ? font(9.5) : fontSize} fontWeight={n.kind === 'loading' ? 400 : 600}>
        {lines.map((l, i) => <tspan key={l} x={0} y={top + i * lineH}>{l}</tspan>)}
      </text>
      {n.external && <text y={top + (lines.length - 1) * lineH + fontSize * 1.1} textAnchor="middle" dominantBaseline="central" className="fill-brass" fontSize={font(8.5) * 0.85} letterSpacing="0.05em">{note || '미수록'}</text>}
      {n.kind === 'candidate' && !n.external && <text y={n.r - 9} textAnchor="middle" dominantBaseline="central" className="fill-brass" fontSize={11}>+</text>}
    </motion.g>
  )
}

const EDGE_STYLE: Record<EdgeKind, { stroke: string, width: number, dash?: string }> = {
  tree: { stroke: 'hsl(var(--ink) / 0.18)', width: 1 },
  cross: { stroke: 'hsl(var(--ink) / 0.13)', width: 1, dash: '3 5' },
  dig: { stroke: 'hsl(var(--brass))', width: 2 },
  candidate: { stroke: 'hsl(var(--brass) / 0.55)', width: 1.25, dash: '4 4' },
}

interface ZoomT { k: number, x: number, y: number }

export function TasteMap({ products, brands = [], candidates = [], loadingFrom = null, collected = null, externalNotes = {}, selectedBrand = null, onOpen, onBrand, onCandidate, onBackground, className, arriving = null, arriveDelay = 0 }: {
  products: MapProduct[]
  brands?: MapBrand[]
  /** 디깅 후보 (아직 저장 안 한 비슷한 브랜드) */
  candidates?: DigCandidate[]
  /** 웹 검색 중인 출발 브랜드 */
  loadingFrom?: string | null
  /** 수집 브랜드 도메인 (여기 없는 저장 브랜드는 '미수록') */
  collected?: Set<string> | null
  /** 미수록 브랜드의 추가 요청 상태 (도메인 → '확인 중' 등). 있으면 '미수록' 대신 보인다 */
  externalNotes?: Record<string, string>
  selectedBrand?: string | null
  onOpen: (code: string) => void
  onBrand?: (domain: string) => void
  onCandidate?: (domain: string) => void
  /** 지도 빈 곳을 눌렀을 때 (드래그로 옮긴 것은 제외) */
  onBackground?: () => void
  className?: string
  /** 카드에서 날아오는 중인 상품: 사진이 도착할 때쯤 동그라미가 나타나게 늦춘다 */
  arriving?: string | null
  arriveDelay?: number
}) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [box, setBox] = useState({ w: 0, h: 0 })
  useEffect(() => {
    const el = wrapRef.current
    if (!el)
      return
    const ro = new ResizeObserver(([e]) => setBox({ w: e.contentRect.width, h: e.contentRect.height }))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  const tall = box.w > 0 && box.h > box.w * 1.3
  const [labelScale, setLabelScale] = useState(1)
  const { nodes, edges, zoneLabels, viewBox } = useMemo(
    () => layout(products, brands, candidates, loadingFrom, collected, tall, labelScale),
    [products, brands, candidates, loadingFrom, collected, tall, labelScale],
  )
  const [hovered, setHovered] = useState<string | null>(null)
  const reduce = useReducedMotion()
  const move = { duration: reduce ? 0 : 0.6, ease }
  // 마우스를 댄 동그라미는 맨 위에 그린다
  const productNodes = nodes.filter(n => n.kind === 'product').sort((a, b) => (a.id === hovered ? 1 : 0) - (b.id === hovered ? 1 : 0))

  // 확대·이동 (d3-zoom). 변환은 SVG 좌표 단위로, 지도 내용 전체를 감싼 <g>에 건다
  const svgRef = useRef<SVGSVGElement>(null)
  const zoomRef = useRef<ZoomBehavior<SVGSVGElement, unknown> | null>(null)
  const [zt, setZt] = useState<ZoomT>({ k: 1, x: 0, y: 0 })
  useEffect(() => {
    const svg = svgRef.current
    if (!svg)
      return
    const behavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.6, 5])
      .on('zoom', e => setZt({ k: e.transform.k, x: e.transform.x, y: e.transform.y }))
    const sel = select(svg)
    sel.call(behavior).on('dblclick.zoom', null)
    zoomRef.current = behavior
    return () => {
      sel.on('.zoom', null)
    }
  }, [])
  const resetZoom = useCallback(() => {
    const svg = svgRef.current
    if (svg && zoomRef.current)
      select(svg).transition().duration(reduce ? 0 : 450).call(zoomRef.current.transform, zoomIdentity)
  }, [reduce])
  const zoomed = Math.abs(zt.k - 1) > 0.01 || Math.abs(zt.x) > 1 || Math.abs(zt.y) > 1

  // 화면 픽셀 / SVG 단위 (viewBox 맞춤 배율 × 확대 배율)
  const [vx, vy, vw, vh] = viewBox.split(' ').map(Number)
  const fit = box.w && box.h ? Math.min(box.w / vw, box.h / vh) : 0
  const px = fit * zt.k
  // 글자는 화면에서 MIN_FONT~MAX_FONT px 사이로 보이게 (확대하면 너무 커지지 않고, 축소해도 읽을 수 있게)
  const font = useCallback((base: number) => (px ? Math.min(Math.max(base * px, MIN_FONT), MAX_FONT) / px : base), [px])
  // 확대하지 않은 상태에서 11단위 글자가 최소 크기보다 작게 보이면 그 배율만큼 동그라미를 키운다 (0.25 단위로 맞춰 흔들리지 않게)
  useEffect(() => {
    if (!fit)
      return
    const want = Math.min(2.2, Math.max(1, Math.ceil((MIN_FONT / (11 * fit)) * 4) / 4))
    if (want > labelScale || want < labelScale - 0.25)
      setLabelScale(want)
  }, [fit, labelScale])

  // 마우스를 댄 상품의 이름·브랜드 라벨. SVG 밖 HTML로 띄워 지도 확대 비율과 상관없이 같은 글자 크기를 쓴다
  const hoveredNode = nodes.find(n => n.id === hovered && n.kind === 'product')
  const toScreen = (x: number, y: number) => ({
    left: (box.w - vw * fit) / 2 + (x * zt.k + zt.x - vx) * fit,
    top: (box.h - vh * fit) / 2 + (y * zt.k + zt.y - vy) * fit,
  })
  const label = hoveredNode && fit
    ? (() => {
        const at = toScreen(hoveredNode.x ?? 0, hoveredNode.y ?? 0)
        return { left: at.left, top: at.top + hoveredNode.r * LENS_SCALE * px + 10, p: hoveredNode.product! }
      })()
    : null

  const onSvgClick = (e: MouseEvent<SVGSVGElement>) => {
    const t = e.target as Element
    if (t === e.currentTarget || t.hasAttribute('data-map-bg'))
      onBackground?.()
  }

  return (
    <div ref={wrapRef} className={`relative ${className ?? ''}`}>
      <AnimatePresence>
        {label && (
          <motion.div
            key={label.p.code}
            className="pointer-events-none absolute z-10 w-max max-w-[240px] rounded-full border border-ink/15 bg-paper/90 px-3 py-1.5 text-center shadow-sm backdrop-blur-sm"
            style={{ left: label.left, top: label.top, x: '-50%' }} // motion이 transform을 쓰므로 가운데 정렬도 motion으로
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: reduce ? 0 : 0.18 }}
          >
            <div className="truncate text-[12px] font-semibold leading-tight text-ink">{label.p.name}</div>
            <div className="truncate text-[10px] uppercase tracking-[0.14em] text-ink/55">{label.p.brand}</div>
          </motion.div>
        )}
      </AnimatePresence>
      <AnimatePresence>
        {zoomed && (
          <motion.button
            type="button"
            onClick={resetZoom}
            className="absolute bottom-0 right-0 z-10 inline-flex items-center gap-1.5 rounded-full border border-ink/20 bg-paper/90 px-3 py-1.5 text-[12px] text-ink/70 backdrop-blur-sm hover:border-ink hover:text-ink"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: reduce ? 0 : 0.2 }}
          >
            <Maximize2 className="h-3.5 w-3.5" strokeWidth={1.5} />
            전체 보기
          </motion.button>
        )}
      </AnimatePresence>
      <motion.svg
        ref={svgRef}
        viewBox={viewBox}
        data-final-viewbox={viewBox}
        data-zoom={`${zt.k} ${zt.x} ${zt.y}`}
        animate={{ viewBox }}
        transition={move}
        onClick={onSvgClick}
        // 확대했을 때는 지도 영역 밖(제목·채팅)으로 넘치지 않게 자른다
        className={`h-full w-full cursor-grab touch-none select-none active:cursor-grabbing ${zoomed ? 'overflow-hidden' : 'overflow-visible'}`}
        role="img"
        aria-label={`취향 지도: 좋아요한 상품 ${products.length}개, 저장한 브랜드 ${brands.length}개. 휠·핀치로 확대, 드래그로 이동`}
      >
        <g transform={`translate(${zt.x} ${zt.y}) scale(${zt.k})`}>
          {/* 빈 곳 클릭·드래그를 받는 바탕 */}
          <rect data-map-bg x={vx - vw * 4} y={vy - vh * 4} width={vw * 9} height={vh * 9} fill="transparent" />
          {zoneLabels.map(l => (
            <motion.text
              key={l.zone}
              initial={false}
              animate={{ x: l.x, y: l.y }}
              transition={move}
              textAnchor="middle"
              dominantBaseline="central"
              className={`pointer-events-none ${l.empty ? 'fill-ink/30' : 'fill-ink/50'}`}
              fontSize={px ? 11 / px : 12}
              letterSpacing="0.2em"
            >
              {l.zone}
            </motion.text>
          ))}
          <g fill="none" className="pointer-events-none">
            <AnimatePresence>
              {edges.map(({ id, kind, a, b }) => (
                <motion.line
                  key={id}
                  stroke={EDGE_STYLE[kind].stroke}
                  strokeWidth={EDGE_STYLE[kind].width}
                  strokeDasharray={EDGE_STYLE[kind].dash}
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                  initial={{ x1: a.x, y1: a.y, x2: a.x, y2: a.y, opacity: 0 }}
                  animate={{ x1: a.x, y1: a.y, x2: b.x, y2: b.y, opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={move}
                />
              ))}
            </AnimatePresence>
          </g>
          <AnimatePresence>
            {nodes.filter(n => n.kind === 'user' || n.kind === 'style').map(n => (
              <motion.g
                key={n.id}
                className="pointer-events-none"
                initial={{ x: n.x, y: n.y, scale: 0, opacity: 0 }}
                animate={{ x: n.x, y: n.y, scale: 1, opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                transition={move}
              >
                {n.kind === 'user'
                  ? (
                    <>
                      <circle r={n.r} fill="hsl(var(--ink))" />
                      <text textAnchor="middle" dominantBaseline="central" className="fill-paper font-serif italic" fontSize={24}>you</text>
                    </>
                  )
                  : (
                    <>
                      <motion.circle initial={false} animate={{ r: n.r }} transition={move} fill="hsl(var(--card))" stroke="hsl(var(--ink) / 0.7)" strokeWidth={1} />
                      <text textAnchor="middle" dominantBaseline="central" className="fill-ink" fontSize={font(13)} fontWeight={500}>{n.label}</text>
                    </>
                  )}
              </motion.g>
            ))}
            {nodes.filter(n => n.kind === 'brand' || n.kind === 'candidate' || n.kind === 'loading').map(n => (
              <BrandNode
                key={n.id}
                n={n}
                font={font}
                note={n.domain ? externalNotes[n.domain] : undefined}
                selected={n.domain === selectedBrand}
                reduce={reduce}
                onClick={() => {
                  if (n.kind === 'brand')
                    onBrand?.(n.domain!)
                  else if (n.kind === 'candidate')
                    onCandidate?.(n.domain!)
                }}
              />
            ))}
            {productNodes.map(n => <ProductNode key={n.id} n={n} delay={n.product?.code === arriving ? arriveDelay : 0} hovered={hovered === n.id} onHover={setHovered} onOpen={onOpen} reduce={reduce} />)}
          </AnimatePresence>
        </g>
      </motion.svg>
    </div>
  )
}

/** 지도 노드의 최종 화면 위치. viewBox가 애니메이션 중이어도 끝났을 때의 위치를 계산한다 (preserveAspectRatio: xMidYMid meet, 확대·이동 포함) */
export function mapNodeScreenPosition(code: string) {
  const g = document.querySelector<SVGGElement>(`svg [data-code="${code}"]`)
  const svg = g?.closest('svg')
  if (!g || !svg)
    return null
  const [vx, vy, vw, vh] = (svg.dataset.finalViewbox || '').split(' ').map(Number)
  const [k, tx, ty] = (svg.dataset.zoom || '1 0 0').split(' ').map(Number)
  const rect = svg.getBoundingClientRect()
  const s = Math.min(rect.width / vw, rect.height / vh)
  const ox = rect.left + (rect.width - vw * s) / 2
  const oy = rect.top + (rect.height - vh * s) / 2
  return { x: ox + (Number(g.dataset.x) * k + tx - vx) * s, y: oy + (Number(g.dataset.y) * k + ty - vy) * s, size: PRODUCT_R * 2 * s * k }
}
