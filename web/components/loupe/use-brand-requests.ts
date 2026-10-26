'use client'
import { useCallback, useEffect, useMemo, useState } from 'react'

/**
 * 미수록 브랜드 "추가 요청"과 자동 추가 대기열 상태 (/api/brand-requests ← insta-crawler/state/add_queue.json).
 * 확인 중이면 4초마다, 추가 예정이면 1분마다 다시 읽는다.
 */
export type QueueStatus = 'checking' | 'queued' | 'adding' | 'failed' | 'added' | 'rejected' | 'gave_up'
export interface RequestInfo { status: QueueStatus | 'sending' | 'error', reason: string }

export const requestLabel = (s: RequestInfo['status']) => ({
  sending: '요청 중', error: '요청 실패', checking: '확인 중', queued: '추가 예정', adding: '추가 예정', failed: '추가 예정',
  added: '추가됨', rejected: '추가 불가', gave_up: '추가 불가',
} as const)[s]

export function useBrandRequests(domains: string[]) {
  const [states, setStates] = useState<Record<string, RequestInfo>>({})
  const key = useMemo(() => [...new Set(domains)].sort().join(','), [domains])

  const refresh = useCallback(async () => {
    if (!key)
      return
    try {
      const res = await fetch(`/api/brand-requests?domains=${encodeURIComponent(key)}`, { cache: 'no-store' })
      const body = await res.json()
      setStates(prev => ({ ...prev, ...(body?.states ?? {}) }))
    }
    catch {}
  }, [key])
  useEffect(() => {
    refresh()
  }, [refresh])

  const statuses = Object.values(states).map(s => s.status)
  const delay = statuses.some(s => s === 'checking' || s === 'sending') ? 4000 : statuses.some(s => s === 'queued' || s === 'adding' || s === 'failed') ? 60000 : 0
  useEffect(() => {
    if (!delay)
      return
    const t = setInterval(refresh, delay)
    return () => clearInterval(t)
  }, [delay, refresh])

  const request = useCallback((b: { domain: string, name: string, en?: string, url: string, instagram?: string, from?: string }) => {
    setStates(prev => ({ ...prev, [b.domain]: { status: 'sending', reason: '' } }))
    fetch('/api/brand-requests', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) })
      .then(r => r.json().then(body => ({ ok: r.ok, body })))
      .then(({ ok, body }) => setStates(prev => ({ ...prev, [b.domain]: ok ? { status: body.status, reason: body.reason || '' } : { status: 'error', reason: '' } })))
      .catch(() => setStates(prev => ({ ...prev, [b.domain]: { status: 'error', reason: '' } })))
  }, [])

  return { states, request }
}
