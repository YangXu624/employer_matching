const API_BASE_URL = (window.EMPLOYER_MATCH_API_BASE_URL || "").replace(/\/$/, "");

function apiUrl(path) {
  return `${API_BASE_URL}${path}`;
}

function apiHeaders(extra = {}) {
  return { "ngrok-skip-browser-warning": "true", ...extra };
}

async function authHeaders(extra = {}) {
  const client = await window.EmployerMatchSupabase.getClient();
  const {
    data: { session },
  } = await client.auth.getSession();
  if (!session?.access_token) {
    throw new Error("Not signed in.");
  }
  return apiHeaders({
    Authorization: `Bearer ${session.access_token}`,
    ...extra,
  });
}

async function getSession() {
  const client = await window.EmployerMatchSupabase.getClient();
  const {
    data: { session },
  } = await client.auth.getSession();
  return session;
}

async function getProfile() {
  const session = await getSession();
  if (!session) return null;
  const client = await window.EmployerMatchSupabase.getClient();
  const { data, error } = await client.from("profiles").select("id, role, display_name").eq("id", session.user.id).maybeSingle();
  if (error) throw error;
  return data;
}

async function requireRole(expectedRole) {
  if (!window.EmployerMatchSupabase.isConfigured()) {
    document.body.innerHTML =
      '<main class="auth-shell"><p class="status-text">Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY in config.js.</p></main>';
    return null;
  }

  const session = await getSession();
  if (!session) {
    window.location.href = expectedRole === "seeker" ? "/login-seeker" : "/login-employer";
    return null;
  }

  let profile = await getProfile();
  if (!profile) {
    await new Promise((r) => setTimeout(r, 500));
    profile = await getProfile();
  }

  if (!profile) {
    window.location.href = expectedRole === "seeker" ? "/login-seeker" : "/login-employer";
    return null;
  }

  if (profile.role !== expectedRole) {
    window.location.href = profile.role === "seeker" ? "/seeker" : "/employer";
    return null;
  }

  return { session, profile };
}

async function signUp(email, password, role, displayName) {
  const client = await window.EmployerMatchSupabase.getClient();
  const { data, error } = await client.auth.signUp({
    email,
    password,
    options: {
      data: {
        role,
        display_name: displayName || email.split("@")[0],
      },
    },
  });
  if (error) throw error;
  return data;
}

async function signIn(email, password) {
  const client = await window.EmployerMatchSupabase.getClient();
  const { data, error } = await client.auth.signInWithPassword({ email, password });
  if (error) throw error;
  return data;
}

async function signOut() {
  const client = await window.EmployerMatchSupabase.getClient();
  await client.auth.signOut();
}

function wireLogoutButton(buttonId) {
  const button = document.getElementById(buttonId);
  if (!button) return;
  button.addEventListener("click", async () => {
    await signOut();
    window.location.href = "/";
  });
}

window.EmployerMatchAuth = {
  apiUrl,
  apiHeaders,
  authHeaders,
  getSession,
  getProfile,
  requireRole,
  signUp,
  signIn,
  signOut,
  wireLogoutButton,
};
