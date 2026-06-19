const API_BASE_URL = (window.EMPLOYER_MATCH_API_BASE_URL || "").replace(/\/$/, "");

const state = {
  history: JSON.parse(localStorage.getItem("employerMatchHistory") || "[]"),
  lastResult: null,
  currentWeights: {},
};

const historyList = document.querySelector("#historyList");
const clearHistoryButton = document.querySelector("#clearHistoryButton");
const jobTitle = document.querySelector("#jobTitle");
const jobText = document.querySelector("#jobText");
const statusText = document.querySelector("#statusText");
const scoreButton = document.querySelector("#scoreButton");
const newCheckButton = document.querySelector("#newCheckButton");
const breakdownList = document.querySelector("#breakdownList");
const spiderChartCanvas = document.querySelector("#spiderChart");
const matchButton = document.getElementById("matchButton");
const candidatesSection = document.getElementById("candidatesSection");
const candidatesList = document.getElementById("candidatesList");
const auditButton = document.getElementById("auditButton");
const auditSection = document.getElementById("auditSection");
const auditSummary = document.getElementById("auditSummary");
const auditResults = document.getElementById("auditResults");
const applyAuditButton = document.getElementById("applyAuditButton");
let chartInstance = null;

function apiUrl(path) {
  return `${API_BASE_URL}${path}`;
}

function apiHeaders(extra = {}) {
  return { "ngrok-skip-browser-warning": "true", ...extra };
}

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
  historyList.innerHTML = "";
  if (!state.history.length) {
    historyList.classList.add("empty-list");
    historyList.textContent = "No saved checks yet.";
    updateHistoryControls();
    return;
  }
  historyList.classList.remove("empty-list");
  state.history.forEach((item, index) => {
    const row = document.createElement("div");
    row.className = "history-row";
    const card = document.createElement("button");
    card.type = "button";
    card.className = "item-card";
    card.innerHTML = `<strong>${item.title}</strong><span>${compactText(item.body || item.summary || "")}</span>`;
    card.addEventListener("click", () => loadHistoryItem(item));

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "delete-history-btn";
    deleteButton.textContent = "×";
    deleteButton.setAttribute("aria-label", `Delete ${item.title}`);
    deleteButton.addEventListener("click", () => deleteHistoryItem(index));

    row.appendChild(card);
    row.appendChild(deleteButton);
    historyList.appendChild(row);
  });
  updateHistoryControls();
}

function loadHistoryItem(item) {
    jobTitle.value = item.title;
    jobText.value = item.body;
    if (item.result) {
      renderResult(item.result);
    }
}

function persistHistory() {
  if (state.history.length) {
    localStorage.setItem("employerMatchHistory", JSON.stringify(state.history));
  } else {
    localStorage.removeItem("employerMatchHistory");
  }
}

function updateHistoryControls() {
  if (clearHistoryButton) clearHistoryButton.hidden = state.history.length === 0;
}

function deleteHistoryItem(index) {
  state.history.splice(index, 1);
  persistHistory();
  renderHistory();
}

function clearHistory() {
  state.history = [];
  localStorage.removeItem("employerMatchHistory");
  renderHistory();
}

function renderResult(result) {
  state.lastResult = result;
  breakdownList.innerHTML = "";
  state.currentWeights = {};

  // Integerize the original AI weights exactly once so they sum to 100.
  if (!result.is_integerized) {
    let total = 0;
    result.competencies.forEach((competency) => {
      competency.ai_weight = Math.round(Number(competency.weight || 0));
      competency.weight = competency.ai_weight;
      total += competency.weight;
    });
    if (total !== 100 && result.competencies.length > 0) {
      const diff = 100 - total;
      result.competencies[0].weight += diff;
      result.competencies[0].ai_weight += diff;
    }
    result.is_integerized = true;
  }

  result.competencies.forEach((competency) => {
    state.currentWeights[competency.competency_id] = competency.weight;
  });

  result.competencies.forEach((competency) => {
    const id = competency.competency_id;
    const row = document.createElement("article");
    row.className = "metric-row";
    row.innerHTML = `
      <header>
        <span>${competency.label}</span>
        <div class="score-controls">
          <input type="number" id="num-${id}" min="0" max="100" step="1" value="${competency.weight}" class="score-input" aria-label="${competency.label} weight">
          <span style="color: var(--muted); font-size: 13px;">pts</span>
        </div>
      </header>
      <input type="range" id="slider-${id}" min="0" max="100" step="1" value="${competency.weight}" aria-label="${competency.label} slider">
      <div class="metric-meta">Level ${competency.matched_level} · similarity ${Number(competency.peak_similarity).toFixed(3)}</div>
    `;
    breakdownList.appendChild(row);

    const slider = row.querySelector(`#slider-${id}`);
    const numInput = row.querySelector(`#num-${id}`);

    const syncValue = (value) => {
      let nextValue = parseInt(value, 10);
      if (Number.isNaN(nextValue)) nextValue = 0;
      handleSliderChange(id, nextValue);
    };

    slider.addEventListener("input", (event) => syncValue(event.target.value));
    numInput.addEventListener("input", (event) => syncValue(event.target.value));
  });

  updateDOM();
}

