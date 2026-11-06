document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-current-year]").forEach((element) => {
    element.textContent = new Date().getFullYear();
  });
});

window.formatDatasetValue = (value, maximumFractionDigits = 0) =>
  new Intl.NumberFormat("en-US", { maximumFractionDigits }).format(value);

window.showToast = (message, type = "info") => {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast align-items-center text-bg-${type} border-0`;
  toast.setAttribute("role", "status");
  toast.innerHTML = '<div class="d-flex"><div class="toast-body"></div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>';
  toast.querySelector(".toast-body").textContent = message;
  container.appendChild(toast);
  const instance = new bootstrap.Toast(toast, { delay: 3500 });
  toast.addEventListener("hidden.bs.toast", () => toast.remove());
  instance.show();
};
