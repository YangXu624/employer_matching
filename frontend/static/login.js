(function () {
  let mode = "signin";
  let config = null;

  async function redirectIfSignedIn() {
    const session = await window.EmployerMatchAuth.getSession();
    if (!session) return;
    const profile = await window.EmployerMatchAuth.getProfile();
    if (profile?.role === config.role) {
      window.location.href = config.dashboardPath;
    } else if (profile) {
      window.location.href = profile.role === "seeker" ? "/seeker" : "/employer";
    }
  }

  function init(pageConfig) {
    config = pageConfig;
    const form = document.getElementById("authForm");
    const statusText = document.getElementById("statusText");
    const submitButton = document.getElementById("submitButton");
    const toggleModeButton = document.getElementById("toggleModeButton");
    const displayNameInput = document.getElementById("displayName");

    if (!window.EmployerMatchSupabase.isConfigured()) {
      statusText.textContent = "Configure SUPABASE_URL and SUPABASE_ANON_KEY in config.js.";
      return;
    }

    redirectIfSignedIn();

    toggleModeButton.addEventListener("click", () => {
      mode = mode === "signin" ? "signup" : "signin";
      submitButton.textContent = mode === "signin" ? "Sign in" : "Create account";
      toggleModeButton.textContent =
        mode === "signin" ? "Need an account? Sign up" : "Already have an account? Sign in";
      displayNameInput.closest("label")?.previousElementSibling?.classList;
      displayNameInput.parentElement?.previousElementSibling;
      displayNameInput.style.display = mode === "signup" ? "block" : "none";
      const nameLabel = document.querySelector('label[for="displayName"]');
      if (nameLabel) nameLabel.style.display = mode === "signup" ? "block" : "none";
    });

    displayNameInput.style.display = "none";
    const nameLabel = document.querySelector('label[for="displayName"]');
    if (nameLabel) nameLabel.style.display = "none";

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      submitButton.disabled = true;
      statusText.textContent = mode === "signin" ? "Signing in..." : "Creating account...";
      try {
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;
        const displayName = displayNameInput.value.trim();
        if (mode === "signup") {
          await window.EmployerMatchAuth.signUp(email, password, config.role, displayName);
          statusText.textContent = "Account created. Signing in...";
        }
        await window.EmployerMatchAuth.signIn(email, password);
        window.location.href = config.dashboardPath;
      } catch (error) {
        statusText.textContent = error.message || "Authentication failed.";
      } finally {
        submitButton.disabled = false;
      }
    });
  }

  window.LoginPage = { init };
})();
