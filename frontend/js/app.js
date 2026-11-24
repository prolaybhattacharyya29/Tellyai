/**
 * Frontend Application Logic for AI Voice Assistant Dashboard
 */

// Initialize campaigns from window variable (injected by backend) or fetch API fallback
let campaigns = window.__INITIAL_CAMPAIGNS__ || [];
let selectedCampaign = (campaigns && campaigns.length > 0) ? campaigns[0].id : "cross_sell";
let lastClickedCampaign = selectedCampaign;

// DOM Elements
let phoneInput;
let consentCheck;
let callBtn;
let statusBanner;

function renderCampaignGrid() {
  const grid = document.getElementById("campaign-grid");
  if (!grid) return;
  grid.innerHTML = "";

  campaigns.forEach(c => {
    const isSelected = c.id === selectedCampaign;
    const justClicked = isSelected && c.id === lastClickedCampaign;
    const card = document.createElement("div");
    
    card.className = `relative p-3 sm:p-4 rounded-xl border text-left cursor-pointer transition-all duration-200 ease-out flex flex-col justify-between min-h-[96px] sm:min-h-[110px] select-none active:scale-[0.96] ${
      isSelected 
        ? "border-blue-600 bg-blue-50/50 ring-2 ring-blue-500/20 shadow-sm " + (justClicked ? "card-selected-pulse" : "")
        : "border-slate-200/90 bg-white hover:border-slate-300 hover:shadow-xs hover:-translate-y-0.5"
    }`;
    card.onclick = () => selectCampaign(c.id);

    card.innerHTML = `
      <div class="flex items-start justify-between">
        <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-lg flex items-center justify-center transition-colors duration-200 ${isSelected ? 'text-blue-600 ' + (justClicked ? 'icon-wiggle' : '') : 'text-slate-500'}">
          <i data-lucide="${c.icon}" class="w-4 h-4 sm:w-5 sm:h-5"></i>
        </div>
      </div>
      <div class="mt-2 sm:mt-2.5">
        <h4 class="font-bold text-xs sm:text-sm tracking-tight transition-colors duration-150 ${isSelected ? 'text-blue-900' : 'text-slate-900'}">${c.title}</h4>
        <p class="text-[11px] sm:text-xs text-slate-500 mt-0.5 line-clamp-1">${c.sub}</p>
      </div>
    `;
    grid.appendChild(card);
  });

  if (window.lucide) {
    lucide.createIcons();
  }
}

