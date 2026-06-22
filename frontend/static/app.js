function getApiBaseUrl() {
  return (window.EMPLOYER_MATCH_API_BASE_URL || "").replace(/\/$/, "");
}

function readHistory() {
  try {
    return JSON.parse(localStorage.getItem("employerMatchHistory") || "[]");
  } catch {
    return [];
  }
}

const state = {
  samples: [],
  history: readHistory(),
  lastResult: null,
  currentWeights: {},
};

const sampleList = document.querySelector("#sampleList");
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
  if (window.EmployerMatchAuth?.apiUrl) {
    return window.EmployerMatchAuth.apiUrl(path);
  }
  return `${getApiBaseUrl()}${path}`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]),
  );
}

function apiHeaders(extra = {}) {
  if (window.EmployerMatchAuth?.apiHeaders) {
    return window.EmployerMatchAuth.apiHeaders(extra);
  }
  return { "ngrok-skip-browser-warning": "true", ...extra };
}

function compactText(text, maxLength = 96) {
  const value = text.replace(/\s+/g, " ").trim();
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}...` : value;
}

function renderCards(container, items, onClick, emptyText = "No saved checks yet.") {
  if (!container) return;
  container.innerHTML = "";
  if (!items.length) {
    container.classList.add("empty-list");
    container.textContent = emptyText;
    return;
  }
  container.classList.remove("empty-list");
  items.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "item-card";
    button.innerHTML = `<strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(compactText(item.body || item.summary || ""))}</span>`;
    button.addEventListener("click", () => onClick(item));
    container.appendChild(button);
  });
}

function persistHistory() {
  localStorage.setItem("employerMatchHistory", JSON.stringify(state.history));
  renderHistory();
}

function deleteHistoryItem(index) {
  state.history = state.history.filter((_, i) => i !== index);
  persistHistory();
}

function clearHistory() {
  state.history = [];
  persistHistory();
  statusText.textContent = "Cleared saved JD checks.";
}

function renderHistory() {
  historyList.innerHTML = "";
  if (!state.history.length) {
    historyList.classList.add("empty-list");
    historyList.textContent = "No saved checks yet.";
    if (clearHistoryButton) clearHistoryButton.hidden = true;
    return;
  }

  historyList.classList.remove("empty-list");
  if (clearHistoryButton) clearHistoryButton.hidden = false;

  state.history.forEach((item, index) => {
    const row = document.createElement("div");
    row.className = "history-row";

    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.className = "item-card";
    openButton.innerHTML = `<strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(compactText(item.body || item.summary || ""))}</span>`;
    openButton.addEventListener("click", () => {
      jobTitle.value = item.title;
      jobText.value = item.body;
      if (item.result) {
        renderResult(item.result);
      }
      statusText.textContent = `Loaded ${item.title}`;
    });

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "delete-history-btn";
    deleteButton.setAttribute("aria-label", `Delete ${item.title}`);
    deleteButton.title = "Delete";
    deleteButton.textContent = "\u00d7";
    deleteButton.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteHistoryItem(index);
    });

    row.appendChild(openButton);
    row.appendChild(deleteButton);
    historyList.appendChild(row);
  });
}

async function loadSamples() {
  if (!sampleList) return;
  const apiBase = getApiBaseUrl();
  if (!apiBase) {
    sampleList.classList.add("empty-list");
    sampleList.textContent = "Backend URL not configured in config.js.";
    statusText.textContent = "Set EMPLOYER_MATCH_API_BASE_URL in config.js.";
    return;
  }

  sampleList.classList.add("empty-list");
  sampleList.textContent = "Loading samples...";

  try {
    const response = await fetch(apiUrl("/api/samples"), { headers: apiHeaders() });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Failed to load samples");
    state.samples = payload.samples || [];
    renderCards(
      sampleList,
      state.samples,
      (item) => {
        jobTitle.value = item.title;
        jobText.value = item.body;
        hideAudit();
        if (item.result) {
          statusText.textContent = "Loaded pre-calculated result for sample.";
          if (matchButton) matchButton.style.display = "none";
          if (candidatesSection) candidatesSection.style.display = "none";
          renderResult(item.result);
        } else {
          statusText.textContent = "Sample loaded. Click 'Score JD' to analyze.";
          breakdownList.innerHTML = "";
          if (chartInstance) {
            chartInstance.destroy();
            chartInstance = null;
          }
          const budgetTracker = document.getElementById("budgetTracker");
          if (budgetTracker) budgetTracker.style.display = "none";
          if (matchButton) matchButton.style.display = "none";
          if (candidatesSection) candidatesSection.style.display = "none";
        }
      },
      "No sample JDs found.",
    );
  } catch (error) {
    console.error("Failed to load samples:", error);
    sampleList.classList.add("empty-list");
    sampleList.textContent = error.message || "Failed to load samples.";
    statusText.textContent =
      "Could not load samples. Is the backend running on " + apiBase + "?";
  }
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
}

async function scoreCurrentJd() {
  scoreButton.disabled = true;
  statusText.textContent = "Scoring...";
  hideAudit();
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

newCheckButton?.addEventListener("click", () => {
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
  hideAudit();
});

scoreButton?.addEventListener("click", scoreCurrentJd);

const resetButton = document.getElementById("resetButton");
const saveButton = document.getElementById("saveButton");

if (resetButton) {
  resetButton.addEventListener("click", () => {
    if (state.lastResult) {
      state.lastResult.competencies.forEach((competency) => {
        competency.weight = competency.ai_weight;
      });
      renderResult(state.lastResult);
    }
  });
}

if (saveButton) {
  saveButton.addEventListener("click", async () => {
    if (!state.lastResult) return;
    saveHistory(state.lastResult);
    saveButton.disabled = true;
    statusText.textContent = "Saving and publishing job…";
    try {
      await publishCurrentJob();
      statusText.textContent = "Scores saved and job published for seekers. You can now match with candidates.";
      await loadSeekers();
    } catch (error) {
      statusText.textContent = `Saved locally. Publish failed: ${error.message || error}`;
    } finally {
      saveButton.disabled = false;
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

function hideAudit() {
  if (auditSection) auditSection.style.display = "none";
  if (applyAuditButton) applyAuditButton.style.display = "none";
}

function renderAudit(data) {
  auditSection.style.display = "block";
  auditSummary.textContent = data.summary || "";
  auditResults.innerHTML = "";

  const changesCount = data.changes_count ?? data.competencies.filter((c) => c.changed).length;

  data.competencies.forEach((competency) => {
    const changed = competency.changed === true;
    const card = document.createElement("div");
    card.className = changed ? "audit-card" : "audit-card unchanged";

    if (changed) {
      const delta = competency.delta;
      const arrow = delta > 0 ? "\u25B2" : delta < 0 ? "\u25BC" : "\u2014";
      const deltaClass = delta > 0 ? "delta-up" : delta < 0 ? "delta-down" : "delta-same";
      card.innerHTML = `
        <div class="audit-head">
          <strong>${escapeHtml(competency.label)}</strong>
          <span class="audit-nums">
            <span class="audit-base">${competency.baseline}</span>
            <span class="audit-arrow ${deltaClass}">\u2192 ${competency.corrected} ${arrow}</span>
          </span>
        </div>
        <div class="audit-reason">${escapeHtml(competency.reason)}</div>
        ${competency.evidence ? `<div class="audit-evidence">${escapeHtml(competency.evidence)}</div>` : ""}
      `;
    } else {
      card.innerHTML = `
        <div class="audit-head">
          <strong>${escapeHtml(competency.label)}</strong>
          <span class="audit-nums audit-no-change">${competency.baseline} — no change</span>
        </div>
        <div class="audit-reason">${escapeHtml(competency.reason || "Embedding weight aligns with JD.")}</div>
      `;
    }

    auditResults.appendChild(card);
  });

  if (changesCount > 0) {
    applyAuditButton.style.display = "block";
    applyAuditButton.disabled = false;
    applyAuditButton.onclick = () => {
      const updated = { ...state.currentWeights };
      data.competencies.forEach((competency) => {
        if (competency.changed) {
          updated[competency.competency_id] = competency.corrected;
        }
      });
      state.currentWeights = updated;
      updateDOM();
      hideAudit();
      statusText.textContent = "Applied AI corrections. Review the sliders and Save.";
    };
  } else {
    applyAuditButton.style.display = "none";
    applyAuditButton.onclick = null;
  }

  auditSection.scrollIntoView({ behavior: "smooth" });
}

async function auditWeights() {
  if (!state.lastResult) return;
  const originalLabel = auditButton.textContent;
  auditButton.disabled = true;
  auditButton.textContent = "Auditing...";
  statusText.textContent = "Running AI audit (this can take a few seconds)...";
  try {
    const response = await fetch(apiUrl("/api/audit"), {
      method: "POST",
      headers: apiHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        jd_text: jobText.value,
        weights: state.currentWeights,
        competencies: state.lastResult.competencies,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Audit failed");
    renderAudit(payload);
    statusText.textContent =
      payload.changes_count > 0
        ? `AI audit complete (${payload.model}). ${payload.changes_count} correction(s) suggested.`
        : `AI audit complete (${payload.model}). No corrections needed.`;
  } catch (error) {
    statusText.textContent = error.message;
  } finally {
    auditButton.disabled = false;
    auditButton.textContent = originalLabel;
  }
}

if (auditButton) {
  auditButton.addEventListener("click", auditWeights);
}

if (clearHistoryButton) {
  clearHistoryButton.addEventListener("click", clearHistory);
}

function renderCandidates(matches) {
  candidatesSection.style.display = "block";
  candidatesList.innerHTML = "";
  matches.forEach((match) => {
    const div = document.createElement("div");
    div.className = "candidate-card";
    const sourceTag =
      match.source === "seeker" ? '<span class="source-tag">live</span>' : "";
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
      <span>${escapeHtml(match.name)} ${sourceTag}</span>
      <span class="candidate-score">${match.match_score.toFixed(1)} / 100</span>
      <div class="tooltip">${tooltipHtml}</div>
    `;
    candidatesList.appendChild(div);
  });
  candidatesSection.scrollIntoView({ behavior: "smooth" });
}

