# 팀 자동 배정 (anyship-demo-team-picker)

참가자 이름을 줄마다 입력하고 팀 수를 고르면, 인원 차이가 최대 1명이 되도록 무작위로 팀을 나누는 작은 FastAPI 앱입니다.
AnyShip 시연(AI 분석 → 변경안 검토 → PR → 병합 → 배포)에 쓰기 위해 만들었습니다.

- 원본 저장소: <https://github.com/jaedong29/anyship-demo-team-picker> (브랜치 `main`)
- 맞춘 AnyShip 기준: `gumtiket/anyship` main `ad371ad6fedb5aa2a1a92050a5a056ba190990dc`
- DB·파일 저장·외부 API·시크릿을 쓰지 않습니다. 명단과 결과는 요청과 브라우저 화면에만 있습니다.

> **일부러 남겨 둔 것 하나:** `app/main.py` 맨 아래 직접 실행 블록(`if __name__ == "__main__":`)의
> `uvicorn.run(..., port=8000)` 고정 포트입니다. AnyShip AI가 이것을 찾아 `PORT` 환경변수로 바꾸는 변경안을 만드는 것이
> 시연 포인트입니다. 컨테이너는 처음부터 `PORT`(기본 8080)를 읽으므로 이 블록 때문에 배포가 실패하지 않습니다.
> 시연 전에는 이 줄을 직접 고치지 마세요.

## 기능

- 참가자 2~60명, 이름은 앞뒤 공백 제거 후 1~30자, 빈 이름·중복 이름은 거부합니다.
- 팀 수는 정수이며 2 이상, 참가자 수 이하입니다.
- 모든 참가자를 정확히 한 번 배정하고 팀별 인원 차이는 최대 1명입니다.
- 계산과 검증은 서버 API가 하고, 오류는 화면에 한국어로 표시합니다.
- "다시 섞기"와 "입력 초기화"를 제공합니다. 결과는 DOM `textContent`로만 표시합니다.

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| GET | `/` | 화면 (HTML/CSS/JS는 `app/static`, 외부 CDN 없음) |
| GET | `/healthz` | `{"status": "ok"}` — 인증 없음 |
| POST | `/api/teams` | `{"participants": ["가람", "나래"], "team_count": 2}` → 팀 목록. 잘못된 입력은 422 `{"code", "detail"}` |

## 폴더 구성

```
app/main.py            FastAPI 앱 (전역 app, 진입점 app.main:app)
app/static/            index.html, style.css, app.js
tests/test_api.py      API 테스트
scripts/check_spec.py  deploy-spec.yaml 검증 (AnyShip 저장소 필요)
Dockerfile             AnyShip AI가 생성하는 Dockerfile과 바이트 단위로 같음
.dockerignore          추가 제외 항목 + AnyShip AI 기본 목록(끝부분 그대로)
deploy-spec.yaml       AnyShip 배포 명세 (source.commit 없음)
requirements.txt       실행 의존성 (정확한 버전)
requirements-dev.txt   테스트·명세 검증 의존성 (정확한 버전)
```

## 1. Fork 후 로컬에서 실행하기

### 1-1. 본인 계정으로 fork

1. <https://github.com/jaedong29/anyship-demo-team-picker> 를 엽니다.
2. 오른쪽 위 **Fork** → Owner를 본인 계정으로 선택 → 저장소 이름은 그대로 `anyship-demo-team-picker` → **Create fork**.

### 1-2. clone과 Python 3.12 환경

macOS / Linux:

```bash
git clone https://github.com/<내 GitHub ID>/anyship-demo-team-picker.git
cd anyship-demo-team-picker
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Windows (PowerShell):

```powershell
git clone https://github.com/<내 GitHub ID>/anyship-demo-team-picker.git
cd anyship-demo-team-picker
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

### 1-3. 테스트

```bash
python -m pytest
```

