const API_BASE_URL = (window.EMPLOYER_MATCH_API_BASE_URL || "").replace(/\/$/, "");
const state = {
  samples: [],
  history: JSON.parse(localStorage.getItem("employerMatchHistory") || "[]"),
  lastResult: null,
  llmResult: null,
  currentWeights: {},
};
const historyList = document.querySelector("#historyList");
const clearHistoryButton = document.querySelector("#clearHistoryButton");
const sampleList = document.querySelector("#sampleList");
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
const llmCheckButton = document.getElementById("llmCheckButton");
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
  state.llmResult = null;
  breakdownList.innerHTML = "";
  state.currentWeights = {};

  // Integerize the original AI weights exactly once so they sum to 100
  if (!result.is_integerized) {
    let total = 0;
    result.competencies.forEach(c => {
      c.ai_weight = Math.round(Number(c.weight || 0));
      c.weight = c.ai_weight;
      total += c.weight;
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

    const syncValue = (val) => {
      let v = parseInt(val, 10);
      if (isNaN(v)) v = 0;
      handleSliderChange(id, v);
    };

    slider.addEventListener("input", (e) => syncValue(e.target.value));
    numInput.addEventListener("input", (e) => syncValue(e.target.value));
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
  const llmDataPoints = [];
  let totalWeight = 0;

  const acronyms = {
    "effective_communicator": "EC",
    "global_citizen": "GC",
    "creative_innovator": "CI",
    "critical_thinker": "CT",
    "reflective_future_focused": "RFF",
    "career_ready": "CR"
  };

  state.lastResult.competencies.forEach((competency) => {
    const id = competency.competency_id;
    const weight = state.currentWeights[id];
    totalWeight += weight;
    
    // Keep the core result object synced so history saves reflect user edits
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

    if (state.llmResult && state.llmResult.weights) {
      llmDataPoints.push(Math.round(state.llmResult.weights[id] || 0));
    }
  });

  const budgetTracker = document.getElementById("budgetTracker");
  const budgetText = document.getElementById("budgetText");
  const saveBtn = document.getElementById("saveButton");

  if (budgetTracker) {
    budgetTracker.style.display = "block";
    const difference = 100 - totalWeight;
    
    if (totalWeight === 100) {
      budgetText.textContent = `Allocated: 100 / 100 (Perfect)`;
      budgetText.className = "success";
      if (saveBtn) saveBtn.disabled = false;
    } else if (totalWeight > 100) {
      budgetText.textContent = `Allocated: ${totalWeight} / 100 (Over by ${Math.abs(difference)})`;
      budgetText.className = "error";
      if (saveBtn) saveBtn.disabled = true;
      if (matchButton) matchButton.style.display = "none";
      if (candidatesSection) candidatesSection.style.display = "none";
    } else {
      budgetText.textContent = `Allocated: ${totalWeight} / 100 (${difference} remaining)`;
      budgetText.className = "error";
      if (saveBtn) saveBtn.disabled = true;
      if (matchButton) matchButton.style.display = "none";
      if (candidatesSection) candidatesSection.style.display = "none";
    }
  }

  const datasets = [{
    label: 'Vector Similarity (Current)',
    data: dataPoints,
    backgroundColor: 'rgba(37, 99, 235, 0.2)',
    borderColor: 'rgba(37, 99, 235, 1)',
    pointBackgroundColor: 'rgba(37, 99, 235, 1)',
    pointBorderColor: '#fff',
    pointHoverBackgroundColor: '#fff',
    pointHoverBorderColor: 'rgba(37, 99, 235, 1)'
  }];

  if (state.llmResult) {
    datasets.push({
      label: 'LLM Score (Gemini)',
      data: llmDataPoints,
      backgroundColor: 'rgba(107, 92, 196, 0.2)',
      borderColor: 'rgba(107, 92, 196, 1)',
      borderDash: [5, 5],
      pointBackgroundColor: 'rgba(107, 92, 196, 1)',
      pointBorderColor: '#fff',
      pointHoverBackgroundColor: '#fff',
      pointHoverBorderColor: 'rgba(107, 92, 196, 1)'
    });
  }

  renderSpiderChart(labels, datasets);
}

function renderSpiderChart(labels, datasets) {
  if (chartInstance) {
    chartInstance.destroy();
  }
  chartInstance = new Chart(spiderChartCanvas, {
    type: 'radar',
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      scales: {
        r: {
          beginAtZero: true,
          ticks: {
            display: false
          }
        }
      },
      plugins: {
        legend: {
          display: true,
          position: 'bottom'
        }
      }
    }
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
  resetComparison();
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
  resetComparison();
  const budgetTracker = document.getElementById("budgetTracker");
  if (budgetTracker) budgetTracker.style.display = "none";
  if (matchButton) matchButton.style.display = "none";
  if (candidatesSection) candidatesSection.style.display = "none";
});

scoreButton.addEventListener("click", scoreCurrentJd);

if (llmCheckButton) {
  llmCheckButton.addEventListener("click", async () => {
    llmCheckButton.disabled = true;
      const originalText = "LLM Check";
    llmCheckButton.textContent = "Checking...";
    try {
      const response = await fetch(apiUrl("/api/llm-score"), {
        method: "POST",
        headers: apiHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          title: jobTitle.value,
          jd_text: jobText.value,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "LLM scoring failed");
      
      state.llmResult = payload;
      updateDOM();
      renderComparison();
      statusText.textContent = "LLM Check complete! Comparison added to chart.";
    } catch (error) {
      statusText.textContent = "LLM Error: " + error.message;
    } finally {
      llmCheckButton.disabled = false;
      llmCheckButton.textContent = originalText;
    }
  });
}

function renderComparison() {
  const container = document.getElementById("comparisonList");
  const itemsContainer = document.getElementById("comparisonItems");
  if (!container || !itemsContainer || !state.llmResult) return;

  container.style.display = "block";
  itemsContainer.innerHTML = "";
  
  state.lastResult.competencies.forEach(vecComp => {
    const llmComp = state.llmResult.competencies.find(c => c.competency_id === vecComp.competency_id);
    if (!llmComp) return;
    
    const vecWeight = Math.round(vecComp.weight);
    const llmWeight = Math.round(state.llmResult.weights[llmComp.competency_id] || 0);

    const li = document.createElement("div");
    li.className = "item-card";
    li.innerHTML = `
      <strong>${vecComp.label}</strong>
      <span>Vector: ${vecWeight} pts  &rarr;  LLM: ${llmWeight} pts</span>
    `;
    itemsContainer.appendChild(li);
  });
}

function resetComparison() {
  const container = document.getElementById("comparisonList");
  if (container) {
    container.style.display = "none";
  }
}

const resetButton = document.getElementById("resetButton");
const saveButton = document.getElementById("saveButton");

if (resetButton) {
  resetButton.addEventListener("click", () => {
    if (state.lastResult) {
      // Restore the original AI weights
      state.lastResult.competencies.forEach(c => {
        c.weight = c.ai_weight;
      });
      renderResult(state.lastResult);
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
        body: JSON.stringify({ weights: state.currentWeights })
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error);
      renderCandidates(payload.matches);
    } catch (error) {
      statusText.textContent = error.message;
    } finally {
      matchButton.disabled = false;
      matchButton.textContent = "Match with Students";
    }
  });
}

function renderMatchExplanation(match) {
  const strengths = (match.strengths || [])
    .map((item) => `${item.label} (${item.score.toFixed(1)})`)
    .join(", ");
  const gaps = (match.gaps || [])
    .map((item) => `${item.label} (${item.score.toFixed(1)})`)
    .join(", ");
  return `
    <p class="match-reason">${match.match_reason || ""}</p>
    <div class="match-explanation">
      <span><strong>Strongest alignment</strong>${strengths || "No weighted strengths"}</span>
      <span><strong>Watch gaps</strong>${gaps || "No weighted gaps"}</span>
    </div>
  `;
}

function renderCandidates(matches) {
  candidatesSection.style.display = "block";
  candidatesList.innerHTML = "";
  matches.forEach(m => {
    const div = document.createElement("div");
    div.className = "candidate-card";
    const tooltipHtml = `
      <div class="tooltip-grid">
        <div>EC: ${m.scores.effective_communicator}</div>
        <div>GC: ${m.scores.global_citizen}</div>
        <div>CI: ${m.scores.creative_innovator}</div>
        <div>CT: ${m.scores.critical_thinker}</div>
        <div>RFF: ${m.scores.reflective_future_focused}</div>
        <div>CR: ${m.scores.career_ready}</div>
      </div>
    `;
    div.innerHTML = `
      <div class="candidate-main">
        <span>${m.name}</span>
        <span class="candidate-score">${m.match_score.toFixed(1)} / 100</span>
      </div>
      ${renderMatchExplanation(m)}
      <div class="tooltip">${tooltipHtml}</div>
    `;
    candidatesList.appendChild(div);
  });
  candidatesSection.scrollIntoView({ behavior: 'smooth' });
}

async function loadSamples() {
  try {
    const response = await fetch(apiUrl("/api/samples"), {
      headers: apiHeaders(),
    });
    const data = await response.json();
    renderCards(sampleList, data.samples || [], (item) => {
      jobTitle.value = item.title;
      jobText.value = item.body;
      if (item.result) {
        statusText.textContent = "Loaded pre-calculated result for sample.";
        renderResult(item.result);
      } else {
        statusText.textContent = "Sample loaded. Click 'Score JD' to analyze.";
        // Clear previous results if any
        breakdownList.innerHTML = "";
        if (chartInstance) {
          chartInstance.destroy();
          chartInstance = null;
        }
      }
    });
  } catch (error) {
    console.error("Failed to load samples:", error);
    if (sampleList) sampleList.textContent = "Failed to load samples.";
  }
}

renderHistory();
loadSamples();
