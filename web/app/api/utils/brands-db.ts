import 'server-only'
import { readFile, stat } from 'node:fs/promises'
import path from 'node:path'

/** public/brands.json의 수집 브랜드 (도메인, 이름). 파일이 바뀌면(add_brand.py) 다시 읽는다 */
let cached: { mtime: number, domains: string[], names: string[] } | null = null

export async function knownBrands() {
  const file = path.join(process.cwd(), 'public', 'brands.json')
  const mtime = (await stat(file)).mtimeMs
  if (cached?.mtime !== mtime) {
    const data = JSON.parse(await readFile(file, 'utf-8'))
    const brands = Object.entries<any>(data.brands || {})
    cached = { mtime, domains: brands.map(([d]) => d), names: brands.map(([, b]) => `${b.ko}/${b.en}`) }
  }
  return cached
}

/** brand_requests.py의 norm과 같은 이름 정규화 (대소문자·공백·기호 무시) */
export const normName = (name: string) => name.toLowerCase().replace(/[^0-9a-z가-힣]/g, '')
