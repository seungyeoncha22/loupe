// 상품명으로 카테고리 재확인 — 워크플로 "후보 정리" 노드의 name_category와 같은 규칙.
// 워크플로가 카드마다 category를 보내지만, 그 필드가 없던 예전 답변의 상품을 지도에 올릴 때 이 함수로 판단한다.
export type Zone = '상의' | '하의' | '아우터' | '브랜드'
export const PRODUCT_ZONES: Zone[] = ['상의', '하의', '아우터']

const OUTER = ['카디건', '가디건', 'cardigan', '자켓', '재킷', 'jacket', '코트', 'coat', '점퍼', 'jumper', '블루종', 'blouson', '파카', 'parka',
  '패딩', 'padding', '무스탕', 'mustang', '바람막이', 'windbreaker', '아노락', 'anorak', '집업', 'zip-up', 'zipup', '블레이저', 'blazer', '트렌치', 'trench', '야상']
const TOP = ['t', '니트', 'knit', '스웨터', 'sweater', '티셔츠', '티', 'tee', 't-shirt', '블라우스', 'blouse', '셔츠', 'shirt', '맨투맨', 'sweatshirt',
  '후드', '후디', 'hoodie', '탑', 'top', '슬리브', 'sleeve', '폴로', 'polo', '나시', '탱크', 'tank']
const BOTTOM = ['팬츠', 'pants', '바지', '슬랙스', 'slacks', '트라우저', 'trousers', '진', 'jeans', '스커트', 'skirt', '치마', '쇼츠', 'shorts',
  '반바지', '레깅스', 'leggings', '조거', 'jogger']

const isAscii = (w: string) => /^[\x00-\x7F]+$/.test(w)
const hasWord = (text: string, w: string) => isAscii(w)
  ? new RegExp(`(?<![a-z0-9])${w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![a-z0-9])`).test(text)
  : text.includes(w)

export function nameCategory(name: string, fallback: string): Exclude<Zone, '브랜드'> {
  const low = name.replace(/\([^)]*\)|\[[^\]]*\]/g, ' ').toLowerCase()
  if (OUTER.some(w => hasWord(low, w)))
    return '아우터'
  const tail = low.split(/\s+/).filter(Boolean).slice(-2)
  const inTail = (words: string[]) => tail.some(t => words.some(w => isAscii(w) ? hasWord(t, w) : t.endsWith(w)))
  if (inTail(TOP))
    return '상의'
  if (inTail(BOTTOM))
    return '하의'
  return (PRODUCT_ZONES as string[]).includes(fallback) ? fallback as Exclude<Zone, '브랜드'> : '상의'
}
