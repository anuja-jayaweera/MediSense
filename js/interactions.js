(function () {
  const parentDoc = window.parent.document;

  // Guard against re-running this whole setup on every Streamlit
  // rerun — the observer below already keeps things in sync.
  if (parentDoc.__msInteractionsInit) return;
  parentDoc.__msInteractionsInit = true;

  // ---------------- Toast ----------------
  function showToast(message) {
    let toast = parentDoc.querySelector(".ms-toast");
    if (!toast) {
      toast = parentDoc.createElement("div");
      toast.className = "ms-toast";
      parentDoc.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add("ms-toast-show");
    clearTimeout(toast._msHideTimer);
    toast._msHideTimer = setTimeout(() => {
      toast.classList.remove("ms-toast-show");
    }, 1800);
  }

  // ---------------- Click-to-copy on card values ----------------
  function wireCardCopy(card) {
    if (card.dataset.msCopyWired) return;
    const valueEl = card.querySelector(".ms-card-value");
    if (!valueEl) return;
    card.dataset.msCopyWired = "true";

    valueEl.style.cursor = "pointer";
    valueEl.title = "Click to copy";
    valueEl.addEventListener("click", () => {
      const titleEl = card.querySelector(".ms-card-title");
      const text = valueEl.textContent.trim();
      const label = titleEl ? titleEl.textContent.trim() : "Value";

      const copy = navigator.clipboard && navigator.clipboard.writeText
        ? navigator.clipboard.writeText(text)
        : Promise.reject();

      copy
        .then(() => showToast(`Copied ${label}: ${text}`))
        .catch(() => showToast("Couldn't copy — try selecting the text manually"));
    });
  }

  // ---------------- Heartbeat glow on "Attention" cards ----------------
  function wireAttentionPulse(card) {
    const statusEl = card.querySelector(".ms-card-status");
    if (statusEl && statusEl.textContent.toUpperCase().includes("ATTENTION")) {
      card.classList.add("ms-pulse");
    }
  }

  // ---------------- Count-up animation for the top metrics ----------------
  function animateMetric(el) {
    if (el.dataset.msAnimated) return;
    const target = parseInt(el.textContent.replace(/[^\d-]/g, ""), 10);
    if (Number.isNaN(target)) return;
    el.dataset.msAnimated = "true";

    const duration = 550;
    const start = performance.now();

    function step(now) {
      const progress = Math.min((now - start) / duration, 1);
      el.textContent = String(Math.round(target * progress));
      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        el.textContent = String(target);
      }
    }
    requestAnimationFrame(step);
  }

  // ---------------- "/" jumps focus to the search box ----------------
  parentDoc.addEventListener("keydown", (e) => {
    const active = parentDoc.activeElement;
    const isTyping = active && (active.tagName === "INPUT" || active.tagName === "TEXTAREA");
    if (e.key === "/" && !isTyping) {
      const input = parentDoc.querySelector('input[type="text"]');
      if (input) {
        e.preventDefault();
        input.focus();
      }
    }
  });

  // ---------------- Floating back-to-top button ----------------
  function ensureBackToTop() {
    if (parentDoc.querySelector(".ms-back-to-top")) return;
    const btn = parentDoc.createElement("button");
    btn.className = "ms-back-to-top";
    btn.textContent = "↑";
    btn.title = "Back to top";
    btn.addEventListener("click", () => {
      const main = parentDoc.querySelector('section[data-testid="stMain"]') || parentDoc.body;
      main.scrollTo({ top: 0, behavior: "smooth" });
    });
    parentDoc.body.appendChild(btn);
  }

  // ---------------- Scan the DOM and wire up anything new ----------------
  function scan() {
    parentDoc.querySelectorAll(".ms-card").forEach((card) => {
      wireCardCopy(card);
      wireAttentionPulse(card);
    });
    parentDoc.querySelectorAll('[data-testid="stMetricValue"]').forEach(animateMetric);
    ensureBackToTop();
  }

  scan();

  // Streamlit rewrites large chunks of the DOM on every rerun
  // (new search results, a fresh analysis, etc.) — watch for that
  // and re-wire anything new instead of re-injecting this script.
  const observer = new MutationObserver(() => scan());
  observer.observe(parentDoc.body, { childList: true, subtree: true });
})();