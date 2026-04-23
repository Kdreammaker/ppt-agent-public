# PPTX Design System

## 목표
- 원본 reference PPTX는 보존하고, 실제 제작은 `assets/slides/templates/decks/*.pptx`와 JSON spec으로 통제한다.
- slide purpose만 맞추는 수준을 넘어서, 원본의 시각 언어를 분석한 뒤 디자인 품질 점수와 사용 정책을 함께 적용한다.
- 한글 보고서에 맞는 줄바꿈, 여백, 헤더/푸터, 페이지 번호 규칙을 시스템 기본값으로 둔다.

## 디자인 기준
- 구조와 디자인을 분리한다. `template_library_04_v1`는 구조 참조용, Template System/portfolio 계열은 디자인 참조용으로 우선 사용한다.
- 색상은 기본적으로 2색, 최대 3색만 사용한다. 메인 색 1개, 보조 색 1개, 강조 색 1개까지만 허용한다.
- 한 슬라이드의 메시지는 `제목 -> 핵심 문장 -> 근거/도표 -> 액션` 순서로 읽히게 한다.
- 시각적 완성도가 중요한 슬라이드는 `usage_policy=production_ready`, `quality_score>=4.0` 후보를 우선 선택한다.
- 원본의 좋은 특징은 보존하고, placeholder/저작권/불필요한 장식은 제거한다.

## Reference별 활용 방향
- `template_library_04_v1`: 구조, 목적 분류, placeholder geometry 참조용입니다. 그대로 디자인 기준으로 쓰면 빈약하므로 custom layout builder로 다시 그리는 것이 안전합니다.
- `template_library_01_v1`: 흰 배경, 네이비 룰, 연한 카드, 아이콘, 작은 footer가 반복되는 B2B 공유/세일즈형 기준입니다.
- `template_library_02_v1`: 네이비와 오렌지 accent, 차트, proof, 데이터 스토리텔링에 가장 강한 기준입니다.
- `template_library_03_v1`: 스크린샷, 성과 bullet, pill tag, 프로젝트 사례 페이지의 기준입니다.

## Typography
- 기본 한글 폰트는 Windows 호환성을 위해 `Malgun Gothic`을 사용한다. 프로젝트별로 `Pretendard`, `Noto Sans CJK KR`, `SUIT` 등으로 교체 가능하다.
- 제목은 조사나 짧은 수식어가 다음 줄에 외톨이로 남지 않게 명사구 단위로 끊는다.
- `API`, `WebSocket`, `UI/UX`, `PoC`, `ROI`, `KPI` 같은 토큰은 줄 중간에서 쪼개지지 않게 보호한다.
- 본문은 긴 문장보다 1줄 핵심 문장과 짧은 근거 bullet을 선호한다.

## Font Scale
- `cover_title`: 30-36pt
- `hero_title`: 22-26pt
- `section_header`: 11-13pt
- `card_title`: 15-18pt
- `body_strong`: 12.5-14pt
- `body`: 10.8-12.5pt
- `caption`: 8.5-10pt
- `footer`: 9.5-11.5pt

## Color Rules
- `primary`: 제목, 주요 텍스트, 큰 배경 패널
- `accent_1`: 중요한 단계, 버튼, 숫자, 강조 라벨
- `accent_2`: 보조 강조 또는 상태 구분
- `light/panel`: 카드 배경
- `border`: 카드 경계와 얇은 separator
- 데이터/차트 슬라이드는 원본 Template System 투자 자료처럼 `navy + orange` 조합을 우선 고려한다.

## Header / Footer / Page
- 페이지 번호는 기본적으로 우하단 하나만 사용한다.
- 좌상단 숫자는 페이지 번호가 아니라 section number로만 사용한다.
- footer가 진한 바 형태일 때는 페이지 번호를 그 안에 넣고, 별도 위치에 중복 배치하지 않는다.
- section header, footer, page number의 금지 영역은 blueprint에 포함한다.

## Layout Rules
- 표지: 큰 색면 또는 강한 이미지 하나를 중심으로 하고, 키워드 chip은 2-3개까지만 둔다.
- 목차: 4개 이하의 section이면 visual tile, 5개 이상이면 simple index를 쓴다.
- 요약: 두 문단 이상 설명하지 말고, 카드/패널에 핵심 claim을 나눈다.
- 이슈: 2x2 카드나 pain-story 구조를 우선 사용한다.
- 전략/프로세스: 3-4단계 flow를 기본으로 하고, 마지막에 결론 strip을 둔다.
- 차트: 범례보다 직접 라벨을 우선하고, 카테고리는 5개 이하로 제한한다.
- 사례: 큰 screenshot 또는 proof 이미지를 왼쪽에 두고 오른쪽에 outcome bullet을 둔다.

