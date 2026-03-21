/* ===================================================================
   MediSync - Global Application JS
   Handles: real-time clock, notifications, logout, toasts, modals
   =================================================================== */

// --- Global API Configuration ---
// Ensure all fetch requests send cookies for cross-origin authentication
const originalFetch = window.fetch;
window.fetch = function() {
    let [resource, config] = arguments;
    if (!config) {
        config = {};
    }
    if (config.credentials === undefined) {
        config.credentials = 'include';
    }
    return originalFetch(resource, config);
};

window.API_BASE = (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost')
  ? 'http://127.0.0.1:5000'
  : 'https://medisync-yvp7.onrender.com';

// --- Real-time Clock ---
function updateClock() {
  const now = new Date();
  const dateEl = document.getElementById("headerDate");
  const timeEl = document.getElementById("headerTime");
  if (dateEl) {
    dateEl.textContent = now.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }
  if (timeEl) {
    timeEl.textContent = now.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }
}
setInterval(updateClock, 1000);
updateClock();

// --- Load User Info ---
async function loadUserInfo() {
  try {
    const res = await fetch(window.API_BASE + "/api/me");
    if (!res.ok) return;
    const user = await res.json();
    const nameEl = document.getElementById("headerUserName");
    if (nameEl) nameEl.textContent = user.full_name || user.username;
    const picEl = document.getElementById("headerProfilePic");
    if (picEl && user.profile_picture) {
      picEl.innerHTML =
        '<img src="' + user.profile_picture + '" alt="Profile">';
    }
  } catch (e) {
    /* ignore */
  }
}
loadUserInfo();

// --- Notifications ---
let notifOpen = false;

async function loadNotifications() {
  try {
    const res = await fetch(window.API_BASE + "/api/notifications");
    if (!res.ok) return;
    const notifs = await res.json();
    const badge = document.getElementById("notifBadge");
    const unread = notifs.filter((n) => !n.is_read).length;
    if (badge) {
      badge.textContent = unread;
      badge.style.display = unread > 0 ? "flex" : "none";
    }
    renderNotifications(notifs);
  } catch (e) {
    /* ignore */
  }
}

function renderNotifications(notifs) {
  const list = document.getElementById("notifList");
  if (!list) return;
  if (notifs.length === 0) {
    list.innerHTML =
      '<div class="empty-state" style="padding:32px;"><div class="empty-title">No notifications</div></div>';
    return;
  }
  list.innerHTML = notifs
    .map((n) => {
      const date = new Date(n.created_at);
      const timeAgo = getTimeAgo(date);
      return (
        '<div class="notif-item ' +
        (n.is_read ? "" : "unread") +
        '" data-id="' +
        n.id +
        '">' +
        '<div class="notif-dot ' +
        n.type +
        '"></div>' +
        '<div><div class="notif-text">' +
        escapeHtml(n.message) +
        "</div>" +
        '<div class="notif-time">' +
        timeAgo +
        "</div></div></div>"
      );
    })
    .join("");
}

function getTimeAgo(date) {
  const diff = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diff < 60) return "Just now";
  if (diff < 3600) return Math.floor(diff / 60) + "m ago";
  if (diff < 86400) return Math.floor(diff / 3600) + "h ago";
  return Math.floor(diff / 86400) + "d ago";
}

const notifBtn = document.getElementById("notifBtn");
const notifPopup = document.getElementById("notifPopup");
if (notifBtn && notifPopup) {
  notifBtn.addEventListener("click", function (e) {
    e.stopPropagation();
    notifOpen = !notifOpen;
    notifPopup.classList.toggle("show", notifOpen);
  });
  document.addEventListener("click", function (e) {
    if (
      notifOpen &&
      !notifPopup.contains(e.target) &&
      !notifBtn.contains(e.target)
    ) {
      notifOpen = false;
      notifPopup.classList.remove("show");
    }
  });
}

const markAllBtn = document.getElementById("markAllReadBtn");
if (markAllBtn) {
  markAllBtn.addEventListener("click", async function () {
    await fetch(window.API_BASE + "/api/notifications/read-all", { method: "PUT" });
    loadNotifications();
  });
}

loadNotifications();
setInterval(loadNotifications, 30000);

// --- Logout ---
const logoutTriggers = document.querySelectorAll("#sidebarLogout");
const logoutModal = document.getElementById("logoutModal");
const logoutNo = document.getElementById("logoutNo");
const logoutYes = document.getElementById("logoutYes");

logoutTriggers.forEach(function (el) {
  el.addEventListener("click", function (e) {
    e.preventDefault();
    if (logoutModal) logoutModal.classList.add("show");
  });
});
if (logoutNo)
  logoutNo.addEventListener("click", function () {
    logoutModal.classList.remove("show");
  });
if (logoutYes) {
  logoutYes.addEventListener("click", async function () {
    await fetch(window.API_BASE + "/api/logout", { method: "POST" });
    window.location.href = "/login";
  });
}

// --- Sidebar Toggle ---
const sidebarToggleBtn = document.getElementById("sidebarToggle");
const appLayout = document.querySelector(".app-layout");
const mobileToggle = document.getElementById("hamburgerMenu");
const sidebar = document.querySelector(".sidebar");
const sidebarOverlay = document.getElementById("sidebarOverlay");

if (sidebarToggleBtn && appLayout) {
  sidebarToggleBtn.addEventListener("click", function () {
    appLayout.classList.toggle("collapsed");
    localStorage.setItem("sidebarCollapsed", appLayout.classList.contains("collapsed"));
  });
}

if (mobileToggle && sidebar && sidebarOverlay) {
  mobileToggle.addEventListener("click", function () {
    sidebar.classList.add("mobile-open");
    sidebarOverlay.classList.add("active");
  });
  sidebarOverlay.addEventListener("click", function () {
    sidebar.classList.remove("mobile-open");
    sidebarOverlay.classList.remove("active");
  });
  // Also close when a link is clicked
  sidebar.querySelectorAll(".sidebar-nav a").forEach(link => {
    link.addEventListener("click", () => {
      sidebar.classList.remove("mobile-open");
      sidebarOverlay.classList.remove("active");
    });
  });
}

// --- Modal Utility ---
function openModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.add("show");
}
function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove("show");
}

// --- Toast Utility ---
function showToast(message, type) {
  type = type || "success";
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className =
    "toast" +
    (type === "error" ? " error" : type === "warning" ? " warning" : "");
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(function () {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(40px)";
    setTimeout(function () {
      toast.remove();
    }, 300);
  }, 3500);
}

// --- Global Utilities ---
window.escapeHtml = function (str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
};

window.formatDate = function (dateStr) {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

window.formatDateTime = function (dateStr) {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  return d.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

// --- Badge HTML ---
function statusBadge(status) {
  var cls = "badge-active";
  if (status === "Expired") cls = "badge-expired";
  else if (status === "Near Expiry") cls = "badge-near-expiry";
  else if (status === "Discarded") cls = "badge-discarded";
  else if (status === "Pending") cls = "badge-pending";
  else if (status === "Fulfilled") cls = "badge-fulfilled";
  return '<span class="badge ' + cls + '">' + escapeHtml(status) + "</span>";
}
window.statusBadge = statusBadge;

// --- Remove Preload Transition Lock ---
window.addEventListener("load", function () {
  document.body.classList.remove("preload");
});
