// Global API Base URL
const API_URL = "http://127.0.0.1:8000/api";

// State Management
let currentTab = "page-dashboard";
let qualityChartInstance = null;
let sseSource = null;
let scanStatusInterval = null;
let campaignStatusInterval = null;


// Pagination state for Leads
let leadsCurrentPage = 1;
const leadsPageLimit = 15;

// ==========================================
// Initialization
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  loadDashboardData();
  
  // Initial API loads
  loadSearchConfigs();
  loadSectorsDropdown();
  loadLeadsTable();
  loadSmtpSettings();
  loadCampaignsList();
  
  // Register forms and click listeners
  registerEventListeners();
});

// ==========================================
// Sidebar & Tab Switcher
// ==========================================
function initTabs() {
  const navItems = document.querySelectorAll(".sidebar .nav-item");
  navItems.forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const targetPageId = item.getAttribute("data-target");
      
      // Update active nav style
      navItems.forEach(nav => nav.classList.remove("active"));
      item.classList.add("active");
      
      // Toggle pages
      const pages = document.querySelectorAll(".main-content .page");
      pages.forEach(page => page.classList.remove("active"));
      document.getElementById(targetPageId).classList.add("active");
      
      currentTab = targetPageId;
      
      // Page specific onload refreshes
      if (currentTab === "page-dashboard") {
        loadDashboardData();
      } else if (currentTab === "page-search") {
        loadSearchConfigs();
      } else if (currentTab === "page-scan") {
        loadSearchConfigsForScanDropdown();
        checkScraperRunningStatus();
      } else if (currentTab === "page-leads") {
        loadSectorsDropdown();
        loadLeadsTable();
      } else if (currentTab === "page-campaign") {
        loadSmtpSettings();
        loadCampaignsList();
        updateCampaignAutoSelectCount();
      }
    });
  });
}

function registerEventListeners() {
  // Config form submission
  document.getElementById("search-config-form").addEventListener("submit", handleSaveSearchConfig);
  document.getElementById("btn-reset-config-form").addEventListener("click", resetConfigForm);
  
  // Scraper controls
  document.getElementById("btn-start-scan").addEventListener("click", handleStartScan);
  document.getElementById("btn-stop-scan").addEventListener("click", handleStopScan);
  
  // Leads filters
  document.getElementById("lead-filter-search").addEventListener("input", () => { leadsCurrentPage = 1; loadLeadsTable(); });
  document.getElementById("lead-filter-status").addEventListener("change", () => { leadsCurrentPage = 1; loadLeadsTable(); });
  document.getElementById("lead-filter-sector").addEventListener("change", () => { leadsCurrentPage = 1; loadLeadsTable(); });
  
  const scoreSlider = document.getElementById("lead-filter-score-range");
  scoreSlider.addEventListener("input", (e) => {
    document.getElementById("filter-score-val").textContent = e.target.value;
    leadsCurrentPage = 1;
    loadLeadsTable();
  });
  
  // Leads Pagination
  document.getElementById("leads-prev-btn").addEventListener("click", () => {
    if (leadsCurrentPage > 1) {
      leadsCurrentPage--;
      loadLeadsTable();
    }
  });
  document.getElementById("leads-next-btn").addEventListener("click", () => {
    leadsCurrentPage++;
    loadLeadsTable();
  });
  
  // Lead details CRM Save
  document.getElementById("btn-save-lead-crm").addEventListener("click", handleUpdateLeadCRM);
  
  // Modals close buttons
  document.getElementById("btn-close-lead-modal").addEventListener("click", () => {
    document.getElementById("lead-detail-modal").classList.remove("active");
  });
  document.getElementById("btn-close-add-modal").addEventListener("click", () => {
    document.getElementById("add-lead-modal").classList.remove("active");
  });
  document.getElementById("btn-add-lead-manual").addEventListener("click", () => {
    document.getElementById("add-lead-modal").classList.add("active");
  });
  
  // Manual Lead Form
  document.getElementById("manual-lead-form").addEventListener("submit", handleSaveManualLead);
  
  // SMTP settings form
  document.getElementById("smtp-settings-form").addEventListener("submit", handleSaveSmtpSettings);
  document.getElementById("btn-toggle-smtp-pass").addEventListener("click", toggleSmtpPasswordVisibility);
  
  // Campaign creation form
  document.getElementById("campaign-create-form").addEventListener("submit", handleCreateCampaign);
  
  // Test email trigger
  document.getElementById("btn-send-test-mail").addEventListener("click", handleSendTestMail);
}

