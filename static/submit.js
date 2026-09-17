const form = document.getElementById("bug-form");
const submitBtn = document.getElementById("submit-btn");
const resultPanel = document.getElementById("result-panel");
const severityBadge = document.getElementById("severity-badge");
const recommendationFlow = document.getElementById("recommendation-flow");

// Matches the icons used in templates/icons.html, kept as plain
// SVG strings here since this file can't use Jinja macros.
const REC_ICONS = {
  root_cause: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/></svg>',
  suggested_fix: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>',
  best_practice: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>',
};
const REC_LABELS = { root_cause: "Root Cause", suggested_fix: "Suggested Fix", best_practice: "Best Practice" };
const REC_CLASS = { root_cause: "root-cause", suggested_fix: "fix", best_practice: "best-practice" };

function renderRecommendationFlow(rec) {
  const steps = ["root_cause", "suggested_fix", "best_practice"].filter(key => rec[key]);
  recommendationFlow.innerHTML = steps.map((key, i) => {
    const arrow = i > 0 ? '<div class="rec-arrow">&#8595;</div>' : "";
    return `${arrow}<div class="rec-step">
      <div class="rec-step-icon ${REC_CLASS[key]}">${REC_ICONS[key]}</div>
      <div class="rec-step-body">
        <div class="rec-step-label">${REC_LABELS[key]}</div>
        <div class="rec-step-text">${rec[key]}</div>
      </div>
    </div>`;
  }).join("");
}
const errorMsg = document.getElementById("error-msg");

const dropzone = document.getElementById("dropzone");
const screenshotInput = document.getElementById("screenshot-input");
const screenshotPreview = document.getElementById("screenshot-preview");

function showPreview(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    screenshotPreview.src = e.target.result;
    screenshotPreview.hidden = false;
  };
  reader.readAsDataURL(file);
}

// Click to browse
dropzone.addEventListener("click", () => screenshotInput.click());

screenshotInput.addEventListener("change", () => {
  if (screenshotInput.files[0]) showPreview(screenshotInput.files[0]);
});

// Drag and drop
["dragenter", "dragover"].forEach(evt => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
});
["dragleave", "drop"].forEach(evt => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  });
});
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) {
    screenshotInput.files = e.dataTransfer.files;
    showPreview(file);
  }
});

// Paste a screenshot directly, e.g. after pressing PrintScreen or
// using a snipping tool, Ctrl+V while the form is focused.
document.addEventListener("paste", (e) => {
  const items = e.clipboardData.items;
  for (const item of items) {
    if (item.type.startsWith("image/")) {
      const file = item.getAsFile();
      const dt = new DataTransfer();
      dt.items.add(file);
      screenshotInput.files = dt.files;
      showPreview(file);
      break;
    }
  }
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  errorMsg.hidden = true;
  resultPanel.hidden = true;
  submitBtn.disabled = true;
  submitBtn.textContent = "Classifying...";

  const formData = new FormData(form);

  try {
    const response = await fetch("/classify", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Something went wrong.");
    }

    severityBadge.textContent = data.severity;
    severityBadge.className = "badge " + data.severity.toLowerCase();
    renderRecommendationFlow(data.recommendation);
    resultPanel.hidden = false;
    form.reset();
    screenshotPreview.hidden = true;

  } catch (err) {
    errorMsg.textContent = err.message;
    errorMsg.hidden = false;
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Submit Report";
  }
});
