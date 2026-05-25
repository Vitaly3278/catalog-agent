const $ = (id) => document.getElementById(id);

async function api(path, opts = {}) {
  const r = await fetch(path, {
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });
  return r.json();
}

function statusClass(s) {
  return "status-" + (s || "pending");
}

function esc(s) {
  if (s == null) return "";
  const d = document.createElement("div");
  d.textContent = String(s);
  return d.innerHTML;
}

async function loadCatalogs() {
  const data = await api("/api/catalogs");
  $("mode-badge").textContent = data.demo_mode
    ? "Режим: DEMO (10 локальных форм)"
    : "Режим: LIVE (реальные каталоги)";
  $("catalog-list").innerHTML = data.catalogs
    .map((c) => `<li><strong>${esc(c.name)}</strong> <span class="mono">${esc(c.id)}</span></li>`)
    .join("");
}

async function loadSites() {
  const sites = await api("/api/sites");
  if (!sites.length) {
    $("sites-table-wrap").innerHTML = "<p>Нет сайтов. Добавьте URL и email.</p>";
    return;
  }
  let html = "<table><thead><tr><th>ID</th><th>Сайт</th><th>Email</th><th>Статус</th><th>Каталоги</th><th></th></tr></thead><tbody>";
  for (const s of sites) {
    const regs = (s.registrations || [])
      .map(
        (r) =>
          `<div><span class="${statusClass(r.status)}">${esc(r.catalog_name)}: ${esc(r.status)}</span></div>`
      )
      .join("");
    html += `<tr>
      <td>${s.id}</td>
      <td class="mono">${esc(s.url)}</td>
      <td>${esc(s.email)}</td>
      <td class="${statusClass(s.status)}">${esc(s.status)}</td>
      <td>${regs || "—"}</td>
      <td><button class="btn btn-secondary btn-retry" data-id="${s.id}">Повтор</button></td>
    </tr>`;
  }
  html += "</tbody></table>";
  $("sites-table-wrap").innerHTML = html;
  document.querySelectorAll(".btn-retry").forEach((btn) => {
    btn.onclick = async () => {
      await api(`/api/sites/${btn.dataset.id}/retry`, { method: "POST" });
      loadSites();
      loadRegs();
    };
  });
}

async function loadRegs() {
  const regs = await api("/api/registrations");
  if (!regs.length) {
    $("regs-table-wrap").innerHTML = "<p>Регистрации появятся после запуска.</p>";
    return;
  }
  let html = `<table><thead><tr>
    <th>Каталог</th><th>Сайт</th><th>Статус</th><th>Логин</th><th>Пароль</th>
    <th>Профиль</th><th>Backlink</th><th>Ошибка</th>
  </tr></thead><tbody>`;
  for (const r of regs) {
    html += `<tr>
      <td>${esc(r.catalog_name)}</td>
      <td class="mono">${esc(r.site_url)}</td>
      <td class="${statusClass(r.status)}">${esc(r.status)}</td>
      <td class="mono">${esc(r.login)}</td>
      <td class="mono">${esc(r.password)}</td>
      <td class="mono">${r.profile_url ? `<a href="${esc(r.profile_url)}">${esc(r.profile_url)}</a>` : ""}</td>
      <td class="mono">${r.backlink_url ? `<a href="${esc(r.backlink_url)}">${esc(r.backlink_url)}</a>` : ""}</td>
      <td>${esc(r.error_message)}</td>
    </tr>`;
  }
  html += "</tbody></table>";
  $("regs-table-wrap").innerHTML = html;
}

$("add-form").onsubmit = async (e) => {
  e.preventDefault();
  $("add-status").textContent = "Запускаем…";
  const body = {
    url: $("site-url").value.trim(),
    email: $("site-email").value.trim(),
  };
  try {
    const res = await api("/api/sites", { method: "POST", body: JSON.stringify(body) });
    if (res.ok) {
      $("add-status").textContent = `Сайт #${res.site.id} в очереди. Идёт скрапинг и регистрация в 10 каталогах.`;
      $("site-url").value = "";
      loadSites();
      loadRegs();
    }
  } catch (err) {
    $("add-status").textContent = "Ошибка: " + err.message;
  }
};

$("btn-refresh").onclick = () => {
  loadSites();
  loadRegs();
};

loadCatalogs();
loadSites();
loadRegs();
setInterval(() => {
  loadSites();
  loadRegs();
}, 8000);
