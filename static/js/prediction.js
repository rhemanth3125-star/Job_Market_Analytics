document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("predictionForm");
  const button = document.getElementById("predictButton");
  const errorBox = document.getElementById("predictionError");
  const result = document.getElementById("estimateResult");
  const placeholder = document.getElementById("estimatePlaceholder");
  const skills = {
    python: "skillPython",
    sql: "skillSql",
    machineLearning: "skillMachineLearning",
    deepLearning: "skillDeepLearning",
    cloud: "skillCloud",
  };
  const displaySkills = {
    python: "Python",
    sql: "SQL",
    machineLearning: "Machine learning",
    deepLearning: "Deep learning",
    cloud: "Cloud computing",
  };

  const addDetail = (container, label, value) => {
    const wrapper = document.createElement("div");
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = label;
    description.textContent = value;
    wrapper.append(term, description);
    container.appendChild(wrapper);
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.classList.add("d-none");
    form.classList.add("was-validated");
    if (!form.checkValidity()) return;

    button.disabled = true;
    button.querySelector(".button-label").classList.add("d-none");
    button.querySelector(".button-loading").classList.remove("d-none");
    const payload = {
      jobRole: document.getElementById("jobRole").value,
      country: document.getElementById("country").value,
      experienceLevel: document.getElementById("experienceLevel").value,
      yearsExperience: Number(document.getElementById("yearsExperience").value),
      skills: Object.fromEntries(
        Object.entries(skills).map(([key, id]) => [key, document.getElementById(id).checked]),
      ),
    };

    try {
      const response = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Prediction could not be completed.");
      const prediction = data.prediction;
      document.getElementById("predictedSalary").textContent = window.formatDatasetValue(prediction.predictedSalary, 2);
      document.getElementById("estimateNotice").textContent = data.estimateNotice;
      const details = document.getElementById("resultDetails");
      details.replaceChildren();
      addDetail(details, "Job role", prediction.jobRole);
      addDetail(details, "Country", prediction.country);
      addDetail(details, "Experience", `${prediction.experienceLevel} · ${window.formatDatasetValue(prediction.yearsExperience)} years`);
      const selectedSkills = Object.entries(prediction.skills).filter(([, enabled]) => enabled).map(([key]) => displaySkills[key]);
      addDetail(details, "Skills", selectedSkills.length ? selectedSkills.join(", ") : "None selected");
      placeholder.classList.add("d-none");
      result.classList.remove("d-none");
      window.showToast("Prediction saved to your history.", "success");
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.classList.remove("d-none");
    } finally {
      button.disabled = false;
      button.querySelector(".button-label").classList.remove("d-none");
      button.querySelector(".button-loading").classList.add("d-none");
    }
  });
});