// ==========================================
// Dashboard Page Logic
// ==========================================
async function loadDashboardData() {
  try {
    const res = await fetch(`${API_URL}/leads?limit=500`);
    const data = await res.json();
    const leads = data.leads;
    
    // Update metric cards
    document.getElementById("stat-total-leads").textContent = data.total_count;
    
    const withEmail = leads.filter(l => l.email && l.email !== "Belirsiz / Bilgi Yok").length;
    document.getElementById("stat-has-email").textContent = withEmail;
    
    const highScore = leads.filter(l => l.score >= 80).length;
    document.getElementById("stat-high-score").textContent = highScore;
    
    // Fetch campaigns to count mail sent
    const campRes = await fetch(`${API_URL}/campaigns`);
    const campaigns = await campRes.json();
    const totalSent = campaigns.reduce((acc, c) => acc + c.sent_count, 0);
    document.getElementById("stat-mail-sent").textContent = totalSent;
    
    // Quality Distribution Chart
    const strongCount = leads.filter(l => l.score >= 80).length;
    const mediumCount = leads.filter(l => l.score >= 60 && l.score < 80).length;
    const weakCount = leads.filter(l => l.score >= 40 && l.score < 60).length;
    const lowCount = leads.filter(l => l.score < 40).length;
    
    renderQualityChart(strongCount, mediumCount, weakCount, lowCount);
    
    // En Son Güçlü Adaylar
    const strongLeads = leads.filter(l => l.score >= 80).slice(0, 10);
    const container = document.getElementById("recent-strong-leads-list");
    container.innerHTML = "";
    
    if (strongLeads.length === 0) {
      container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem;">Güçlü uyum gösteren aday bulunmamaktadır.</p>`;
      return;
    }
    
    strongLeads.forEach(lead => {
      const emailText = lead.email ? `<span style="font-size:0.75rem; color:var(--text-muted);"><i class="fa-solid fa-envelope" style="margin-right:4px;"></i>${lead.email}</span>` : '';
      const div = document.createElement("div");
      div.style.cssText = "display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.02); border:1px solid var(--card-border); padding:12px; border-radius:8px;";
      div.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:4px;">
          <span style="font-size:0.9rem; font-weight:600; cursor:pointer;" onclick="openLeadDetails(${lead.id})">${lead.company_name}</span>
          <div style="display:flex; gap:12px; align-items:center;">
            <span style="font-size:0.75rem; color:var(--secondary);">${lead.sector}</span>
            ${emailText}
          </div>
        </div>
        <div class="score-badge strong" style="width:30px; height:30px; font-size:0.75rem;">${lead.score}</div>
      `;
      container.appendChild(div);
    });
    
  } catch (err) {
    console.error("Dashboard yükleme hatası:", err);
  }
}

function renderQualityChart(strong, medium, weak, low) {
  const ctx = document.getElementById("qualityChart").getContext("2d");
  
  if (qualityChartInstance) {
    qualityChartInstance.destroy();
  }
  
  qualityChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Güçlü Uyum (80-100)', 'Orta Uyum (60-79)', 'Zayıf Uyum (40-59)', 'Düşük Kalite (<40)'],
      datasets: [{
        data: [strong, medium, weak, low],
        backgroundColor: ['#10b981', '#f59e0b', '#3b82f6', '#ef4444'],
        borderWidth: 1,
        borderColor: '#1f2937'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: '#f3f4f6',
            boxWidth: 12,
            font: { size: 11 }
          }
        }
      },
      cutout: '65%'
    }
  });
}

// ==========================================
// Search Configs Page Logic
// ==========================================
async function loadSearchConfigs() {
  try {
    const res = await fetch(`${API_URL}/search-configs`);
    const configs = await res.json();
    const container = document.getElementById("configs-list");
    container.innerHTML = "";
    
    if (configs.length === 0) {
      container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem;">Kayıtlı arama kriteri bulunmuyor. Yeni bir tane ekleyebilirsiniz.</p>`;
      return;
    }
    
    configs.forEach(conf => {
      const card = document.createElement("div");
      card.className = "glass-card";
      card.style.padding = "20px";
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <h3 style="font-family:'Outfit'; font-size:1.1rem; color:white;">${conf.sector_name}</h3>
          <div style="display:flex; gap:8px;">
            <button class="btn btn-secondary" style="padding:6px 12px; font-size:0.8rem;" onclick='editSearchConfig(${JSON.stringify(conf)})'><i class="fa-solid fa-edit"></i>Düzenle</button>
            <button class="btn btn-danger" style="padding:6px 12px; font-size:0.8rem; background:rgba(239,68,68,0.15); border:1px solid rgba(239,68,68,0.3); color:var(--danger);" onclick="deleteSearchConfig(${conf.id})"><i class="fa-solid fa-trash"></i>Sil</button>
          </div>
        </div>
        <p style="font-size:0.85rem; color:var(--text-muted); margin-bottom:8px;"><strong>Kelimeler:</strong> ${conf.keywords.join(', ')}</p>
        <p style="font-size:0.85rem; color:var(--text-muted); margin-bottom:8px;"><strong>Şehirler:</strong> ${conf.cities.join(', ')}</p>
        <p style="font-size:0.85rem; color:var(--text-muted);"><strong>Limit:</strong> ${conf.search_limit} sayfa | <strong>Bekleme:</strong> ${conf.delay_min}-${conf.delay_max} sn</p>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error("Arama ayarları yükleme hatası:", err);
  }
}

async function handleSaveSearchConfig(e) {
  e.preventDefault();
  
  const sectorName = document.getElementById("conf-sector-name").value.trim();
  const rawKeywords = document.getElementById("conf-keywords").value;
  const rawCities = document.getElementById("conf-cities").value;
  const limit = parseInt(document.getElementById("conf-limit").value);
  const delayMin = parseInt(document.getElementById("conf-delay-min").value);
  const delayMax = parseInt(document.getElementById("conf-delay-max").value);
  const rawBlacklist = document.getElementById("conf-blacklist").value;
  
  // Parse inputs (split by commas or newlines)
  const keywords = rawKeywords.split(/[\n,]+/).map(k => k.trim()).filter(k => k.length > 0);
  const cities = rawCities.split(/[\n,]+/).map(c => c.trim()).filter(c => c.length > 0);
  const blacklist_domains = rawBlacklist.split(/[\n,]+/).map(d => d.trim()).filter(d => d.length > 0);
  
  const payload = {
    sector_name: sectorName,
    keywords,
    cities,
    districts: [],
    search_limit: limit,
    delay_min: delayMin,
    delay_max: delayMax,
    blacklist_domains
  };
  
  try {
    const res = await fetch(`${API_URL}/search-configs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    
    if (res.ok) {
      alert("Arama kriterleri kaydedildi!");
      resetConfigForm();
      loadSearchConfigs();
    } else {
      const err = await res.json();
      alert(`Hata: ${err.detail}`);
    }
  } catch (err) {
    console.error("Kaydetme hatası:", err);
  }
}

function editSearchConfig(conf) {
  document.getElementById("config-form-title").textContent = "Sektör Kriterini Düzenle";
  document.getElementById("conf-sector-name").value = conf.sector_name;
  document.getElementById("conf-sector-name").disabled = true; // Key parameter
  document.getElementById("conf-keywords").value = conf.keywords.join('\n');
  document.getElementById("conf-cities").value = conf.cities.join('\n');
  document.getElementById("conf-limit").value = conf.search_limit;
  document.getElementById("conf-delay-min").value = conf.delay_min;
  document.getElementById("conf-delay-max").value = conf.delay_max;
  document.getElementById("conf-blacklist").value = conf.blacklist_domains.join('\n');
}

function resetConfigForm() {
  document.getElementById("config-form-title").textContent = "Yeni Sektör Kriteri Ekle";
  document.getElementById("conf-sector-name").value = "";
  document.getElementById("conf-sector-name").disabled = false;
  document.getElementById("conf-keywords").value = "";
  document.getElementById("conf-cities").value = "";
  document.getElementById("conf-limit").value = "15";
  document.getElementById("conf-delay-min").value = "15";
  document.getElementById("conf-delay-max").value = "30";
  document.getElementById("conf-blacklist").value = "";
}

async function deleteSearchConfig(id) {
  if (!confirm("Bu konfigürasyonu silmek istediğinizden emin misiniz?")) return;
  try {
    const res = await fetch(`${API_URL}/search-configs/${id}`, { method: "DELETE" });
    if (res.ok) {
      loadSearchConfigs();
    }
  } catch (err) {
    console.error("Silme hatası:", err);
  }
}

// ==========================================
// Canlı Tarama Page Logic
// ==========================================
async function loadSearchConfigsForScanDropdown() {
  try {
    const res = await fetch(`${API_URL}/search-configs`);
    const configs = await res.json();
    const select = document.getElementById("scan-config-select");
    select.innerHTML = "";
    
    configs.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = `${c.sector_name} (${c.cities.join(', ')})`;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error("Dropdown yüklenirken hata:", err);
  }
}

async function handleStartScan() {
  const configId = parseInt(document.getElementById("scan-config-select").value);
  if (!configId) {
    alert("Lütfen bir arama ayarı seçin!");
    return;
  }
  
  try {
    const res = await fetch(`${API_URL}/scrape/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config_id: configId })
    });
    
    if (res.ok) {
      // Connect to SSE stream
      connectSSELogs();
      // Start status polling
      startStatusPolling();
      // Adjust UI buttons
      document.getElementById("btn-start-scan").disabled = true;
      document.getElementById("btn-stop-scan").disabled = false;
    } else {
      const err = await res.json();
      alert(`Hata: ${err.detail}`);
    }
  } catch (err) {
    console.error("Tarama başlatılamadı:", err);
  }
}