function handleSliderChange(changedId, newValue) {
  newValue = Math.max(0, Math.min(100, newValue));
  state.currentWeights = { ...state.currentWeights, [changedId]: newValue };
  resetAudit();
  updateDOM();
}

function updateDOM() {
  const labels = [];
  const dataPoints = [];
  let totalWeight = 0;

  const acronyms = {
    effective_communicator: "EC",
    global_citizen: "GC",
    creative_innovator: "CI",
    critical_thinker: "CT",
    reflective_future_focused: "RFF",
    career_ready: "CR",
  };

  state.lastResult.competencies.forEach((competency) => {
    const id = competency.competency_id;
    const weight = state.currentWeights[id];
    totalWeight += weight;
    competency.weight = weight;

    const numInput = document.getElementById(`num-${id}`);
    if (numInput && parseInt(numInput.value, 10) !== weight) {
      numInput.value = weight;
    }

    const slider = document.getElementById(`slider-${id}`);
    if (slider && parseInt(slider.value, 10) !== weight) {
      slider.value = weight;
    }

    labels.push(acronyms[id] || competency.label);
    dataPoints.push(weight);
  });

  const budgetTracker = document.getElementById("budgetTracker");
  const budgetText = document.getElementById("budgetText");
  const saveBtn = document.getElementById("saveButton");

  if (budgetTracker) {
    budgetTracker.style.display = "block";
    const difference = 100 - totalWeight;

    if (totalWeight === 100) {
      budgetText.textContent = "Allocated: 100 / 100 (Perfect)";
      budgetText.className = "success";
      saveBtn.disabled = false;
    } else if (totalWeight > 100) {
      budgetText.textContent = `Allocated: ${totalWeight} / 100 (Over by ${Math.abs(difference)})`;
      budgetText.className = "error";
      saveBtn.disabled = true;
      if (matchButton) matchButton.style.display = "none";
      if (candidatesSection) candidatesSection.style.display = "none";
    } else {
      budgetText.textContent = `Allocated: ${totalWeight} / 100 (${difference} remaining)`;
      budgetText.className = "error";
      saveBtn.disabled = true;
      if (matchButton) matchButton.style.display = "none";
      if (candidatesSection) candidatesSection.style.display = "none";
    }
  }

  renderSpiderChart(labels, dataPoints);
}