function selectCampaign(id) {
  lastClickedCampaign = id;
  selectedCampaign = id;
  const c = campaigns.find(item => item.id === id);
  if (c) {
    const previewBox = document.querySelector(".bg-blue-50\\/60");
    if (previewBox) {
      previewBox.classList.remove("fade-in-up");
      void previewBox.offsetWidth; // Trigger reflow for re-animation
      previewBox.classList.add("fade-in-up");
    }
    const titleEl = document.getElementById("preview-title");
    const descEl = document.getElementById("preview-desc");
    if (titleEl) titleEl.innerText = c.title;
    if (descEl) descEl.innerText = c.description || c.desc || "";
  }
  renderCampaignGrid();

  // Smoothly scroll to Step 2 on mobile devices (< 1024px)
  if (window.innerWidth < 1024) {
    setTimeout(() => {
      const step2 = document.getElementById("step-2-section");
      if (step2) {
        step2.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 150);
  }
}

function validateForm() {
  if (!phoneInput || !consentCheck || !callBtn) return;
  // Strip any non-digit character immediately
  phoneInput.value = phoneInput.value.replace(/\D/g, "");
  const phone = phoneInput.value.trim();
  const agreed = consentCheck.checked;
  
  // Valid if phone has digits and consent is checked
  if (phone.length >= 7 && agreed) {
    callBtn.disabled = false;
    callBtn.className = "w-full py-3.5 px-4 rounded-xl font-bold text-sm text-white bg-blue-600 hover:bg-blue-700 active:scale-[0.99] transition-all duration-200 flex items-center justify-center space-x-2 shadow-md shadow-blue-500/20 cursor-pointer";
  } else {
    callBtn.disabled = true;
    callBtn.className = "w-full py-3.5 px-4 rounded-xl font-bold text-sm text-white bg-slate-400 cursor-not-allowed transition-all duration-200 flex items-center justify-center space-x-2 shadow-sm";
  }
}

async function initiateCall() {
  if (!callBtn || callBtn.disabled) return;

  const prefix = document.getElementById("country-code")?.value || "+91";
  let rawPhone = phoneInput.value.trim();
  // Remove spaces or hyphens
  rawPhone = rawPhone.replace(/[\s-]/g, "");
  const fullPhone = rawPhone.startsWith("+") ? rawPhone : `${prefix}${rawPhone.replace(/^0+/, "")}`;
  const language = document.getElementById("lang-select")?.value || "English";

  callBtn.disabled = true;
  callBtn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Initiating AI Call...</span>`;
  if (window.lucide) lucide.createIcons();

  statusBanner.className = "rounded-xl p-3.5 text-xs font-medium leading-relaxed bg-blue-50 border border-blue-200 text-blue-700 flex items-center space-x-2";
  statusBanner.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin shrink-0"></i><span>Contacting AI telephony engine...</span>`;
  statusBanner.classList.remove("hidden");
  if (window.lucide) lucide.createIcons();

  try {
    const resp = await fetch("/api/trigger-call", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        campaign: selectedCampaign,
        phone: fullPhone,
        language: language
      })
    });

    const data = await resp.json();

    if (resp.ok && data.ok) {
      statusBanner.className = "rounded-xl p-4 text-xs font-medium leading-relaxed bg-emerald-50 border border-emerald-200 text-emerald-800 space-y-1";
      statusBanner.innerHTML = `
        <div class="flex items-center space-x-1.5 font-bold text-emerald-900">
          <i data-lucide="check-circle" class="w-4 h-4 text-emerald-600"></i>
          <span>Call Successfully Dispatched!</span>
        </div>
        <div>Your phone (${data.phone}) should ring in <strong>5 to 10 seconds</strong>.</div>
        <div class="text-[11px] text-emerald-700/80 mt-1">Call ID: ${data.call_id || "N/A"} · Profile: ${data.customer_name || "Demo User"}</div>
      `;
    } else {
      statusBanner.className = "rounded-xl p-3.5 text-xs font-medium leading-relaxed bg-rose-50 border border-rose-200 text-rose-700";
      statusBanner.innerHTML = `<strong>Error triggering call:</strong> ${data.error || "Please verify credentials and phone format."}`;
    }
  } catch (err) {
    statusBanner.className = "rounded-xl p-3.5 text-xs font-medium leading-relaxed bg-rose-50 border border-rose-200 text-rose-700";
    statusBanner.innerHTML = `<strong>Network error:</strong> ${err.message}`;
  } finally {
    validateForm();
    callBtn.innerHTML = `<i data-lucide="phone" class="w-4 h-4"></i><span>Call Me Now</span>`;
    if (window.lucide) lucide.createIcons();
  }
}

// Global initialization
document.addEventListener("DOMContentLoaded", async () => {
  phoneInput = document.getElementById("phone-input");
  consentCheck = document.getElementById("consent-check");
  callBtn = document.getElementById("call-btn");
  statusBanner = document.getElementById("status-banner");

  // Fallback to fetch /api/campaigns if window.__INITIAL_CAMPAIGNS__ is empty
  if (!campaigns || campaigns.length === 0) {
    try {
      const res = await fetch("/api/campaigns");
      campaigns = await res.json();
      if (campaigns && campaigns.length > 0) {
        selectedCampaign = campaigns[0].id;
        lastClickedCampaign = selectedCampaign;
      }
    } catch (e) {
      console.warn("Could not fetch /api/campaigns:", e);
    }
  }

  // Bind input validation
  if (phoneInput) {
    phoneInput.addEventListener("keydown", (e) => {
      const allowedKeys = ["Backspace", "Delete", "ArrowLeft", "ArrowRight", "Tab", "Enter"];
      if (allowedKeys.includes(e.key) || e.ctrlKey || e.metaKey) return;
      if (!/^\d$/.test(e.key)) e.preventDefault();
    });
    phoneInput.addEventListener("input", validateForm);
  }

  if (consentCheck) {
    consentCheck.addEventListener("change", validateForm);
  }

  // Render initial campaigns
  renderCampaignGrid();
  if (window.lucide) lucide.createIcons();
});
