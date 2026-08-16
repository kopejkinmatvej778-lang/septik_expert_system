const storageKeys = {
  apiBase: "septik_control_api_base_v1",
  localMeasurements: "septik_control_local_measurements_v1",
};

const state = {
  view: "measurements",
  search: "",
  measurementFilter: "all",
  salesPeriod: "week",
  selectedClientId: "",
  apiBase: window.SEPTIK_API_BASE_URL || localStorage.getItem(storageKeys.apiBase) || "",
  data: null,
};

const now = new Date();
const dayMs = 24 * 60 * 60 * 1000;

const addDays = (days, hour = 10, minute = 0) => {
  const date = new Date(now);
  date.setDate(date.getDate() + days);
  date.setHours(hour, minute, 0, 0);
  return date.toISOString();
};

const emptyData = {
  measurements: [],
  montages: [],
  clients: [],
  sales: [],
  tasks: [],
  agentEvents: [],
};

const elements = {
  pageTitle: document.querySelector("#pageTitle"),
  globalSearch: document.querySelector("#globalSearch"),
  navItems: [...document.querySelectorAll(".nav-item")],
  views: {
    measurements: document.querySelector("#measurementsView"),
    montage: document.querySelector("#montageView"),
    database: document.querySelector("#databaseView"),
    sales: document.querySelector("#salesView"),
    tasks: document.querySelector("#tasksView"),
  },
  connectionStatus: document.querySelector("#connectionStatus"),
  notice: document.querySelector("#notice"),
  refreshButton: document.querySelector("#refreshButton"),
  settingsButton: document.querySelector("#settingsButton"),
  settingsModal: document.querySelector("#settingsModal"),
  settingsForm: document.querySelector("#settingsForm"),
  apiBaseInput: document.querySelector("#apiBaseInput"),
  closeSettingsButton: document.querySelector("#closeSettingsButton"),
  clearApiButton: document.querySelector("#clearApiButton"),
  addMeasurementButton: document.querySelector("#addMeasurementButton"),
  measurementModal: document.querySelector("#measurementModal"),
  measurementForm: document.querySelector("#measurementForm"),
  closeMeasurementButton: document.querySelector("#closeMeasurementButton"),
  cancelMeasurementButton: document.querySelector("#cancelMeasurementButton"),
  measurementFilter: document.querySelector("#measurementFilter"),
  periodFilter: document.querySelector("#periodFilter"),
};

const formatMoney = new Intl.NumberFormat("ru-RU", {
  style: "currency",
  currency: "RUB",
  maximumFractionDigits: 0,
});

const formatDate = new Intl.DateTimeFormat("ru-RU", {
  day: "2-digit",
  month: "short",
});

const formatDateTime = new Intl.DateTimeFormat("ru-RU", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

const titles = {
  measurements: "Замеры",
  montage: "Монтажи",
  database: "База",
  sales: "Продажи",
  tasks: "Задачи",
};

const safeText = (value) => String(value || "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#039;",
}[char]));

const searchText = (item) => Object.values(item)
  .filter((value) => typeof value === "string" || typeof value === "number")
  .join(" ")
  .toLowerCase();

const parseMoney = (value) => {
  const normalized = String(value || "").replace(/[^\d,-]/g, "").replace(",", ".");
  return Number.parseFloat(normalized) || 0;
};

const parseDateValue = (value) => {
  const text = String(value || "").trim();
  if (!text) return new Date().toISOString();
  const normalized = text.replace(/^(\d{2})\.(\d{2})\.(\d{4})(.*)$/u, "$3-$2-$1$4").replace(" ", "T");
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? new Date().toISOString() : date.toISOString();
};

const inferMeasurer = (text) => {
  const value = String(text || "");
  if (/егор/iu.test(value)) return "Егор";
  if (/витал/iu.test(value)) return "Виталий";
  return "";
};

