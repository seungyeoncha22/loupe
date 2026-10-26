import 'server-only'

// Dify 앱 API 키는 서버(API 라우트)에서만 읽는다. NEXT_PUBLIC_ 접두어를 쓰지 않으므로 브라우저 번들에 들어가지 않는다.
export const DIFY_API_KEY = process.env.DIFY_API_KEY || ''
export const DIFY_API_URL = process.env.DIFY_API_URL || 'http://localhost/v1'
// 예시 답변(mock/answers.json)으로 Dify 없이 화면을 확인할 때 1
export const DIFY_MOCK = process.env.DIFY_MOCK === '1'
// 브랜드 웹 디깅 Dify 앱(workflow) API 키 — "비슷한 브랜드 더 파보기"의 미수록 후보
export const DIFY_DIG_API_KEY = process.env.DIFY_DIG_API_KEY || ''
// insta-crawler 폴더: "추가 요청"을 적는 brand_requests.md, 자동 추가 대기열(add_queue.py, state/add_queue.json)
export const INSTA_CRAWLER_DIR = process.env.INSTA_CRAWLER_DIR || `${process.env.HOME}/insta-crawler`
export const BRAND_REQUESTS_MD = process.env.BRAND_REQUESTS_MD || `${INSTA_CRAWLER_DIR}/brand_requests.md`
export const PYTHON = process.env.PYTHON || 'python3'
