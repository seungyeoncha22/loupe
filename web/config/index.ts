import type { AppInfo } from '@/types/app'

// 브라우저에도 들어가는 값만 둔다. Dify 앱 API 키와 API 주소는 서버 전용(app/api/utils/server-config.ts, .env.local의 DIFY_*).
// APP_ID는 비밀이 아니고, 브라우저 저장소에서 대화 ID를 앱별로 구분하는 데만 쓴다.
export const APP_ID = process.env.NEXT_PUBLIC_APP_ID || 'fashion-bot'
export const APP_INFO: AppInfo = {
  title: '패션 추천 봇',
  description: '취향에 맞는 옷과 브랜드를 찾아드려요',
  copyright: '',
  privacy_policy: '',
  default_language: 'en',
  disable_session_same_site: false, // set it to true if you want to embed the chatbot in an iframe
}

export const isShowPrompt = false
export const promptTemplate = 'I want you to act as a javascript console.'

export const API_PREFIX = '/api'

export const LOCALE_COOKIE_NAME = 'locale'

export const DEFAULT_VALUE_MAX_LEN = 48
