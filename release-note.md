# Release Notes

---

## v0.12.0 — 프로덕션 안정화 (2026-04-14)

### 버그 수정

- **`Capital.sync_from_upbit()` 데드락 수정** (`src/core/capital.py`)  
  `threading.Lock`을 보유한 채로 동일 락을 획득하는 `self.total_equity()`를 내부에서 호출해 재진입 데드락 발생. 기동 60초 후 첫 Upbit 동기화 시 메인 스레드와 uvicorn 스레드 모두 무한 대기 → 전체 시스템 동결. 락 재진입 없이 인라인으로 동등 계산하도록 수정.

- **`PortfolioAgent.setup()` 기동 블로킹 수정** (`src/agents/portfolio.py`)  
  `live=True` 모드에서 `setup()`이 Upbit API를 동기 호출해 httpx 연결이 CLOSE_WAIT 상태가 되면 `asyncio.wait_for`로도 취소 불가 → Orchestrator.start() 전체 블로킹. `setup()`을 no-op으로 변경하고 초기 동기화를 `run()` 루프로 이전.

- **uvicorn 스레드 분리** (`src/main.py`)  
  uvicorn을 메인 asyncio 루프의 `create_task`로 실행 시 에이전트 이벤트 루프 포화로 HTTP 응답 불가. `threading.Thread` + `asyncio.run(dashboard.serve())`로 독립 이벤트 루프에서 실행.

- **uvicorn 비-메인 스레드 signal handler 제거** (`src/main.py`)  
  uvicorn 0.44.0은 `Config.__init__`에 `install_signal_handlers` 파라미터 미지원. `Server` 인스턴스 메서드를 `lambda: None`으로 패치해 비-메인 스레드에서의 signal handler 설치 시도 방지.

- **uvicorn cross-loop WebSocket 브로드캐스트** (`src/dashboard/app.py`)  
  uvicorn이 별도 스레드에서 실행될 때 메인 루프에서 직접 `await ws.send_text()` 호출 시 루프 불일치 오류. 시작 시 uvicorn 루프를 캡처(`_uvicorn_loop`)해 `asyncio.run_coroutine_threadsafe()`로 위임.

### 인프라

- **EC2 IMDSv2 hop limit 조정**: Docker 브리지가 네트워크 홉 1개를 추가해 컨테이너 내부에서 IMDSv2 메타데이터 접근 불가. `HttpPutResponseHopLimit=2`로 수정.
- **Secrets Manager 연동 정상화**: 컨테이너 실행 시 `-e ENV=prod -e SECRETS_NAME=kuromi/prod` 환경변수 필수. Dockerfile에 기본 `ENV=prod` 포함.
- **`dry_run` 런타임 전환**: `/api/config PUT` 엔드포인트로 재기동 없이 실매매 모드 전환 가능.

### 개선

- 대시보드 헤더에 Kuromi 캐릭터 이미지 추가 (base64 인라인 임베딩, 28px 원형)

---

## v0.11.0 — Docker + CI/CD (2026-04-13)

### 추가
- **Multi-stage Dockerfile**: deps 레이어 분리로 캐시 최적화, ~150MB 이미지
- **docker-compose.yml**: 로컬 개발용 (소스 볼륨 마운트)
- **docker-compose.prod.yml**: EC2 프로덕션용 (ECR 이미지, 로그 로테이션)
- **infra/create-ec2.sh**: AWS CLI one-shot — EC2(t3.small), ECR, IAM 역할(Secrets Manager + ECR pull), SG, Elastic IP 자동 생성
- **infra/ec2-userdata-docker.sh**: EC2 기동 시 Docker 자동 설치
- **infra/iam-ec2-policy.json**: 최소 권한 IAM 정책
- **infra/setup-github-secrets.sh**: `gh` CLI로 GitHub Secrets 일괄 등록
- **.github/workflows/deploy.yml**: `main` push → lint → build → ECR push → SSH deploy → health check → 자동 rollback
- **.github/workflows/pr-check.yml**: PR lint 자동 검사

---

## v0.10.0 — 운영 대시보드 (2026-04-13)

### 추가
- **FastAPI 대시보드** (`http://localhost:8080`)
  - Portfolio KPI, Positions 테이블, Agents 상태
  - Chart.js 기반 Equity Curve (실시간 WebSocket)
  - Orders / Trades 이력 테이블
  - Event Log (WebSocket 스트림)
- **제어 API 6종**: Halt, Resume, 긴급 청산, Dry-run 런타임 전환, 파라미터 직접 적용, Improver 프롬프트 핫 리로드
- **EquityTracker**: 링버퍼 기반 equity 히스토리 수집 (최대 72시간)
- **Orchestrator.agent_statuses()**: Agent 상태·예외 조회

---

## v0.9.0 — 다층 시그널 (2026-04-13)

### 추가
- **기술 지표 모듈** (`src/indicators/technical.py`): RSI, Bollinger Bands(%B), MACD, Stochastic(%K/%D), ATR, OBV slope, VWAP
- **전략 플러그인 4종**: `rsi`, `bollinger`, `macd_cross`, `stochastic`
- **파생 지표** (`src/indicators/crypto.py`): 김치프리미엄, 펀딩레이트·L/S 비율 정규화
- **DerivativeAgent**: Binance 퍼블릭 API (펀딩레이트, 미결제약정, L/S 비율, 호가 스프레드)
- **온체인 지표** (`src/indicators/onchain.py`): netflow, NVT, MVRV 정규화
- **OnchainAgent**: CryptoQuant free tier (거래소 유입/유출, 활성주소, NVT, MVRV)
- **MultiFactorStrategy**: 기술(6) + 파생(3) + 온체인(3) = 12팩터 가중 앙상블, graceful degradation
- **StrategyAgent 확장**: `signal.derivative`·`signal.onchain` 머지

