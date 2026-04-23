# Production Template Guide

이 문서는 `reference_catalog.json`의 품질 메타데이터를 기준으로 실제 deck 제작에 우선 사용할 슬라이드를 정리합니다.

- Production-ready slides: `32`
- Known gaps: `toc, timeline, market`

## 목적별 추천 후보

### cover

- Coverage: `production_ready`
- `template_library_01_v1.channel_cover_v1` | variant=`cover/narrative-sales` | score=`4.5` | policy=`production_ready`
- `template_library_02_v1.finance_cover_v1` | variant=`cover/finance-sales` | score=`4.4` | policy=`production_ready`
- `template_library_03_v1.portfolio_cover_v1` | variant=`cover/portfolio` | score=`4.1` | policy=`production_ready`

### toc

- Coverage: `gap`
- Production-ready 후보가 없어 fallback 후보만 있습니다.
- `template_library_04_v1.toc_visual_tiles_v1` | variant=`toc/visual-tiles` | score=`2.7` | policy=`curate_before_use`
- `template_library_04_v1.toc_simple_index_v1` | variant=`toc/simple-index` | score=`2.4` | policy=`structure_only`

### summary

- Coverage: `production_ready`
- `template_library_02_v1.service_components_v1` | variant=`summary/service-components` | score=`4.4` | policy=`production_ready`
- `template_library_01_v1.service_intro_cards_v1` | variant=`summary/service-intro-cards` | score=`4.3` | policy=`production_ready`

### issue

- Coverage: `production_ready`
- `template_library_02_v1.problem_story_v1` | variant=`issue/pain-story` | score=`4.6` | policy=`production_ready`

### analysis

- Coverage: `production_ready`
- `template_library_03_v1.project_case_v1` | variant=`analysis/project-case-metric-1` | score=`4.4` | policy=`production_ready`
- `template_library_02_v1.before_after_compare_v1` | variant=`analysis/before-after` | score=`4.4` | policy=`production_ready`
- `template_library_02_v1.core_technology_v1` | variant=`analysis/core-technology` | score=`4.4` | policy=`production_ready`
- `template_library_02_v1.vertical_use_cases_v1` | variant=`analysis/vertical-use-cases` | score=`4.4` | policy=`production_ready`

### chart

- Coverage: `production_ready`
- `template_library_02_v1.proof_metrics_v1` | variant=`chart/proof-metrics` | score=`4.4` | policy=`production_ready`
- `template_library_02_v1.signal_speed_v1` | variant=`chart/single-metric-story` | score=`4.4` | policy=`production_ready`

### process

- Coverage: `production_ready`
- `template_library_02_v1.poc_process_v1` | variant=`process/poc-steps` | score=`4.4` | policy=`production_ready`
- `template_library_01_v1.data_method_v1` | variant=`process/method-diagram` | score=`4.2` | policy=`production_ready`
- `template_library_01_v1.service_model_v1` | variant=`process/service-operating-model` | score=`4.2` | policy=`production_ready`
- `template_library_01_v1.pilot_program_v1` | variant=`process/pilot-program` | score=`4.2` | policy=`production_ready`

### strategy

- Coverage: `production_ready`
- `template_library_02_v1.alpha_signal_timeline_v1` | variant=`strategy/signal-timeline` | score=`4.4` | policy=`production_ready`
- `template_library_01_v1.sales_strategy_steps_v1` | variant=`strategy/sales-step-story` | score=`4.2` | policy=`production_ready`
- `template_library_01_v1.expansion_story_v1` | variant=`strategy/expansion-story` | score=`4.2` | policy=`production_ready`

### timeline

- Coverage: `gap`
- Production-ready 후보가 없어 fallback 후보만 있습니다.
- `template_library_04_v1.company_history_v1` | variant=`timeline/company-history` | score=`2.4` | policy=`structure_only`
- `template_library_04_v1.roadmap_timeline_v1` | variant=`timeline/horizontal-roadmap` | score=`2.4` | policy=`structure_only`

### market

- Coverage: `gap`
- Production-ready 후보가 없어 fallback 후보만 있습니다.
- `template_library_04_v1.market_tam_sam_som_v1` | variant=`market/tam-sam-som` | score=`2.4` | policy=`structure_only`
- `template_library_04_v1.market_stat_cards_v1` | variant=`market/stat-cards` | score=`2.4` | policy=`structure_only`

### team

- Coverage: `production_ready`
- `template_library_03_v1.profile_resume_v1` | variant=`team/resume-card` | score=`4.1` | policy=`production_ready`

### closing

- Coverage: `production_ready`
- `template_library_02_v1.finance_closing_v1` | variant=`closing/finance-cta` | score=`4.6` | policy=`production_ready`
- `template_library_01_v1.partnership_goal_v1` | variant=`closing/partnership-goal` | score=`4.2` | policy=`production_ready`
- `template_library_03_v1.portfolio_closing_v1` | variant=`closing/portfolio-thank-you` | score=`4.2` | policy=`production_ready`
- `template_library_01_v1.discussion_closing_v1` | variant=`closing/discussion-next-step` | score=`4.2` | policy=`production_ready`

## 사용 권장

- 데이터/리스크/시장 논리는 `data_story` 세트를 우선 사용합니다.
- 서비스 소개/프로세스/영업 제안은 `service_story` 세트를 우선 사용합니다.
- 사례/성과/스크린샷 중심 내용은 `case_study` 세트를 우선 사용합니다.
- `toc`, `timeline`, `market`은 아직 production-ready gap이므로 custom layout builder 또는 추가 reference 보강이 필요합니다.
