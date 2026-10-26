import type { NextRequest } from 'next/server'
import { DIFY_API_URL, DIFY_DIG_API_KEY, DIFY_MOCK } from '@/app/api/utils/server-config'
import { knownBrands } from '@/app/api/utils/brands-db'

/**
 * "비슷한 브랜드 더 파보기"의 미수록 후보: Dify '브랜드 웹 디깅' 워크플로(Tavily 웹 검색 → 후보 고르기 → 자사몰 확인)를 부른다.
 * 웹 검색은 느리고(10~25초) 비용이 들어서, 같은 출발 브랜드는 서버에서 6시간 동안 결과를 재사용한다.
 */
export interface WebCandidate { name: string, en: string, url: string, domain: string, instagram: string, reason: string, mood: string[] }

const TTL = 6 * 60 * 60 * 1000
const cache = new Map<string, { at: number, data: Promise<WebCandidate[]> }>()

async function run(brand: string, tags: string): Promise<WebCandidate[]> {
  const known = await knownBrands()
  const res = await fetch(`${DIFY_API_URL}/workflows/run`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${DIFY_DIG_API_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      inputs: { brand, tags, known: known.domains.join(','), known_names: known.names.join(',') },
      response_mode: 'blocking',
      user: 'loupe-dig',
    }),
    signal: AbortSignal.timeout(90_000),
  })
  if (!res.ok)
    throw new Error(`dify ${res.status}`)
  const body = await res.json()
  const result = JSON.parse(body?.data?.outputs?.result || '{}')
  // 그사이 수집 브랜드가 된 곳은 빼고, 주소는 확인된(리다이렉트 뒤) 도메인 첫 화면으로 맞춘다 (지도 저장 키 = 도메인)
  return (result.candidates || [])
    .filter((c: WebCandidate) => c.domain && !known.domains.includes(c.domain))
    .map((c: WebCandidate) => ({ ...c, url: `https://${c.domain}/` }))
}

export async function POST(request: NextRequest) {
  const { key, brand, tags } = await request.json().catch(() => ({}))
  if (typeof key !== 'string' || typeof brand !== 'string' || !brand.trim() || brand.length > 120)
    return Response.json({ message: 'brand 필요' }, { status: 400 })
  if (DIFY_MOCK || !DIFY_DIG_API_KEY)
    return Response.json({ candidates: [] })
  const hit = cache.get(key)
  if (!hit || Date.now() - hit.at > TTL) {
    // LLM이 가끔 빈 목록을 내므로 비면 한 번 더 돌린다
    const data = run(brand.trim(), String(tags || '').slice(0, 200))
      .then(list => list.length ? list : run(brand.trim(), String(tags || '').slice(0, 200)))
    cache.set(key, { at: Date.now(), data })
    // 실패나 빈 결과는 캐시하지 않는다 (다음에 다시 찾아본다)
    data.then(list => !list.length && cache.delete(key), () => cache.delete(key))
  }
  try {
    return Response.json({ candidates: await cache.get(key)!.data })
  }
  catch {
    return Response.json({ candidates: [], message: '웹 검색 실패' }, { status: 502 })
  }
}
