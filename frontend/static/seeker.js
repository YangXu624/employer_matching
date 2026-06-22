const COMPETENCY_LABELS = {
  effective_communicator: "Effective Communicator",
  global_citizen: "Global Citizen",
  creative_innovator: "Creative Innovator",
  critical_thinker: "Critical Thinker",
  reflective_future_focused: "Reflective Future-Focused",
  career_ready: "Career Ready",
};

const COMPETENCY_ORDER = [
  "effective_communicator",
  "global_citizen",
  "creative_innovator",
  "critical_thinker",
  "reflective_future_focused",
  "career_ready",
];

let chartInstance = null;
let pollTimer = null;
let loadingElapsedTimer = null;
let loadingStartedAt = null;
let scoringInProgress = false;
let currentPassportScores = null;
let opportunitiesVisible = false;

function formatElapsed(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes > 0) return `${minutes}m ${seconds}s elapsed`;
  return `${seconds}s elapsed`;
}

function setUploadLoading(active, message = "") {
  const wrap = document.getElementById("uploadLoading");
  const text = document.getElementById("uploadLoadingText");
  if (!wrap) return;
  wrap.hidden = !active;
  if (text) text.textContent = message || "Working…";
}

async function fetchJson(url, options = {}, timeoutMs = 30000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `Request failed (${response.status})`);
    }
    return payload;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Backend request timed out. Is the API running on port 8766?");
    }
    if (error instanceof TypeError) {
      throw new Error("Cannot reach backend API at port 8766. Check that the server is running.");
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

async function checkBackendHealth(statusText) {
  try {
    await fetchJson(window.EmployerMatchAuth.apiUrl("/health"), {}, 5000);
    return true;
  } catch (error) {
    if (statusText) {
      statusText.textContent = formatError(error);
    }
    return false;
  }
}

async function fetchPassportStatusFromApi() {
  const headers = await window.EmployerMatchAuth.authHeaders();
  return fetchJson(window.EmployerMatchAuth.apiUrl("/api/seeker/passport/status"), { headers });
}

async function fetchPassportFromApi() {
  const headers = await window.EmployerMatchAuth.authHeaders();
  const payload = await fetchJson(window.EmployerMatchAuth.apiUrl("/api/seeker/passport"), { headers });
  return payload.passport;
}

function setPipelineStep(step) {
  const steps = document.querySelectorAll("#passportLoadingSteps li");
  const order = ["upload", "queue", "score", "done"];
  const activeIndex = order.indexOf(step);
  steps.forEach((item) => {
    const itemStep = item.getAttribute("data-step");
    const itemIndex = order.indexOf(itemStep);
    item.classList.remove("is-done", "is-active");
    if (itemIndex < activeIndex) item.classList.add("is-done");
    if (itemIndex === activeIndex) item.classList.add("is-active");
  });
}

function setPipelineLoading(active, { step = "upload", title, detail } = {}) {
  const panel = document.getElementById("passportLoading");
  const titleEl = document.getElementById("passportLoadingTitle");
  const detailEl = document.getElementById("passportLoadingDetail");
  const elapsedEl = document.getElementById("passportLoadingElapsed");
  const list = document.getElementById("passportList");
  const canvas = document.getElementById("passportChart");
  const statusEl = document.getElementById("passportStatus");

  if (!panel) return;

  if (active) {
    if (!loadingStartedAt) loadingStartedAt = Date.now();
    panel.hidden = false;
    if (titleEl && title) titleEl.textContent = title;
    if (detailEl && detail) detailEl.textContent = detail;
    setPipelineStep(step);
    if (list) list.hidden = true;
    if (canvas) canvas.hidden = true;
    if (statusEl) statusEl.hidden = true;

    clearInterval(loadingElapsedTimer);
    loadingElapsedTimer = setInterval(() => {
      if (elapsedEl && loadingStartedAt) {
        elapsedEl.textContent = formatElapsed(Date.now() - loadingStartedAt);
      }
    }, 1000);
    if (elapsedEl && loadingStartedAt) {
      elapsedEl.textContent = formatElapsed(Date.now() - loadingStartedAt);
    }
    return;
  }

  panel.hidden = true;
  clearInterval(loadingElapsedTimer);
  loadingElapsedTimer = null;
  loadingStartedAt = null;
  if (list) list.hidden = false;
  if (canvas) canvas.hidden = false;
  if (statusEl) statusEl.hidden = false;
  if (elapsedEl) elapsedEl.textContent = "";
}

function jobStepFromStatus(jobStatus, passportStatus) {
  if (jobStatus === "complete" || passportStatus === "complete") return "done";
  if (jobStatus === "running") return "score";
  if (jobStatus === "queued" || passportStatus === "processing") return "queue";
  return "upload";
}

function formatError(error) {
  if (!error) return "Unknown error";
  if (typeof error === "string") return error;
  return error.message || error.error_description || error.msg || JSON.stringify(error);
}

function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]),
  );
}

