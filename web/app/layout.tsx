import type { Metadata, Viewport } from 'next'
import { Instrument_Serif } from 'next/font/google'

import 'pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css'
import './styles/globals.css'
import './styles/markdown.scss'

// 로고와 제목용 세리프. 빌드 때 받아서 자체 호스팅된다
const serif = Instrument_Serif({ subsets: ['latin'], weight: '400', style: ['normal', 'italic'], variable: '--font-serif', display: 'swap' })

export const metadata: Metadata = {
  title: 'loupe',
  description: '숨은 브랜드를 가까이 들여다보는 패션 디깅',
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#F3EFE8',
}

const RootLayout = ({ children }: { children: React.ReactNode }) => {
  return (
    <html lang="ko" className={serif.variable}>
      <body className="bg-paper font-sans text-ink">{children}</body>
    </html>
  )
}

export default RootLayout
