const state = {
  samples: [],
  history: JSON.parse(localStorage.getItem("employerMatchHistory") || "[]"),
  lastResult: null,
};

const sampleList = document.querySelector("#sampleList");
const historyList = document.querySelector("#historyList");
const jobTitle = document.querySelector("#jobTitle");
const jobText = document.querySelector("#jobText");
const statusText = document.querySelector("#statusText");
const scoreButton = document.querySelector("#scoreButton");
const newCheckButton = document.querySelector("#newCheckButton");
const overallScore = document.querySelector("#overallScore");
const breakdownList = document.querySelector("#breakdownList");

function compactText(text, maxLength = 96) {
  const value = text.replace(/\s+/g, " ").trim();
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}...` : value;
}

function renderCards(container, items, onClick) {
  container.innerHTML = "";
  if (!items.length) {
    container.classList.add("empty-list");
    container.textContent = "No saved checks yet.";
    return;
  }
  container.classList.remove("empty-list");
  items.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "item-card";
    button.innerHTML = `<strong>${item.title}</strong><span>${compactText(item.body || item.summary || "")}</span>`;
    button.addEventListener("click", () => onClick(item));
    container.appendChild(button);
  });
}

function renderHistory() {
  renderCards(historyList, state.history, (item) => {
    jobTitle.value = item.title;
    jobText.value = item.body;
    if (item.result) {
      renderResult(item.result);
    }
  });
}

function renderSamples() {
  renderCards(sampleList, state.samples, (item) => {
    jobTitle.value = item.title;
    jobText.value = item.body;
    statusText.textContent = `Loaded ${item.title}`;
  });
}

function renderResult(result) {
  state.lastResult = result;
  overallScore.textContent = result.overall_score;
  breakdownList.innerHTML = "";
  result.competencies.forEach((competency) => {
    const weight = Number(competency.weight || 0);
    const row = document.createElement("article");
    row.className = "metric-row";
    row.innerHTML = `
      <header>
        <span>${competency.label}</span>
        <span>${weight.toFixed(1)} pts</span>
      </header>
      <div class="bar-track" aria-hidden="true"><div class="bar-fill" style="width:${Math.min(weight, 100)}%"></div></div>
      <div class="metric-meta">Level ${competency.matched_level} · similarity ${Number(competency.peak_similarity).toFixed(3)}</div>
    `;
    breakdownList.appendChild(row);
  });
}

function saveHistory(result) {
  const item = {
    title: result.title,
    body: jobText.value,
    summary: `${result.overall_score}/100`,
    result,
    savedAt: new Date().toISOString(),
  };
  state.history = [item, ...state.history.filter((entry) => entry.body !== item.body)].slice(0, 12);
  localStorage.setItem("employerMatchHistory", JSON.stringify(state.history));
  renderHistory();
}

async function loadSamples() {
  const response = await fetch("/api/samples");
  const payload = await response.json();
  state.samples = payload.samples || [];
  renderSamples();
}

async function scoreCurrentJd() {
  scoreButton.disabled = true;
  statusText.textContent = "Scoring...";
  try {
    const response = await fetch("/api/score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: jobTitle.value,
        jd_text: jobText.value,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Scoring failed");
    }
    renderResult(payload);
    saveHistory(payload);
    statusText.textContent = payload.used_uniform_fallback
      ? `Scored with fallback: ${payload.fallback_reason}`
      : "Scored and saved to previous checks.";
  } catch (error) {
    statusText.textContent = error.message;
  } finally {
    scoreButton.disabled = false;
  }
}

newCheckButton.addEventListener("click", () => {
  jobTitle.value = "Untitled JD";
  jobText.value = "";
  statusText.textContent = "";
  overallScore.textContent = "--";
  breakdownList.innerHTML = "";
});

scoreButton.addEventListener("click", scoreCurrentJd);

renderHistory();
loadSamples().catch((error) => {
  statusText.textContent = error.message;
});