## Template Selection
- `slide_selector`는 `purpose`, `scope`, `preferred_variant`, `required_tags`를 기본으로 사용한다.
- 디자인 품질이 중요한 deck은 selector에 `min_quality_score` 또는 `usage_policies`를 추가한다.
- 자동 선택은 다음 순서로 판단한다: purpose 일치, scope 일치, preferred/fallback variant, design tier, quality score, default rank.
- 원본 요소를 그대로 쓰는 `blueprint_overlay`는 production-ready slide에만 제한적으로 사용한다.
- `structure_only` slide는 custom layout builder로 다시 그리는 것을 기본으로 한다.
- 이미지 관계가 많은 production-ready reference를 스타일 기준으로만 활용할 때는 `source_mode: blank`를 사용한다. 이렇게 하면 원본 slide 선택/품질 메타데이터는 유지하되 PPTX media 관계 손상 위험 없이 16:9 빈 캔버스 위에 다시 그린다.

## Elevated Layouts
- `brand_cover`: 큰 네이비 색면, 얇은 accent rule, 중앙 타이틀을 사용한다.
- `summary_panels`: 좌측 메타 카드와 우측 핵심 패널을 나눠 내부 보고의 요약성을 높인다.
- `issue_grid`: 2x2 이슈/리스크 카드를 사용해 판단 포인트를 빠르게 비교하게 한다.
- `insight_split`: 좌측에는 핵심 판단, 우측에는 의사결정 포인트를 카드로 정리한다.
- `proof_metrics`: KPI 카드 3개, 검증 bullet, 간단한 chart를 조합한다.
- `case_study`: screenshot mock과 outcome bullet을 나눠 포트폴리오형 proof slide를 만든다.
- `step_flow`: 3-4단계 실행 흐름과 결론 strip을 함께 제공한다.
- `message_rows`: 핵심 메시지를 행 단위로 나눠 회의 공유/의사결정 맥락에 맞춘다.
- `action_cards`: owner, due, output을 카드화해 후속 실행 관리가 바로 가능하게 한다.

## Component-Based Composition
- slide 전체를 가져오는 방식이 무겁거나 위험할 때는 `component_canvas`와 `source_mode: blank`를 쓴다.
- 반복되는 디자인 유닛은 `title_block`, `kpi_card`, `insight_card`, `toc_tiles`, `process_flow`, `timeline`, `browser_mock`, `callout_bar`로 조립한다.
- 컴포넌트는 원본 reference의 디자인 문법을 작게 분해한 단위다. 따라서 “좋은 slide를 통째로 복사”하는 대신 “좋은 slide의 문법을 재사용”할 수 있다.
- 자세한 컴포넌트 규칙은 [COMPONENT_SYSTEM.md](</C:/Users/kimjo/Downloads/ppt-test/docs/COMPONENT_SYSTEM.md>)를 따른다.

## Quality Checklist
- 제목이 2줄을 넘으면 의도된 줄바꿈인지 확인한다.
- 한글 단어가 글자 단위로 잘리지 않는지 확인한다.
- 카드별 정보량이 비슷한지 확인한다.
- footer와 page number가 겹치거나 중복되지 않는지 확인한다.
- 사용 색상이 3개를 넘지 않는지 확인한다.
- 한 슬라이드에 핵심 메시지가 하나인지 확인한다.
- `pptx -> pdf -> preview image` 렌더링을 반드시 거친다.

## 산출물
- 디자인 분석 결과: [REFERENCE_DESIGN_AUDIT.md](</C:/Users/kimjo/Downloads/ppt-test/docs/REFERENCE_DESIGN_AUDIT.md>)
- 스타일 프로필: [reference_style_profiles.json](</C:/Users/kimjo/Downloads/ppt-test/config/reference_style_profiles.json>)
- 품질 override: [template_quality_overrides.json](</C:/Users/kimjo/Downloads/ppt-test/config/template_quality_overrides.json>)
- 통합 catalog: [reference_catalog.json](</C:/Users/kimjo/Downloads/ppt-test/config/reference_catalog.json>)

## 현재 구현 상태
- 주요 일반 레이아웃은 `system/layouts/` 모듈로 분리되어 `LayoutRegistry`에서 등록한다.
- 신규 deck은 가능한 `component_canvas`, `component_preset`, `slide_selector`, `source_mode: blank` 조합을 우선 사용한다.
- 아직 `cover_panel`과 `blueprint_overlay`는 추가 모듈화 및 config/placeholder 승격이 남아 있다.
- 최신 대표 산출물 품질 검사 기준: `jb_meeting_component_preset_system.pptx`, `jb_meeting_design_elevated_system.pptx`, `jb_meeting_component_modular_system.pptx`, `jb_meeting_internal_share_deck_system.pptx` 모두 `errors=0`, `warnings=0`.
