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
  apiBase: localStorage.getItem(storageKeys.apiBase) || window.SEPTIK_API_BASE_URL || "",
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

const demoData = {
  measurements: [
    {
      id: "m-101",
      source: "amoCRM",
      client: "Айрат",
      phone: "+7 917 000-21-44",
      address: "Нагаево, ул. Сосновая, 18",
      deal: "Аэролос Био 5",
      measurer: "Виталий",
      dueAt: addDays(0, 12, 30),
      status: "Назначить замер",
      note: "Ответственный за замер Виталий. Проверить подъезд техники, УГВ и место под сброс.",
      amoLeadId: 44821801,
    },
    {
      id: "m-102",
      source: "amoCRM",
      client: "Наталья",
      phone: "+7 937 000-16-80",
      address: "Булгаково, Полевая, 7",
      deal: "Подбор станции",
      measurer: "Егор",
      dueAt: addDays(0, 16, 0),
      status: "Активная задача: замер",
      note: "Замерщик Егор. Клиент хочет сравнить Bio и Pro.",
      amoLeadId: 44821802,
    },
    {
      id: "m-103",
      source: "task",
      client: "Ренат",
      phone: "+7 917 000-61-09",
      address: "Жилино, ул. Лесная, 26",
      deal: "Монтаж под ключ",
      measurer: "",
      dueAt: addDays(1, 9, 0),
      status: "Нужен ответственный",
      note: "В карточке есть задача замер, но замерщик не указан.",
      amoLeadId: 44821803,
    },
  ],
  montages: [
    {
      id: "mt-201",
      date: addDays(1, 9, 0),
      client: "Линар",
      address: "Отары, Forest Village",
      product: "Аэролос Био 4",
      crew: "Бригада 1",
      materials: "Песок 5 м3, гравий 2 м3",
      revenue: 270000,
    },
    {
      id: "mt-202",
      date: addDays(3, 8, 30),
      client: "Дилара",
      address: "Новые Сокуры",
      product: "Аэролос Про 4",
      crew: "Бригада 2",
      materials: "Песок 4 м3, гравий 2 м3",
      revenue: 384400,
    },
    {
      id: "mt-203",
      date: addDays(5, 9, 0),
      client: "Александр",
      address: "Тарлаши",
      product: "Аэролос Про 8",
      crew: "Бригада 1",
      materials: "Песок 6 м3",
      revenue: 399000,
    },
  ],
  clients: [
    {
      id: "c-301",
      name: "Линар",
      address: "Отары, Forest Village",
      phone: "+7 987 000-55-10",
      proposals: [
        { title: "КП Линар Отары Аэролос Био 4", type: "PNG", url: "https://placehold.co/900x1200/png?text=KP+Linar+Bio+4" },
        { title: "КП Линар Отары Аэролос Про 4", type: "PNG", url: "https://placehold.co/900x1200/png?text=KP+Linar+Pro+4" },
      ],
      contracts: [
        { title: "Договор Аэролос Био 4 Линар", type: "PDF", url: "#" },
      ],
    },
    {
      id: "c-302",
      name: "Дилара",
      address: "Новые Сокуры",
      phone: "+7 927 000-40-21",
      proposals: [
        { title: "КП Дилара Новые Сокуры Аэролос Про 4", type: "PNG", url: "https://placehold.co/900x1200/png?text=KP+Dilara+Pro+4" },
      ],
      contracts: [
        { title: "Договор Аэролос Про 4 Муртазина Дилара", type: "PDF", url: "#" },
      ],
    },
    {
      id: "c-303",
      name: "Гульшат",
      address: "Сокуры",
      phone: "+7 917 000-77-12",
      proposals: [
        { title: "КП Гульшат Погреб Тингард", type: "PNG", url: "https://placehold.co/900x1200/png?text=KP+Gulshat+Tingard" },
      ],
      contracts: [
        { title: "Договор поставки погреба Гульшат", type: "PDF", url: "#" },
      ],
    },
  ],
  sales: [
    { id: "s-401", date: addDays(-2), client: "Линар", source: "Telegram", stage: "Монтаж назначен", amount: 270000, status: "won" },
    { id: "s-402", date: addDays(-6), client: "Дилара", source: "Avito", stage: "Договор", amount: 384400, status: "won" },
    { id: "s-403", date: addDays(-12), client: "Ренат", source: "Сайт", stage: "КП отправлено", amount: 312000, status: "open" },
    { id: "s-404", date: addDays(-32), client: "Айрат", source: "Рекомендации", stage: "Замер", amount: 246000, status: "open" },
  ],
  tasks: [
    { id: "t-501", title: "Поставить задачу по сделке Ренат", owner: "ИИ-агент", dueAt: addDays(0, 18), status: "Сегодня" },
    { id: "t-502", title: "Уточнить поставку песка по монтажу Линар", owner: "Матвей", dueAt: addDays(0, 17), status: "Сегодня" },
    { id: "t-503", title: "Проверить сделки без задач", owner: "ИИ-агент", dueAt: addDays(1, 18), status: "Автоматически" },
  ],
  agentEvents: [
    { time: "18:00", text: "Найдено 3 сделки без задач, создано 3 следующих шага." },
    { time: "18:01", text: "В сделке Ренат нет замерщика, требуется назначить ответственного." },
    { time: "18:02", text: "По КП Линар выручка внесена в бюджет сделки." },
  ],
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
    ...demoData,
    ...(state.data || {}),
    measurements: [...localMeasurements, ...((state.data || demoData).measurements || [])],
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
    state.data = null;
    elements.connectionStatus.textContent = "Демо-режим";
    elements.connectionStatus.classList.remove("is-live");
    setNotice("Сейчас показаны демо-данные. Укажи API VPS в кнопке API, и панель начнет брать живые сделки, монтажи и документы.");
    render();
    return;
  }

  try {
    const payload = await requestApi("/dashboard");
    state.data = payload.data || payload;
    elements.connectionStatus.textContent = "VPS подключен";
    elements.connectionStatus.classList.add("is-live");
    setNotice("");
  } catch (error) {
    state.data = null;
    elements.connectionStatus.textContent = "API недоступен";
    elements.connectionStatus.classList.remove("is-live");
    setNotice(`${error.message}. Показываю демо-данные, чтобы панель оставалась рабочей.`);
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
