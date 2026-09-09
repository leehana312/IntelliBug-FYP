const form = document.getElementById("bug-form");
const submitBtn = document.getElementById("submit-btn");
const resultPanel = document.getElementById("result-panel");
const severityBadge = document.getElementById("severity-badge");
const recommendationText = document.getElementById("recommendation-text");
const errorMsg = document.getElementById("error-msg");

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

    // Show the result
    severityBadge.textContent = data.severity;
    severityBadge.className = "badge " + data.severity.toLowerCase();
    recommendationText.textContent = data.recommendation;
    resultPanel.hidden = false;

  } catch (err) {
    errorMsg.textContent = err.message;
    errorMsg.hidden = false;
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Classify bug";
  }
});