const normalizeDocument = (row) => {
  const type = String(row["Тип"] || "").toUpperCase().includes("КП") ? "PNG" : "PDF";
  return {
    title: row["Оборудование"] || row["Тип"] || "Документ",
    type,
    url: row["Файл PNG/PDF"] || row["Папка клиента"] || "#",
  };
};

const normalizeSheetsDashboard = (raw) => {
  const sheets = raw.sheets || {};
  const documentRows = sheets["Документы"]?.rows || [];
  const documentsByClient = new Map();

  documentRows.forEach((row) => {
    const key = `${row["Клиент"] || ""}|${row["Телефон"] || ""}`.toLowerCase();
    if (!documentsByClient.has(key)) {
      documentsByClient.set(key, { proposals: [], contracts: [] });
    }
    const bucket = documentsByClient.get(key);
    const document = normalizeDocument(row);
    if (document.type === "PNG") {
      bucket.proposals.push(document);
    } else {
      bucket.contracts.push(document);
    }
  });

  const clients = (sheets["Клиенты"]?.rows || []).map((row, index) => {
    const key = `${row["Клиент"] || ""}|${row["Телефон"] || ""}`.toLowerCase();
    const documents = documentsByClient.get(key) || { proposals: [], contracts: [] };
    return {
      id: `client-${row["amo lead id"] || index}`,
      name: row["Клиент"] || "Без имени",
      address: row["Адрес"] || "",
      phone: row["Телефон"] || "",
      proposals: documents.proposals,
      contracts: documents.contracts,
    };
  });

  const measurements = [
    ...(raw.measurements || []),
    ...(sheets["Замеры"]?.rows || []).map((row, index) => ({
    id: `measurement-${row["amo lead id"] || index}`,
    source: row["Источник"] || "Google Sheets",
    client: row["Клиент"] || "Без имени",
    phone: row["Телефон"] || "",
    address: row["Адрес"] || "",
    deal: row["Рекомендованное оборудование"] || "Замер",
    measurer: inferMeasurer(`${row["Заметки"] || ""} ${row["Статус"] || ""}`),
    dueAt: parseDateValue(row["Дата замера"] || row["Дата создания"]),
    status: row["Статус"] || "Замер",
    note: row["Заметки"] || row["КП"] || "",
    amoLeadId: row["amo lead id"] || "",
    })),
  ];

  const montages = (sheets["Монтажи"]?.rows || []).map((row, index) => ({
    id: `montage-${index}`,
    date: parseDateValue(row["Дата монтажа"]),
    client: row["Клиент"] || "Без имени",
    address: row["Адрес"] || "",
    product: row["Оборудование"] || "",
    crew: row["Бригада"] || "Бригада не указана",
    materials: row["Комментарий"] || "",
    revenue: parseMoney(row["Сумма договора"]),
  }));

  const sales = (sheets["Продажи"]?.rows || []).map((row, index) => ({
    id: `sale-${row["amo lead id"] || index}`,
    date: parseDateValue(row["Дата обновления"] || row["Дата создания"]),
    client: row["Клиент"] || row["Название сделки"] || "Без имени",
    source: row["Источник/канал"] || row["Теги"] || "Не указано",
    stage: row["Статус"] || "",
    amount: parseMoney(row["Бюджет"]),
    status: /успешно|реализовано/iu.test(row["Статус"] || "") ? "won" : "open",
  }));

  const tasks = (sheets["Задачи"]?.rows || []).map((row, index) => ({
    id: `task-${row["amo task id"] || index}`,
    title: row["Текст"] || row["Тип"] || "Задача",
    owner: row["Ответственный"] || "Не указан",
    dueAt: parseDateValue(row["Дата выполнения"]),
    status: row["Статус"] || "",
  }));

  const updated = raw.summary?.updated || "не указано";
  return {
    measurements,
    montages,
    clients,
    sales,
    tasks,
    agentEvents: [
      { time: updated, text: `Данные загружены из реальных вкладок: ${Object.keys(sheets).join(", ")}` },
    ],
  };
};