### 1-4. 로컬 실행

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8080
```

브라우저에서 <http://localhost:8080> 을 엽니다. "예시 이름 넣기" → "팀 배정하기"로 바로 확인할 수 있습니다.

`python -m app.main`으로도 실행할 수 있지만 포트가 다릅니다.

- AI PR 병합 **전**(지금 상태): 고정 포트 **8000** → <http://localhost:8000>
- AI PR 병합 **후**: `PORT` 환경변수, 없으면 **8080**

## 2. Docker로 실행하기

```bash
docker build --platform linux/amd64 -t anyship-demo-team-picker:local .
docker run --rm --platform linux/amd64 -p 8080:8080 \
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true \
  anyship-demo-team-picker:local
```

- 이미지는 비root 사용자(`10001`)로 실행되고, 읽기 전용 파일시스템에서 동작합니다(쓰기는 `/tmp`만).
- 확인: `curl http://localhost:8080/healthz`
- 다른 포트로 실행: `docker run ... -e PORT=9090 -p 9090:9090 anyship-demo-team-picker:local`
- Docker 실행은 컨테이너 단독 확인입니다. AnyShip 배포 성공을 뜻하지 않습니다.

## 3. Fork에서 배포 명세 고치기

`deploy-spec.yaml`의 `source.repo`를 본인 fork 주소로 바꿉니다. 다른 값은 그대로 둡니다.

```yaml
source:
  repo: https://github.com/<내 GitHub ID>/anyship-demo-team-picker
```

바꾼 뒤 AnyShip 현재 main으로 검증합니다(이 저장소 옆에 AnyShip을 clone).

```bash
git clone --depth 1 https://github.com/gumtiket/anyship.git ../anyship
python scripts/check_spec.py ../anyship
```

`AI JSON Schema: OK`와 `infra parse_spec: OK`가 나오면 됩니다. 바꾸지 않아도 AnyShip AI PR이 fork 주소로 고쳐 주지만,
미리 바꾸면 PR 차이가 줄어듭니다. `source.commit`은 직접 넣지 마세요(AI가 분석 기준 커밋으로 채웁니다).

## 4. AnyShip GitHub App이 내 fork에 접근하도록 허용하기

1. AnyShip 웹에서 **저장소 연결** → 저장소 URL에 본인 fork 주소 입력 → **주소 확인**.
2. **GitHub에서 접근 승인**을 누르면 GitHub 설치 화면으로 이동합니다.
3. 설치할 계정으로 본인 계정을 고르고 **Only select repositories**에서 `anyship-demo-team-picker`만 선택해 저장합니다.
4. AnyShip으로 돌아와 **프로젝트 연결**을 누릅니다. 화면이 그대로면 **접근 권한 다시 확인**을 누릅니다.

이미 앱을 설치했는데 이 저장소가 빠져 있으면: GitHub **Settings → Applications → Installed GitHub Apps → (AnyShip 앱) Configure →
Repository access**에서 이 저장소를 추가하고 **Save** 합니다. 앱 표시 이름은 서비스 운영자가 정한 이름입니다.

## 5. 로컬 확인과 AnyShip 배포 확인은 다릅니다

| 구분 | 무엇을 확인하나 | 어디서 |
| --- | --- | --- |
| 로컬 확인 | 테스트 통과, `uvicorn`/Docker에서 화면과 API 동작 | 내 PC |
| AnyShip 분석 | AI 진단·변경안·명세 호환. 현재 웹 분석은 `no_gate=True`라 컨테이너 실행 검증을 하지 않습니다 | AnyShip 웹 |
| AnyShip 배포 | 병합된 커밋을 서비스 서버에서 빌드해 연결된 환경에 배포, 공개 URL 응답 | AnyShip 웹 + 배포 환경 |

로컬에서 잘 돌아도 AnyShip 배포가 성공한 것은 아닙니다. AI 분석이 성공해도 배포가 검증된 것은 아닙니다.

## 6. 3분 시연 순서