---

## v0.8.0 — 통합 멀티 티커 백테스트 (2026-04-13)

### 추가
- **candle_merge.py**: heap 기반 크로노 머지, 메모리 O(num_tickers)
- **UnifiedBacktester**: 하나의 EventBus + Capital + SharedState에서 복수 티커 리플레이. 포트폴리오 레벨 `max_positions` 적용
- **multi.py `--unified` 플래그**: 기존 독립 모드와 통합 모드 선택 가능

---

## v0.7.0 — 주문 로그 DB 영속화 (2026-04-13)

### 추가
- **PersistenceAgent**: `order.*` 전 상태 전이 DB 기록, `order.filled` → TradeLog, `signal.generated` 샘플링 → SignalLog
- **crash recovery**: 기동 시 DB의 `accepted`/`partially_filled` 주문 복원 → 폴링 재개
- **이력 조회 API**: Dashboard `/api/orders`, `/api/trades`
- **Telegram `/orders`, `/trades`** 커맨드

### 변경
- `OrderRecord` 테이블: `created_at`·`updated_at` 분리
- `TradeLog`: `volume`, `pnl` 컬럼 추가

---

## v0.6.0 — 실자본 추적 (2026-04-13)

### 추가
- **Capital 클래스** (`src/core/capital.py`): thread-safe 잔고·포지션·실현손익 추적, `sync_from_upbit()`, `InsufficientFundsError`
- **Position 데이터클래스**: cost, unrealized PnL, mark-to-market
- **PortfolioAgent 재작성**: 실 Upbit 계좌 동기화, Capital 기반 포지션 관리
- **RiskAgent 사이징**: `equity × per_trade_risk_pct` → 실 volume 계산, `available_krw` 초과 방지
- **ExecutionAgent**: zero-volume 방어, dry-run 로그 강화

### 변경
- SharedState.positions: Capital 레이어에서 읽음
- 백테스터: `initial_krw` 기반 equity curve, `final_equity`·`total_pnl_krw` 리포트

---

## v0.5.0 — 그리드 서치 + Improver 시드 (2026-04-13)

### 추가
- **grid.py**: 파라미터 카티시안 스윕, `asyncio.Semaphore` 동시성 제한, 스코어링(return + DD + sharpe)
- **ImproverAgent.setup()**: 시드 JSON 로드 → `improver.params_updated` 즉시 발행 (콜드스타트 최적화)
- **multi.py**: 멀티 티커 독립 병렬 백테스트 (이 버전 기준 독립 모드만)
- `IMPROVER_SEED_FILE` 설정 추가

---

## v0.4.0 — 백테스트 러너 (2026-04-13)

### 추가
- **Backtester**: 캔들 리플레이, Signal·Strategy·Risk·MockExecution 재사용
- **MockExecutionAgent**: 슬리피지 모델 적용 즉시 체결
- **리포트**: closed_trades, win_rate, max_drawdown, sharpe-like
- CLI: `python -m src.backtest.runner`

---

## v0.3.0 — 주문 상태 머신 (2026-04-13)

### 추가
- **OrderState enum**: `submitted → accepted → partially_filled → filled / cancelled / failed`
- **ExecutionAgent 폴링**: Upbit UUID 상태 확인, 타임아웃 자동 취소
- **UpbitClient 확장**: `get_order()`, `cancel_order()`, GET/DELETE 서명 분리
- **OrderRecord** DB 모델

---

## v0.2.0 — 전략 플러그인 + WebSocket (2026-04-13)

### 추가
- **Strategy ABC** + Registry (자동 디스커버리)
- 전략 2종: `momentum`, `mean_reversion`
- **StrategyAgent 앙상블**: 가중 투표, `decision_threshold` 게이트
- **SignalAgent**: 멀티 시그널 번들 (`momentum`, `zscore`)
- **UpbitWSClient**: 자동 재연결, 지수 백오프
- **MarketDataAgent 재작성**: WS-first (ticker/trade/orderbook) + REST fallback
- **Improver 파라미터 확장**: dict 전체 적용 (숫자 only → 제거)

---

## v0.1.0 — 초기 멀티 Agent 골격 (2026-04-13)

### 추가
- **EventBus**: glob 패턴 구독 + tap (전체 이벤트 수신)
- **Orchestrator**: Agent 생명주기, SIGTERM/SIGINT graceful shutdown
- **SharedState**: 인메모리 공유 상태
- **BaseAgent**: `setup()`, `run()`, `stop()`, `emit()`, `sleep()` 공통 인터페이스
- **Agent 11종**: MarketData, Signal, Strategy, Risk, Execution, Portfolio, Performance, Improver, Notifier, Monitor, Dashboard
- **UpbitClient**: REST (시세, 계좌, 주문)
- **SQLite 스키마**: TradeLog, SignalLog, OrderRecord
- **TelegramBot**: `/status`, `/halt`, `/resume`, `/params`
- **Dashboard**: FastAPI + WebSocket + 기본 UI
- **Settings**: Pydantic Settings, AWS Secrets Manager 자동 하이드레이션
- **EC2 인프라**: systemd 서비스, userdata 스크립트