const normalizeDashboardData = (raw) => {
  if (raw?.sheets) {
    return normalizeSheetsDashboard(raw);
  }
  return {
    ...emptyData,
    ...(raw || {}),
  };
};

const getLocalMeasurements = () => {
  try {
    return JSON.parse(localStorage.getItem(storageKeys.localMeasurements) || "[]");
  } catch {
    return [];
  }
};

const setLocalMeasurements = (items) => {
  localStorage.setItem(storageKeys.localMeasurements, JSON.stringify(items));
};

const getData = () => {
  const localMeasurements = getLocalMeasurements();
  return {
    ...emptyData,
    ...(state.data || {}),
    measurements: [...localMeasurements, ...((state.data || emptyData).measurements || [])],
  };
};

const setNotice = (message) => {
  elements.notice.hidden = !message;
  elements.notice.textContent = message || "";
};

const apiUrl = (path) => {
  const base = state.apiBase.replace(/\/+$/, "");
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
};

const requestApi = async (path, options = {}) => {
  if (!state.apiBase) {
    throw new Error("API не указан");
  }

  const response = await fetch(apiUrl(path), {
    method: options.method || "GET",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    credentials: "include",
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.message || `Ошибка API ${response.status}`);
  }
  return payload;
};

const loadDashboard = async () => {
  if (!state.apiBase) {
    state.data = emptyData;
    elements.connectionStatus.textContent = "API не указан";
    elements.connectionStatus.classList.remove("is-live");
    setNotice("API не указан. Панель не показывает примерные данные: укажи адрес VPS API.");
    render();
    return;
  }

  try {
    const payload = await requestApi("/dashboard");
    state.data = normalizeDashboardData(payload.data || payload);
    elements.connectionStatus.textContent = "VPS подключен";
    elements.connectionStatus.classList.add("is-live");
    setNotice("");
  } catch (error) {
    state.data = emptyData;
    elements.connectionStatus.textContent = "API недоступен";
    elements.connectionStatus.classList.remove("is-live");
    setNotice(`${error.message}. Данные не подменяются примером.`);
  }
  render();
};

const metric = (value, label) => `<div class="metric"><strong>${safeText(value)}</strong><span>${safeText(label)}</span></div>`;

const renderMetrics = (targetId, items) => {
  document.querySelector(targetId).innerHTML = items.map((item) => metric(item.value, item.label)).join("");
};

const filtered = (items) => {
  const q = state.search.trim().toLowerCase();
  if (!q) return items;
  return items.filter((item) => searchText(item).includes(q));
};