async function handleStopScan() {
  try {
    const res = await fetch(`${API_URL}/scrape/stop`, { method: "POST" });
    if (res.ok) {
      stopStatusPolling();
      disconnectSSELogs();
      document.getElementById("btn-start-scan").disabled = false;
      document.getElementById("btn-stop-scan").disabled = true;
    }
  } catch (err) {
    console.error("Tarama durdurulamadı:", err);
  }
}

function connectSSELogs() {
  if (sseSource) {
    sseSource.close();
  }
  
  const consoleContainer = document.getElementById("scan-console-logs");
  consoleContainer.innerHTML = ""; // Clear log board
  
  sseSource = new EventSource(`${API_URL}/scrape/stream`);
  
  sseSource.onmessage = (event) => {
    const log = JSON.parse(event.data);
    const timeSpan = `<span class="log-time">[${log.timestamp}]</span>`;
    const row = document.createElement("div");
    row.className = "log-row";
    
    let levelClass = "log-info";
    if (log.level === "success") levelClass = "log-success";
    if (log.level === "warning") levelClass = "log-warning";
    if (log.level === "error") levelClass = "log-error";
    
    row.innerHTML = `${timeSpan}<span class="${levelClass}">${log.message}</span>`;
    consoleContainer.appendChild(row);
    
    // Auto Scroll to bottom
    consoleContainer.scrollTop = consoleContainer.scrollHeight;
  };
  
  sseSource.onerror = () => {
    disconnectSSELogs();
  };
}

