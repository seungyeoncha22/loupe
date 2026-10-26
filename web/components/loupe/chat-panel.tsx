'use client'
import { ArrowUp } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import StreamdownMarkdown from '@/app/components/base/streamdown-markdown'
import { BrandAnswer } from '@/app/components/fashion/brand-answer'
import { ProductAnswer } from '@/app/components/fashion/product-answer'
import { NoMatchAnswer } from '@/app/components/fashion/no-match-answer'
import type { ParsedMessage } from './derive'

const SUGGESTIONS = ['빈티지한 아우터 추천해줘', '코이세이오랑 비슷한 브랜드', '페미닌한 브랜드 뭐 있어?']

function Pending() {
  return (
    <div className="flex items-center gap-1.5 py-2" aria-label="답변을 찾는 중">
      {[0, 1, 2].map(i => <span key={i} className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink/40" style={{ animationDelay: `${i * 160}ms` }} />)}
    </div>
  )
}

function Message({ m }: { m: ParsedMessage }) {
  if (m.role === 'user') {
    return (
      <div className="flex justify-end">
        <p className="max-w-[85%] rounded-[18px] rounded-br-[4px] bg-ink px-4 py-2.5 text-[14px] leading-relaxed text-paper">{m.text}</p>
      </div>
    )
  }
  const p = m.payload
  if (p?.type === 'products')
    return <ProductAnswer data={p} />
  if (p?.type === 'brands')
    return <BrandAnswer data={p} />
  if (p?.type === 'no_match')
    return <NoMatchAnswer data={p} body={m.body} />
  // 응답 중에는 데이터 블록이 오기 전 마크다운이 잠깐 보이지 않게 로딩만 표시
  if (m.pending || !m.body)
    return <Pending />
  return (
    <div className="max-w-[92%] text-[14px] leading-relaxed [&_p]:my-1">
      <StreamdownMarkdown content={m.body} />
    </div>
  )
}

export function ChatPanel({ messages, responding, restoring, onSend }: {
  messages: ParsedMessage[]
  responding: boolean
  restoring: boolean
  onSend: (text: string) => void
}) {
  const [draft, setDraft] = useState('')
  const listRef = useRef<HTMLDivElement>(null)
  const composing = useRef(false)

  useEffect(() => {
    const el = listRef.current
    if (el)
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages.length, messages[messages.length - 1]?.pending])

  const submit = () => {
    if (!draft.trim() || responding)
      return
    onSend(draft)
    setDraft('')
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div ref={listRef} className="min-h-0 flex-1 space-y-7 overflow-y-auto overscroll-contain px-5 pb-6 pt-6">
        {!restoring && messages.length === 0 && (
          <div className="flex h-full flex-col justify-end gap-5 pb-4">
            <p className="font-serif text-4xl leading-[1.05]">
              무엇을
              <br />
              <span className="italic">들여다볼까요?</span>
            </p>
            <p className="text-[13px] leading-relaxed text-ink/60">원하는 옷이나 좋아하는 스타일, 브랜드를 말해 주세요. 좋아요를 누를수록 취향 지도가 채워져요.</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map(s => (
                <button key={s} type="button" onClick={() => onSend(s)} className="rounded-full border border-ink/25 px-3.5 py-1.5 text-[12.5px] transition-colors hover:border-ink hover:bg-ink hover:text-paper">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map(m => <Message key={m.id} m={m} />)}
      </div>
      <form
        className="border-t border-ink/10 p-3"
        onSubmit={(e) => {
          e.preventDefault()
          submit()
        }}
      >
        <div className="flex items-end gap-2 rounded-[22px] border border-ink/20 bg-card px-4 py-2 focus-within:border-ink">
          <textarea
            value={draft}
            rows={1}
            placeholder="예: 빈티지한 아우터 추천해줘"
            aria-label="메시지"
            onChange={e => setDraft(e.target.value)}
            onCompositionStart={() => { composing.current = true }}
            onCompositionEnd={() => { composing.current = false }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && !composing.current) {
                e.preventDefault()
                submit()
              }
            }}
            className="max-h-32 min-h-[28px] flex-1 resize-none bg-transparent py-1 text-[14px] leading-relaxed outline-none placeholder:text-ink/35"
          />
          <button type="submit" aria-label="보내기" disabled={!draft.trim() || responding} className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-ink text-paper transition-opacity disabled:opacity-25">
            <ArrowUp className="h-4 w-4" strokeWidth={1.75} />
          </button>
        </div>
      </form>
    </div>
  )
}
