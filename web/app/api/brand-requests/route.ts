import type { NextRequest } from 'next/server'
import { spawn } from 'node:child_process'
import { appendFile, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { BRAND_REQUESTS_MD, INSTA_CRAWLER_DIR, PYTHON } from '@/app/api/utils/server-config'
import { knownBrands, normName } from '@/app/api/utils/brands-db'

/**
 * 미수록 브랜드 "추가 요청".
 * POST: insta-crawler의 brand_requests.md에 한 줄 적고(brand_requests.py와 같은 형식, 같은 이름은 한 번만),
 *       add_queue.py --request를 뒤에서 돌려 수집 가능 여부를 확인한다 → 통과하면 자동 추가 대기열에 오른다.
 * GET ?domains=a,b: 대기열 상태 (확인 중 / 추가 예정 / 추가됨 / 추가 불가 + 이유)
 */
const HEADER = `# 브랜드 추가 요청

패션 추천 봇에서 사용자가 물어봤지만 아직 데이터에 없는 브랜드. \`python3 brand_requests.py\`가 Dify 실행 기록에서 모아 추가한다.
추가하고 싶은 브랜드는 \`sites.py\`에 넣고 크롤링하면 된다. 처리한 줄은 지우지 말고 \`[x]\`로 바꿔 둘 것
(줄을 지우면 다음 실행 때 다시 추가된다. 크롤링해서 수집 브랜드가 된 이름은 자동으로 건너뛴다).

`
const LINE_RE = /^- \[[ xX]\] \*\*(.+?)\*\*/
// 테스트할 때는 add_queue.py와 같은 ADD_QUEUE_FILE로 다른 파일을 쓴다
const QUEUE_FILE = process.env.ADD_QUEUE_FILE || path.join(INSTA_CRAWLER_DIR, 'state', 'add_queue.json')
const clean = (v: unknown, max: number) => String(v ?? '').replace(/[\r\n*`]/g, ' ').trim().slice(0, max)
const httpUrl = (v: unknown) => {
  try {
    const u = new URL(String(v))
    return u.protocol === 'https:' || u.protocol === 'http:' ? u.href : ''
  }
  catch {
    return ''
  }
}
const domainOf = (url: string) => new URL(url).hostname.replace(/^www\./, '').toLowerCase()

export type QueueStatus = 'checking' | 'queued' | 'adding' | 'failed' | 'added' | 'rejected' | 'gave_up'
export interface BrandRequestState { status: QueueStatus, reason: string }

async function readQueue(): Promise<Record<string, any>> {
  try {
    return JSON.parse(await readFile(QUEUE_FILE, 'utf-8'))
  }
  catch {
    return {}
  }
}

async function appendRequestLine(name: string, url: string, insta: string, from: string) {
  let text = ''
  try {
    text = await readFile(BRAND_REQUESTS_MD, 'utf-8')
  }
  catch {}
  const existing = new Set(text.split('\n').map(l => l.match(LINE_RE)?.[1]).filter(Boolean).map(n => normName(n!)))
  if (existing.has(normName(name)))
    return
  const day = new Date().toLocaleDateString('sv-SE') // 서버 시간대 기준 YYYY-MM-DD
  const line = `- [ ] **${name}** — 웹사이트 추가 요청 (${day}) · 자사몰 ${url}${insta ? ` · 인스타 ${insta}` : ''}${from ? ` · ${from}에서 디깅` : ''}\n`
  if (!text)
    await writeFile(BRAND_REQUESTS_MD, HEADER + line, 'utf-8')
  else
    await appendFile(BRAND_REQUESTS_MD, (text.endsWith('\n') ? '' : '\n') + line, 'utf-8')
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}))
  const name = clean(body.name, 60)
  const en = clean(body.en, 60)
  const url = httpUrl(body.url)
  if (!name || !url)
    return Response.json({ message: 'name, url 필요' }, { status: 400 })
  const domain = domainOf(url)
  const known = await knownBrands()
  if (known.domains.includes(domain))
    return Response.json({ status: 'added', reason: '' })

  const insta = httpUrl(body.instagram)
  const from = clean(body.from, 60)
  await appendRequestLine(name, url, insta, from)

  const cur = (await readQueue())[domain]
  if (cur && cur.status !== 'rejected')
    return Response.json({ status: cur.status, reason: cur.reason || '' })
  // 수집 가능 여부 확인은 수십 초 걸리므로 뒤에서 돌린다 (상태는 GET으로 확인)
  const args = ['add_queue.py', '--request', name, url, ...(en ? ['--en', en] : []), ...(insta ? ['--instagram', insta] : []), ...(from ? ['--from', from] : [])]
  const child = spawn(PYTHON, args, { cwd: INSTA_CRAWLER_DIR, detached: true, stdio: 'ignore' })
  child.on('error', () => {})
  child.unref()
  return Response.json({ status: 'checking', reason: '' })
}

export async function GET(request: NextRequest) {
  const domains = (request.nextUrl.searchParams.get('domains') || '').split(',').map(d => d.trim().toLowerCase()).filter(Boolean).slice(0, 50)
  const queue = await readQueue()
  const states: Record<string, BrandRequestState> = {}
  for (const d of domains) {
    if (queue[d])
      states[d] = { status: queue[d].status, reason: queue[d].reason || '' }
  }
  return Response.json({ states })
}