function disconnectSSELogs() {
  if (sseSource) {
    sseSource.close();
    sseSource = null;
  }
}

function startStatusPolling() {
  if (scanStatusInterval) clearInterval(scanStatusInterval);
  scanStatusInterval = setInterval(async () => {
    await updateScraperProgressUI();
  }, 1500);
}

function stopStatusPolling() {
  if (scanStatusInterval) {
    clearInterval(scanStatusInterval);
    scanStatusInterval = null;
  }
}

async function updateScraperProgressUI() {
  try {
    const res = await fetch(`${API_URL}/scrape/status`);
    const status = await res.json();
    
    document.getElementById("scan-state-label").textContent = status.is_running ? `Çalışıyor (${status.current_sector})` : "Boşta (Idle)";
    document.getElementById("scan-state-label").style.color = status.is_running ? "var(--success)" : "white";
    
    document.getElementById("scan-stat-found").textContent = status.total_found;
    document.getElementById("scan-stat-processed").textContent = status.total_processed;
    
    document.getElementById("scan-progress-bar").style.width = `${status.progress_percent}%`;
    document.getElementById("scan-progress-percent").textContent = status.progress_percent;
    
    if (!status.is_running) {
      stopStatusPolling();
      disconnectSSELogs();
      document.getElementById("btn-start-scan").disabled = false;
      document.getElementById("btn-stop-scan").disabled = true;
    }
  } catch (err) {
    console.error("Durum alma hatası:", err);
  }
}

async function checkScraperRunningStatus() {
  try {
    const res = await fetch(`${API_URL}/scrape/status`);
    const status = await res.json();
    if (status.is_running) {
      connectSSELogs();
      startStatusPolling();
      document.getElementById("btn-start-scan").disabled = true;
      document.getElementById("btn-stop-scan").disabled = false;
    } else {
      document.getElementById("btn-start-scan").disabled = false;
      document.getElementById("btn-stop-scan").disabled = true;
    }
  } catch (e) {}
}

