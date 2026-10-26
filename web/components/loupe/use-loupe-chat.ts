'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { sendChatMessage } from '@/service'
import { APP_ID } from '@/config'

/**
 * Dify 대화 상태. 서버 API 라우트(/api/chat-messages, /api/messages)를 거치므로 API 키는 브라우저에 없다.
 * conversation_id를 브라우저에 저장해 두고 그대로 보내서, 워크플로의 대화 변수(평가, 보여준 상품 등)가 이어진다.
 */
export interface LoupeMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  pending?: boolean
}

const STORAGE_KEY = `loupe:conversation:${APP_ID}`
const HISTORY_PAGE = 100
const HISTORY_MAX_PAGES = 10

const noop = () => {}

function readStored() {
  try {
    return localStorage.getItem(STORAGE_KEY)
  }
  catch {
    return null
  }
}
function writeStored(id: string | null) {
  try {
    if (id)
      localStorage.setItem(STORAGE_KEY, id)
    else
      localStorage.removeItem(STORAGE_KEY)
  }
  catch {}
}

/** 대화 기록 전체 (오래된 → 최신). 지도 복원에 예전 답변이 필요해서 페이지를 넘겨 다 불러온다 */
async function loadHistory(conversationId: string): Promise<LoupeMessage[] | null> {
  const pages: any[][] = []
  let firstId = ''
  for (let i = 0; i < HISTORY_MAX_PAGES; i++) {
    const res = await fetch(`/api/messages?conversation_id=${encodeURIComponent(conversationId)}&limit=${HISTORY_PAGE}&first_id=${firstId}`)
    if (!res.ok)
      return null
    const body = await res.json()
    const data: any[] = body?.data ?? []
    pages.unshift(data)
    if (!body?.has_more || !data.length)
      break
    firstId = data[0].id
  }
  return pages.flat().flatMap(m => [
    { id: `q-${m.id}`, role: 'user' as const, text: m.query ?? '' },
    { id: m.id, role: 'assistant' as const, text: m.answer ?? '' },
  ])
}

/**
 * getInputs: 새 대화의 첫 메시지에 붙일 Dify 입력 (저장된 취향 taste). 이어지는 대화에서는 보내지 않는다 —
 * Dify는 대화 첫 메시지의 입력만 쓰고, 그 뒤 취향은 대화 변수로 이어진다.
 */
export function useLoupeChat(getInputs?: () => Record<string, string>) {
  const inputsRef = useRef(getInputs)
  inputsRef.current = getInputs
  // 답변 중에 눌린 숨은 메시지(브랜드 저장 등)는 기다렸다 차례로 보낸다
  const queueRef = useRef<string[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<LoupeMessage[]>([])
  const [responding, setResponding] = useState(false)
  const [restoring, setRestoring] = useState(true)
  const convRef = useRef<string | null>(null)
  const respondingRef = useRef(false)

  useEffect(() => {
    const stored = readStored()
    if (!stored) {
      setRestoring(false)
      return
    }
    loadHistory(stored).then((history) => {
      if (history) {
        convRef.current = stored
        setConversationId(stored)
        setMessages(history)
      }
      else {
        writeStored(null) // 지워진 대화
      }
      setRestoring(false)
    })
  }, [])

  const send = useCallback((query: string, { queue = false } = {}) => {
    const text = query.trim()
    if (!text)
      return
    if (respondingRef.current) {
      if (queue)
        queueRef.current.push(text)
      return
    }
    respondingRef.current = true
    setResponding(true)
    const stamp = Date.now()
    const answerId = `a-${stamp}`
    setMessages(prev => [...prev, { id: `q-${stamp}`, role: 'user', text }, { id: answerId, role: 'assistant', text: '', pending: true }])
    // 상태 갱신 함수는 순수해야 한다 (개발 모드 StrictMode는 두 번 실행한다). 메시지는 끝까지 로컬 id(answerId)로 찾는다
    const finish = () => {
      respondingRef.current = false
      setResponding(false)
      setMessages(prev => prev.map(m => m.id === answerId ? { ...m, pending: false } : m))
      const next = queueRef.current.shift()
      if (next)
        setTimeout(() => sendRef.current(next, { queue: true }), 0)
    }
    const inputs = convRef.current ? {} : (inputsRef.current?.() ?? {})
    sendChatMessage({ inputs, query: text, conversation_id: convRef.current }, {
      onData: (chunk, _first, { conversationId: cid }) => {
        if (cid && cid !== convRef.current) {
          convRef.current = cid
          setConversationId(cid)
          writeStored(cid)
        }
        setMessages(prev => prev.map(m => m.id === answerId ? { ...m, text: m.text + chunk } : m))
      },
      onCompleted: finish,
      onError: () => {
        setMessages(prev => prev.map(m => m.id === answerId && !m.text ? { ...m, text: '연결이 잠시 불안정해요. 다시 한 번 말씀해 주세요.' } : m))
        finish()
        // 저장된 대화가 Dify에 더 없으면(지워짐 등) 다음 메시지는 새 대화로 시작한다
        const cid = convRef.current
        if (cid) {
          fetch(`/api/messages?conversation_id=${encodeURIComponent(cid)}&limit=1`).then((res) => {
            if (!res.ok && convRef.current === cid) {
              convRef.current = null
              writeStored(null)
              setConversationId(null)
            }
          }).catch(noop)
        }
      },
      onMessageEnd: noop,
      onMessageReplace: noop,
      onThought: noop,
      onFile: noop,
      onWorkflowStarted: noop,
      onNodeStarted: noop,
      onNodeFinished: noop,
      onWorkflowFinished: noop,
    })
  }, [])
  const sendRef = useRef(send)
  sendRef.current = send

  const reset = useCallback(() => {
    if (respondingRef.current)
      return
    queueRef.current = []
    convRef.current = null
    writeStored(null)
    setConversationId(null)
    setMessages([])
  }, [])

  return { conversationId, messages, responding, restoring, send, reset }
}
