# Third-party notices

loupe 웹사이트에 가져다 쓴 오픈소스와 쓴 곳. 코드를 복사해 다듬은 것은 파일 머리 주석에도 출처를 적었다.

| 저장소 | 라이선스 | 방식 | 쓴 곳 |
|---|---|---|---|
| [langgenius/webapp-conversation](https://github.com/langgenius/webapp-conversation) | MIT | 템플릿 | 프로젝트 시작점. Dify API 라우트(`app/api/*`), SSE 스트리밍 서비스(`service/`) |
| [d3/d3-force](https://github.com/d3/d3-force) | ISC | npm `d3-force@3.0.0` | `components/loupe/taste-map.tsx` 취향 지도 배치(상의·하의·아우터·브랜드 4구역으로 끌어당김, 링크·충돌·반발력, 같은 스타일끼리 뭉침) |
| [d3/d3-zoom](https://github.com/d3/d3-zoom) · [d3-selection](https://github.com/d3/d3-selection) · [d3-transition](https://github.com/d3/d3-transition) | ISC | npm `d3-zoom@3.0.0`, `d3-selection@3.0.0`, `d3-transition@3.0.1` | `components/loupe/taste-map.tsx` 취향 지도 휠·핀치 확대, 드래그 이동, '전체 보기' 되돌리기 |
| [motiondivision/motion](https://github.com/motiondivision/motion) | MIT | npm `motion@13.4.6` | 첫 화면 스크롤 연동(`useScroll`/`useTransform`), 렌즈가 퍼지며 채팅 열기(`clip-path`), 지도 동그라미 등장·위치 이동·마우스를 대면 커지는 렌즈, 카드에서 지도로 날아가기(`fly-layer.tsx`), 모바일 지도 시트, 카드 다이얼로그, 아래 react-bits·magicui 컴포넌트의 애니메이션 |
| [darkroomengineering/lenis](https://github.com/darkroomengineering/lenis) | MIT | npm `lenis@1.3.26` | `components/loupe/landing.tsx` 첫 화면 부드러운 스크롤 |
| [DavidHDev/react-bits](https://github.com/DavidHDev/react-bits) | MIT + Commons Clause | 코드 복사 후 수정 | `components/vendor/blur-text.tsx`(BlurText → 로고 등장), `components/vendor/paper-grain.tsx`(Noise의 그레인 타일 → 정적인 종이 결 배경) |
| [magicuidesign/magicui](https://github.com/magicuidesign/magicui) | MIT | 코드 복사 후 수정 | `components/vendor/magic-card.tsx`(MagicCard → 상품 카드 테두리 하이라이트), `components/vendor/lens.tsx`(Lens → 첫 화면 렌즈 안 확대) |
| [shadcn-ui/ui](https://github.com/shadcn-ui/ui) | MIT | 코드 복사 | `components/ui/card.tsx`, `carousel.tsx`, `button.tsx` (톤은 `app/styles/globals.css` 토큰으로) |
| [vercel/commerce](https://github.com/vercel/commerce) | MIT | 디자인 참고 | `app/components/fashion/product-card.tsx` 정사각형 이미지 타일·아래쪽 블러 알약 라벨·가격 칩·브랜드 표기 |
| [Instrument Serif](https://fonts.google.com/specimen/Instrument+Serif) | OFL 1.1 | `next/font/google` (자체 호스팅) | 로고, 제목 |
| [Pretendard](https://github.com/orioncactus/pretendard) | OFL 1.1 | npm `pretendard@1.3.9` | 본문 |

## react-bits

MIT + Commons Clause License Condition v1.0 — Copyright (c) 2026 David Haz

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, and distribute the Software as part of an application, website, or product, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

Commons Clause Restriction: You may use this Software, including for any commercial purpose, so long as you do not sell, sublicense, or redistribute the components themselves-whether alone, in a bundle, or as a ported version.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

## magicui, shadcn/ui, motion, lenis, vercel/commerce, webapp-conversation (MIT)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

Copyright: magicui (c) 2023 Dillion Verma · shadcn/ui (c) 2023 shadcn · motion (c) 2018 Framer B.V. / Motion Division · lenis (c) 2024 darkroom.engineering · vercel/commerce (c) 2023 Vercel, Inc. · webapp-conversation (c) LangGenius

## d3-force, d3-zoom, d3-selection, d3-transition (ISC)

Copyright 2010-2021 Mike Bostock. Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.
