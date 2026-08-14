"use client";

import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Bot,
  CalendarDays,
  Check,
  Download,
  ExternalLink,
  FileDown,
  FileImage,
  FolderArchive,
  HardHat,
  Layers3,
  PackageCheck,
  Plus,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  TrendingUp,
  Truck,
  Users,
} from "lucide-react";

type View = "clients" | "documents" | "measurements" | "montage" | "sales" | "tasks";

type DashboardDocument = {
  id: number;
  type: "proposal" | "contract";
  title: string;
  status: string;
  amount: number;
  equipment: string;
  fileUrl: string;
  mimeType?: string;
  driveFileId?: string;
  dueDate: string;
  createdAt: string;
  clientName: string;
  phone: string;
  address: string;
  manager: string;
  clientFolderUrl?: string;
  amoLeadId?: string;
};

type Montage = {
  id: number;
  clientName: string;
  phone: string;
  address: string;
  installDate: string;
  status: string;
  equipment: string;
  amount: number;
  sandTons: number;
  gravelTons: number;
  rings: string;
  team: string;
  manager: string;
  proposalUrl: string;
  contractUrl: string;
  reminderAt: string;
  reminderText: string;
  reminderStatus: "due_tomorrow" | "scheduled" | "sent" | "done";
};

type Measurement = {
  id: number;
  clientName: string;
  phone: string;
  address: string;
  status: string;
  source: string;
  scheduledAt: string;
  measuredAt: string;
  soil: string;
  groundwater: string;
  pipeDepth: string;
  distanceToHouse: string;
  recommendedEquipment: string;
  photosCount: number;
  telegramChatId: string;
  amoLeadId: string;
  sheetRowUrl: string;
  notes: string;
  manager: string;
  createdAt: string;
};

type AgentEvent = {
  id: number;
  agent: string;
  title: string;
  status: string;
  documentId: number | null;
  createdAt: string;
};

type SaleDeal = {
  id: number;
  amoLeadId: string;
  title: string;
  statusId: string;
  statusName?: string;
  pipelineId: string;
  pipelineName?: string;
  source?: string;
  price: number;
  responsibleUserId: string;
  responsibleUserName?: string;
  clientName: string;
  phone: string;
  nextTaskAt: string;
  updatedAt: string;
};

type SalesPipeline = {
  id: number;
  amoPipelineId: string;
  name: string;
  dealsCount: number;
  amount: number;
};

type SalesTask = {
  id: number;
  amoTaskId: string;
  amoLeadId: string;
  text: string;
  responsibleUserId: string;
  responsibleUserName?: string;
  dueAt: string;
  dealTitle?: string;
  clientName?: string;
};

type DashboardData = {
  stats: {
    proposals: number;
    contracts: number;
    activeAmount: number;
    attention: number;
    montages: number;
    measurements: number;
    tomorrowOrders: number;
    monthlyAmount: number;
    salesDeals: number;
    salesAmount: number;
  };
  documents: DashboardDocument[];
  measurements: Measurement[];
  montages: Montage[];
  sales: SaleDeal[];
  salesPipelines: SalesPipeline[];
  salesTasks: SalesTask[];
  events: AgentEvent[];
};

const defaultData: DashboardData = {
  stats: { proposals: 0, contracts: 0, activeAmount: 0, attention: 0, montages: 0, measurements: 0, tomorrowOrders: 0, monthlyAmount: 0, salesDeals: 0, salesAmount: 0 },
  documents: [],
  measurements: [],
  montages: [],
  sales: [],
  salesPipelines: [],
  salesTasks: [],
  events: [],
};

function normalizeDashboardData(nextData: DashboardData): DashboardData {
  return {
    ...defaultData,
    ...nextData,
    stats: { ...defaultData.stats, ...(nextData.stats ?? {}) },
    documents: nextData.documents ?? [],
    measurements: nextData.measurements ?? [],
    montages: nextData.montages ?? [],
    sales: nextData.sales ?? [],
    salesPipelines: nextData.salesPipelines ?? [],
    salesTasks: nextData.salesTasks ?? [],
    events: nextData.events ?? [],
  };
}

