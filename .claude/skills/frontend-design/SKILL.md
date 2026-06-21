---
name: frontend-design
description: >
  포켓주식 앱의 UI 컴포넌트 작성 가이드. HTML/CSS/JS로 모바일 퍼스트 카드형 UI를 만들 때 반드시 사용.
  보유종목, 뉴스카드, 상세페이지, 배지, 차트 섹션 등 어떤 UI 작업이든 이 스킬을 먼저 읽고 시작하세요.
  "카드 만들어줘", "섹션 추가", "배지 색상", "레이아웃 바꿔줘" 같은 프론트엔드 작업에 항상 적용.
---

# 포켓주식 프론트엔드 디자인 시스템

## 핵심 원칙
- **모바일 퍼스트**: max-width 430px, 모든 터치 타깃 최소 44px
- **프레임워크 없음**: 순수 HTML/CSS/JS, Tabler Icons (`ti ti-*`) 아이콘
- **일관성 우선**: 아래 토큰과 컴포넌트를 그대로 사용. 임의로 색상·폰트 크기 만들지 말 것

---

## 컬러 토큰

| 용도 | 값 |
|---|---|
| Primary (보라) | `#5B5BD6` |
| 배경 (앱) | `#F5F5F7` |
| 카드 배경 | `#fff` |
| 텍스트 기본 | `#1A1A2E` |
| 텍스트 보조 | `#8E8E9A` |
| 구분선 | `#E5E5EA` |
| 상승 (빨강) | `#E24B4A` |
| 하락 (파랑) | `#185FA5` |
| 수익 배경 | `#EAF3DE` / `#27500A` |
| 손실 배경 | `#FCEBEB` / `#791F1F` |
| 경고 배경 | `#FAEEDA` / `#633806` |
| 중립 배경 | `#EEEDFE` / `#3C3489` |

**한국 주식 컬러 규칙**: 상승=빨강(`.up`), 하락=파랑(`.down`) — 서양 반대임에 주의.

---

## 레이아웃 구조

```
body (max-width: 430px, background: #F5F5F7)
 └─ .header (sticky top, white)
 └─ [페이지 콘텐츠]
      └─ .section (margin: 0 16px 12px)
           └─ .sec-title (섹션 헤더, 아이콘 포함)
           └─ .card (white, border-radius: 16px, border: 0.5px solid #E5E5EA)
 └─ .bottom-nav (fixed bottom)
```

---

## 핵심 컴포넌트

### 카드
```html
<div class="card">내용</div>
<!-- 클릭 가능한 카드 -->
<div class="card clickable" onclick="...">내용</div>
```

### 섹션 타이틀
```html
<div class="sec-title">
  <i class="ti ti-chart-candle" style="font-size:15px;color:#5B5BD6;"></i>섹션명
</div>
```

### 배지
```html
<span class="badge badge-ok">중립</span>      <!-- 보라 배경 -->
<span class="badge badge-buy">매수</span>     <!-- 초록 배경 -->
<span class="badge badge-sell">매도</span>    <!-- 빨강 배경 -->
<span class="badge badge-warn">주의</span>    <!-- 주황 배경 -->
<span class="badge badge-neutral">보통</span> <!-- 회색 배경 -->
```

### 상승/하락 텍스트
```html
<span class="up">▲ 1,500원 (2.3%)</span>   <!-- 빨강 -->
<span class="down">▼ 500원 (0.8%)</span>    <!-- 파랑 -->
```

### 버튼
```html
<button class="btn-primary" style="width:100%;">확인</button>
<button class="btn-secondary">취소</button>
<button class="btn-danger" style="width:100%;">삭제</button>
```

### 입력 필드
```html
<label class="input-label">라벨</label>
<input class="input-field" style="width:100%;box-sizing:border-box;" placeholder="...">
```

### 탭
```html
<button class="tab active">활성</button>
<button class="tab inactive">비활성</button>
```

### 히어로 카드 (흰색, 상세 페이지용)
```html
<div class="section" style="margin-top:0;">
  <div class="card" style="padding:16px;">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;">
      <div>
        <div style="font-size:18px;font-weight:700;color:#1A1A2E;">종목명</div>
        <div style="font-size:11px;color:#8E8E9A;margin-top:2px;">005930</div>
      </div>
      <span class="badge badge-buy">수익 +18.79%</span>
    </div>
    <div style="font-size:28px;font-weight:800;color:#1A1A2E;margin-top:10px;">354,000원</div>
    <div style="font-size:13px;color:#E24B4A;margin-top:3px;">▲ 8,500원 (2.34%)</div>
    <!-- 구분선 -->
    <div style="border-top:1px solid #F0F0F5;margin:14px 0 10px;"></div>
    <!-- 보유현황 그리드 -->
    <div class="detail-grid">
      <div class="detail-item" style="background:#F8F8FA;">...</div>
    </div>
    <!-- P&L 바 -->
    <div style="height:4px;background:#F0F0F5;border-radius:2px;margin-top:10px;overflow:hidden;">
      <div style="height:4px;width:60%;background:#E24B4A;border-radius:2px;"></div>
    </div>
  </div>
</div>
```

