'use client'
/**
 * PaperGrain — react-bits(DavidHDev/react-bits, src/ts-tailwind/Animations/Noise)의 그레인 타일 생성(paintTile, generator)을
 * 가져와 다듬은 것. Copyright (c) 2026 David Haz. MIT + Commons Clause (THIRD_PARTY_NOTICES.md 참고)
 *
 * 바꾼 점: 원본은 매 프레임 그레인·먼지·스크래치·스캔라인을 다시 그리는 필름 노이즈다. 성능과 매거진 톤을 위해
 * 256px 그레인 타일을 한 번만 만들어 배경 이미지로 반복하는 '종이 결'만 남겼다 (애니메이션 없음).
 */
import { useEffect, useState } from 'react'

const TILE = 256

// react-bits Noise의 시드 고정 난수 생성기
const generator = (seed: number) => {
  let state = seed >>> 0 || 1
  return () => {
    state = (state + 0x6D2B79F5) | 0
    let t = Math.imul(state ^ (state >>> 15), 1 | state)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v))

function paintTile(contrast: number) {
  const canvas = document.createElement('canvas')
  canvas.width = TILE
  canvas.height = TILE
  const ctx = canvas.getContext('2d')
  if (!ctx)
    return ''
  const image = ctx.createImageData(TILE, TILE)
  const random = generator(1013904223)
  const range = 0.5 + contrast * 1.1
  for (let i = 0; i < image.data.length; i += 4) {
    const v = clamp(0.5 + (random() + random() - 1) * range, 0, 1) * 255
    image.data[i] = v
    image.data[i + 1] = v
    image.data[i + 2] = v
    image.data[i + 3] = 255
  }
  ctx.putImageData(image, 0, 0)
  return canvas.toDataURL('image/png')
}

export function PaperGrain({ opacity = 0.06, contrast = 0.6, className = 'fixed' }: { opacity?: number, contrast?: number, className?: string }) {
  const [url, setUrl] = useState('')
  useEffect(() => setUrl(paintTile(contrast)), [contrast])
  if (!url)
    return null
  return (
    <div
      aria-hidden
      className={`pointer-events-none inset-0 z-0 ${className}`}
      style={{ backgroundImage: `url(${url})`, backgroundSize: `${TILE}px`, opacity, mixBlendMode: 'multiply' }}
    />
  )
}