const statusLabels: Record<string, string> = {
  approved: "Согласовано",
  rendered: "PNG готов",
  draft: "Черновик",
  needs_review: "Проверить",
  signed: "Заключен",
  ready: "Готов",
  issued: "Выставлен",
  ok: "Ок",
  attention: "Контроль",
  proposal_ready: "КП готово",
  measured: "Замерен",
  new: "Новый",
  scheduled: "Запланирован",
  confirmed: "Подтвержден",
  in_progress: "В работе",
  done: "Смонтирован",
  postponed: "Перенос",
  due_tomorrow: "Заказать завтра",
  sent: "Отправлено",
};

function money(value: number) {
  return new Intl.NumberFormat("ru-RU").format(value || 0) + " р.";
}

function statusText(status: string) {
  return statusLabels[status] ?? status;
}

function typeText(document: Pick<DashboardDocument, "type">) {
  return document.type === "contract" ? "Договор PDF" : "КП PNG";
}

function isHttpUrl(value: string) {
  return /^https?:\/\//i.test((value ?? "").trim());
}

function shortDate(value: string) {
  if (!value) {
    return "Дата не задана";
  }
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "short" }).format(new Date(`${value}T12:00:00`));
}

export default function DashboardClient() {
  const [activeView, setActiveView] = useState<View>("clients");
  const [data, setData] = useState<DashboardData>(defaultData);
  const [query, setQuery] = useState("");
  const [selectedClientKey, setSelectedClientKey] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    clientName: "",
    phone: "",
    address: "",
    type: "contract",
    title: "",
    status: "draft",
    amount: "",
    equipment: "",
    fileUrl: "",
    dueDate: "",
  });

  const load = async () => {
    setLoading(true);
    const response = await fetch("/api/dashboard", { cache: "no-store" });
    const nextData = (await response.json()) as DashboardData;
    setData(normalizeDashboardData(nextData));
    setLoading(false);
  };

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await fetch("/api/dashboard", { cache: "no-store" });
      const nextData = (await response.json()) as DashboardData;
      if (!cancelled) {
        setData(normalizeDashboardData(nextData));
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return data.documents.filter((document) => {
      const haystack = `${document.title} ${document.clientName} ${document.phone} ${document.address} ${document.equipment}`.toLowerCase();
      return !needle || haystack.includes(needle);
    });
  }, [data.documents, query]);

  const clientGroups = useMemo(() => {
    const grouped = new Map<
      string,
      {
        key: string;
        clientName: string;
        phone: string;
        address: string;
        folderUrl: string;
        documents: DashboardDocument[];
      }
    >();

    for (const document of data.documents) {
      const key = `${document.clientName}|${document.phone}|${document.address}`;
      const current =
        grouped.get(key) ??
        {
          key,
          clientName: document.clientName,
          phone: document.phone,
          address: document.address,
          folderUrl: document.clientFolderUrl ?? "",
          documents: [],
        };
      current.documents.push(document);
      if (!current.folderUrl && document.clientFolderUrl) {
        current.folderUrl = document.clientFolderUrl;
      }
      grouped.set(key, current);
    }

    return Array.from(grouped.values())
      .map((group) => ({
        ...group,
        documents: group.documents.sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
      }))
      .sort((a, b) => (b.documents[0]?.createdAt ?? "").localeCompare(a.documents[0]?.createdAt ?? ""));
  }, [data.documents]);

  const selectedClient = clientGroups.find((group) => group.key === selectedClientKey) ?? clientGroups[0];
  const activeClientKey = selectedClient?.key ?? selectedClientKey;
  const attention = data.documents.filter((document) => ["draft", "needs_review", "ready"].includes(document.status));
  const tomorrowMontages = data.montages.filter((montage) => montage.reminderStatus === "due_tomorrow");
  const contractDocuments = filtered.filter((document) => document.type === "contract");

  const saveDocument = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    await fetch("/api/dashboard", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, amount: Number(form.amount) || 0 }),
    });
    setForm({
      clientName: "",
      phone: "",
      address: "",
      type: "contract",
      title: "",
      status: "draft",
      amount: "",
      equipment: "",
      dueDate: "",
      fileUrl: "",
    });
    await load();
    setSaving(false);
  };

  const renderFileAction = (document: DashboardDocument, label = "Открыть") => {
    if (!isHttpUrl(document.fileUrl)) {
      return (
        <span className="file-muted">
          {document.type === "contract" ? <FileDown size={16} /> : <FileImage size={16} />}
          Локально
        </span>
      );
    }

    return (
      <a className="file-action" href={document.fileUrl} target="_blank" rel="noreferrer">
        <Download size={16} />
        <span>{label}</span>
      </a>
    );
  };

  const metricStrip = (
    <section className="metric-grid" aria-label="Сводка">
      <article className="metric">
        <FileImage size={20} />
        <span>КП PNG</span>
        <strong>{data.stats.proposals || 0}</strong>
      </article>
      <article className="metric">
        <FileDown size={20} />
        <span>Договоры PDF</span>
        <strong>{data.stats.contracts || 0}</strong>
      </article>
      <article className="metric">
        <Users size={20} />
        <span>Клиенты</span>
        <strong>{clientGroups.length}</strong>
      </article>
      <article className="metric attention">
        <Truck size={20} />
        <span>Заказать завтра</span>
        <strong>{data.stats.tomorrowOrders || 0}</strong>
      </article>
    </section>
  );

  return (
    <main className="control-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark"><ShieldCheck size={23} /></div>
          <div>
            <strong>Septik Expert</strong>
            <span>Панель</span>
          </div>
        </div>

        <nav className="nav-stack" aria-label="Разделы панели">
          <button className={`nav-item ${activeView === "clients" ? "active" : ""}`} onClick={() => setActiveView("clients")} type="button">
            <Users size={18} /> Клиенты
          </button>
          <button className={`nav-item ${activeView === "documents" ? "active" : ""}`} onClick={() => setActiveView("documents")} type="button">
            <FolderArchive size={18} /> Договоры
          </button>
          <button className={`nav-item ${activeView === "measurements" ? "active" : ""}`} onClick={() => setActiveView("measurements")} type="button">
            <Bot size={18} /> Замеры
          </button>
          <button className={`nav-item ${activeView === "montage" ? "active" : ""}`} onClick={() => setActiveView("montage")} type="button">
            <HardHat size={18} /> Монтажи
          </button>
          <button className={`nav-item ${activeView === "sales" ? "active" : ""}`} onClick={() => setActiveView("sales")} type="button">
            <TrendingUp size={18} /> Продажи
          </button>
          <button className={`nav-item ${activeView === "tasks" ? "active" : ""}`} onClick={() => setActiveView("tasks")} type="button">
            <Check size={18} /> Задачи
          </button>
        </nav>

        <div className="drive-card">
          <span className="signal-dot" />
          <b>Google Drive</b>
          <small>Панель показывает только записи, пришедшие из Drive, Google Таблиц, Telegram и CRM.</small>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Пульт управления</p>
            <h1>
              {activeView === "clients" && "Клиенты и КП"}
              {activeView === "measurements" && "Замеры и заявки"}
              {activeView === "documents" && "Договоры PDF"}
              {activeView === "montage" && "Монтажи и предзаказы"}
              {activeView === "sales" && "Продажи"}
              {activeView === "tasks" && "Задачи руководителя"}
            </h1>
          </div>
          <button className="icon-button" onClick={load} type="button" aria-label="Обновить панель">
            <RefreshCw size={18} />
          </button>
        </header>

        {activeView === "clients" ? (
          <>
            {metricStrip}
            <section className="dashboard-grid">
              <ClientVault
                clientGroups={clientGroups}
                selectedClient={selectedClient}
                selectedClientKey={activeClientKey}
                setSelectedClientKey={setSelectedClientKey}
                renderFileAction={renderFileAction}
              />
              <TomorrowOrders montages={tomorrowMontages} />
            </section>
          </>
        ) : null}

        {activeView === "documents" ? (
          <>
            {metricStrip}
            <section className="content-grid">
              <section className="panel documents-panel">
                <div className="panel-head">
                  <div>
                    <p className="eyebrow">Документы</p>
                    <h2>Договоры PDF</h2>
                  </div>
                  <div className="filters">
                    <label className="search-box">
                      <Search size={17} />
                      <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Поиск" />
                    </label>
                  </div>
                </div>

                <div className="document-table" aria-busy={loading}>
                  <div className="table-row table-head-row">
                    <span>Клиент</span>
                    <span>Документ</span>
                    <span>Статус</span>
                    <span>Сумма</span>
                    <span>Срок</span>
                    <span>Файл</span>
                  </div>
                  {contractDocuments.map((document) => (
                    <div className="table-row" key={document.id}>
                      <span>
                        <b>{document.clientName}</b>
                        <small>{document.address}</small>
                      </span>
                      <span>
                        <b>{document.title}</b>
                        <small>{typeText(document)} · {document.equipment}</small>
                      </span>
                      <span><i className={`status ${document.status}`}>{statusText(document.status)}</i></span>
                      <span>{money(document.amount)}</span>
                      <span>{document.dueDate || "—"}</span>
                      <span>{renderFileAction(document, document.type === "contract" ? "PDF" : "PNG")}</span>
                    </div>
                  ))}
                </div>
              </section>

              <aside className="side-stack">
                <section className="panel add-panel">
                  <div className="panel-head compact">
                    <div>
                      <p className="eyebrow">Новая запись</p>
                      <h2>Добавить договор</h2>
                    </div>
                  </div>
                  <form className="doc-form" onSubmit={saveDocument}>
                    <input required value={form.clientName} onChange={(event) => setForm({ ...form, clientName: event.target.value })} placeholder="Клиент" />
                    <input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} placeholder="Телефон" />
                    <input value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} placeholder="Адрес" />
                    <select value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value })}>
                      <option value="contract">Договор PDF</option>
                    </select>
                    <input required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="Название документа" />
                    <input value={form.equipment} onChange={(event) => setForm({ ...form, equipment: event.target.value })} placeholder="Оборудование" />
                    <input inputMode="numeric" value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} placeholder="Сумма" />
                    <input value={form.fileUrl} onChange={(event) => setForm({ ...form, fileUrl: event.target.value })} placeholder="Ссылка на PNG/PDF" />
                    <input type="date" value={form.dueDate} onChange={(event) => setForm({ ...form, dueDate: event.target.value })} />
                    <button className="primary-button" disabled={saving} type="submit">
                      {saving ? <RefreshCw size={17} /> : <Plus size={17} />}
                      {saving ? "Сохраняю" : "Добавить"}
                    </button>
                  </form>
                </section>

                <section className="panel attention-panel">
                  <div className="panel-head compact">
                    <div>
                      <p className="eyebrow">Очередь</p>
                      <h2>Требует действия</h2>
                    </div>
                  </div>
                  <div className="attention-list">
                    {attention.slice(0, 6).map((document) => (
                      <div className="attention-item" key={document.id}>
                        <Check size={16} />
                        <span>{document.clientName}</span>
                        <b>{statusText(document.status)}</b>
                      </div>
                    ))}
                  </div>
                </section>
              </aside>
            </section>
          </>
        ) : null}

        {activeView === "measurements" ? (
          <>
            <section className="measurement-summary">
              <article className="metric">
                <Users size={20} />
                <span>Замеры</span>
                <strong>{data.stats.measurements}</strong>
              </article>
              <article className="metric">
                <Bot size={20} />
                <span>Telegram</span>
                <strong>{data.measurements.filter((measurement) => measurement.source === "telegram").length}</strong>
              </article>
              <article className="metric">
                <Activity size={20} />
                <span>amoCRM</span>
                <strong>{data.measurements.filter((measurement) => measurement.source === "amocrm").length}</strong>
              </article>
              <article className="metric attention">
                <FileImage size={20} />
                <span>Ждут КП</span>
                <strong>{data.measurements.filter((measurement) => ["new", "measured", "needs_review"].includes(measurement.status)).length}</strong>
              </article>
            </section>

            <section className="measurement-grid">
              {data.measurements.map((measurement) => (
                <article className="measurement-card" key={measurement.id}>
                  <div className="measurement-head">
                    <span>
                      <b>{measurement.clientName}</b>
                      <small>{measurement.address || measurement.phone}</small>
                    </span>
                    <i className={`status ${measurement.status}`}>{statusText(measurement.status)}</i>
                  </div>
                  <div className="measurement-facts">
                    <span><CalendarDays size={15} /> {measurement.scheduledAt || "Дата не задана"}</span>
                    <span><Bot size={15} /> {measurement.source === "telegram" ? "Telegram" : "amoCRM"}</span>
                    <span><FileImage size={15} /> Фото: {measurement.photosCount}</span>
                  </div>
                  <div className="measurement-spec">
                    <span>Грунт: <b>{measurement.soil}</b></span>
                    <span>УГВ: <b>{measurement.groundwater}</b></span>
                    <span>Глубина трубы: <b>{measurement.pipeDepth}</b></span>
                    <span>До дома: <b>{measurement.distanceToHouse || "—"}</b></span>
                  </div>
                  <div className="measurement-footer">
                    <span>{measurement.recommendedEquipment || "Оборудование не выбрано"}</span>
                    {isHttpUrl(measurement.sheetRowUrl) ? (
                      <a className="file-action" href={measurement.sheetRowUrl} target="_blank" rel="noreferrer">
                        <ExternalLink size={16} />
                        Таблица
                      </a>
                    ) : (
                      <span className="file-muted"><ExternalLink size={16} /> Таблица</span>
                    )}
                  </div>
                  <p>{measurement.notes}</p>
                </article>
              ))}
            </section>
          </>
        ) : null}

        {activeView === "montage" ? (
          <>
            <section className="montage-summary">
              <article className="metric">
                <CalendarDays size={20} />
                <span>Монтажи</span>
                <strong>{data.stats.montages}</strong>
              </article>
              <article className="metric attention">
                <Truck size={20} />
                <span>Предзаказ завтра</span>
                <strong>{data.stats.tomorrowOrders}</strong>
              </article>
              <article className="metric">
                <PackageCheck size={20} />
                <span>Песок завтра</span>
                <strong>{tomorrowMontages.reduce((sum, montage) => sum + montage.sandTons, 0)} т</strong>
              </article>
              <article className="metric">
                <Layers3 size={20} />
                <span>Гравий завтра</span>
                <strong>{tomorrowMontages.reduce((sum, montage) => sum + montage.gravelTons, 0)} т</strong>
              </article>
            </section>

            <section className="dashboard-grid">
              <TomorrowOrders montages={tomorrowMontages} />
              <section className="panel reminder-panel">
                <div className="panel-head compact">
                  <div>
                    <p className="eyebrow">Telegram-напоминания</p>
                    <h2>Сообщение за день до монтажа</h2>
                  </div>
                  <Send size={18} />
                </div>
                <div className="reminder-preview">
                  {tomorrowMontages[0]?.reminderText ?? "Нет монтажей, по которым завтра нужно делать заказ."}
                </div>
              </section>
            </section>

            <section className="montage-grid">
              {data.montages.map((montage) => (
                <article className="montage-card" key={montage.id}>
                  <div className="montage-date">
                    <CalendarDays size={18} />
                    <b>{shortDate(montage.installDate)}</b>
                    <i className={`status ${montage.status}`}>{statusText(montage.status)}</i>
                  </div>
                  <h3>{montage.clientName}</h3>
                  <p>{montage.address}</p>
                  <div className="supply-pills">
                    <span><PackageCheck size={15} /> Песок {montage.sandTons} т</span>
                    <span><Layers3 size={15} /> Гравий {montage.gravelTons} т</span>
                    <span><HardHat size={15} /> {montage.rings}</span>
                  </div>
                  <div className="montage-meta">
                    <span>{montage.equipment}</span>
                    <b>{money(montage.amount)}</b>
                  </div>
                  <div className="montage-meta">
                    <span>{montage.team}</span>
                    <span>{montage.manager}</span>
                  </div>
                </article>
              ))}
            </section>
          </>
        ) : null}

        {activeView === "tasks" ? (
          <>
            <section className="dashboard-grid">
              <section className="panel attention-panel">
                <div className="panel-head compact">
                  <div>
                    <p className="eyebrow">amoCRM</p>
                    <h2>Активные задачи менеджеров</h2>
                  </div>
                </div>
                <div className="attention-list">
                  {data.salesTasks.map((task) => (
                    <div className="attention-item" key={task.id}>
                      <Check size={16} />
                      <span>{task.responsibleUserName || task.responsibleUserId || "Менеджер"}</span>
                      <b>{task.clientName || task.dealTitle || `Сделка ${task.amoLeadId}`}: {task.text || "Задача без текста"}</b>
                    </div>
                  ))}
                  {!data.salesTasks.length ? <div className="empty-state">Активные задачи появятся после синхронизации amoCRM.</div> : null}
                </div>
              </section>
              <ActivityPanel events={data.events} />
            </section>
          </>
        ) : null}

        {activeView === "sales" ? (
          <>
            <section className="metric-grid" aria-label="Продажи">
              <article className="metric">
                <TrendingUp size={20} />
                <span>Сделки amoCRM</span>
                <strong>{data.stats.salesDeals || data.sales.length}</strong>
              </article>
              <article className="metric">
                <FolderArchive size={20} />
                <span>Сумма сделок</span>
                <strong>{money(data.stats.salesAmount || data.sales.reduce((sum, deal) => sum + deal.price, 0))}</strong>
              </article>
              <article className="metric">
                <Check size={20} />
                <span>Активные задачи</span>
                <strong>{data.salesTasks.length}</strong>
              </article>
              <article className="metric attention">
                <Truck size={20} />
                <span>Монтажи</span>
                <strong>{data.stats.montages || 0}</strong>
              </article>
            </section>

            <section className="sales-layout">
              <section className="panel">
                <div className="panel-head compact">
                  <div>
                    <p className="eyebrow">Воронки</p>
                    <h2>Сводка по amoCRM</h2>
                  </div>
                </div>
                <div className="pipeline-list">
                  {data.salesPipelines.map((pipeline) => (
                    <article className="pipeline-item" key={pipeline.id}>
                      <span>
                        <b>{pipeline.name || `Воронка ${pipeline.amoPipelineId}`}</b>
                        <small>{pipeline.dealsCount} сделок</small>
                      </span>
                      <strong>{money(pipeline.amount)}</strong>
                    </article>
                  ))}
                  {!data.salesPipelines.length ? <div className="empty-state compact">Воронки появятся после подключения токена amoCRM.</div> : null}
                </div>
              </section>

              <section className="panel">
                <div className="panel-head compact">
                  <div>
                    <p className="eyebrow">Задачи</p>
                    <h2>Продажи на контроле</h2>
                  </div>
                </div>
                <div className="attention-list">
                  {data.salesTasks.slice(0, 8).map((task) => (
                    <div className="attention-item" key={task.id}>
                      <Check size={16} />
                      <span>{task.responsibleUserName || task.responsibleUserId || "Менеджер"}</span>
                      <b>{task.text || task.dealTitle || `Сделка ${task.amoLeadId}`}</b>
                    </div>
                  ))}
                  {!data.salesTasks.length ? <div className="empty-state compact">Активных задач в amoCRM пока нет.</div> : null}
                </div>
              </section>
            </section>

            <section className="panel documents-panel">
              <div className="panel-head">
                <div>
                  <p className="eyebrow">amoCRM</p>
                  <h2>Реальные сделки</h2>
                </div>
              </div>
              <div className="document-table">
                <div className="table-row sales-row table-head-row">
                  <span>Сделка</span>
                  <span>Клиент</span>
                  <span>Статус</span>
                  <span>Сумма</span>
                  <span>Канал</span>
                  <span>Обновлено</span>
                </div>
                {data.sales.map((deal) => (
                  <div className="table-row sales-row" key={deal.id}>
                    <span>
                      <b>{deal.title || `Сделка ${deal.amoLeadId}`}</b>
                      <small>ID {deal.amoLeadId}</small>
                    </span>
                    <span>
                      <b>{deal.clientName || "Клиент не указан"}</b>
                      <small>{deal.phone || "Телефон не указан"}</small>
                    </span>
                    <span>
                      <i className="status">{deal.statusName || deal.statusId || "—"}</i>
                      <small>{deal.pipelineName || deal.pipelineId || ""}</small>
                    </span>
                    <span>{money(deal.price)}</span>
                    <span>{deal.source || "—"}</span>
                    <span>{deal.updatedAt || "—"}</span>
                  </div>
                ))}
                {!data.sales.length ? <div className="empty-state">Сделки появятся после подключения amoCRM.</div> : null}
              </div>
            </section>
          </>
        ) : null}
      </section>
    </main>
  );
}

