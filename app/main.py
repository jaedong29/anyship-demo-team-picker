import os
import random
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

MIN_PARTICIPANTS = 2
MAX_PARTICIPANTS = 60
MAX_NAME_LENGTH = 30
STATIC_DIR = Path(__file__).parent / "static"
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; object-src 'none'; "
        "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}

app = FastAPI(title="팀 자동 배정", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
shuffler = random.SystemRandom()


class TeamRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    participants: list[StrictStr] = Field(max_length=500)
    team_count: StrictInt


class Team(BaseModel):
    name: str
    members: list[str]


class TeamResult(BaseModel):
    participant_count: int
    team_count: int
    teams: list[Team]


class AssignmentError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def clean_participants(raw: list[str]) -> list[str]:
    names = [name.strip() for name in raw]
    for position, name in enumerate(names, 1):
        if not name:
            raise AssignmentError("empty_name", f"{position}번째 이름이 비어 있습니다.")
        if len(name) > MAX_NAME_LENGTH:
            raise AssignmentError(
                "name_too_long", f"이름은 {MAX_NAME_LENGTH}자 이하로 입력해 주세요: {name[:10]}…"
            )
    if len(names) < MIN_PARTICIPANTS:
        raise AssignmentError(
            "too_few_participants", f"참가자를 {MIN_PARTICIPANTS}명 이상 입력해 주세요."
        )
    if len(names) > MAX_PARTICIPANTS:
        raise AssignmentError(
            "too_many_participants",
            f"참가자는 최대 {MAX_PARTICIPANTS}명까지 입력할 수 있습니다. (현재 {len(names)}명)",
        )
    seen: set[str] = set()
    duplicates: list[str] = []
    for name in names:
        if name in seen and name not in duplicates:
            duplicates.append(name)
        seen.add(name)
    if duplicates:
        raise AssignmentError(
            "duplicate_name",
            "같은 이름이 있습니다. 구분할 수 있게 바꿔 주세요: " + ", ".join(duplicates),
        )
    return names


def split_into_teams(names: list[str], team_count: int) -> list[list[str]]:
    """Shuffle once, then deal names in turn so team sizes differ by at most one."""
    shuffled = names.copy()
    shuffler.shuffle(shuffled)
    return [shuffled[index::team_count] for index in range(team_count)]


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


@app.exception_handler(AssignmentError)
async def assignment_error(_: Request, exc: AssignmentError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"code": exc.code, "detail": exc.message})


@app.exception_handler(RequestValidationError)
async def request_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    fields = {error["loc"][1]: error["type"] for error in exc.errors() if len(error["loc"]) > 1}
    if fields.get("participants") == "too_long":
        message = f"참가자는 최대 {MAX_PARTICIPANTS}명까지 입력할 수 있습니다."
    elif "participants" in fields:
        message = "참가자 이름은 글자 목록으로 보내 주세요."
    elif "team_count" in fields:
        message = "팀 수는 2 이상의 정수로 선택해 주세요."
    else:
        message = "요청 형식이 올바르지 않습니다. 참가자 이름과 팀 수를 확인해 주세요."
    return JSONResponse(status_code=422, content={"code": "invalid_request", "detail": message})


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/teams")
def create_teams(request: TeamRequest) -> TeamResult:
    names = clean_participants(request.participants)
    if not MIN_PARTICIPANTS <= request.team_count <= len(names):
        raise AssignmentError(
            "invalid_team_count",
            f"팀 수는 2 이상, 참가자 수({len(names)}명) 이하로 선택해 주세요.",
        )
    groups = split_into_teams(names, request.team_count)
    return TeamResult(
        participant_count=len(names),
        team_count=request.team_count,
        teams=[Team(name=f"{number}팀", members=members) for number, members in enumerate(groups, 1)],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