const renderMeasurements = () => {
  const data = getData();
  let items = filtered(data.measurements || []);
  if (state.measurementFilter === "unassigned") {
    items = items.filter((item) => !item.measurer);
  } else if (state.measurementFilter !== "all") {
    items = items.filter((item) => item.measurer === state.measurementFilter);
  }

  renderMetrics("#measurementMetrics", [
    { value: items.length, label: "в очереди" },
    { value: items.filter((item) => item.measurer === "Егор").length, label: "Егор" },
    { value: items.filter((item) => item.measurer === "Виталий").length, label: "Виталий" },
    { value: items.filter((item) => item.source === "amoCRM").length, label: "из amoCRM" },
  ]);

  document.querySelector("#measurementsList").innerHTML = items.length ? items.map((item) => `
    <article class="card-row">
      <div class="row-head">
        <div>
          <p class="row-title">${safeText(item.client || "Без имени")}</p>
          <p class="row-subtitle">${safeText(item.address || "Адрес не указан")}</p>
        </div>
        <span class="tag">${safeText(item.measurer || "Без замерщика")}</span>
      </div>
      <div class="row-meta">
        <span>${safeText(formatDateTime.format(new Date(item.dueAt || Date.now())))}</span>
        <span>${safeText(item.deal || "Сделка")}</span>
        <span>${safeText(item.status || item.source || "Задача")}</span>
        ${item.amoLeadId ? `<span>amoCRM #${safeText(item.amoLeadId)}</span>` : ""}
      </div>
      <p class="row-note">${safeText(item.note || "Комментариев нет")}</p>
    </article>
  `).join("") : `<div class="empty">По выбранному фильтру замеров нет.</div>`;

  const groups = ["Егор", "Виталий", "Без замерщика"].map((name) => {
    const count = items.filter((item) => name === "Без замерщика" ? !item.measurer : item.measurer === name).length;
    return `<article class="card-row"><p class="row-title">${name}</p><p class="row-subtitle">${count} активных замеров</p></article>`;
  });
  document.querySelector("#measurerSummary").innerHTML = groups.join("");
};

const renderMontage = () => {
  const items = filtered(getData().montages || []).sort((a, b) => new Date(a.date) - new Date(b.date));
  const revenue = items.reduce((sum, item) => sum + Number(item.revenue || 0), 0);
  renderMetrics("#montageMetrics", [
    { value: items.length, label: "монтажей" },
    { value: formatMoney.format(revenue), label: "выручка" },
    { value: items.filter((item) => /песок/i.test(item.materials || "")).length, label: "с песком" },
    { value: items.filter((item) => /грав/i.test(item.materials || "")).length, label: "с гравием" },
  ]);

  const byDay = new Map();
  items.forEach((item) => {
    const key = new Date(item.date).toISOString().slice(0, 10);
    byDay.set(key, [...(byDay.get(key) || []), item]);
  });

  document.querySelector("#montageCalendar").innerHTML = [...byDay.entries()].map(([key, dayItems]) => `
    <section class="day-column">
      <div class="day-title">${safeText(formatDate.format(new Date(key)))}</div>
      ${dayItems.map((item) => `
        <article class="montage-item">
          <p class="row-title">${safeText(item.client)}</p>
          <p class="row-subtitle">${safeText(item.product)} / ${safeText(item.crew)}</p>
          <p class="row-note">${safeText(item.address)}</p>
          <p class="row-note">${safeText(item.materials)}</p>
        </article>
      `).join("")}
    </section>
  `).join("") || `<div class="empty">Монтажей не найдено.</div>`;
};

const renderDatabase = () => {
  const clients = filtered(getData().clients || []);
  if (!state.selectedClientId && clients[0]) {
    state.selectedClientId = clients[0].id;
  }

  document.querySelector("#clientList").innerHTML = clients.map((client) => `
    <button class="card-row ${client.id === state.selectedClientId ? "is-selected" : ""}" type="button" data-client-id="${safeText(client.id)}">
      <span class="row-title">${safeText(client.name)}</span>
      <span class="row-subtitle">${safeText(client.address)}</span>
      <span class="row-note">${safeText(client.phone)}</span>
    </button>
  `).join("") || `<div class="empty">Клиенты не найдены.</div>`;

  const selected = clients.find((client) => client.id === state.selectedClientId) || clients[0];
  if (!selected) {
    document.querySelector("#clientDetails").innerHTML = `<div class="empty">Выбери клиента слева.</div>`;
    return;
  }

  const docs = (items, fallback) => (items || []).map((doc) => `
    <a class="doc-tile" href="${safeText(doc.url || "#")}" target="_blank" rel="noreferrer">
      ${doc.type === "PNG" && doc.url ? `<img src="${safeText(doc.url)}" alt="${safeText(doc.title)}" />` : `<div class="doc-preview">${safeText(doc.type || fallback)}</div>`}
      <span>${safeText(doc.title)}</span>
    </a>
  `).join("") || `<div class="empty">Документов пока нет.</div>`;

  document.querySelector("#clientDetails").innerHTML = `
    <div class="panel-head">
      <div>
        <p class="section-label">Карточка клиента</p>
        <h2>${safeText(selected.name)}</h2>
      </div>
      <span class="status-pill">${safeText(selected.address)}</span>
    </div>
    <p class="row-note">${safeText(selected.phone || "Телефон не указан")}</p>
    <h3>КП PNG</h3>
    <div class="doc-grid">${docs(selected.proposals, "PNG")}</div>
    <h3>Договоры</h3>
    <div class="doc-grid">${docs(selected.contracts, "PDF")}</div>
  `;

  document.querySelectorAll("[data-client-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedClientId = button.dataset.clientId;
      renderDatabase();
    });
  });
};

const periodStart = (period) => {
  const date = new Date();
  if (period === "week") date.setDate(date.getDate() - 7);
  if (period === "month") date.setMonth(date.getMonth() - 1);
  if (period === "prev") {
    date.setMonth(date.getMonth() - 2);
    date.setDate(1);
  }
  if (period === "all") date.setFullYear(2000);
  return date;
};

const renderSales = () => {
  const start = periodStart(state.salesPeriod);
  const sales = filtered(getData().sales || []).filter((item) => new Date(item.date) >= start);
  const revenue = sales.reduce((sum, item) => sum + Number(item.amount || 0), 0);
  const won = sales.filter((item) => item.status === "won").length;
  const conversion = sales.length ? Math.round((won / sales.length) * 100) : 0;

  renderMetrics("#salesMetrics", [
    { value: sales.length, label: "сделок" },
    { value: formatMoney.format(revenue), label: "выручка" },
    { value: new Set(sales.map((item) => item.client)).size, label: "клиентов" },
    { value: `${conversion}%`, label: "конверсия" },
  ]);

  const total = Math.max(sales.length, 1);
  const sources = sales.reduce((acc, item) => {
    acc[item.source] = acc[item.source] || { count: 0, revenue: 0 };
    acc[item.source].count += 1;
    acc[item.source].revenue += Number(item.amount || 0);
    return acc;
  }, {});

  document.querySelector("#sourceGrid").innerHTML = Object.entries(sources).map(([name, info]) => `
    <article class="source-card">
      <p class="row-title">${safeText(name)}</p>
      <p class="row-subtitle">${info.count} сделок / ${safeText(formatMoney.format(info.revenue))}</p>
      <div class="source-bar"><span style="width:${Math.round((info.count / total) * 100)}%"></span></div>
    </article>
  `).join("") || `<div class="empty">Нет сделок за период.</div>`;

  document.querySelector("#salesList").innerHTML = sales.map((item) => `
    <article class="card-row">
      <div class="row-head">
        <p class="row-title">${safeText(item.client)}</p>
        <span class="tag">${safeText(formatMoney.format(item.amount || 0))}</span>
      </div>
      <div class="row-meta">
        <span>${safeText(formatDate.format(new Date(item.date)))}</span>
        <span>${safeText(item.source)}</span>
        <span>${safeText(item.stage)}</span>
      </div>
    </article>
  `).join("") || `<div class="empty">Сделки не найдены.</div>`;
};

const renderTasks = () => {
  const data = getData();
  const tasks = filtered(data.tasks || []);
  document.querySelector("#tasksList").innerHTML = tasks.map((task) => `
    <article class="card-row">
      <div class="row-head">
        <p class="row-title">${safeText(task.title)}</p>
        <span class="tag">${safeText(task.status)}</span>
      </div>
      <div class="row-meta">
        <span>${safeText(task.owner)}</span>
        <span>${safeText(formatDateTime.format(new Date(task.dueAt)))}</span>
      </div>
    </article>
  `).join("") || `<div class="empty">Активных задач нет.</div>`;

  document.querySelector("#agentTimeline").innerHTML = (data.agentEvents || []).map((event) => `
    <div class="timeline-item">
      <p class="row-title">${safeText(event.time)}</p>
      <p class="row-note">${safeText(event.text)}</p>
    </div>
  `).join("");
};

const render = () => {
  elements.pageTitle.textContent = titles[state.view];
  elements.navItems.forEach((item) => item.classList.toggle("is-active", item.dataset.view === state.view));
  Object.entries(elements.views).forEach(([name, view]) => view.classList.toggle("is-visible", name === state.view));
  renderMeasurements();
  renderMontage();
  renderDatabase();
  renderSales();
  renderTasks();
};

const downloadText = (filename, text) => {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
};

const saveMeasurement = async (payload) => {
  if (state.apiBase) {
    try {
      await requestApi("/measurements", { method: "POST", body: payload });
      await loadDashboard();
      return;
    } catch (error) {
      setNotice(`${error.message}. Сохранил замер локально в браузере.`);
    }
  }

  const items = getLocalMeasurements();
  items.unshift({
    id: `local-${Date.now()}`,
    source: "manual",
    status: "Ручная задача",
    deal: "Замер",
    ...payload,
  });
  setLocalMeasurements(items);
  render();
};

elements.navItems.forEach((button) => {
  button.addEventListener("click", () => {
    state.view = button.dataset.view;
    render();
  });
});

elements.globalSearch.addEventListener("input", (event) => {
  state.search = event.target.value;
  render();
});

elements.refreshButton.addEventListener("click", loadDashboard);
elements.settingsButton.addEventListener("click", () => {
  elements.apiBaseInput.value = state.apiBase;
  elements.settingsModal.showModal();
});
elements.closeSettingsButton.addEventListener("click", () => elements.settingsModal.close());
elements.clearApiButton.addEventListener("click", () => {
  state.apiBase = "";
  localStorage.removeItem(storageKeys.apiBase);
  elements.settingsModal.close();
  loadDashboard();
});
elements.settingsForm.addEventListener("submit", (event) => {
  event.preventDefault();
  state.apiBase = elements.apiBaseInput.value.trim().replace(/\/+$/, "");
  localStorage.setItem(storageKeys.apiBase, state.apiBase);
  elements.settingsModal.close();
  loadDashboard();
});

elements.measurementFilter.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  state.measurementFilter = button.dataset.filter;
  elements.measurementFilter.querySelectorAll("button").forEach((item) => item.classList.toggle("is-active", item === button));
  renderMeasurements();
});

elements.periodFilter.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  state.salesPeriod = button.dataset.period;
  elements.periodFilter.querySelectorAll("button").forEach((item) => item.classList.toggle("is-active", item === button));
  renderSales();
});

elements.addMeasurementButton.addEventListener("click", () => {
  document.querySelector("#newDueAt").value = addDays(0, 15, 0).slice(0, 16);
  elements.measurementModal.showModal();
});
elements.closeMeasurementButton.addEventListener("click", () => elements.measurementModal.close());
elements.cancelMeasurementButton.addEventListener("click", () => elements.measurementModal.close());
elements.measurementForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    client: document.querySelector("#newClient").value.trim(),
    phone: document.querySelector("#newPhone").value.trim(),
    address: document.querySelector("#newAddress").value.trim(),
    measurer: document.querySelector("#newMeasurer").value,
    dueAt: new Date(document.querySelector("#newDueAt").value).toISOString(),
    note: document.querySelector("#newNote").value.trim(),
  };
  await saveMeasurement(payload);
  elements.measurementForm.reset();
  elements.measurementModal.close();
});

document.querySelector("#exportMontageButton").addEventListener("click", () => {
  const rows = (getData().montages || []).map((item) => `${formatDateTime.format(new Date(item.date))}; ${item.client}; ${item.address}; ${item.product}; ${item.materials}`);
  downloadText("montazhi.txt", rows.join("\n"));
});

document.querySelector("#exportTasksButton").addEventListener("click", () => {
  const rows = (getData().tasks || []).map((item) => `${formatDateTime.format(new Date(item.dueAt))}; ${item.owner}; ${item.title}; ${item.status}`);
  downloadText("tasks-report.txt", rows.join("\n"));
});

loadDashboard();