function ClientVault({
  clientGroups,
  selectedClient,
  selectedClientKey,
  setSelectedClientKey,
  renderFileAction,
}: {
  clientGroups: Array<{
    key: string;
    clientName: string;
    phone: string;
    address: string;
    folderUrl: string;
    documents: DashboardDocument[];
  }>;
  selectedClient: {
    key: string;
    clientName: string;
    phone: string;
    address: string;
    folderUrl: string;
    documents: DashboardDocument[];
  } | undefined;
  selectedClientKey: string;
  setSelectedClientKey: (key: string) => void;
  renderFileAction: (document: DashboardDocument, label?: string) => React.ReactNode;
}) {
  const proposalDocuments = selectedClient?.documents.filter((document) => document.type === "proposal") ?? [];
  const contractDocuments = selectedClient?.documents.filter((document) => document.type === "contract") ?? [];

  return (
    <aside className="client-vault" aria-label="Архив документов клиента">
      <div className="panel-head compact">
        <div>
          <p className="eyebrow">Клиентский архив</p>
          <h2>Все PNG и PDF по клиенту</h2>
        </div>
        <Users size={20} />
      </div>

      <div className="client-list" aria-label="Клиенты">
        {clientGroups.map((group) => {
          const proposalCount = group.documents.filter((document) => document.type === "proposal").length;
          const contractCount = group.documents.filter((document) => document.type === "contract").length;
          return (
            <button
              className={group.key === selectedClientKey ? "selected" : ""}
              key={group.key}
              onClick={() => setSelectedClientKey(group.key)}
              type="button"
            >
              <span>
                <b>{group.clientName}</b>
                <small>{group.address || group.phone}</small>
              </span>
              <i>{proposalCount} PNG / {contractCount} PDF</i>
            </button>
          );
        })}
      </div>

      <div className="client-docs">
        <div className="doc-group-title">КП PNG</div>
        <div className="proposal-photo-grid">
          {proposalDocuments.map((document) => (
            <article className="proposal-photo" key={document.id}>
              {isHttpUrl(document.fileUrl) ? (
                <a href={document.fileUrl} target="_blank" rel="noreferrer" aria-label={`Открыть ${document.title}`}>
                  <Image src={document.fileUrl} alt={document.title} width={720} height={540} unoptimized />
                </a>
              ) : (
                <div className="proposal-photo-missing">
                  <FileImage size={24} />
                  <span>PNG ещё не загружен</span>
                </div>
              )}
              <div className="proposal-photo-caption">
                <b>{document.title}</b>
                <small>{statusText(document.status)} · {money(document.amount)}</small>
              </div>
            </article>
          ))}
        </div>
        {!proposalDocuments.length ? <div className="empty-state compact">КП по клиенту пока нет.</div> : null}

        <div className="doc-group-title">Договоры PDF</div>
        {contractDocuments.map((document) => (
          <article className="client-doc" key={document.id}>
            <div>
              <FileDown size={18} />
              <span>
                <b>{document.title}</b>
                <small>{typeText(document)} · {statusText(document.status)}</small>
              </span>
            </div>
            {renderFileAction(document, "PDF")}
          </article>
        ))}
        {!contractDocuments.length ? <div className="empty-state compact">Договоров по клиенту пока нет.</div> : null}
        {selectedClient?.folderUrl && isHttpUrl(selectedClient.folderUrl) ? (
          <a className="folder-link" href={selectedClient.folderUrl} target="_blank" rel="noreferrer">
            <ExternalLink size={16} />
            Папка клиента на Google Диске
          </a>
        ) : null}
      </div>
    </aside>
  );
}

