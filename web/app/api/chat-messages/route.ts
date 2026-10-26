import type { NextRequest } from 'next/server'
import { client, getInfo, setSession } from '@/app/api/utils/common'

export async function POST(request: NextRequest) {
  const body = await request.json()
  const {
    inputs,
    query,
    files,
    conversation_id: conversationId,
    response_mode: responseMode,
  } = body
  const { sessionId, user } = getInfo(request)
  try {
    const res = await client.createChatMessage(inputs, query, user, responseMode, conversationId, files)
    return new Response(res.data as any, { headers: { 'Content-Type': 'text/event-stream', ...setSession(sessionId) } })
  }
  catch (error: any) {
    // 대화가 없을 때(지워짐, 다른 세션) 등: 상태 코드와 메시지를 그대로 넘겨 화면이 알 수 있게 한다
    const status = error?.response?.status || 500
    return Response.json({ code: 'dify_error', message: error?.response?.data?.message || 'Dify 요청 실패', status }, { status, headers: setSession(sessionId) })
  }
}
