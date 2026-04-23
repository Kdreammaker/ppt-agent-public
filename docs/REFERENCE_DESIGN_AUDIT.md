# Reference Design Audit

이 문서는 `assets/slides/templates/decks/*.pptx`를 기준으로 원본 reference의 시각 언어를 추출한 결과입니다.
자동 생성 deck의 디자인 품질을 높이기 위해, 단순 slide purpose뿐 아니라 `design_tier`, `quality_score`, `usage_policy`를 함께 사용합니다.

## 핵심 결론
- `template_library_04_v1`는 구조 참조용입니다. 그대로 디자인 기준으로 쓰면 완성도가 낮아지기 쉽습니다.
- `template_library_01_v1`는 내부/외부 공유용 B2B 카드 시스템의 기준으로 적합합니다.
- `template_library_02_v1`는 데이터, 차트, 시장/리스크 서사의 기준으로 가장 강합니다.
- `template_library_03_v1`는 스크린샷, 사례, 성과 증명 중심 슬라이드의 기준으로 좋습니다.
- 앞으로 자동 선택은 purpose만 보지 말고 `quality_score`, `usage_policy`, `style_tags`를 같이 봐야 합니다.

## template_library_04_v1

- Scope: `report`
- Slides: `22`
- Avg shapes: `16.7`
- Avg text chars: `235.0`
- Avg images: `1.7`
- Layout signatures: `[('image-led', 8), ('open-canvas', 6), ('text-card-system', 4), ('minimal-cover-or-divider', 3), ('dense-card-system', 1)]`
- Dominant fills: `[('#0540F3', 15), ('#26D07C', 7), ('#00249C', 1), ('#D6D5FF', 1), ('#9EACFF', 1)]`
- Dominant font colors: `[('#0540F3', 22), ('#FFFFFF', 21), ('#000000', 10), ('#004BF7', 8), ('#2A2A2A', 4)]`

### 디자인 해석
- 구조와 목적 분류에는 유용하지만, 시각적 완성도는 낮은 편입니다.
- 원본 placeholder의 빈 여백과 작은 텍스트가 많아 그대로 쓰기보다 layout builder의 골격으로 쓰는 것이 안전합니다.
- 커버, 목차, 2x2, 4-step처럼 목적형 구조를 빌려오고 실제 디자인은 별도 규칙으로 덮는 전략이 적합합니다.

## template_library_01_v1

- Scope: `sales`
- Slides: `10`
- Avg shapes: `42`
- Avg text chars: `502.8`
- Avg images: `8.5`
- Layout signatures: `[('image-led', 9), ('open-canvas', 1)]`
- Dominant fills: `[('#1E3A8A', 96), ('#FFFFFF', 14), ('#EFF6FF', 4), ('#F59E0B', 1), ('#6B7280', 1)]`
- Dominant font colors: `[('#6B7280', 140), ('#1E3A8A', 89), ('#FFFFFF', 17)]`

### 디자인 해석
- 흰 배경, 네이비 룰, 연한 카드, 작은 아이콘으로 구성된 정돈된 B2B 세일즈 문법이 강합니다.
- 상단 얇은 라인과 우상단 페이지, 하단의 작은 브랜드 문구가 반복되어 deck 전체 rhythm을 만듭니다.
- 내부 공유 자료에서는 과도한 장식보다 요약 카드/절차/근거 블록의 기준 디자인으로 쓰기 좋습니다.

## template_library_02_v1

- Scope: `sales`
- Slides: `12`
- Avg shapes: `35.9`
- Avg text chars: `349`
- Avg images: `10.3`
- Layout signatures: `[('image-led', 12)]`
- Dominant fills: `[('#FFFFFF', 40), ('#F97316', 14), ('#F3F4F6', 12), ('#1E3A8A', 12), ('#DBEAFE', 3)]`
- Dominant font colors: `[('#6B7280', 120), ('#1E3A8A', 67), ('#4B5563', 30), ('#FFFFFF', 21), ('#F97316', 18)]`

### 디자인 해석
- 네이비와 오렌지 accent 조합이 가장 명확하며, 차트와 proof 중심 페이지의 완성도가 높습니다.
- 제목은 크고 짧게, 본문은 좌측 narrative와 우측 chart/diagram으로 나누는 구조가 반복됩니다.
- 시장/유가/리스크처럼 데이터가 있는 보고서에는 이 스타일을 우선 적용하는 것이 좋습니다.

## template_library_03_v1

- Scope: `portfolio`
- Slides: `10`
- Avg shapes: `38.4`
- Avg text chars: `265.4`
- Avg images: `7.6`
- Layout signatures: `[('image-led', 10)]`
- Dominant fills: `[('#FFFFFF', 45), ('#F3F4F6', 29), ('#F9FAFB', 29), ('#EFF6FF', 14), ('#DBEAFE', 7)]`
- Dominant font colors: `[('#1A2332', 57), ('#6B7280', 47), ('#4B5563', 37), ('#9CA3AF', 21), ('#374151', 18)]`

### 디자인 해석
- 스크린샷 또는 실적 이미지를 크게 두고 오른쪽에 결과 bullet을 배치하는 case-study 문법이 강합니다.
- 파란 CTA/pill, 회색 메타 태그, 넓은 여백이 포트폴리오형 신뢰감을 만듭니다.
- 프로젝트 성과, 적용 사례, before/after 정리 슬라이드의 reference로 좋습니다.

## 시스템 반영 규칙

- 목적형 구조만 필요한 경우: `template_library_04_v1`를 사용하되 `layout builder`가 실제 시각 구성을 다시 그립니다.
- 디자인 완성도가 중요한 경우: `usage_policy=production_ready`, `min_quality_score>=4.0` 조건을 우선 적용합니다.
- 데이터/차트 슬라이드: `template_library_02_v1`를 우선 후보로 둡니다.
- 사례/성과 슬라이드: `template_library_03_v1`를 우선 후보로 둡니다.
- 프로세스/서비스 소개: `template_library_01_v1`를 우선 후보로 둡니다.

## 다음 큐레이션 기준

- slide별 실제 사용 가능 상태를 `production_ready`, `curate_before_use`, `structure_only`로 분류합니다.
- `structure_only` 슬라이드는 원본 요소를 보존하지 않고, custom layout builder 또는 overlay safe zone으로만 활용합니다.
- `production_ready` 슬라이드는 원본의 footer, rule, card, icon, chart rhythm을 보존하는 방식으로 치환합니다.
- 같은 purpose라도 최소 2개 이상의 visual variant를 유지하되, default는 품질 점수가 높은 슬라이드로 둡니다.