function coverageLabel(value) {
  if (value == null) return "resume only";
  const pct = Math.round(Number(value) * 100);
  if (pct >= 50) return `${pct}% coverage`;
  return `${pct}% coverage (limited)`;
}

function computeMatchScore(seekerScores, weights) {
  const totalWeight = COMPETENCY_ORDER.reduce((sum, key) => sum + Number(weights[key] || 0), 0);
  if (totalWeight <= 0) return null;
  const weighted = COMPETENCY_ORDER.reduce(
    (sum, key) => sum + Number(weights[key] || 0) * Number(seekerScores[key] || 0),
    0,
  );
  return Math.round((weighted / totalWeight) * 10) / 10;
}

function updateOpportunitiesUi(passport) {
  const showButton = document.getElementById("showOpportunitiesButton");
  const jobsSection = document.getElementById("jobsSection");

  if (passport.status === "complete" && passport.scores) {
    currentPassportScores = passport.scores;
    if (showButton) showButton.hidden = false;
  } else {
    currentPassportScores = null;
    opportunitiesVisible = false;
    if (showButton) showButton.hidden = true;
    if (jobsSection) jobsSection.hidden = true;
  }
}

function renderPassport(passport) {
  const section = document.getElementById("passportSection");
  const list = document.getElementById("passportList");
  const statusEl = document.getElementById("passportStatus");
  section.hidden = false;
  list.innerHTML = "";
  updateOpportunitiesUi(passport);

  const scores = passport.scores || {};
  const details = passport.details || {};

  if (passport.status === "processing") {
    setPipelineLoading(true, {
      step: jobStepFromStatus(passport.job?.status, passport.status),
      title: "Building your competency passport…",
      detail:
        "The AI pipeline is reading your resume and scoring all six competencies. This usually takes 1–2 minutes.",
    });
    statusEl.textContent = "";
    return;
  }

  setPipelineLoading(false);

  if (passport.status === "failed") {
    statusEl.textContent = passport.error || passport.job?.error || "Scoring failed. Upload your resume again.";
    return;
  }
  if (passport.status !== "complete") {
    statusEl.textContent = "Upload a resume to generate your passport.";
    return;
  }

  statusEl.textContent = "Your latest competency scores (0–100). Finish reviewing, then see matched roles.";

  const labels = [];
  const dataPoints = [];

  COMPETENCY_ORDER.forEach((id) => {
    const score = Math.round(Number(scores[id] || 0));
    const detail = details[id] || {};
    labels.push(id.slice(0, 3).toUpperCase());
    dataPoints.push(score);

    const row = document.createElement("article");
    row.className = "metric-row passport-row";
    row.innerHTML = `
      <header>
        <span>${COMPETENCY_LABELS[id]}</span>
        <strong>${score}</strong>
      </header>
      <div class="metric-meta">${coverageLabel(detail.data_coverage)} · ${escapeHtml(detail.source || "docs")}</div>
      ${detail.reasoning ? `<details class="passport-reason"><summary>Reasoning</summary><p>${escapeHtml(detail.reasoning)}</p></details>` : ""}
    `;
    list.appendChild(row);
  });

  const canvas = document.getElementById("passportChart");
  if (chartInstance) chartInstance.destroy();
  chartInstance = new Chart(canvas, {
    type: "radar",
    data: {
      labels,
      datasets: [
        {
          label: "Passport score",
          data: dataPoints,
          backgroundColor: "rgba(70, 60, 140, 0.2)",
          borderColor: "rgba(70, 60, 140, 1)",
          pointBackgroundColor: "rgba(70, 60, 140, 1)",
        },
      ],
    },
    options: {
      scales: { r: { beginAtZero: true, max: 100, ticks: { display: false } } },
      plugins: { legend: { display: false } },
    },
  });
}