// ==========================================
// Firma Havuzu Page Logic
// ==========================================
async function loadSectorsDropdown() {
  try {
    const res = await fetch(`${API_URL}/leads?limit=500`);
    const data = await res.json();
    const sectors = [...new Set(data.leads.map(l => l.sector))];
    
    const select = document.getElementById("lead-filter-sector");
    const currentVal = select.value;
    select.innerHTML = `<option value="">Hepsi</option>`;
    
    sectors.forEach(sec => {
      const opt = document.createElement("option");
      opt.value = sec;
      opt.textContent = sec;
      select.appendChild(opt);
    });
    
    select.value = currentVal;
  } catch (e) {}
}

async function loadLeadsTable() {
  const searchVal = document.getElementById("lead-filter-search").value;
  const statusVal = document.getElementById("lead-filter-status").value;
  const sectorVal = document.getElementById("lead-filter-sector").value;
  const scoreVal = parseInt(document.getElementById("lead-filter-score-range").value);
  
  let query = `${API_URL}/leads?page=${leadsCurrentPage}&limit=${leadsPageLimit}`;
  if (searchVal) query += `&search=${encodeURIComponent(searchVal)}`;
  if (statusVal) query += `&status=${encodeURIComponent(statusVal)}`;
  if (sectorVal) query += `&sector=${encodeURIComponent(sectorVal)}`;
  if (scoreVal > 0) query += `&min_score=${scoreVal}`;
  
  try {
    const res = await fetch(query);
    const data = await res.json();
    const leads = data.leads;
    
    const tbody = document.getElementById("leads-table-body");
    tbody.innerHTML = "";
    
    if (leads.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:40px; color:var(--text-muted);"><i class="fa-solid fa-box-open" style="font-size:2rem; margin-bottom:12px; display:block;"></i>Kriterlere uygun firma bulunamadı.</td></tr>`;
      document.getElementById("leads-count-label").textContent = `Gösterilen: 0 / Toplam: 0`;
      document.getElementById("leads-prev-btn").disabled = true;
      document.getElementById("leads-next-btn").disabled = true;
      return;
    }
    
    leads.forEach(lead => {
      const tr = document.createElement("tr");
      
      // Determine badge color class based on lead status
      const cleanStatus = lead.lead_status.replace(' ', '-');
      const statusBadge = `<span class="badge badge-${cleanStatus}">${lead.lead_status}</span>`;
      
      // Score badge class
      let scoreClass = "weak";
      if (lead.score >= 80) scoreClass = "strong";
      else if (lead.score >= 60) scoreClass = "medium";
      
      const scoreBadge = `<div class="score-badge ${scoreClass}">${lead.score}</div>`;
      
      const websiteLink = lead.website ? `<a href="${lead.website}" target="_blank" style="color:var(--secondary); text-decoration:none;"><i class="fa-solid fa-arrow-up-right-from-square" style="font-size:0.8rem; margin-right:6px;"></i>${lead.website.replace('http://','').replace('https://','').split('/')[0]}</a>` : '<span style="color:var(--text-muted);">Yok</span>';
      const emailVal = lead.email ? lead.email.split(',')[0] : '<span style="color:var(--text-muted);">-</span>';
      const phoneVal = lead.phone ? lead.phone.split(',')[0] : '<span style="color:var(--text-muted);">-</span>';
      
      tr.innerHTML = `
        <td style="padding-left:24px; font-weight:600; cursor:pointer;" onclick="openLeadDetails(${lead.id})">
          <div style="display:flex; flex-direction:column; gap:4px;">
            <span>${lead.company_name}</span>
            ${websiteLink}
          </div>
        </td>
        <td>
          <div style="display:flex; flex-direction:column; gap:4px;">
            <span style="font-size:0.8rem; color:var(--text-muted);">${lead.sector}</span>
            <span style="font-size:0.75rem; color:#94a3b8;"><i class="fa-solid fa-location-dot" style="margin-right:4px;"></i>${lead.city}, ${lead.district}</span>
          </div>
        </td>
        <td style="font-family:monospace; font-size:0.85rem;">${emailVal}</td>
        <td>${phoneVal}</td>
        <td style="text-align:center;">${scoreBadge}</td>
        <td>${statusBadge}</td>
        <td style="padding-right:24px; text-align:right;">
          <div style="display:flex; gap:8px; justify-content:flex-end;">
            <button class="btn btn-secondary" style="padding:6px 12px; font-size:0.8rem;" onclick="openLeadDetails(${lead.id})"><i class="fa-solid fa-eye"></i></button>
            <button class="btn btn-danger" style="padding:6px 12px; font-size:0.8rem; background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.2); color:var(--danger);" onclick="deleteLead(${lead.id})"><i class="fa-solid fa-trash"></i></button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
    
    // Update pagination labels
    const totalCount = data.total_count;
    const startNum = (leadsCurrentPage - 1) * leadsPageLimit + 1;
    const endNum = Math.min(leadsCurrentPage * leadsPageLimit, totalCount);
    document.getElementById("leads-count-label").textContent = `Gösterilen: ${startNum}-${endNum} / Toplam: ${totalCount}`;
    
    document.getElementById("leads-page-info").textContent = `Sayfa ${leadsCurrentPage}`;
    document.getElementById("leads-prev-btn").disabled = leadsCurrentPage === 1;
    document.getElementById("leads-next-btn").disabled = endNum >= totalCount;
    
  } catch (err) {
    console.error("Table loading error:", err);
  }
}

async function openLeadDetails(id) {
  try {
    const res = await fetch(`${API_URL}/leads/${id}`);
    const lead = await res.json();
    
    document.getElementById("md-lead-title").textContent = lead.company_name;
    document.getElementById("md-lead-website").innerHTML = lead.website ? `<a href="${lead.website}" target="_blank" style="color:var(--secondary);">${lead.website}</a>` : '-';
    document.getElementById("md-lead-email").textContent = lead.email || '-';
    document.getElementById("md-lead-phone").textContent = lead.phone || '-';
    document.getElementById("md-lead-location").textContent = `${lead.sector} | ${lead.city}, ${lead.district}`;
    document.getElementById("md-lead-desc").textContent = lead.description || 'Web sitesi açıklaması bulunamadı.';
    
    // Score Badge
    const badge = document.getElementById("md-lead-score-badge");
    badge.textContent = lead.score;
    badge.className = "score-badge " + (lead.score >= 80 ? "strong" : (lead.score >= 60 ? "medium" : "weak"));
    
    // Breakdown json & reason text
    document.getElementById("md-lead-score-reason").textContent = lead.score_reason || '';
    
    // CRM updates fields
    document.getElementById("md-lead-status").value = lead.lead_status;
    document.getElementById("md-lead-notes").value = lead.notes || '';
    
    // Store current lead ID on the Save button
    document.getElementById("btn-save-lead-crm").setAttribute("data-lead-id", lead.id);
    
    // Show Modal overlay
    document.getElementById("lead-detail-modal").classList.add("active");
    
  } catch (err) {
    console.error("Firma detayı yükleme hatası:", err);
  }
}

async function handleUpdateLeadCRM() {
  const btn = document.getElementById("btn-save-lead-crm");
  const leadId = btn.getAttribute("data-lead-id");
  const newStatus = document.getElementById("md-lead-status").value;
  const notes = document.getElementById("md-lead-notes").value.trim();
  
  if (!leadId) return;
  
  try {
    const res = await fetch(`${API_URL}/leads/${leadId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lead_status: newStatus, notes: notes })
    });
    
    if (res.ok) {
      document.getElementById("lead-detail-modal").classList.remove("active");
      loadLeadsTable();
    }
  } catch (err) {
    console.error("CRM güncelleme hatası:", err);
  }
}

