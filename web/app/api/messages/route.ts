import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'
import { client, getInfo, setSession } from '@/app/api/utils/common'

// 대화 기록. 취향 지도를 복원하려면 예전 답변까지 필요해서 first_id(이 메시지보다 오래된 것)와 limit(최대 100)로 페이지를 넘긴다.
export async function GET(request: NextRequest) {
  const { sessionId, user } = getInfo(request)
  const { searchParams } = new URL(request.url)
  const conversationId = searchParams.get('conversation_id')
  const firstId = searchParams.get('first_id') || null
  const limit = Math.min(Number(searchParams.get('limit')) || 20, 100)
  try {
    const { data }: any = await client.getConversationMessages(user, conversationId as string, firstId as any, limit as any)
    return NextResponse.json(data, { headers: setSession(sessionId) })
  }
  catch (error: any) {
    // 다른 세션의 대화이거나 지워진 대화면 Dify가 404를 준다. 그대로 넘겨 화면이 저장된 대화 ID를 지우게 한다
    const status = error?.response?.status || 500
    return NextResponse.json({ data: [], has_more: false, message: error?.response?.data?.message || 'error' }, { status, headers: setSession(sessionId) })
  }
}
