const form = document.getElementById("bug-form");
const submitBtn = document.getElementById("submit-btn");
const resultPanel = document.getElementById("result-panel");
const severityBadge = document.getElementById("severity-badge");
const recommendationText = document.getElementById("recommendation-text");
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
    recommendationText.textContent = data.recommendation;
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
