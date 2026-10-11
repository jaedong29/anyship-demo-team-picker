import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def names(count: int) -> list[str]:
    return [f"참가자{number:02d}" for number in range(1, count + 1)]


def assign(participants, team_count):
    return client.post("/api/teams", json={"participants": participants, "team_count": team_count})


def test_healthz_is_public_and_simple():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_and_static_files_are_served():
    page = client.get("/")
    assert page.status_code == 200
    assert "팀 자동 배정" in page.text
    assert "default-src 'self'" in page.headers["content-security-policy"]
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200


@pytest.mark.parametrize(
    ("count", "team_count"),
    [(2, 2), (5, 2), (7, 3), (12, 5), (60, 2), (60, 7), (60, 60)],
)
def test_every_participant_is_assigned_once_and_sizes_are_balanced(count, team_count):
    participants = names(count)
    response = assign(participants, team_count)
    assert response.status_code == 200
    data = response.json()
    assert data["participant_count"] == count
    assert data["team_count"] == team_count
    assert [team["name"] for team in data["teams"]] == [f"{n}팀" for n in range(1, team_count + 1)]
    assigned = [member for team in data["teams"] for member in team["members"]]
    assert sorted(assigned) == sorted(participants)
    assert len(assigned) == len(set(assigned))
    sizes = [len(team["members"]) for team in data["teams"]]
    assert min(sizes) >= 1
    assert max(sizes) - min(sizes) <= 1


def test_names_are_trimmed():
    response = assign(["  가람 ", "나래", " 다온"], 2)
    assert response.status_code == 200
    assigned = sorted(m for team in response.json()["teams"] for m in team["members"])
    assert assigned == ["가람", "나래", "다온"]


def test_reshuffle_produces_different_arrangements():
    participants = names(10)
    arrangements = {
        tuple(tuple(team["members"]) for team in assign(participants, 3).json()["teams"])
        for _ in range(20)
    }
    assert len(arrangements) > 1


@pytest.mark.parametrize(
    ("participants", "team_count", "code", "message"),
    [
        ([], 2, "too_few_participants", "2명 이상"),
        (["혼자"], 2, "too_few_participants", "2명 이상"),
        (names(61), 2, "too_many_participants", "최대 60명"),
        (["가람", ""], 2, "empty_name", "2번째 이름이 비어"),
        (["가람", "   "], 2, "empty_name", "2번째 이름이 비어"),
        (["가람", "나래", "가람"], 2, "duplicate_name", "같은 이름"),
        (["가람", " 가람 "], 2, "duplicate_name", "같은 이름"),
        (["가" * 31, "나래"], 2, "name_too_long", "30자 이하"),
        (names(4), 1, "invalid_team_count", "팀 수는 2 이상"),
        (names(4), 0, "invalid_team_count", "팀 수는 2 이상"),
        (names(4), -3, "invalid_team_count", "팀 수는 2 이상"),
        (names(4), 5, "invalid_team_count", "참가자 수(4명) 이하"),
    ],
)
def test_invalid_input_is_rejected_with_korean_message(participants, team_count, code, message):
    response = assign(participants, team_count)
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == code
    assert message in body["detail"]


@pytest.mark.parametrize("team_count", ["3", 2.5, True, None])
def test_team_count_must_be_an_integer(team_count):
    response = assign(names(4), team_count)
    assert response.status_code == 422
    assert response.json() == {"code": "invalid_request", "detail": "팀 수는 2 이상의 정수로 선택해 주세요."}


@pytest.mark.parametrize(
    "payload",
    [
        {"participants": "가람\n나래", "team_count": 2},
        {"participants": ["가람", 7], "team_count": 2},
        {"team_count": 2},
    ],
)
def test_participants_must_be_a_list_of_strings(payload):
    response = client.post("/api/teams", json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"
    assert "참가자" in response.json()["detail"]


def test_oversized_participant_list_is_rejected_before_processing():
    response = assign(names(501), 2)
    assert response.status_code == 422
    assert "최대 60명" in response.json()["detail"]


def test_unknown_fields_and_bad_json_are_rejected():
    extra = client.post("/api/teams", json={"participants": names(2), "team_count": 2, "seed": 1})
    assert extra.status_code == 422
    broken = client.post(
        "/api/teams", content="{", headers={"Content-Type": "application/json"}
    )
    assert broken.status_code == 422
    assert broken.json()["code"] == "invalid_request"
