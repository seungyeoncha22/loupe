import type { NextRequest } from 'next/server'
import { ChatClient } from 'dify-client'
import { v4 } from 'uuid'
import { APP_ID, APP_INFO } from '@/config'
import { DIFY_API_KEY, DIFY_API_URL, DIFY_MOCK } from '@/app/api/utils/server-config'
import { mockClient } from '@/app/api/utils/mock-client'

const userPrefix = `user_${APP_ID}:`

export const getInfo = (request: NextRequest) => {
  const sessionId = request.cookies.get('session_id')?.value || v4()
  const user = userPrefix + sessionId
  return {
    sessionId,
    user,
  }
}

// Dify 대화는 user(= 이 세션 ID) 단위로 묶인다. 쿠키가 없으면 요청마다 다른 사용자가 되어 대화를 못 찾으므로(404)
// 모든 API 응답에서 쿠키를 심고, 브라우저를 닫아도 1년 유지한다
export const setSession = (sessionId: string) => {
  const base = `session_id=${sessionId}; Path=/; Max-Age=31536000; HttpOnly`
  if (APP_INFO.disable_session_same_site)
  { return { 'Set-Cookie': `${base}; SameSite=None; Secure` } }

  return { 'Set-Cookie': `${base}; SameSite=Lax` }
}

// 모든 Dify 호출은 이 서버 쪽 client를 거친다 (API 키는 서버에만 있음)
type DifyChatClient = InstanceType<typeof ChatClient>
export const client: DifyChatClient = DIFY_MOCK ? (mockClient as unknown as DifyChatClient) : new ChatClient(DIFY_API_KEY, DIFY_API_URL)
