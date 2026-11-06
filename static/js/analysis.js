document.addEventListener("DOMContentLoaded", async () => {
  const number = window.formatDatasetValue;
  try {
    const response = await fetch("/api/analytics");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Job market analysis could not be loaded.");
    if (!window.Chart) throw new Error("Chart library did not load. Check your internet connection and reload.");

    document.getElementById("leadingRole").textContent = data.topRoles.labels[0] || "No data";
    const leadingSkill = data.skillDemand.details[0];
    document.getElementById("leadingSkill").textContent = leadingSkill ? `${leadingSkill.skill} · ${number(leadingSkill.count)}` : "No data";
    document.getElementById("leadingCountry").textContent = data.opportunitiesByCountry.labels[0] || "No data";

    Chart.defaults.font.family = '"DM Sans", sans-serif';
    Chart.defaults.color = "#77859b";
    Chart.defaults.font.size = 10;
    const barOptions = (horizontal = false) => ({
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: horizontal ? "y" : "x",
      plugins: { legend: { display: false }, tooltip: { backgroundColor: "#142442", padding: 11, cornerRadius: 8 } },
      scales: horizontal ? {
        x: { grid: { color: "#eff2f7" }, border: { display: false }, ticks: { precision: 0 } },
        y: { grid: { display: false }, border: { display: false }, ticks: { font: { size: 9 } } },
      } : {
        x: { grid: { display: false }, border: { display: false } },
        y: { grid: { color: "#eff2f7" }, border: { display: false }, ticks: { precision: 0 } },
      },
    });
    const chart = (id, type, labels, values, color, horizontal = false) => {
      new Chart(document.getElementById(id), {
        type,
        data: { labels, datasets: [{ data: values, backgroundColor: color, borderRadius: type === "bar" ? 5 : 0, borderWidth: 0, maxBarThickness: horizontal ? 20 : 34, tension: .35 }] },
        options: {
          ...barOptions(horizontal),
          plugins: { ...barOptions(horizontal).plugins, tooltip: { ...barOptions(horizontal).plugins.tooltip, callbacks: { label: (context) => ` ${number(context.parsed[horizontal ? "x" : "y"] ?? context.parsed)}` } } },
        },
      });
    };
    chart("analysisRolesChart", "bar", data.topRoles.labels, data.topRoles.values, "#5080e8", true);
    chart("programmingLanguagesChart", "bar", data.topProgrammingLanguages.map((item) => item.skill), data.topProgrammingLanguages.map((item) => item.demand), ["#3976ec", "#30b69e"], true);
    chart("analysisSkillsChart", "bar", data.topLanguages.map((item) => item.skill), data.topLanguages.map((item) => item.demand), ["#3976ec", "#30b69e", "#8666e8", "#f0a24b", "#e66a8a"], true);
    chart("opportunitiesChart", "bar", data.opportunitiesByCountry.labels, data.opportunitiesByCountry.values, "#39a99b");
    new Chart(document.getElementById("experienceDistributionChart"), {
      type: "doughnut",
      data: { labels: data.experienceDistribution.labels, datasets: [{ data: data.experienceDistribution.values, backgroundColor: ["#89aaf3", "#4b79e3", "#28b59c", "#8d73dc"], borderWidth: 3, borderColor: "#fff", hoverOffset: 6 }] },
      options: { responsive: true, maintainAspectRatio: false, cutout: "66%", plugins: { legend: { position: "bottom", labels: { usePointStyle: true, pointStyle: "circle", padding: 18, font: { size: 10 } } }, tooltip: { backgroundColor: "#142442", padding: 11, cornerRadius: 8 } } },
    });

    const table = document.getElementById("skillsTable");
    table.replaceChildren();
    const maxDemand = Math.max(...data.skillDemand.details.map((item) => item.count), 1);
    data.skillDemand.details.forEach((item) => {
      const row = document.createElement("tr");
      const cells = [item.skill, number(item.count), `${number(item.percentage, 1)}%`];
      cells.forEach((value, index) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        if (index === 0) cell.className = "fw-semibold";
        row.appendChild(cell);
      });
      const demand = document.createElement("td");
      const track = document.createElement("div");
      track.className = "demand-track";
      const fill = document.createElement("span");
      fill.style.width = `${(item.count / maxDemand) * 100}%`;
      track.appendChild(fill);
      demand.appendChild(track);
      row.appendChild(demand);
      table.appendChild(row);
    });
  } catch (error) {
    document.querySelectorAll(".chart-card").forEach((card) => {
      const message = document.createElement("p");
      message.className = "text-danger small mt-3";
      message.textContent = error.message;
      card.appendChild(message);
    });
  }
});
