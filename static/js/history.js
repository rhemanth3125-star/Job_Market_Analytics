document.addEventListener("DOMContentLoaded", () => {
  const rows = document.getElementById("historyRows");
  const empty = document.getElementById("historyEmpty");
  const count = document.getElementById("recordCount");
  const errorBox = document.getElementById("historyError");
  const clearButton = document.getElementById("clearHistoryButton");
  const search = document.getElementById("historySearch");
  const filter = document.getElementById("experienceFilter");
  let debounceTimer;

  const skillLabels = [
    ["python", "Python"],
    ["sql", "SQL"],
    ["machineLearning", "ML"],
    ["deepLearning", "Deep learning"],
    ["cloud", "Cloud"],
  ];

  const showError = (message) => {
    errorBox.textContent = message;
    errorBox.classList.remove("d-none");
  };

  const skillCell = (skills) => {
    const cell = document.createElement("td");
    const enabled = skillLabels.filter(([key]) => skills[key]);
    if (!enabled.length) {
      cell.textContent = "—";
      return cell;
    }
    enabled.forEach(([, label]) => {
      const chip = document.createElement("span");
      chip.className = "skill-chip";
      chip.textContent = label;
      cell.appendChild(chip);
    });
    return cell;
  };

  const renderRecord = (record) => {
    const row = document.createElement("tr");
    const role = document.createElement("td");
    role.className = "role-cell";
    role.textContent = record.jobRole;
    row.appendChild(role);
    [record.country].forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.appendChild(cell);
    });
    const experience = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = "experience-pill";
    badge.textContent = record.experienceLevel;
    experience.appendChild(badge);
    row.appendChild(experience);
    const years = document.createElement("td");
    years.textContent = `${window.formatDatasetValue(record.yearsExperience)} yrs`;
    row.appendChild(years);
    row.appendChild(skillCell(record.skills || {}));
    const salary = document.createElement("td");
    salary.className = "salary-cell";
    salary.textContent = window.formatDatasetValue(record.predictedSalary, 2);
    row.appendChild(salary);
    const date = document.createElement("td");
    const parsedDate = new Date(record.createdAt);
    date.textContent = Number.isNaN(parsedDate.getTime()) ? "Unknown" : parsedDate.toLocaleString();
    row.appendChild(date);
    const action = document.createElement("td");
    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "delete-record";
    deleteButton.dataset.deleteId = record.id;
    deleteButton.setAttribute("aria-label", `Delete ${record.jobRole} prediction`);
    deleteButton.innerHTML = '<i class="bi bi-trash3"></i>';
    action.appendChild(deleteButton);
    row.appendChild(action);
    return row;
  };

  const loadHistory = async () => {
    errorBox.classList.add("d-none");
    rows.replaceChildren();
    const loading = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 8;
    cell.className = "empty-state";
    cell.textContent = "Loading your saved predictions…";
    loading.appendChild(cell);
    rows.appendChild(loading);
    const params = new URLSearchParams();
    if (search.value.trim()) params.set("search", search.value.trim());
    if (filter.value) params.set("experienceLevel", filter.value);
    try {
      const response = await fetch(`/api/history?${params}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Prediction history could not be loaded.");
      rows.replaceChildren();
      count.textContent = window.formatDatasetValue(data.records.length);
      clearButton.disabled = data.records.length === 0;
      empty.classList.toggle("d-none", data.records.length !== 0);
      data.records.forEach((record) => rows.appendChild(renderRecord(record)));
    } catch (error) {
      rows.replaceChildren();
      count.textContent = "—";
      clearButton.disabled = true;
      empty.classList.add("d-none");
      showError(error.message);
    }
  };

  search.addEventListener("input", () => {
    window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(loadHistory, 250);
  });
  filter.addEventListener("change", loadHistory);

  rows.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-delete-id]");
    if (!button) return;
    if (!window.confirm("Delete this prediction from your history?")) return;
    button.disabled = true;
    try {
      const response = await fetch(`/api/history/${encodeURIComponent(button.dataset.deleteId)}`, { method: "DELETE" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Prediction could not be deleted.");
      window.showToast("Prediction deleted.", "success");
      await loadHistory();
    } catch (error) {
      button.disabled = false;
      showError(error.message);
    }
  });

  clearButton.addEventListener("click", async () => {
    if (!window.confirm("Permanently clear all saved prediction history? This cannot be undone.")) return;
    clearButton.disabled = true;
    try {
      const response = await fetch("/api/history", { method: "DELETE" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "History could not be cleared.");
      window.showToast(`${window.formatDatasetValue(data.deletedCount)} prediction(s) cleared.`, "success");
      await loadHistory();
    } catch (error) {
      showError(error.message);
      clearButton.disabled = false;
    }
  });

  loadHistory();
});
