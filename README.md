# Kuromi — Upbit 자가개선 자동매매 시스템

![Python](https://img.shields.io/badge/Python-3.11-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Deploy](https://github.com/khaneun/kuromi/actions/workflows/deploy.yml/badge.svg)

> **24시간 가동되는 멀티 Agent 기반 Upbit 자동매매 시스템.**  
> 고정 전략 없이 출발해 LLM Improver가 성과 로그를 분석, 파라미터를 스스로 개선합니다.

---

## 목차

- [아키텍처](#아키텍처)
- [Agent 구성](#agent-구성)
- [전략 플러그인](#전략-플러그인)
- [시그널 계층](#시그널-계층)
- [빠른 시작](#빠른-시작)
- [설정](#설정)
- [백테스트](#백테스트)
- [배포 (AWS EC2)](#배포-aws-ec2)
- [대시보드](#대시보드)
- [Telegram 제어](#telegram-제어)

---

## 아키텍처

```
Market Data (WebSocket + REST fallback)
       │  market.tick / market.trade / market.orderbook
       ▼
  SignalAgent ── 기술 지표 번들 ──────────────────────────────┐
  DerivativeAgent ── 펀딩레이트 / L·S 비율 / 김치프리미엄 ──┤  signal.*
  OnchainAgent ── exchange netflow / NVT / MVRV ────────────┘
       │
       ▼
  StrategyAgent  [momentum | mean_reversion | rsi | bollinger |
  (앙상블 호스트)  macd_cross | stochastic | multi_factor]
       │  trade.intent
       ▼
  RiskAgent ── 일일손실 한도 / 최대 포지션 / 실자본 사이징
       │  trade.approved
       ▼
  ExecutionAgent ── 주문 상태 머신 (submitted→filled/cancelled)
       │  order.*
       ▼
  PortfolioAgent ── Capital 추적 / Upbit 계좌 동기화
  PerformanceAgent ── PnL / win rate / sharpe 집계
  PersistenceAgent ── SQLite 영속화 + crash recovery
  ImproverAgent ── LLM(Claude)이 성과 분석 → 파라미터 개선
  MonitorAgent ── 헬스체크 / 시장 스톨 감지 / 자동 halt
  NotifierAgent ── Telegram 알림 브리지
  Dashboard ── FastAPI + WebSocket 실시간 UI
```

모든 Agent는 **EventBus** 단일 채널로 통신합니다. 이벤트 흐름을 바꾸지 않고 Agent를 추가·제거할 수 있습니다.

---

## Agent 구성

| Agent | 역할 | 주요 이벤트 |
|---|---|---|
| **MarketData** | Upbit WebSocket 시세 수집, REST fallback | `market.tick`, `market.trade`, `market.orderbook` |
| **Signal** | 기술 지표 8종 계산 및 정규화 번들 발행 | `signal.generated` |
| **Derivative** | 펀딩레이트, 미결제약정, L/S 비율, 김치프리미엄 | `signal.derivative` |
| **Onchain** | CryptoQuant: netflow, NVT, MVRV | `signal.onchain` |
| **Strategy** | 플러그인 앙상블, 가중 투표, 진입/청산 결정 | `trade.intent` |
| **Risk** | 포지션 한도 게이트, 실자본 기반 사이징 | `trade.approved`, `trade.rejected` |
| **Execution** | 주문 상태 머신, UUID 폴링, 타임아웃 취소 | `order.*` |
| **Portfolio** | Capital 추적, Upbit 계좌 동기화, equity 기록 | `portfolio.snapshot` |
| **Performance** | PnL / win rate / sharpe-like 집계 | `performance.report` |
| **Persistence** | order·trade·signal DB 영속화, crash recovery | — |
| **Improver** | LLM 성과 분석 → 파라미터 자동 개선 | `improver.params_updated` |
| **Monitor** | 시장 스톨 감지, 자동 halt | `system.halt`, `system.alert` |
| **Notifier** | Telegram 알림 브리지 | — |
| **Dashboard** | FastAPI + WebSocket 실시간 대시보드 | — |

---

## 전략 플러그인

`src/strategies/` 디렉토리에 파일을 추가하면 자동으로 디스커버리됩니다.

| 전략 | 설명 |
|---|---|
| `momentum` | 가격 모멘텀 (rolling return) |
| `mean_reversion` | z-score 기반 평균 회귀 |
| `rsi` | RSI 과매수/과매도 역전 |
| `bollinger` | Bollinger Band %B 이탈 |
| `macd_cross` | MACD 히스토그램 크로스오버 |
| `stochastic` | Stochastic %K/%D 교차 |
| `multi_factor` | 기술·파생·온체인 통합 팩터 (12개) |

---

## 시그널 계층

| 계층 | 지표 | 정규화 |
|---|---|---|
| **기술 지표** | RSI, Bollinger %B, MACD histogram, Stochastic %K, OBV slope, Momentum, Z-score, VWAP | `[-1, 1]` |
| **파생 지표** | 펀딩레이트, L/S 비율, 김치프리미엄, 호가 스프레드 | `[-1, 1]` |
| **온체인** | Exchange netflow, NVT, MVRV | `[-1, 1]` |

---

## 빠른 시작

```bash
# 1. 의존성 설치
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 2. 설정
cp .env.example .env
# .env 파일에 Upbit / Telegram / Anthropic 키 입력

# 3. 실행 (DRY_RUN=true 기본값)
python -m src.main

# 4. 대시보드: http://localhost:8080
```

### Docker로 실행

```bash
docker compose up -d
```

---

## 설정

`.env` 또는 AWS Secrets Manager(`SECRETS_NAME` 키)로 관리합니다.

| 변수 | 설명 | 기본값 |
|---|---|---|
| `ENV` | `dev` / `prod` | `dev` |
| `UPBIT_ACCESS_KEY` | Upbit API 액세스 키 | — |
| `UPBIT_SECRET_KEY` | Upbit API 시크릿 키 | — |
| `TELEGRAM_BOT_TOKEN` | Telegram 봇 토큰 | — |
| `TELEGRAM_ADMIN_CHAT_ID` | 관리자 Chat ID | — |
| `ANTHROPIC_API_KEY` | Claude API 키 (Improver용) | — |
| `CRYPTOQUANT_API_KEY` | CryptoQuant API 키 (온체인, 선택) | — |
| `DRY_RUN` | `true` = 실주문 없음 | `true` |
| `TRADING_TICKERS` | 대상 티커 (콤마 구분) | `KRW-BTC,KRW-ETH` |
| `MAX_CONCURRENT_POSITIONS` | 최대 동시 포지션 수 | `3` |
| `PER_TRADE_RISK_PCT` | 거래당 자본 비율 | `0.01` |
| `DAILY_LOSS_LIMIT_PCT` | 일일 손실 한도 | `0.03` |
| `IMPROVER_CADENCE_SEC` | Improver 실행 주기(초) | `3600` |
| `INITIAL_CAPITAL_KRW` | 초기 자본 (0 = Upbit 계좌 동기화) | `0` |

---

## 백테스트

```bash
# 단일 티커
python -m src.backtest.runner --ticker KRW-BTC --minutes 5 --count 200

# 독립 멀티 티커 (티커별 별도 자본)
python -m src.backtest.multi --tickers KRW-BTC,KRW-ETH,KRW-SOL

# 통합 멀티 티커 (공유 자본, 포트폴리오 레벨)
python -m src.backtest.multi --tickers KRW-BTC,KRW-ETH,KRW-SOL --unified

# 그리드 서치 → Improver 시드 생성
python -m src.backtest.grid --ticker KRW-BTC --sweep-weights --out data/improver_seed.json
```

---

## 배포 (AWS EC2)

### 초기 인프라 생성 (1회)

```bash
# EC2 + ECR + IAM + Elastic IP 자동 생성
KEY_PAIR_NAME=kitty-key bash infra/create-ec2.sh

# GitHub Secrets 일괄 등록
REPO=khaneun/kuromi EC2_HOST=<IP> KEY_PATH=~/kitty-key.pem \
  bash infra/setup-github-secrets.sh

# AWS Secrets Manager에 앱 시크릿 등록
aws secretsmanager create-secret --name kuromi/prod \
  --secret-string '{"UPBIT_ACCESS_KEY":"...","UPBIT_SECRET_KEY":"...",...}'
```

### 이후 배포 (자동)

```bash
git push origin main
# → GitHub Actions: lint → build → ECR push → SSH deploy → healthcheck
```

---

## 대시보드

`http://<EC2_IP>:8080` 접속

| 섹션 | 기능 |
|---|---|
| Portfolio KPI | Equity, PnL, 수익률, 포지션 수 |
| Positions | 티커별 진입가·현재가·평가손익 |
| Equity Curve | Chart.js 실시간 차트 |
| Agents | 14개 Agent 상태 모니터링 |
| Control Panel | Halt / Resume / 긴급청산 / Dry-run 전환 / 파라미터 조정 / Improver 프롬프트 |
| Orders / Trades | 최근 주문·체결 이력 |
| Event Log | WebSocket 실시간 이벤트 스트림 |

---

## Telegram 제어

| 명령 | 설명 |
|---|---|
| `/status` | 자본·포지션 스냅샷 |
| `/halt` | 거래 즉시 중단 |
| `/resume` | 거래 재개 |
| `/params` | 현재 전략 파라미터 조회 |
| `/orders` | 최근 주문 10건 |
| `/trades` | 최근 체결 10건 |

---

## 프로젝트 구조

```
kuromi/
├── src/
│   ├── agents/          # 14개 전문가 Agent
│   ├── core/            # EventBus, Orchestrator, Capital, EquityTracker
│   ├── strategies/      # 7개 전략 플러그인 (자동 디스커버리)
│   ├── indicators/      # 기술·파생·온체인 지표 순수 함수
│   ├── exchange/        # Upbit REST/WS, Binance, CryptoQuant 클라이언트
│   ├── backtest/        # 단일·멀티·통합 백테스터, 그리드 서치
│   ├── dashboard/       # FastAPI + WebSocket 대시보드
│   ├── telegram/        # Telegram 봇
│   └── storage/         # SQLAlchemy 모델, DB 초기화
├── config/              # Pydantic Settings (dev/.env, prod/Secrets Manager)
├── infra/               # EC2 생성, IAM, GitHub Secrets 스크립트
├── .github/workflows/   # CI/CD 파이프라인
├── Dockerfile           # Multi-stage 빌드
└── docker-compose*.yml  # dev / prod
```
