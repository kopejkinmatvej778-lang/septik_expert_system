"use client";

import Image from "next/image";
import type { ComponentType } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  CalendarDays,
  Check,
  ChevronRight,
  ClipboardList,
  Download,
  ExternalLink,
  FileDown,
  FileImage,
  FolderArchive,
  HardHat,
  Layers3,
  PackageCheck,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  TrendingUp,
  Truck,
  UserRoundCheck,
  Users,
} from "lucide-react";

type View = "measurements" | "montage" | "database" | "sales" | "tasks";
type Period = "week" | "month" | "prev" | "all";

type DashboardDocument = {
  id: number;
  type: "proposal" | "contract";
  title: string;
  status: string;
  amount: number;
  equipment: string;
  fileUrl: string;
  dueDate: string;
  createdAt: string;
  clientName: string;
  phone: string;
  address: string;
  manager: string;
  clientFolderUrl?: string;
  amoLeadId?: string;
};

type Measurement = {
  id: number | string;
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
  measurer?: string;
  taskText?: string;
  createdAt: string;
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
  stats: {
    proposals: 0,
    contracts: 0,
    activeAmount: 0,
    attention: 0,
    montages: 0,
    measurements: 0,
    tomorrowOrders: 0,
    monthlyAmount: 0,
    salesDeals: 0,
    salesAmount: 0,
  },
  documents: [],
  measurements: [],
  montages: [],
  sales: [],
  salesPipelines: [],
  salesTasks: [],
  events: [],
};

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
  from_amocrm: "amoCRM",
};

const navItems: Array<{ view: View; label: string; icon: ComponentType<{ size?: number }> }> = [
  { view: "measurements", label: "Замеры", icon: ClipboardList },
  { view: "montage", label: "Монтажи", icon: HardHat },
  { view: "database", label: "База", icon: FolderArchive },
  { view: "sales", label: "Продажи", icon: TrendingUp },
  { view: "tasks", label: "Задачи", icon: Check },
];

function normalizeDashboardData(nextData: Partial<DashboardData>): DashboardData {
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

function money(value: number) {
  return new Intl.NumberFormat("ru-RU").format(value || 0) + " р.";
}

function statusText(status: string) {
  return statusLabels[status] ?? (status || "-");
}

function isHttpUrl(value: string | undefined) {
  return /^https?:\/\//i.test((value ?? "").trim());
}

function toDate(value: string) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function shortDate(value: string) {
  const date = toDate(value);
  if (!date) return "Дата не задана";
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "short" }).format(date);
}

function fullDate(value: string) {
  const date = toDate(value);
  if (!date) return "-";
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "long", hour: "2-digit", minute: "2-digit" }).format(date);
}

function periodStart(period: Period) {
  const now = new Date();
  if (period === "all") return null;
  if (period === "week") {
    const date = new Date(now);
    date.setDate(now.getDate() - 7);
    return date;
  }
  if (period === "month") return new Date(now.getFullYear(), now.getMonth(), 1);
  return new Date(now.getFullYear(), now.getMonth() - 1, 1);
}

function periodEnd(period: Period) {
  const now = new Date();
  return period === "prev" ? new Date(now.getFullYear(), now.getMonth(), 1) : null;
}

function inPeriod(value: string, period: Period) {
  if (period === "all") return true;
  const date = toDate(value);
  if (!date) return false;
  const start = periodStart(period);
  const end = periodEnd(period);
  return (!start || date >= start) && (!end || date < end);
}

function extractMeasurer(text: string) {
  const match = text.match(/(?:замерщик|ответственный\s+за\s+замер)\s*[:\-\s]?\s*([А-ЯЁA-Z][а-яёa-z]+)/i);
  return match?.[1] ?? "";
}

function clientKey(clientName: string, phone: string, address: string) {
  return `${clientName || "Клиент"}|${phone || ""}|${address || ""}`;
}

function documentType(document: DashboardDocument) {
  return document.type === "contract" ? "Договор PDF" : "КП PNG";
}