function TomorrowOrders({ montages }: { montages: Montage[] }) {
  return (
    <section className="panel orders-panel">
      <div className="panel-head compact">
        <div>
          <p className="eyebrow">За день до монтажа</p>
          <h2>Что заказать</h2>
        </div>
        <Truck size={18} />
      </div>
      <div className="order-list">
        {montages.length ? (
          montages.map((montage) => (
            <article className="order-item" key={montage.id}>
              <div>
                <b>{montage.clientName}</b>
                <small>{montage.address}</small>
              </div>
              <p>{montage.reminderText}</p>
              <div className="supply-pills">
                <span>Песок {montage.sandTons} т</span>
                <span>Гравий {montage.gravelTons} т</span>
                <span>{montage.rings}</span>
              </div>
            </article>
          ))
        ) : (
          <div className="empty-state">На завтра предзаказов нет.</div>
        )}
      </div>
    </section>
  );
}

function ActivityPanel({ events }: { events: AgentEvent[] }) {
  return (
    <section className="panel activity-panel">
      <div className="panel-head compact">
        <div>
          <p className="eyebrow">Журнал</p>
          <h2>Последние действия</h2>
        </div>
        <Activity size={18} />
      </div>
      <div className="activity-grid">
        {events.map((event) => (
          <article className="activity-item" key={event.id}>
            <Bot size={18} />
            <span>{event.agent}</span>
            <b>{event.title}</b>
            <i className={`status ${event.status}`}>{statusText(event.status)}</i>
          </article>
        ))}
      </div>
    </section>
  );
}