function initApp() {
  renderHistory();
  loadSamples();
  loadSeekers();
}

async function publishCurrentJob() {
  if (!state.lastResult || !window.EmployerMatchSupabase?.isConfigured()) return;
  const session = await window.EmployerMatchAuth.getSession();
  if (!session) return;
  const client = await window.EmployerMatchSupabase.getClient();
  const { error } = await client.from("employer_jobs").insert({
    employer_id: session.user.id,
    title: jobTitle.value.trim() || state.lastResult.title || "Untitled JD",
    jd_text: jobText.value.trim(),
    weights: state.currentWeights,
    status: "published",
  });
  if (error) throw error;
}

async function loadSeekers() {
  const seekersList = document.getElementById("seekersList");
  if (!seekersList || !window.EmployerMatchSupabase?.isConfigured()) return;

  seekersList.classList.add("empty-list");
  seekersList.textContent = "Loading seekers...";

  try {
    const client = await window.EmployerMatchSupabase.getClient();
    const [{ data: demoRows, error: demoError }, { data: liveRows, error: liveError }] =
      await Promise.all([
        client.from("demo_seekers").select("name, scores").order("name"),
        client
          .from("seeker_passports")
          .select("user_id, scores, status, profiles(display_name)")
          .eq("status", "complete"),
      ]);

    if (demoError && !demoError.message.includes("does not exist")) throw demoError;
    if (liveError) throw liveError;

    const cards = [];
    (demoRows || []).forEach((row) => {
      cards.push({ name: row.name, source: "demo", scores: row.scores || {} });
    });
    (liveRows || []).forEach((row) => {
      const name = row.profiles?.display_name || `Seeker ${String(row.user_id || "").slice(0, 8)}`;
      cards.push({ name, source: "live", scores: row.scores || {} });
    });

    seekersList.innerHTML = "";
    if (!cards.length) {
      seekersList.textContent = "No seekers yet. Run supabase/seed.sql for demo users.";
      return;
    }

    seekersList.classList.remove("empty-list");
    cards.forEach((card) => {
      const item = document.createElement("div");
      item.className = "candidate-card";
      const tag = card.source === "live" ? "live" : "demo";
      const avg = COMPETENCY_ORDER.reduce((sum, key) => sum + Number(card.scores[key] || 0), 0) / 6;
      item.innerHTML = `
        <span>${escapeHtml(card.name)} <span class="source-tag">${tag}</span></span>
        <span class="candidate-score">${avg.toFixed(0)} avg</span>
      `;
      seekersList.appendChild(item);
    });
  } catch (error) {
    seekersList.classList.add("empty-list");
    seekersList.textContent = error.message || "Failed to load seekers.";
  }
}

const COMPETENCY_ORDER = [
  "effective_communicator",
  "global_citizen",
  "creative_innovator",
  "critical_thinker",
  "reflective_future_focused",
  "career_ready",
];

window.initApp = initApp;
