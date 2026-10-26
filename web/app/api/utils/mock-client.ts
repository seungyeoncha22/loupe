import 'server-only'
import { v4 } from 'uuid'
import answers from '@/mock/answers.json'

/**
 * DIFY_MOCK=1 일 때 쓰는 가짜 Dify 클라이언트 (개발·화면 확인용).
 * mock/answers.json은 실제 워크플로 Code 노드와 실제 지식베이스 검색으로 만든 답변이라 화면에 나오는 데이터는 진짜다.
 * 대화는 서버 메모리에만 있어서 dev 서버를 다시 켜면 사라진다.
 */
type Fixture = { name: string, answer: string }
type Message = { id: string, conversation_id: string, query: string, answer: string, created_at: number, feedback: null, message_files: [], retriever_resources: [], agent_thoughts: [] }

const fixtures = answers as Fixture[]
const byName = (name: string) => fixtures.find(f => f.name === name)?.answer ?? ''
const conversations = new Map<string, { id: string, name: string, created_at: number, messages: Message[], next: number, ratings: Record<string, number> }>()

function pickAnswer(query: string, conv: { next: number, ratings: Record<string, number> }) {
  const rating = query.match(/(\d+)\s*번\s*(좋아|별로|취소)(?:\s*#([0-9a-z]{4}))?/)
  if (rating) {
    if (rating[3] && rating[2] === '취소')
      delete conv.ratings[rating[3]]
    else if (rating[3])
      conv.ratings[rating[3]] = rating[2] === '좋아' ? 1 : -1
    return `✓\n\n<!--fashion-ui ${JSON.stringify({ type: 'rating', ratings: conv.ratings, v: 1 })} -->`
  }
  if (/비슷한\s*브랜드|같은\s*브랜드/.test(query))
    return /코이세이오|coyseio/i.test(query) ? byName('유사 브랜드') : byName('없는 브랜드(텍스트만)')
  if (/브랜드/.test(query))
    return byName('스타일 브랜드')
  if (/다음\s*추천/.test(query)) {
    conv.next = conv.next % 2 + 1
    return byName(conv.next === 1 ? '다음 추천 2' : '다음 추천 3 (탐색 포함)')
  }
  return byName('상품 추천 1')
}

function sse(events: object[]) {
  const enc = new TextEncoder()
  return new ReadableStream({
    async start(controller) {
      for (const e of events) {
        controller.enqueue(enc.encode(`data: ${JSON.stringify(e)}\n\n`))
        await new Promise(r => setTimeout(r, 40))
      }
      controller.close()
    },
  })
}

export const mockClient = {
  async getApplicationParameters() {
    return {
      data: {
        opening_statement: '안녕하세요! 원하는 옷이나 좋아하는 스타일·브랜드를 말씀해 주세요.',
        suggested_questions: ['빈티지한 아우터 추천해줘', '코이세이오랑 비슷한 브랜드', '빈티지 좋아하는데 브랜드 추천해줘'],
        user_input_form: [],
        file_upload: { enabled: false },
        system_parameters: {},
      },
    }
  },
  async getConversations() {
    const data = [...conversations.values()].reverse().map(c => ({ id: c.id, name: c.name, inputs: {}, introduction: '', created_at: c.created_at }))
    return { data: { data, has_more: false, limit: 20 } }
  },
  async getConversationMessages(_user: string, conversationId: string, firstId?: string | null, limit?: number | null) {
    const all = conversations.get(conversationId)?.messages ?? []
    const end = firstId ? all.findIndex(m => m.id === firstId) : all.length
    const size = limit || 20
    const page = all.slice(Math.max(0, end - size), end)
    return { data: { data: page, has_more: end - size > 0, limit: size } }
  },
  async renameConversation(conversationId: string) {
    return { data: { id: conversationId, name: conversations.get(conversationId)?.name ?? '' } }
  },
  async messageFeedback() {
    return { data: { result: 'success' } }
  },
  async fileUpload() {
    throw new Error('mock: 파일 업로드 없음')
  },
  async createChatMessage(_inputs: object, query: string, _user: string, _stream: boolean, conversationId?: string | null) {
    let conv = conversationId ? conversations.get(conversationId) : undefined
    if (!conv) {
      conv = { id: v4(), name: query.slice(0, 20), created_at: Math.floor(Date.now() / 1000), messages: [], next: 0, ratings: {} }
      conversations.set(conv.id, conv)
    }
    const answer = pickAnswer(query, conv)
    const messageId = v4()
    conv.messages.push({ id: messageId, conversation_id: conv.id, query, answer, created_at: Math.floor(Date.now() / 1000), feedback: null, message_files: [], retriever_resources: [], agent_thoughts: [] })
    const base = { conversation_id: conv.id, message_id: messageId, task_id: v4(), id: messageId }
    // 실제 Dify처럼 본문은 여러 조각, 숨은 데이터 블록은 한 덩어리로 온다
    const [visible, hidden = ''] = answer.split(/(?=\n\n<!--fashion-ui )/)
    const chunks = visible.match(/[\s\S]{1,400}/g) ?? []
    return {
      data: sse([
        ...chunks.map(c => ({ event: 'message', answer: c, ...base })),
        ...(hidden ? [{ event: 'message', answer: hidden, ...base }] : []),
        { event: 'message_end', metadata: {}, ...base },
      ]),
    }
  },
}
