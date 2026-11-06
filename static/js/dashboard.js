document.addEventListener("DOMContentLoaded", async () => {
  const number = window.formatDatasetValue;
  const colors = ["#3976ec", "#30b69e", "#8666e8", "#f0a24b", "#e66a8a", "#35a6c5", "#6dbb63", "#a483df", "#e47e48", "#54708d"];
  try {
    const response = await fetch("/api/analytics");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Analytics could not be loaded.");

    document.querySelectorAll("[data-stat]").forEach((element) => {
      const value = data.stats[element.dataset.stat];
      element.textContent = number(value);
    });

    if (!window.Chart) throw new Error("Chart library did not load. Check your internet connection and reload.");
    Chart.defaults.font.family = '"DM Sans", sans-serif';
    Chart.defaults.color = "#77859b";
    Chart.defaults.font.size = 10;

    const baseOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { backgroundColor: "#142442", padding: 11, cornerRadius: 8, titleFont: { weight: "700" }, bodyFont: { size: 10 } },
      },
      scales: {
        x: { grid: { display: false }, border: { display: false }, ticks: { maxRotation: 0 } },
        y: { grid: { color: "#eff2f7" }, border: { display: false }, ticks: { precision: 0 } },
      },
    };
    const draw = (id, type, labels, values, options = {}) => {
      const canvas = document.getElementById(id);
      if (!canvas) return;
      new Chart(canvas, {
        type,
        data: { labels, datasets: [{ data: values, backgroundColor: options.backgroundColor || "#4c80eb", borderColor: options.borderColor || "#4c80eb", borderWidth: options.borderWidth ?? 0, borderRadius: options.borderRadius ?? 5, maxBarThickness: options.maxBarThickness || 34, tension: .38, fill: type === "line" ? { target: "origin", above: "rgba(55,112,231,.09)" } : false }] },
        options: {
          ...baseOptions,
          indexAxis: options.indexAxis || "x",
          scales: options.indexAxis === "y" ? {
            x: { grid: { color: "#eff2f7" }, border: { display: false }, ticks: { precision: 0 } },
            y: { grid: { display: false }, border: { display: false }, ticks: { font: { size: 9 } } },
          } : baseOptions.scales,
          plugins: { ...baseOptions.plugins, tooltip: { ...baseOptions.plugins.tooltip, callbacks: { label: (context) => ` ${number(context.parsed[options.indexAxis === "y" ? "x" : "y"] ?? context.parsed)}` } } },
        },
      });
    };

    draw("rolesChart", "bar", data.topRoles.labels, data.topRoles.values, { indexAxis: "y", backgroundColor: "#5282e9", maxBarThickness: 18 });
    draw("skillsChart", "bar", data.skillDemand.labels, data.skillDemand.values, { indexAxis: "y", backgroundColor: colors.slice(0, data.skillDemand.values.length), maxBarThickness: 22 });
    draw("salaryChart", "bar", data.salaryDistribution.labels, data.salaryDistribution.values, { backgroundColor: "rgba(72,126,235,.78)", maxBarThickness: 38 });
    draw("countrySalaryChart", "bar", data.salaryByCountry.labels, data.salaryByCountry.values, { backgroundColor: colors.slice(0, data.salaryByCountry.values.length), maxBarThickness: 34 });
    draw("experienceChart", "line", data.experienceSalary.labels, data.experienceSalary.values, { backgroundColor: "rgba(55,112,231,.1)", borderColor: "#3472e8", borderWidth: 3, borderRadius: 0, maxBarThickness: 5 });
  } catch (error) {
    document.querySelectorAll(".chart-card").forEach((card) => {
      const message = document.createElement("p");
      message.className = "text-danger small mt-3";
      message.textContent = error.message;
      card.appendChild(message);
    });
  }
});
