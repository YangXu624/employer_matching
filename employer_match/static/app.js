// If empty string, uses relative paths. Change to "https://your-ngrok-url.ngrok-free.app" if hosting frontend separately.
const API_BASE_URL = "https://e1fb-69-122-192-234.ngrok-free.app";

const state = {
  samples: [],
  history: JSON.parse(localStorage.getItem("employerMatchHistory") || "[]"),
  lastResult: null,
  currentWeights: {},
};
const historyList = document.querySelector("#historyList");
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
let chartInstance = null;

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

function renderResult(result) {
  state.lastResult = result;
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
    type: 'radar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Competency Weight',
        data: data,
        backgroundColor: 'rgba(37, 99, 235, 0.2)',
        borderColor: 'rgba(37, 99, 235, 1)',
        pointBackgroundColor: 'rgba(37, 99, 235, 1)',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: 'rgba(37, 99, 235, 1)'
      }]
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
          display: false
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
  localStorage.setItem("employerMatchHistory", JSON.stringify(state.history));
  renderHistory();
}

async function scoreCurrentJd() {
  scoreButton.disabled = true;
  statusText.textContent = "Scoring...";
  try {
    const response = await fetch(`${API_BASE_URL}/api/score`, {
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
});

scoreButton.addEventListener("click", scoreCurrentJd);

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
      const response = await fetch(`${API_BASE_URL}/api/match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
      <span>${m.name}</span>
      <span class="candidate-score">${m.match_score.toFixed(1)} / 100</span>
      <div class="tooltip">${tooltipHtml}</div>
    `;
    candidatesList.appendChild(div);
  });
  candidatesSection.scrollIntoView({ behavior: 'smooth' });
}

async function loadSamples() {
  try {
    const response = await fetch("/api/samples");
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