async function handleSaveManualLead(e) {
  e.preventDefault();
  
  const payload = {
    company_name: document.getElementById("add-lead-name").value.trim(),
    sector: document.getElementById("add-lead-sector").value.trim(),
    website: document.getElementById("add-lead-website").value.trim(),
    city: document.getElementById("add-lead-city").value.trim(),
    district: document.getElementById("add-lead-district").value.trim(),
    email: document.getElementById("add-lead-email").value.trim() || null,
    phone: document.getElementById("add-lead-phone").value.trim() || null,
    description: document.getElementById("add-lead-desc").value.trim() || null,
    notes: document.getElementById("add-lead-notes").value.trim() || null,
    lead_status: "yeni"
  };
  
  try {
    const res = await fetch(`${API_URL}/leads`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    
    if (res.ok) {
      alert("Firma başarıyla manuel eklendi ve kalitesi otomatik skorlandı!");
      document.getElementById("add-lead-modal").classList.remove("active");
      document.getElementById("manual-lead-form").reset();
      loadLeadsTable();
    } else {
      const err = await res.json();
      alert(`Hata: ${err.detail}`);
    }
  } catch (err) {
    console.error("Firma ekleme hatası:", err);
  }
}

async function deleteLead(id) {
  if (!confirm("Bu firmayı veritabanından tamamen silmek istediğinizden emin misiniz?")) return;
  try {
    const res = await fetch(`${API_URL}/leads/${id}`, { method: "DELETE" });
    if (res.ok) {
      loadLeadsTable();
    }
  } catch (err) {
    console.error("Firma silme hatası:", err);
  }
}

// ==========================================
// Mail Kampanyası Page Logic
// ==========================================
async function loadSmtpSettings() {
  try {
    const res = await fetch(`${API_URL}/smtp-settings`);
    const settings = await res.json();
    
    if (settings) {
      document.getElementById("smtp-email").value = settings.sender_email;
      document.getElementById("smtp-host").value = settings.smtp_host;
      document.getElementById("smtp-port").value = settings.smtp_port;
      // We mask password input or leave it blank for user to overwrite
      document.getElementById("smtp-password").value = "********";
    }
  } catch (err) {}
}

async function handleSaveSmtpSettings(e) {
  e.preventDefault();
  
  const senderEmail = document.getElementById("smtp-email").value.trim();
  const smtpHost = document.getElementById("smtp-host").value.trim();
  const smtpPort = parseInt(document.getElementById("smtp-port").value);
  const password = document.getElementById("smtp-password").value;
  
  if (password === "********") {
    alert("Lütfen SMTP sunucusu şifrenizi girin.");
    return;
  }
  
  const payload = {
    sender_email: senderEmail,
    smtp_host: smtpHost,
    smtp_port: smtpPort,
    password: password
  };
  
  try {
    const res = await fetch(`${API_URL}/smtp-settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    
    if (res.ok) {
      alert("SMTP ayarları kaydedildi!");
      loadSmtpSettings();
    }
  } catch (err) {
    console.error("SMTP kaydetme hatası:", err);
  }
}

function toggleSmtpPasswordVisibility() {
  const input = document.getElementById("smtp-password");
  const icon = document.querySelector("#btn-toggle-smtp-pass i");
  if (input.type === "password") {
    input.type = "text";
    icon.className = "fa-solid fa-eye-slash";
  } else {
    input.type = "password";
    icon.className = "fa-solid fa-eye";
  }
}

async function updateCampaignAutoSelectCount() {
  try {
    // Queries counts of leads matching auto-select: email is present, score >= 80, status is 'yeni'
    const res = await fetch(`${API_URL}/leads?limit=500&status=yeni&min_score=80`);
    const data = await res.json();
    // Filter leads that have valid emails in frontend just to be doubly sure
    const qualified = data.leads.filter(l => l.email && l.email !== "Belirsiz / Bilgi Yok" && l.email !== "");
    document.getElementById("camp-auto-select-label").textContent = qualified.length;
  } catch (e) {}
}

function insertTemplateVar(variable) {
  const textarea = document.getElementById("camp-template-html");
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const text = textarea.value;
  textarea.value = text.substring(0, start) + variable + text.substring(end);
  textarea.focus();
  textarea.selectionStart = start + variable.length;
  textarea.selectionEnd = start + variable.length;
}

async function handleCreateCampaign(e) {
  e.preventDefault();
  
  const payload = {
    name: document.getElementById("camp-name").value.trim(),
    subject: document.getElementById("camp-subject").value.trim(),
    template_html: document.getElementById("camp-template-html").value,
    attachment_path: document.getElementById("camp-attachment").value.trim(),
    delay_min: parseInt(document.getElementById("camp-delay-min").value),
    delay_max: parseInt(document.getElementById("camp-delay-max").value)
  };
  
  try {
    const res = await fetch(`${API_URL}/campaigns`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    
    if (res.ok) {
      alert("Mail kampanyası kuruldu ve alıcı kuyruğu oluşturuldu!");
      document.getElementById("campaign-create-form").reset();
      document.getElementById("camp-template-html").value = "";
      loadCampaignsList();
      updateCampaignAutoSelectCount();
    } else {
      const err = await res.json();
      alert(`Hata: ${err.detail}`);
    }
  } catch (err) {
    console.error("Kampanya ekleme hatası:", err);
  }
}

async function loadCampaignsList() {
  try {
    const res = await fetch(`${API_URL}/campaigns`);
    const campaigns = await res.json();
    const container = document.getElementById("active-campaigns-list");
    container.innerHTML = "";
    
    if (campaigns.length === 0) {
      container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem;">Aktif kampanya bulunmamaktadır.</p>`;
      stopCampaignListPolling();
      return;
    }
    
    let hasRunning = false;
    campaigns.forEach(c => {
      if (c.status === "running") {
        hasRunning = true;
      }
      const card = document.createElement("div");
      card.className = "glass-card";
      card.style.padding = "20px";
      card.style.display = "flex";
      card.style.flexDirection = "column";
      card.style.gap = "14px";
      
      const percent = c.recipient_count > 0 ? Math.round((c.sent_count / c.recipient_count) * 100) : 0;
      
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div>
            <h3 style="font-family:'Outfit'; font-size:1.1rem; color:white;">${c.name}</h3>
            <span style="font-size:0.8rem; color:var(--text-muted);">Konu: ${c.subject} | Ek: ${c.attachment_path || 'Yok'}</span>
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn btn-secondary" style="padding:6px 12px; font-size:0.8rem; border-color:var(--success); color:var(--success);" onclick="startCampaignExecution(${c.id})" ${c.status === 'running' || c.sent_count === c.recipient_count ? 'disabled' : ''}><i class="fa-solid fa-paper-plane"></i>Başlat</button>
            <button class="btn btn-danger" style="padding:6px 12px; font-size:0.8rem; background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.2); color:var(--danger);" onclick="deleteCampaign(${c.id})"><i class="fa-solid fa-trash"></i>Sil</button>
          </div>
        </div>
        
        <div style="display:flex; justify-content:space-between; font-size:0.85rem; color:var(--text-muted); margin-bottom:-4px;">
          <span>Durum: <strong style="color:white; text-transform:uppercase;">${c.status}</strong></span>
          <span>Gönderim Durumu: ${c.sent_count} / ${c.recipient_count} Mail (${percent}%)</span>
        </div>
        
        <div style="width:100%; height:8px; background:rgba(255,255,255,0.05); border-radius:4px; overflow:hidden;">
          <div style="width:${percent}%; height:100%; background:linear-gradient(90deg, var(--success) 0%, #059669 100%);"></div>
        </div>
      `;
      container.appendChild(card);
    });

    if (hasRunning) {
      startCampaignListPolling();
    } else {
      stopCampaignListPolling();
    }
  } catch (err) {
    console.error("Kampanyaları yükleme hatası:", err);
  }
}

function startCampaignListPolling() {
  if (campaignStatusInterval) return;
  campaignStatusInterval = setInterval(async () => {
    await loadCampaignsList();
  }, 3000);
}

function stopCampaignListPolling() {
  if (campaignStatusInterval) {
    clearInterval(campaignStatusInterval);
    campaignStatusInterval = null;
  }
}

async function startCampaignExecution(id) {
  try {
    const res = await fetch(`${API_URL}/campaigns/${id}/status`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "running" })
    });
    if (res.ok) {
      alert("Kampanya kuyruk gönderimi tetiklendi ve arka planda çalışıyor!");
      loadCampaignsList();
    } else {
      const err = await res.json();
      alert(`Hata: ${err.detail}`);
    }
  } catch (err) {
    console.error("Kampanya başlatma hatası:", err);
  }
}

async function handleSendTestMail() {
  const testEmail = document.getElementById("smtp-test-email").value.trim();
  if (!testEmail) {
    alert("Lütfen test maili alıcı adresini girin.");
    return;
  }
  
  const subject = document.getElementById("camp-subject").value.trim();
  const bodyHtml = document.getElementById("camp-template-html").value;
  const attachmentName = document.getElementById("camp-attachment").value.trim();
  
  if (!subject || !bodyHtml) {
    alert("Lütfen test etmek için önce E-posta Konusu ve E-posta Taslak Şablonunu doldurun.");
    return;
  }
  
  const payload = {
    test_email: testEmail,
    subject: subject,
    body_html: bodyHtml,
    attachment_name: attachmentName || null
  };
  
  try {
    const res = await fetch(`${API_URL}/smtp-settings/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    
    if (res.ok) {
      const data = await res.json();
      alert(data.message || "Test maili başarıyla gönderildi!");
    } else {
      const err = await res.json();
      alert(`Test Mail Hatası: ${err.detail}`);
    }
  } catch (err) {
    console.error("Test maili gönderme hatası:", err);
    alert(`Sistem Hatası: ${err.message}`);
  }
}

async function deleteCampaign(id) {
  if (!confirm("Bu kampanyayı silmek istediğinizden emin misiniz? Alıcı kuyruğu silinecektir.")) return;
  try {
    const res = await fetch(`${API_URL}/campaigns/${id}`, { method: "DELETE" });
    if (res.ok) {
      loadCampaignsList();
      updateCampaignAutoSelectCount();
    }
  } catch (err) {
    console.error("Silme hatası:", err);
  }
}

