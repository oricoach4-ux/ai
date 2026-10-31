---
name: pla
description: Playwright MCP 도구(mcp__playwright__*)로 웹페이지를 열고 상호작용하고, DOM 구조/네트워크 요청/콘솔 로그를 확인하는 모든 작업에 사용한다. 사용자가 "플라"라고 부르거나, 웹사이트를 열어서 확인/테스트/디버깅/자동 입력/크롤링/스크린샷/구조 분석해야 하는 모든 상황에서 반드시 이 스킬을 먼저 참고한다. 로그인 폼 테스트, 특정 페이지가 제대로 뜨는지 확인, API 호출 캐치, 콘솔 에러 찾기, 반복적인 브라우저 작업 자동화 같은 요청에도 적용된다.
---

Playwright MCP 도구를 쓸 때 흔히 겪는 실수를 피하고 효율적으로 작업하기 위한 가이드입니다. 이 도구들은 셀렉터를 직접 추측해서 쓰는 방식이 아니라, 먼저 페이지를 "본 뒤" 그 결과에 있는 참조(ref)로 상호작용하는 방식이라는 점이 핵심입니다.

## 기본 흐름

1. `browser_navigate`로 이동한다.
2. 클릭/입력 등 뭔가 조작하기 **전에 항상 `browser_snapshot`을 먼저 찍는다.** 스냅샷이 페이지의 접근성 트리(역할, 텍스트, ref)를 보여주고, `browser_click`/`browser_type`/`browser_select_option` 같은 도구는 그 ref를 입력으로 받는다. CSS 셀렉터나 좌표를 추측해서 쓰지 않는다 — 스냅샷 없이 조작하면 틀린 요소를 건드리기 쉽다.
3. 조작 후 페이지가 바뀌면 다시 `browser_snapshot`을 찍어 결과를 확인한다. 변화가 클 때만 `browser_take_screenshot`으로 시각적으로 재확인한다(스냅샷이 더 가볍고 구조화되어 있어 기본은 스냅샷, 레이아웃/디자인을 눈으로 봐야 할 때만 스크린샷).

## 동적 콘텐츠

- 로딩, 애니메이션, AJAX 응답을 기다릴 때 임의의 sleep 대신 `browser_wait_for`를 쓴다(특정 텍스트가 나타나거나 사라질 때까지 기다리는 방식). 고정 시간 대기는 느린 네트워크에서 실패하고 빠른 경우엔 시간을 낭비한다.
- 네비게이션이 실패하거나(`net::ERR_ABORTED` 등) 응답이 없으면 같은 탭에 이전 페이지가 남아있을 수 있으니, 의심되면 `browser_tabs`로 현재 열린 탭/URL을 확인하고 필요하면 재시도한다. (실제로 여러 사이트를 연달아 조사할 때 이전 탭이 남아 혼선을 준 적이 있다.)

## 폼과 입력

- 필드가 여러 개면 `browser_fill_form`으로 한 번에 채운다. 단일 필드는 `browser_click` 후 `browser_type`.
- **React/Vue 등 controlled input은 `browser_evaluate`로 DOM의 `value`만 강제로 설정해도 내부 상태(state)가 갱신되지 않아 제출 시 빈 값으로 나갈 수 있다.** 실제 타이핑처럼 동작해야 하는 입력은 `browser_type`을 쓰고, `browser_evaluate`로 값 주입은 피한다.
- 드롭다운은 `browser_select_option`, 드래그 앤 드롭은 `browser_drag`/`browser_drop`, 파일 첨부는 `browser_file_upload`.
- `alert`/`confirm`/`prompt` 같은 네이티브 다이얼로그가 뜨면 `browser_handle_dialog`로 처리한다 — 처리하지 않으면 이후 동작이 멈춘다.

## 관찰/디버깅

- 페이지에서 호출하는 API나 리소스를 보려면 `browser_network_requests`(전체 목록), 특정 요청의 상세(헤더/본문)는 `browser_network_request`.
- JS 에러나 경고는 `browser_console_messages`로 확인한다. 자체 서비스 로직 에러인지, 광고/분석 서드파티 스크립트 에러인지 구분해서 보고한다.
- `browser_evaluate`는 커스텀 JS를 실행해 값을 읽거나 가볍게 조작할 때 쓴다. `browser_run_code_unsafe`는 신뢰할 수 없는 사이트에서는 피하고, 꼭 필요할 때만 범위를 좁혀 사용한다.

## 탭과 세션 관리

- 여러 탭을 다룰 땐 `browser_tabs`로 목록 확인/전환/새 탭 생성을 한다.
- 뒤로 가기는 `browser_navigate_back`, 키 입력(Enter, Esc 등)은 `browser_press_key`, 반응형 확인은 `browser_resize`, 다크모드/프린트 미리보기는 `browser_emulate_media`.
- 작업이 끝나면 `browser_close`로 탭을 정리한다. 여러 사이트를 연달아 조사할 때 탭을 안 닫으면 다음 작업에서 엉뚱한 탭이 활성 상태로 남아 혼선을 줄 수 있다.

## 외부 사이트 조사 시 예의

- 실제 운영 중인 외부 사이트(남의 서비스)를 조사할 때는 꼭 필요한 페이지 몇 개만 방문한다. 같은 요청을 반복하거나 대량으로 크롤링하지 않는다 — 사람이 몇 페이지 둘러보는 정도의 트래픽으로 제한한다.
- 로그인/캡차/결제처럼 민감한 흐름은 실제로 값을 제출하기 전에 스냅샷으로 어떤 동작인지 반드시 확인한다.
