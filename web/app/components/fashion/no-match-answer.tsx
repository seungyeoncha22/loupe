'use client'
import { Search } from 'lucide-react'
import { useState } from 'react'
import type { NoMatchPayload } from './payload'

interface WebBrand { name: string, en: string, url: string, domain: string, reason: string, mood: string[] }

/**
 * 맞는 상품이 없다는 답변 + "브랜드 웹 디깅" 버튼. 누르면 /api/dig(브랜드 웹 디깅 워크플로)로 비슷한 브랜드를 웹에서 찾는다.
 * 모르는 브랜드면 그 이름을, 후보가 없었으면 스타일·카테고리를 출발점으로 쓴다. 웹 검색이 10~25초 걸려서 누를 때만 부른다.
 */
export function NoMatchAnswer({ data, body }: { data: NoMatchPayload, body: string }) {
  const seed = data.brand || [...data.styles, data.category || ''].filter(Boolean).join(' ')
  const [state, setState] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [brands, setBrands] = useState<WebBrand[]>([])

  const dig = () => {
    setState('loading')
    fetch('/api/dig', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: `no_match:${seed}`, brand: seed, tags: data.styles.join(',') }),
    })
      .then(res => res.ok ? res.json() : Promise.reject(res.status))
      .then((res) => {
        setBrands(res.candidates || [])
        setState('done')
      })
      .catch(() => setState('error'))
  }

  return (
    <div className="max-w-[92%] space-y-3 text-[14px] leading-relaxed">
      <p>{body || data.text}</p>
      {seed && state !== 'done' && (
        <button
          type="button"
          onClick={dig}
          disabled={state === 'loading'}
          className="inline-flex items-center gap-1.5 rounded-full border border-ink/25 px-3 py-1.5 text-[12.5px] text-ink/75 transition-colors hover:border-ink hover:text-ink disabled:opacity-60"
        >
          <Search className="h-3.5 w-3.5" strokeWidth={1.75} />
          {state === 'loading' ? '웹에서 찾는 중… (10~25초)' : state === 'error' ? '다시 찾아보기' : '비슷한 브랜드 웹에서 찾아보기'}
        </button>
      )}
      {state === 'done' && brands.length === 0 && <p className="text-[12.5px] text-ink/60">웹에서도 비슷한 브랜드를 찾지 못했어요.</p>}
      {brands.length > 0 && (
        <ul className="space-y-2 border-l border-ink/30 pl-3">
          {brands.map(b => (
            <li key={b.domain}>
              <a href={b.url} target="_blank" rel="noopener noreferrer" className="font-serif text-[15px] hover:underline">{b.name}</a>
              {b.en && <span className="ml-2 text-[10px] uppercase tracking-[0.18em] text-ink/40">{b.en}</span>}
              {b.reason && <p className="text-[12.5px] text-ink/65">{b.reason}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