async function pollJobStatus(statusText, uploadButton) {
  clearInterval(pollTimer);

  const tick = async () => {
    try {
      const payload = await fetchPassportStatusFromApi();
      const jobStatus = payload.job?.status;
      const passport = payload.passport || {};

      if (
        jobStatus === "complete" ||
        jobStatus === "failed" ||
        passport.status === "complete" ||
        passport.status === "failed"
      ) {
        clearInterval(pollTimer);
        scoringInProgress = false;
        setUploadLoading(false);
        if (uploadButton) {
          uploadButton.disabled = false;
          uploadButton.textContent = "Upload and score";
        }
        renderPassport({ ...passport, error: payload.job?.error, job: payload.job });
        if (jobStatus === "complete" || passport.status === "complete") {
          setPipelineStep("done");
          statusText.textContent = "Passport ready. Click Show opportunities to see matched jobs.";
        } else {
          statusText.textContent = payload.job?.error || passport.error || "Scoring failed. Upload again.";
        }
        return;
      }

      const step = jobStepFromStatus(jobStatus, passport.status);
      setPipelineLoading(true, {
        step,
        title:
          step === "score"
            ? "AI is scoring your competencies…"
            : "Building your competency passport…",
        detail:
          step === "score"
            ? "Running the passport agent on your resume. Check the backend terminal (port 8766) for live logs."
            : "Your resume is queued for scoring. This usually takes 1–2 minutes.",
      });
      statusText.textContent = step === "score" ? "Scoring in progress…" : "Waiting for scoring to start…";
    } catch (error) {
      clearInterval(pollTimer);
      scoringInProgress = false;
      setPipelineLoading(false);
      setUploadLoading(false);
      if (uploadButton) {
        uploadButton.disabled = false;
        uploadButton.textContent = "Upload and score";
      }
      statusText.textContent = formatError(error);
    }
  };

  await tick();
  pollTimer = setInterval(tick, 3000);
}

async function loadRankedOpportunities() {
  const jobsList = document.getElementById("jobsList");
  const jobDetail = document.getElementById("jobDetail");
  const jobsSection = document.getElementById("jobsSection");
  if (!jobsList || !currentPassportScores) return;

  jobsSection.hidden = false;
  jobsList.classList.add("empty-list");
  jobsList.textContent = "Loading opportunities…";
  jobDetail.hidden = true;

  try {
    const client = await window.EmployerMatchSupabase.getClient();
    const { data: jobs, error } = await client
      .from("employer_jobs")
      .select("id, title, jd_text, weights, created_at")
      .eq("status", "published")
      .order("created_at", { ascending: false });
    if (error) throw error;

    const ranked = (jobs || [])
      .map((job) => ({
        ...job,
        matchScore: computeMatchScore(currentPassportScores, job.weights || {}),
      }))
      .filter((job) => job.matchScore != null)
      .sort((a, b) => b.matchScore - a.matchScore);

    jobsList.innerHTML = "";
    if (!ranked.length) {
      jobsList.textContent =
        "No scored employer jobs yet. Ask an employer to publish a job (Save Scores on their dashboard).";
      return;
    }

    jobsList.classList.remove("empty-list");
    ranked.forEach((job, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "item-card opportunity-card";
      button.innerHTML = `
        <div class="opportunity-head">
          <strong>#${index + 1} · ${escapeHtml(job.title)}</strong>
          <span class="candidate-score">${job.matchScore.toFixed(1)} / 100</span>
        </div>
        <span class="opportunity-meta">Employer fit score · click to read full JD</span>
      `;
      button.addEventListener("click", () => {
        document.getElementById("jobDetailTitle").textContent = job.title;
        document.getElementById("jobDetailMatch").textContent = `Your fit score: ${job.matchScore.toFixed(1)} / 100`;
        document.getElementById("jobDetailBody").textContent = job.jd_text;
        jobDetail.hidden = false;
        jobDetail.scrollIntoView({ behavior: "smooth" });
      });
      jobsList.appendChild(button);
    });

    jobsSection.scrollIntoView({ behavior: "smooth" });
  } catch (error) {
    jobsList.classList.add("empty-list");
    jobsList.textContent = formatError(error);
  }
}