function renderSpiderChart(labels, data) {
  if (chartInstance) {
    chartInstance.destroy();
  }
  chartInstance = new Chart(spiderChartCanvas, {
    type: "radar",
    data: {
      labels,
      datasets: [
        {
          label: "Competency Weight",
          data,
          backgroundColor: "rgba(37, 99, 235, 0.2)",
          borderColor: "rgba(37, 99, 235, 1)",
          pointBackgroundColor: "rgba(37, 99, 235, 1)",
          pointBorderColor: "#fff",
          pointHoverBackgroundColor: "#fff",
          pointHoverBorderColor: "rgba(37, 99, 235, 1)",
        },
      ],
    },
    options: {
      scales: {
        r: {
          beginAtZero: true,
          ticks: {
            display: false,
          },
        },
      },
      plugins: {
        legend: {
          display: false,
        },
      },
    },
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
  persistHistory();
  renderHistory();
}

if (clearHistoryButton) {
  clearHistoryButton.addEventListener("click", clearHistory);
}

async function scoreCurrentJd() {
  scoreButton.disabled = true;
  statusText.textContent = "Scoring...";
  resetAudit();
  try {
    const response = await fetch(apiUrl("/api/score"), {
      method: "POST",
      headers: apiHeaders({ "Content-Type": "application/json" }),
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
    statusText.textContent = payload.used_uniform_fallback
      ? `Scored with fallback: ${payload.fallback_reason}. Adjust sliders and click Save.`
      : "Scored successfully. Adjust sliders and click Save.";
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
  breakdownList.innerHTML = "";
  if (chartInstance) {
    chartInstance.destroy();
    chartInstance = null;
  }
  const budgetTracker = document.getElementById("budgetTracker");
  if (budgetTracker) budgetTracker.style.display = "none";
  if (matchButton) matchButton.style.display = "none";
  if (candidatesSection) candidatesSection.style.display = "none";
  resetAudit();
});

scoreButton.addEventListener("click", scoreCurrentJd);

const resetButton = document.getElementById("resetButton");
const saveButton = document.getElementById("saveButton");

if (resetButton) {
  resetButton.addEventListener("click", () => {
    if (state.lastResult) {
      state.lastResult.competencies.forEach((competency) => {
        competency.weight = competency.ai_weight;
      });
      resetAudit();
      renderResult(state.lastResult);
    }
  });
}

function resetAudit() {
  if (auditSection) auditSection.style.display = "none";
  if (auditSummary) auditSummary.textContent = "";
  if (auditResults) auditResults.innerHTML = "";
  if (applyAuditButton) applyAuditButton.style.display = "none";
}

function applyAuditResult(auditPayload) {
  if (!state.lastResult || !auditPayload.corrected) return;
  state.lastResult.competencies.forEach((competency) => {
    const corrected = auditPayload.corrected[competency.competency_id];
    if (corrected !== undefined) {
      competency.weight = Math.round(Number(corrected));
    }
  });
  renderResult(state.lastResult);
  statusText.textContent = "Audit corrections applied. Review the allocation before saving.";
}

function renderAudit(auditPayload) {
  auditSection.style.display = "block";
  auditSummary.textContent = auditPayload.summary || "AI audit complete.";
  auditResults.innerHTML = "";
  const isFallback = auditPayload.audit_status?.startsWith("fallback_");

  (auditPayload.competencies || []).forEach((item) => {
    const card = document.createElement("article");
    card.className = `audit-card ${item.changed ? "" : "unchanged"}`;
    card.innerHTML = `
      <div class="audit-head">
        <strong>${item.label}</strong>
        <span class="audit-nums">${item.baseline} → ${item.corrected} pts</span>
      </div>
      <div class="audit-reason">${item.reason}</div>
      <div class="audit-evidence">${item.evidence}</div>
    `;
    auditResults.appendChild(card);
  });

  if (isFallback) {
    statusText.textContent = "AI audit unavailable; baseline weights were kept.";
    applyAuditButton.style.display = "none";
    return;
  }

  applyAuditButton.style.display = auditPayload.changes_count > 0 ? "block" : "none";
  applyAuditButton.onclick = () => applyAuditResult(auditPayload);
}

if (auditButton) {
  auditButton.addEventListener("click", async () => {
    if (!state.lastResult) return;
    auditButton.disabled = true;
    auditButton.textContent = "Auditing...";
    try {
      const response = await fetch(apiUrl("/api/audit"), {
        method: "POST",
        headers: apiHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          title: jobTitle.value,
          jd_text: jobText.value,
          weights: state.currentWeights,
          competencies: state.lastResult.competencies,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "AI audit failed");
      renderAudit(payload);
    } catch (error) {
      statusText.textContent = `AI audit failed: ${error.message}`;
    } finally {
      auditButton.disabled = false;
      auditButton.textContent = "AI Audit";
    }
  });
}

if (saveButton) {
  saveButton.addEventListener("click", () => {
    if (state.lastResult) {
      saveHistory(state.lastResult);
      statusText.textContent = "Scores saved! You can now match with candidates.";
      if (matchButton) matchButton.style.display = "inline-block";
    }
  });
}

if (matchButton) {
  matchButton.addEventListener("click", async () => {
    matchButton.disabled = true;
    matchButton.textContent = "Matching...";
    try {
      const response = await fetch(apiUrl("/api/match"), {
        method: "POST",
        headers: apiHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ weights: state.currentWeights }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Matching failed");
      renderCandidates(payload.matches);
    } catch (error) {
      statusText.textContent = error.message;
    } finally {
      matchButton.disabled = false;
      matchButton.textContent = "Match with Students";
    }
  });
}

function renderCandidates(matches) {
  candidatesSection.style.display = "block";
  candidatesList.innerHTML = "";
  matches.forEach((match) => {
    const div = document.createElement("div");
    div.className = "candidate-card";
    const tooltipHtml = `
      <div class="tooltip-grid">
        <div>EC: ${match.scores.effective_communicator}</div>
        <div>GC: ${match.scores.global_citizen}</div>
        <div>CI: ${match.scores.creative_innovator}</div>
        <div>CT: ${match.scores.critical_thinker}</div>
        <div>RFF: ${match.scores.reflective_future_focused}</div>
        <div>CR: ${match.scores.career_ready}</div>
      </div>
    `;
    div.innerHTML = `
      <span>${match.name}</span>
      <span class="candidate-score">${match.match_score.toFixed(1)} / 100</span>
      <div class="tooltip">${tooltipHtml}</div>
    `;
    candidatesList.appendChild(div);
  });
  candidatesSection.scrollIntoView({ behavior: "smooth" });
}

renderHistory();
