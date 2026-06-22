(function () {
  const SUPABASE_URL = window.SUPABASE_URL || "";
  const SUPABASE_ANON_KEY = window.SUPABASE_ANON_KEY || "";

  let clientPromise = null;

  function isConfigured() {
    return Boolean(SUPABASE_URL && SUPABASE_ANON_KEY && !SUPABASE_URL.includes("your-project"));
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) {
        resolve();
        return;
      }
      const script = document.createElement("script");
      script.src = src;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`Failed to load ${src}`));
      document.head.appendChild(script);
    });
  }

  async function getClient() {
    if (!isConfigured()) {
      throw new Error("Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY in config.js.");
    }
    if (clientPromise) return clientPromise;
    clientPromise = loadScript("https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js").then(
      () => window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY),
    );
    return clientPromise;
  }

  window.EmployerMatchSupabase = {
    isConfigured,
    getClient,
  };
})();