async function uploadAndScore(file, statusText, uploadButton) {
  const client = await window.EmployerMatchSupabase.getClient();
  const session = await window.EmployerMatchAuth.getSession();
  if (!session) throw new Error("Not signed in.");

  if (file.size > 5 * 1024 * 1024) {
    throw new Error("Resume must be 5 MB or smaller.");
  }
  if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
    throw new Error("Please upload a PDF resume.");
  }

  const backendOk = await checkBackendHealth(statusText);
  if (!backendOk) {
    scoringInProgress = false;
    throw new Error("Backend API is not reachable on port 8766.");
  }

  document.getElementById("passportSection").hidden = false;
  document.getElementById("jobsSection").hidden = true;
  document.getElementById("showOpportunitiesButton").hidden = true;
  opportunitiesVisible = false;
  scoringInProgress = true;
  loadingStartedAt = Date.now();

  statusText.textContent = "Uploading resume…";
  setUploadLoading(true, "Uploading resume to secure storage…");
  uploadButton.disabled = true;
  uploadButton.textContent = "Uploading…";

  const path = `${session.user.id}/resume.pdf`;
  const { error: uploadError } = await client.storage.from("resumes").upload(path, file, {
    upsert: true,
    contentType: "application/pdf",
  });
  if (uploadError) throw uploadError;

  statusText.textContent = "Starting passport scoring…";
  setUploadLoading(true, "Starting scoring job on the backend…");
  uploadButton.textContent = "Scoring…";
  setPipelineLoading(true, {
    step: "upload",
    title: "Resume uploaded — starting passport pipeline…",
    detail: "Connecting to the scoring backend. Step indicators below show progress.",
  });
  document.getElementById("passportSection").scrollIntoView({ behavior: "smooth", block: "start" });

  const headers = await window.EmployerMatchAuth.authHeaders({ "Content-Type": "application/json" });
  await fetchJson(window.EmployerMatchAuth.apiUrl("/api/seeker/passport"), {
    method: "POST",
    headers,
    body: JSON.stringify({ resume_path: path }),
  }, 60000);

  setUploadLoading(true, "Scoring job queued — watch the progress panel below.");
  setPipelineLoading(true, {
    step: "queue",
    title: "Passport pipeline is running…",
    detail: "The backend is processing your resume. Live logs appear in the terminal running port 8766.",
  });
  renderPassport({ status: "processing", scores: {}, job: { status: "queued" } });
  statusText.textContent = "Scoring in progress… this can take 1–2 minutes.";
  pollJobStatus(statusText, uploadButton);
}

async function initSeekerPage() {
  const ctx = await window.EmployerMatchAuth.requireRole("seeker");
  if (!ctx) return;

  const welcomeTitle = document.getElementById("welcomeTitle");
  if (welcomeTitle && ctx.profile?.display_name) {
    welcomeTitle.textContent = `My passport — ${ctx.profile.display_name}`;
  }
  window.EmployerMatchAuth.wireLogoutButton("logoutButton");

  const statusText = document.getElementById("statusText");
  const uploadButton = document.getElementById("uploadButton");
  const resumeInput = document.getElementById("resumeInput");
  const showOpportunitiesButton = document.getElementById("showOpportunitiesButton");

  showOpportunitiesButton?.addEventListener("click", async () => {
    if (!currentPassportScores) {
      statusText.textContent = "Complete your passport first.";
      return;
    }
    showOpportunitiesButton.disabled = true;
    showOpportunitiesButton.textContent = "Loading…";
    await loadRankedOpportunities();
    opportunitiesVisible = true;
    showOpportunitiesButton.disabled = false;
    showOpportunitiesButton.textContent = "Refresh opportunities";
  });

  const backendOk = await checkBackendHealth(statusText);
  if (!backendOk) return;

  try {
    const statusPayload = await fetchPassportStatusFromApi();
    const passport = statusPayload.passport;
    renderPassport({ ...passport, job: statusPayload.job });

    if (passport.status === "processing") {
      scoringInProgress = true;
      if (uploadButton) {
        uploadButton.disabled = true;
        uploadButton.textContent = "Scoring…";
      }
      setUploadLoading(true, "Passport scoring in progress…");
      loadingStartedAt = Date.now();
      statusText.textContent = "Scoring in progress…";
      pollJobStatus(statusText, uploadButton);
    } else if (passport.status === "failed") {
      statusText.textContent =
        statusPayload.job?.error || "Previous scoring failed. Upload your resume again.";
    } else if (passport.status === "complete") {
      statusText.textContent = "Passport ready. Click Show opportunities to see matched jobs.";
    }
  } catch (error) {
    statusText.textContent = formatError(error);
  }

  resumeInput?.addEventListener("change", () => {
    const file = resumeInput.files?.[0];
    statusText.textContent = file ? `Selected: ${file.name}` : "";
  });

  uploadButton?.addEventListener("click", async () => {
    const file = resumeInput.files?.[0];
    if (!file) {
      statusText.textContent = "Choose a PDF resume first.";
      return;
    }
    try {
      await uploadAndScore(file, statusText, uploadButton);
    } catch (error) {
      scoringInProgress = false;
      setPipelineLoading(false);
      setUploadLoading(false);
      statusText.textContent = formatError(error);
    } finally {
      if (!scoringInProgress && uploadButton) {
        uploadButton.disabled = false;
        uploadButton.textContent = "Upload and score";
      }
    }
  });
}

initSeekerPage();