1. **연결** — fork(또는 원본) 저장소를 AnyShip에 연결하고 기준 브랜치 `main`을 고릅니다.
2. **AI 진단** — 분석 결과에서 고정 포트(12-factor VII) 1건과 `app/main.py`의 `PORT` 변경안을 확인합니다.
3. **PR 검토·병합** — 앱 저장소에 생성된 PR을 사람이 열어 보고 병합합니다.
4. **배포** — 연결된 `aws-always-on` 또는 `onprem` 환경으로 배포합니다.
5. **사용** — 공개 URL에서 "예시 이름 넣기" → "팀 배정하기" → "다시 섞기"를 보여 줍니다.

### 분석·PR 화면에서 미리 알아 둘 것 (2026-10-11 현재 엔진 기준)

AnyShip main 엔진을 모델 호출 없이(provider=none) 실행해 확인한 내용입니다. 실제 모델 제공자를 쓰면 설명 문장은 달라질 수 있습니다.

- **변경안:** `app/main.py`에 `import os` 추가, 포트를 `int(os.environ.get("PORT", "8080"))`로 바꾸는 것뿐입니다.
- **PR 파일:** `app/main.py`와 `deploy-spec.yaml`입니다. 명세에서는 `source.commit`(분석 기준 커밋) 한 줄이 추가되고,
  AnyShip 웹은 앱 이름을 프로젝트 ID로 정하므로 `app:`이 `app-<프로젝트 ID 20자>`로 바뀝니다.
  배포 주소도 이 이름을 따릅니다: `<앱>.<환경ID>.aws.<도메인>` 또는 `<앱>.<환경ID>.onprem.<도메인>`.
  `Dockerfile`과 `.dockerignore`는 엔진 출력과 같아서 PR에 들어가지 않습니다.
- **"배포 방식 제안: aws-serverless":** 엔진 규칙(`short_request`)의 표시입니다. 현재 웹 배포 대상은 `aws-always-on`과
  `onprem`이며 서버리스 배포는 하지 않습니다. Dockerfile의 Lambda 어댑터 `COPY` 줄은 AI 템플릿과 같게 두기 위한 것입니다.
- **분석 경고:** `build_context_skipped`(문구에 "DB 변경안"이 있지만 이 앱은 DB가 없고, 웹 분석이 컨테이너 검증을 생략한다는 뜻),
  `provisional_infra_contract`(비용·인프라 값은 임시 추정), `rule_assessment_scope`(규칙 범위 밖 보장은 아님)가 나옵니다.

## 7. 실제 시연 사전 조건

앱 코드만으로는 아래 조건을 해결할 수 없습니다. 특히 SSH 연결 문제는 서비스·환경 설정에서 풀어야 합니다.

- GitHub App이 대상 저장소(fork 포함)에 접근하고 쓰기 권한(Contents, Pull requests)을 가질 것
- AnyShip 서비스에 정상 AI 제공자 설정(Bedrock 또는 Anthropic)이 되어 있을 것
- 연결 확인을 통과한 배포 환경(`aws-always-on` 또는 `onprem`)이 있을 것
- 서비스 서버의 SSH 키와 대상 서버 deploy 계정 인증이 맞을 것
- 대상 서버에 SSH와 웹(80/443) 포트로 접근할 수 있을 것
- 앱 주소의 DNS 레코드와 TLS 인증서가 준비되어 있을 것

## 8. 검증 기록 (2026-10-11, 로컬 검증)

- API 테스트 `python -m pytest`: 통과
- 브라우저: 배정·다시 섞기·입력 초기화·오류 표시(중복 이름, 팀 수 초과)·모바일(375px) 확인
- Docker: linux/amd64 빌드, uid 10001, `--read-only --tmpfs /tmp --cap-drop ALL`로 `/healthz`·`/api/teams` 응답, `PORT=9090` 동작 확인
- AnyShip main 엔진(provider=none, 모델 호출 0회, `no_gate=True`): 지원 등급 `supported`, 진입점 `app.main:app`,
  탐지 `fixed_port` 1건, 코드 변경 `app/main.py` 1개, Dockerfile·.dockerignore 엔진 출력과 동일, 배포 어댑터 명세 호환
- 실제 AWS/온프레미스 배포와 AnyShip 웹에서의 PR 생성·병합은 하지 않았습니다.