### 정보 행 (지표/수급)
```html
<div class="ind-row">
  <span class="ind-label">RSI (14일)</span>
  <div class="ind-right">
    <span class="ind-val">38</span>
    <span class="badge badge-buy" style="font-size:10px;">과매도</span>
  </div>
</div>
```

### 지지선 행
```html
<div class="sup-row">
  <span class="sup-label">20일선</span>
  <div class="sup-right">
    <span class="sup-price">129,300원</span>
    <span class="sup-dist up">+1.2%</span>
    <span style="font-size:10px;padding:2px 7px;border-radius:5px;background:#EAF3DE;color:#27500A;">현재위</span>
  </div>
</div>
```

### 시스템 판단 (분석 요약 카드)
```html
<div class="section">
  <div class="card" style="background:#FFFBF0;border:1px solid #F5E6B2;">
    <div style="font-size:13px;font-weight:700;color:#8B6914;margin-bottom:8px;display:flex;align-items:center;gap:6px;">
      <span style="font-size:16px;">☀️</span> 시스템 판단
    </div>
    <div style="font-size:13px;color:#3C3C43;line-height:1.7;">분석 텍스트</div>
  </div>
</div>
```

### 경고 박스
```html
<div class="warn-box">
  <i class="ti ti-alert-circle" style="font-size:14px;flex-shrink:0;"></i>
  경고 메시지
</div>
```

### 수급 바
```html
<div class="supply-row">
  <span class="supply-who">외국인</span>
  <div class="supply-bar-bg">
    <div class="supply-bar-fill bar-buy" style="width:60%;"></div>
  </div>
  <span class="supply-val up">+12,345주</span>
</div>
```

### 스톡 아이콘 (종목 심볼)
```html
<div class="stock-icon icon-purple">삼성</div>  <!-- 보라 -->
<div class="stock-icon icon-blue">SK</div>       <!-- 파랑 -->
<div class="stock-icon icon-red">카카오</div>    <!-- 빨강 -->
```

---

## 타이포그래피 스케일

| 용도 | 크기 | 굵기 |
|---|---|---|
| 대형 가격 | 28px | 800 |
| 종목명/페이지 제목 | 18px | 700 |
| 섹션 제목 | 15px | 600 |
| 본문 | 13px | 400 |
| 보조 정보 | 11px | 400 |
| 배지/라벨 | 10px | 500 |

---

## 간격 규칙

- 페이지 좌우 패딩: `16px` (`.section`의 margin)
- 카드 내부 패딩: `14px 16px`
- 카드 간격: `margin-bottom: 8px`
- 섹션 간격: `margin-bottom: 12px`
- 카드 border-radius: `16px`
- 작은 요소 border-radius: `10px`
- 버튼 border-radius: `12px`
- 배지 border-radius: `6px`

---

## Tabler Icons 사용법

```html
<!-- 항상 font-size와 color 인라인으로 지정 -->
<i class="ti ti-아이콘명" style="font-size:15px;color:#5B5BD6;"></i>
```

자주 쓰는 아이콘:
- `ti-chart-candle` — 차트
- `ti-activity` — 기술지표
- `ti-users` — 수급
- `ti-target` — 목표가
- `ti-news` — 뉴스
- `ti-file-text` — 공시
- `ti-barrier-block` — 지지선
- `ti-alert-triangle` — 경고
- `ti-alert-circle` — 주의
- `ti-trash` — 삭제
- `ti-plus` — 추가
- `ti-microscope` — 분석

---

## 자주 쓰는 패턴

### 숫자 포맷 함수
```javascript
// app.js에 fmtNum 함수 존재
fmtNum(354000) // → "354,000"
```

### 조건부 색상
```javascript
const cls = val >= 0 ? 'up' : 'down';
const badgeCls = val >= 0 ? 'badge-buy' : 'badge-sell';
```

### 섹션 조건부 렌더링
```javascript
// 데이터 없으면 섹션 전체 숨김
${data ? `<div class="section">...</div>` : ''}
```

### P&L 퍼센트 바
```javascript
const barW = Math.min(Math.abs(pnlPct) * 2, 100);
const barColor = pnlPct >= 0 ? '#E24B4A' : '#185FA5';
```

---

## 주의사항

- `badges` 배열에서 `.includes()` 전에 반드시 `typeof b === 'string'` 체크
- numpy/pandas 값은 FastAPI 응답 전에 `_to_python()` 변환 필수
- JS 수정 시 `index.html`의 `app.js?v=YYYYMMDDX` 버전 올려서 캐시 무효화