function ClientPreview({ document }: { document: DashboardDocument }) {
  if (document.type === "proposal" && isHttpUrl(document.fileUrl)) {
    return (
      <a className="preview-image" href={document.fileUrl} target="_blank" rel="noreferrer" aria-label={document.title}>
        <Image src={document.fileUrl} alt={document.title} width={720} height={540} unoptimized />
      </a>
    );
  }

  return (
    <a className="preview-file" href={isHttpUrl(document.fileUrl) ? document.fileUrl : "#"} target="_blank" rel="noreferrer" aria-label={document.title}>
      {document.type === "contract" ? <FileDown size={28} /> : <FileImage size={28} />}
      <span>{documentType(document)}</span>
    </a>
  );
}

export default function DashboardClient({ userName = "Руководитель" }: { userName?: string }) {
  const [activeView, setActiveView] = useState<View>("measurements");
  const [period, setPeriod] = useState<Period>("month");
  const [data, setData] = useState<DashboardData>(defaultData);
  const [query, setQuery] = useState("");
  const [selectedClientKey, setSelectedClientKey] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const response = await fetch("/api/dashboard", { cache: "no-store" });
    const nextData = (await response.json()) as Partial<DashboardData>;
    setData(normalizeDashboardData(nextData));
    setLoading(false);
  };

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await fetch("/api/dashboard", { cache: "no-store" });
      const nextData = (await response.json()) as Partial<DashboardData>;
      if (!cancelled) {
        setData(normalizeDashboardData(nextData));
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const measurementRows = useMemo(() => {
    return data.measurements
      .map((measurement) => ({
        ...measurement,
        measurer: measurement.measurer || extractMeasurer(`${measurement.notes} ${measurement.taskText ?? ""}`),
      }))
      .sort((a, b) => (a.scheduledAt || a.createdAt || "").localeCompare(b.scheduledAt || b.createdAt || ""));
  }, [data.measurements]);

  const measurerGroups = useMemo(() => {
    const groups = new Map<string, Measurement[]>();
    for (const measurement of measurementRows) {
      const key = measurement.measurer || "Без замерщика";
      groups.set(key, [...(groups.get(key) ?? []), measurement]);
    }
    return Array.from(groups.entries());
  }, [measurementRows]);

  const montageByDay = useMemo(() => {
    const groups = new Map<string, Montage[]>();
    for (const montage of data.montages) {
      const key = montage.installDate || "Дата не задана";
      groups.set(key, [...(groups.get(key) ?? []), montage]);
    }
    return Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [data.montages]);

  const clientGroups = useMemo(() => {
    const grouped = new Map<
      string,
      { key: string; clientName: string; phone: string; address: string; folderUrl: string; documents: DashboardDocument[] }
    >();
    const needle = query.trim().toLowerCase();

    for (const document of data.documents) {
      const key = clientKey(document.clientName, document.phone, document.address);
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
      if (!current.folderUrl && document.clientFolderUrl) current.folderUrl = document.clientFolderUrl;
      grouped.set(key, current);
    }

    return Array.from(grouped.values())
      .map((group) => ({ ...group, documents: group.documents.sort((a, b) => b.createdAt.localeCompare(a.createdAt)) }))
      .filter((group) => {
        const text = `${group.clientName} ${group.phone} ${group.address} ${group.documents.map((doc) => doc.title).join(" ")}`.toLowerCase();
        return !needle || text.includes(needle);
      })
      .sort((a, b) => (b.documents[0]?.createdAt ?? "").localeCompare(a.documents[0]?.createdAt ?? ""));
  }, [data.documents, query]);

  const selectedClient = clientGroups.find((group) => group.key === selectedClientKey) ?? clientGroups[0];
  const salesInPeriod = data.sales.filter((deal) => inPeriod(deal.updatedAt, period));
  const salesAmount = salesInPeriod.reduce((sum, deal) => sum + (Number(deal.price) || 0), 0);
  const sourceRows = useMemo(() => {
    const rows = new Map<string, { source: string; count: number; amount: number }>();
    for (const deal of salesInPeriod) {
      const source = deal.source || "Без канала";
      const current = rows.get(source) ?? { source, count: 0, amount: 0 };
      current.count += 1;
      current.amount += Number(deal.price) || 0;
      rows.set(source, current);
    }
    return Array.from(rows.values()).sort((a, b) => b.amount - a.amount);
  }, [salesInPeriod]);
  const mountedDeals = data.montages.filter((montage) => inPeriod(montage.installDate, period)).length;
  const conversion = salesInPeriod.length ? Math.round((mountedDeals / salesInPeriod.length) * 100) : 0;
  const tomorrowMontages = data.montages.filter((montage) => montage.reminderStatus === "due_tomorrow");

  const viewTitle: Record<View, string> = {
    measurements: "Замеры",
    montage: "Монтажи",
    database: "База клиентов",
    sales: "Продажи",
    tasks: "Задачи",
  };

  return (
    <main className="control-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark">
            <ShieldCheck size={22} />
          </div>
          <div>
            <strong>Septik Expert</strong>
            <span>{userName}</span>
          </div>
        </div>

        <label className="global-search">
          <Search size={17} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Имя, место, телефон" />
        </label>

        <nav className="nav-stack" aria-label="Разделы панели">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button className={`nav-item ${activeView === item.view ? "active" : ""}`} key={item.view} onClick={() => setActiveView(item.view)} type="button">
                <Icon size={18} />
                <span>{item.label}</span>
                <ChevronRight size={15} />
              </button>
            );
          })}
        </nav>

        <div className="sidebar-card">
          <span className="signal-dot" />
          <b>Закрытый пульт</b>
          <small>Drive, Google Таблицы, Telegram и amoCRM</small>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Рабочий центр</p>
            <h1>{viewTitle[activeView]}</h1>
          </div>
          <button className="icon-button" onClick={load} type="button" aria-label="Обновить панель">
            <RefreshCw size={18} className={loading ? "spin" : ""} />
          </button>
        </header>

        {activeView === "measurements" ? (
          <>
            <section className="metric-grid">
              <Metric icon={ClipboardList} label="В очереди" value={String(measurementRows.length)} />
              <Metric icon={UserRoundCheck} label="Егор" value={String(measurementRows.filter((row) => row.measurer?.toLowerCase() === "егор").length)} />
              <Metric icon={UserRoundCheck} label="Виталий" value={String(measurementRows.filter((row) => row.measurer?.toLowerCase() === "виталий").length)} />
              <Metric icon={Activity} label="Из amoCRM" value={String(measurementRows.filter((row) => row.source === "amocrm").length)} accent />
            </section>

            <section className="measurement-board">
              <div className="board-main">
                {measurementRows.map((measurement) => (
                  <article className="work-card measurement-card" key={measurement.id}>
                    <div className="card-topline">
                      <span className="source-pill">{measurement.source === "amocrm" ? "amoCRM" : "Telegram"}</span>
                      <i className={`status ${measurement.status}`}>{statusText(measurement.status)}</i>
                    </div>
                    <h2>{measurement.clientName || "Клиент"}</h2>
                    <p>{measurement.address || measurement.phone || "Адрес не указан"}</p>
                    <div className="fact-grid">
                      <span><CalendarDays size={15} /> {fullDate(measurement.scheduledAt)}</span>
                      <span><UserRoundCheck size={15} /> {measurement.measurer || "Назначить"}</span>
                      <span><Send size={15} /> {measurement.telegramChatId || "Telegram"}</span>
                      <span><ExternalLink size={15} /> {measurement.amoLeadId || "CRM"}</span>
                    </div>
                    <div className="card-note">{measurement.taskText || measurement.notes || "Задача замера ожидает текста из amoCRM или Telegram."}</div>
                  </article>
                ))}
                {!measurementRows.length ? <EmptyState text="Замеры появятся из amoCRM-задач, Telegram и таблиц." /> : null}
              </div>

              <aside className="board-side">
                {measurerGroups.map(([name, rows]) => (
                  <section className="compact-panel" key={name}>
                    <div className="mini-head">
                      <b>{name}</b>
                      <span>{rows.length}</span>
                    </div>
                    {rows.slice(0, 5).map((row) => (
                      <div className="mini-row" key={row.id}>
                        <span>{shortDate(row.scheduledAt || row.createdAt)}</span>
                        <b>{row.clientName}</b>
                      </div>
                    ))}
                  </section>
                ))}
              </aside>
            </section>
          </>
        ) : null}

        {activeView === "montage" ? (
          <>
            <section className="metric-grid">
              <Metric icon={CalendarDays} label="Монтажи" value={String(data.montages.length)} />
              <Metric icon={Truck} label="Заказать завтра" value={String(tomorrowMontages.length)} accent />
              <Metric icon={PackageCheck} label="Песок" value={`${tomorrowMontages.reduce((sum, item) => sum + item.sandTons, 0)} т`} />
              <Metric icon={Layers3} label="Гравий" value={`${tomorrowMontages.reduce((sum, item) => sum + item.gravelTons, 0)} т`} />
            </section>
            <section className="calendar-layout">
              <div className="calendar-strip">
                {montageByDay.map(([day, rows]) => (
                  <section className="day-column" key={day}>
                    <div className="day-head">
                      <b>{shortDate(day)}</b>
                      <span>{rows.length}</span>
                    </div>
                    {rows.map((montage) => (
                      <article className="calendar-card" key={montage.id}>
                        <h2>{montage.clientName}</h2>
                        <p>{montage.address}</p>
                        <div className="supply-pills">
                          <span>Песок {montage.sandTons} т</span>
                          <span>Гравий {montage.gravelTons} т</span>
                          <span>{montage.rings || "Кольца -"}</span>
                        </div>
                        <div className="card-bottom">
                          <span>{montage.equipment}</span>
                          <b>{montage.team || montage.manager}</b>
                        </div>
                      </article>
                    ))}
                  </section>
                ))}
                {!montageByDay.length ? <EmptyState text="Календарь заполнится из Google Таблицы монтажей." /> : null}
              </div>
              <aside className="board-side">
                <section className="compact-panel accent">
                  <div className="mini-head">
                    <b>Ближайший заказ</b>
                    <Truck size={17} />
                  </div>
                  <p>{tomorrowMontages[0]?.reminderText || "На завтра материалов к заказу нет."}</p>
                </section>
              </aside>
            </section>
          </>
        ) : null}

        {activeView === "database" ? (
          <section className="database-layout">
            <aside className="client-index">
              <div className="panel-title">
                <p className="eyebrow">Клиенты</p>
                <h2>{clientGroups.length}</h2>
              </div>
              <div className="client-list">
                {clientGroups.map((client) => (
                  <button className={selectedClient?.key === client.key ? "selected" : ""} key={client.key} onClick={() => setSelectedClientKey(client.key)} type="button">
                    <span>
                      <b>{client.clientName}</b>
                      <small>{client.address || client.phone}</small>
                    </span>
                    <i>{client.documents.length}</i>
                  </button>
                ))}
              </div>
            </aside>

            <section className="client-detail">
              {selectedClient ? (
                <>
                  <div className="detail-head">
                    <div>
                      <p className="eyebrow">Карточка</p>
                      <h2>{selectedClient.clientName}</h2>
                      <span>{selectedClient.phone || "Телефон не указан"} · {selectedClient.address || "Адрес не указан"}</span>
                    </div>
                    {isHttpUrl(selectedClient.folderUrl) ? (
                      <a className="file-action" href={selectedClient.folderUrl} target="_blank" rel="noreferrer">
                        <ExternalLink size={16} />
                        Drive
                      </a>
                    ) : null}
                  </div>

                  <DocumentShelf title="КП PNG" documents={selectedClient.documents.filter((document) => document.type === "proposal")} />
                  <DocumentShelf title="Договоры PDF" documents={selectedClient.documents.filter((document) => document.type === "contract")} />
                </>
              ) : (
                <EmptyState text="База заполнится после первых КП и договоров." />
              )}
            </section>
          </section>
        ) : null}

        {activeView === "sales" ? (
          <>
            <section className="periodbar">
              {[
                ["week", "Неделя"],
                ["month", "Месяц"],
                ["prev", "Прошлый месяц"],
                ["all", "Все время"],
              ].map(([value, label]) => (
                <button className={period === value ? "selected" : ""} key={value} onClick={() => setPeriod(value as Period)} type="button">
                  {label}
                </button>
              ))}
            </section>

            <section className="metric-grid">
              <Metric icon={TrendingUp} label="Сделки" value={String(salesInPeriod.length)} />
              <Metric icon={BarChart3} label="Выручка" value={money(salesAmount)} />
              <Metric icon={Users} label="Клиенты" value={String(new Set(salesInPeriod.map((deal) => deal.phone || deal.clientName)).size)} />
              <Metric icon={Check} label="До монтажа" value={`${conversion}%`} accent />
            </section>

            <section className="sales-layout">
              <div className="analytics-grid">
                {sourceRows.map((source) => (
                  <article className="analytics-card" key={source.source}>
                    <span>{source.source}</span>
                    <b>{source.count} сделок</b>
                    <strong>{money(source.amount)}</strong>
                  </article>
                ))}
                {!sourceRows.length ? <EmptyState text="Каналы продаж появятся после синхронизации amoCRM." /> : null}
              </div>
              <div className="deal-table">
                {salesInPeriod.map((deal) => (
                  <article className="deal-row" key={deal.id}>
                    <span>
                      <b>{deal.title || `Сделка ${deal.amoLeadId}`}</b>
                      <small>{deal.clientName || "Клиент"} · {deal.phone || "телефон -"}</small>
                    </span>
                    <i className="status">{deal.statusName || deal.statusId || "-"}</i>
                    <strong>{money(deal.price)}</strong>
                    <small>{deal.source || "Без канала"}</small>
                  </article>
                ))}
              </div>
            </section>
          </>
        ) : null}

        {activeView === "tasks" ? (
          <section className="tasks-layout">
            <div className="task-list">
              {data.salesTasks.map((task) => (
                <article className="task-card" key={task.id}>
                  <div className="task-icon"><Check size={17} /></div>
                  <span>
                    <b>{task.clientName || task.dealTitle || `Сделка ${task.amoLeadId}`}</b>
                    <small>{task.responsibleUserName || task.responsibleUserId || "Ответственный"} · {fullDate(task.dueAt)}</small>
                    <p>{task.text || "Задача без текста"}</p>
                  </span>
                </article>
              ))}
              {!data.salesTasks.length ? <EmptyState text="Активные задачи появятся после синхронизации amoCRM." /> : null}
            </div>
            <aside className="board-side">
              <section className="compact-panel">
                <div className="mini-head">
                  <b>Журнал агентов</b>
                  <Activity size={17} />
                </div>
                {data.events.slice(0, 8).map((event) => (
                  <div className="mini-row" key={event.id}>
                    <span>{event.agent}</span>
                    <b>{event.title}</b>
                  </div>
                ))}
              </section>
            </aside>
          </section>
        ) : null}
      </section>
    </main>
  );
}

function Metric({ icon: Icon, label, value, accent = false }: { icon: ComponentType<{ size?: number }>; label: string; value: string; accent?: boolean }) {
  return (
    <article className={`metric ${accent ? "attention" : ""}`}>
      <Icon size={20} />
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>;
}

function DocumentShelf({ title, documents }: { title: string; documents: DashboardDocument[] }) {
  return (
    <section className="doc-shelf">
      <div className="shelf-head">
        <h3>{title}</h3>
        <span>{documents.length}</span>
      </div>
      <div className="proposal-photo-grid">
        {documents.map((document) => (
          <article className="proposal-photo" key={document.id}>
            <ClientPreview document={document} />
            <div className="proposal-photo-caption">
              <b>{document.title}</b>
              <small>{statusText(document.status)} · {money(document.amount)}</small>
              {isHttpUrl(document.fileUrl) ? (
                <a href={document.fileUrl} target="_blank" rel="noreferrer">
                  <Download size={14} />
                  Открыть
                </a>
              ) : null}
            </div>
          </article>
        ))}
        {!documents.length ? <EmptyState text="Пока пусто." /> : null}
      </div>
    </section>
  );
}
