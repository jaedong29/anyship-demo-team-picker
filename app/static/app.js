"use strict";

const MAX_TEAMS = 30;
const SAMPLE_NAMES = [
  "민준", "서연", "도윤", "하은", "지호", "수아",
  "예준", "지유", "시우", "서윤", "주원", "하린",
];

const form = document.getElementById("team-form");
const participants = document.getElementById("participants");
const participantCount = document.getElementById("participant-count");
const teamCount = document.getElementById("team-count");
const errorBox = document.getElementById("error");
const assignButton = document.getElementById("assign-button");
const shuffleButton = document.getElementById("shuffle-button");
const resetButton = document.getElementById("reset-button");
const sampleButton = document.getElementById("sample-button");
const resultSection = document.getElementById("result");
const resultSummary = document.getElementById("result-summary");
const teamList = document.getElementById("teams");

let lastRequest = "";
let lastResult = "";
let busy = false;

for (let count = 2; count <= MAX_TEAMS; count += 1) {
  const option = document.createElement("option");
  option.value = String(count);
  option.textContent = `${count}팀`;
  teamCount.append(option);
}

function readNames() {
  return participants.value
    .split(/\r?\n/)
    .map((name) => name.trim())
    .filter((name) => name.length > 0);
}

function updateCount() {
  participantCount.textContent = `${readNames().length}명`;
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
  participants.setAttribute("aria-invalid", "true");
}

function clearError() {
  errorBox.textContent = "";
  errorBox.hidden = true;
  participants.removeAttribute("aria-invalid");
}

function setBusy(value) {
  busy = value;
  assignButton.disabled = value;
  shuffleButton.disabled = value || lastResult === "";
  assignButton.textContent = value ? "배정 중…" : "팀 배정하기";
}

async function requestTeams(body) {
  let response;
  try {
    response = await fetch("/api/teams", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
  } catch {
    throw new Error("서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.");
  }
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    const message = data && typeof data.detail === "string"
      ? data.detail
      : "팀을 배정하지 못했습니다. 입력을 확인해 주세요.";
    throw new Error(message);
  }
  return data;
}

function renderResult(data) {
  const items = data.teams.map((team, index) => {
    const item = document.createElement("li");
    item.className = `team tone-${index % 6}`;

    const head = document.createElement("div");
    head.className = "team-head";
    const title = document.createElement("h3");
    title.textContent = team.name;
    const size = document.createElement("span");
    size.className = "team-size";
    size.textContent = `${team.members.length}명`;
    head.append(title, size);

    const members = document.createElement("ul");
    members.className = "members";
    for (const member of team.members) {
      const entry = document.createElement("li");
      entry.textContent = member;
      members.append(entry);
    }

    item.append(head, members);
    return item;
  });
  teamList.replaceChildren(...items);
  resultSummary.textContent = `참가자 ${data.participant_count}명을 ${data.team_count}개 팀으로 나눴습니다.`;
  resultSection.hidden = false;
}

async function assign({ reshuffle }) {
  if (busy) {
    return;
  }
  clearError();
  const body = JSON.stringify({ participants: readNames(), team_count: Number(teamCount.value) });
  setBusy(true);
  try {
    let data = await requestTeams(body);
    // "다시 섞기" should visibly change the teams, so retry a few times on an identical draw.
    for (let attempt = 0; reshuffle && body === lastRequest && attempt < 5; attempt += 1) {
      if (JSON.stringify(data.teams) !== lastResult) {
        break;
      }
      data = await requestTeams(body);
    }
    lastRequest = body;
    lastResult = JSON.stringify(data.teams);
    renderResult(data);
    if (!reshuffle) {
      resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  } catch (error) {
    clearResult();
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

function clearResult() {
  lastRequest = "";
  lastResult = "";
  teamList.replaceChildren();
  resultSummary.textContent = "";
  resultSection.hidden = true;
}

function reset() {
  participants.value = "";
  teamCount.value = "2";
  clearResult();
  clearError();
  updateCount();
  setBusy(false);
  participants.focus();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  assign({ reshuffle: false });
});
shuffleButton.addEventListener("click", () => assign({ reshuffle: true }));
resetButton.addEventListener("click", reset);
sampleButton.addEventListener("click", () => {
  participants.value = SAMPLE_NAMES.join("\n");
  teamCount.value = "3";
  clearError();
  updateCount();
});
participants.addEventListener("input", updateCount);
participants.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    form.requestSubmit();
  }
});

updateCount();
