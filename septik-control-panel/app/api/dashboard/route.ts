import { env } from "cloudflare:workers";

type DocumentType = "proposal" | "contract";

type IncomingDocument = {
  clientName?: string;
  phone?: string;
  address?: string;
  type?: DocumentType;
  title?: string;
  status?: string;
  amount?: number;
  equipment?: string;
  fileUrl?: string;
  dueDate?: string;
  amoLeadId?: string;
};

type AmoLead = {
  id?: number;
  name?: string;
  price?: number;
  status_id?: number;
  pipeline_id?: number;
  responsible_user_id?: number;
  updated_at?: number;
  closest_task_at?: number | null;
  custom_fields_values?: Array<{
    field_name?: string;
    field_code?: string;
    values?: Array<{ value?: string }>;
  }>;
  _embedded?: {
    tags?: Array<{ name?: string }>;
    contacts?: Array<{
      id?: number;
      name?: string;
      custom_fields_values?: Array<{
        field_code?: string;
        values?: Array<{ value?: string }>;
      }>;
    }>;
  };
};

type AmoPipeline = {
  id?: number;
  name?: string;
  sort?: number;
  is_main?: boolean;
  _embedded?: {
    statuses?: Array<{
      id?: number;
      name?: string;
    }>;
  };
};

type AmoTask = {
  id?: number;
  entity_id?: number;
  entity_type?: string;
  text?: string;
  task_type_id?: number;
  responsible_user_id?: number;
  complete_till?: number;
  is_completed?: boolean;
  updated_at?: number;
};

type AmoUser = {
  id?: number;
  name?: string;
};

const schemaStatements = [
  "CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT NOT NULL DEFAULT '', address TEXT NOT NULL DEFAULT '', manager TEXT NOT NULL DEFAULT '', folder_url TEXT NOT NULL DEFAULT '', amo_contact_id TEXT NOT NULL DEFAULT '', amo_lead_id TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
  "CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL, type TEXT NOT NULL, title TEXT NOT NULL, status TEXT NOT NULL, amount INTEGER NOT NULL DEFAULT 0, equipment TEXT NOT NULL DEFAULT '', file_url TEXT NOT NULL DEFAULT '', mime_type TEXT NOT NULL DEFAULT '', drive_file_id TEXT NOT NULL DEFAULT '', client_folder_url TEXT NOT NULL DEFAULT '', amo_lead_id TEXT NOT NULL DEFAULT '', due_date TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
  "CREATE TABLE IF NOT EXISTS measurements (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL, status TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'telegram', scheduled_at TEXT NOT NULL DEFAULT '', measured_at TEXT NOT NULL DEFAULT '', soil TEXT NOT NULL DEFAULT '', groundwater TEXT NOT NULL DEFAULT '', pipe_depth TEXT NOT NULL DEFAULT '', distance_to_house TEXT NOT NULL DEFAULT '', recommended_equipment TEXT NOT NULL DEFAULT '', photos_count INTEGER NOT NULL DEFAULT 0, telegram_chat_id TEXT NOT NULL DEFAULT '', amo_lead_id TEXT NOT NULL DEFAULT '', sheet_row_url TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
  "CREATE TABLE IF NOT EXISTS montages (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL, install_date TEXT NOT NULL, status TEXT NOT NULL, equipment TEXT NOT NULL DEFAULT '', amount INTEGER NOT NULL DEFAULT 0, sand_tons INTEGER NOT NULL DEFAULT 0, gravel_tons INTEGER NOT NULL DEFAULT 0, rings TEXT NOT NULL DEFAULT '', team TEXT NOT NULL DEFAULT '', manager TEXT NOT NULL DEFAULT '', proposal_url TEXT NOT NULL DEFAULT '', contract_url TEXT NOT NULL DEFAULT '', reminder_at TEXT NOT NULL DEFAULT '', reminder_status TEXT NOT NULL DEFAULT 'scheduled', reminder_text TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
  "CREATE TABLE IF NOT EXISTS sales_deals (id INTEGER PRIMARY KEY AUTOINCREMENT, amo_lead_id TEXT NOT NULL UNIQUE, title TEXT NOT NULL DEFAULT '', status_id TEXT NOT NULL DEFAULT '', status_name TEXT NOT NULL DEFAULT '', pipeline_id TEXT NOT NULL DEFAULT '', pipeline_name TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT '', price INTEGER NOT NULL DEFAULT 0, responsible_user_id TEXT NOT NULL DEFAULT '', responsible_user_name TEXT NOT NULL DEFAULT '', client_name TEXT NOT NULL DEFAULT '', phone TEXT NOT NULL DEFAULT '', next_task_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
  "CREATE TABLE IF NOT EXISTS sales_pipelines (id INTEGER PRIMARY KEY AUTOINCREMENT, amo_pipeline_id TEXT NOT NULL UNIQUE, name TEXT NOT NULL DEFAULT '', sort INTEGER NOT NULL DEFAULT 0, is_main INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
  "CREATE TABLE IF NOT EXISTS sales_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, amo_task_id TEXT NOT NULL UNIQUE, amo_lead_id TEXT NOT NULL DEFAULT '', entity_type TEXT NOT NULL DEFAULT '', text TEXT NOT NULL DEFAULT '', task_type_id TEXT NOT NULL DEFAULT '', responsible_user_id TEXT NOT NULL DEFAULT '', responsible_user_name TEXT NOT NULL DEFAULT '', due_at TEXT NOT NULL DEFAULT '', is_completed INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
  "CREATE TABLE IF NOT EXISTS agent_events (id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT NOT NULL, title TEXT NOT NULL, status TEXT NOT NULL, document_id INTEGER, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
  "CREATE INDEX IF NOT EXISTS idx_documents_type_status ON documents (type, status)",
  "CREATE INDEX IF NOT EXISTS idx_documents_client_created ON documents (client_id, created_at)",
  "CREATE INDEX IF NOT EXISTS idx_measurements_status_date ON measurements (status, scheduled_at)",
  "CREATE INDEX IF NOT EXISTS idx_montages_date_status ON montages (install_date, status)",
  "CREATE INDEX IF NOT EXISTS idx_sales_deals_status ON sales_deals (pipeline_id, status_id)",
  "CREATE INDEX IF NOT EXISTS idx_sales_deals_updated ON sales_deals (updated_at)",
  "CREATE INDEX IF NOT EXISTS idx_sales_deals_source ON sales_deals (source)",
  "CREATE INDEX IF NOT EXISTS idx_sales_tasks_due ON sales_tasks (due_at, is_completed)",
  "CREATE INDEX IF NOT EXISTS idx_agent_events_created ON agent_events (created_at)",
];

const compatibilityStatements = [
  "ALTER TABLE clients ADD COLUMN folder_url TEXT NOT NULL DEFAULT ''",
  "ALTER TABLE clients ADD COLUMN amo_contact_id TEXT NOT NULL DEFAULT ''",
  "ALTER TABLE clients ADD COLUMN amo_lead_id TEXT NOT NULL DEFAULT ''",
  "ALTER TABLE documents ADD COLUMN mime_type TEXT NOT NULL DEFAULT ''",
  "ALTER TABLE documents ADD COLUMN drive_file_id TEXT NOT NULL DEFAULT ''",
  "ALTER TABLE documents ADD COLUMN client_folder_url TEXT NOT NULL DEFAULT ''",
  "ALTER TABLE documents ADD COLUMN amo_lead_id TEXT NOT NULL DEFAULT ''",
  "ALTER TABLE sales_deals ADD COLUMN status_name TEXT NOT NULL DEFAULT ''",
  "ALTER TABLE sales_deals ADD COLUMN pipeline_name TEXT NOT NULL DEFAULT ''",
  "ALTER TABLE sales_deals ADD COLUMN source TEXT NOT NULL DEFAULT ''",
  "ALTER TABLE sales_deals ADD COLUMN responsible_user_name TEXT NOT NULL DEFAULT ''",
  "ALTER TABLE sales_tasks ADD COLUMN responsible_user_name TEXT NOT NULL DEFAULT ''",
];

const demoCleanupStatements = [
  "DELETE FROM agent_events WHERE title IN ('Новый замер из Telegram занесен в таблицу', 'Черновик КП собран и ожидает проверки', 'PNG КП готов по фирменному шаблону', 'Договор подготовлен к проверке', 'Документы разложены в клиентскую базу', 'На завтра есть заказ песка и колец', 'Есть документы, которые ждут действия')",
  "DELETE FROM montages WHERE client_id IN (SELECT id FROM clients WHERE phone LIKE '+7 960 000-00-%' AND amo_lead_id LIKE '41000%')",
  "DELETE FROM measurements WHERE client_id IN (SELECT id FROM clients WHERE phone LIKE '+7 960 000-00-%' AND amo_lead_id LIKE '41000%')",
  "DELETE FROM documents WHERE client_id IN (SELECT id FROM clients WHERE phone LIKE '+7 960 000-00-%' AND amo_lead_id LIKE '41000%')",
  "DELETE FROM clients WHERE phone LIKE '+7 960 000-00-%' AND amo_lead_id LIKE '41000%'",
];

function envText(key: string) {
  return String((env as unknown as Record<string, unknown>)[key] ?? "").trim();
}

function unixDate(value: number | null | undefined) {
  if (!value) {
    return "";
  }
  return new Date(value * 1000).toISOString();
}

function phoneFromLead(lead: AmoLead) {
  const contacts = lead._embedded?.contacts ?? [];
  for (const contact of contacts) {
    for (const field of contact.custom_fields_values ?? []) {
      if (field.field_code === "PHONE") {
        const phone = String(field.values?.[0]?.value ?? "").trim();
        if (phone) {
          return phone;
        }
      }
    }
  }
  return "";
}

function clientNameFromLead(lead: AmoLead) {
  return String(lead._embedded?.contacts?.[0]?.name ?? "").trim();
}

function sourceFromLead(lead: AmoLead) {
  const fields = lead.custom_fields_values ?? [];
  const sourceField = fields.find((field) => {
    const label = `${field.field_code ?? ""} ${field.field_name ?? ""}`.toLowerCase();
    return label.includes("source") || label.includes("utm") || label.includes("источник") || label.includes("канал");
  });
  const fieldValue = sourceField?.values?.[0]?.value;
  if (fieldValue) {
    return cleanText(fieldValue, "", 120);
  }
  return cleanText(lead._embedded?.tags?.[0]?.name, "", 120);
}

async function amoGet<T>(baseUrl: string, accessToken: string, path: string, params?: Record<string, string>) {
  const url = new URL(path, `${baseUrl}/`);
  for (const [key, value] of Object.entries(params ?? {})) {
    url.searchParams.set(key, value);
  }
  const response = await fetch(url.toString(), {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      Accept: "application/json",
    },
  });
  if (!response.ok) {
    throw new Error(`amoCRM request failed: ${path} ${response.status}`);
  }
  return (await response.json()) as T;
}

async function syncAmoSales() {
  const baseUrl = envText("AMOCRM_BASE_URL").replace(/\/+$/, "");
  const accessToken = envText("AMOCRM_ACCESS_TOKEN");
  if (!baseUrl || !accessToken) {
    return;
  }

  const [pipelineData, leadData, taskData, userData] = await Promise.all([
    amoGet<{ _embedded?: { pipelines?: AmoPipeline[] } }>(baseUrl, accessToken, "/api/v4/leads/pipelines"),
    amoGet<{ _embedded?: { leads?: AmoLead[] } }>(baseUrl, accessToken, "/api/v4/leads", {
      with: "contacts",
      limit: "100",
      "order[updated_at]": "desc",
    }),
    amoGet<{ _embedded?: { tasks?: AmoTask[] } }>(baseUrl, accessToken, "/api/v4/tasks", {
      limit: "100",
      "filter[is_completed]": "0",
      "order[complete_till]": "asc",
    }),
    amoGet<{ _embedded?: { users?: AmoUser[] } }>(baseUrl, accessToken, "/api/v4/users", { limit: "100" }),
  ]);

  const pipelines = pipelineData._embedded?.pipelines ?? [];
  const leads = leadData._embedded?.leads ?? [];
  const tasks = taskData._embedded?.tasks ?? [];
  const users = userData._embedded?.users ?? [];
  const pipelineNames = new Map<string, string>();
  const statusNames = new Map<string, string>();
  const userNames = new Map(users.filter((user) => user.id).map((user) => [String(user.id), cleanText(user.name)]));
  for (const pipeline of pipelines) {
    const pipelineId = String(pipeline.id ?? "");
    if (!pipelineId) {
      continue;
    }
    pipelineNames.set(pipelineId, cleanText(pipeline.name));
    for (const status of pipeline._embedded?.statuses ?? []) {
      if (status.id) {
        statusNames.set(`${pipelineId}:${status.id}`, cleanText(status.name));
      }
    }
  }

  const db = d1();
  if (pipelines.length) {
    await db.batch(
      pipelines
        .filter((pipeline) => pipeline.id)
        .map((pipeline) =>
          db
            .prepare(
              "INSERT INTO sales_pipelines (amo_pipeline_id, name, sort, is_main, updated_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT(amo_pipeline_id) DO UPDATE SET name = excluded.name, sort = excluded.sort, is_main = excluded.is_main, updated_at = excluded.updated_at",
            )
            .bind(
              String(pipeline.id),
              cleanText(pipeline.name),
              Number(pipeline.sort) || 0,
              pipeline.is_main ? 1 : 0,
              new Date().toISOString(),
            ),
        ),
    );
  }

  if (leads.length) {
    await db.batch(
      leads
        .filter((lead) => lead.id)
        .map((lead) => {
          const pipelineId = String(lead.pipeline_id ?? "");
          const statusId = String(lead.status_id ?? "");
          return db
            .prepare(
              "INSERT INTO sales_deals (amo_lead_id, title, status_id, status_name, pipeline_id, pipeline_name, source, price, responsible_user_id, responsible_user_name, client_name, phone, next_task_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(amo_lead_id) DO UPDATE SET title = excluded.title, status_id = excluded.status_id, status_name = excluded.status_name, pipeline_id = excluded.pipeline_id, pipeline_name = excluded.pipeline_name, source = excluded.source, price = excluded.price, responsible_user_id = excluded.responsible_user_id, responsible_user_name = excluded.responsible_user_name, client_name = excluded.client_name, phone = excluded.phone, next_task_at = excluded.next_task_at, updated_at = excluded.updated_at",
            )
            .bind(
              String(lead.id),
              cleanText(lead.name),
              statusId,
              statusNames.get(`${pipelineId}:${statusId}`) ?? "",
              pipelineId,
              pipelineNames.get(pipelineId) ?? "",
              sourceFromLead(lead),
              Math.max(0, Number(lead.price) || 0),
              String(lead.responsible_user_id ?? ""),
              userNames.get(String(lead.responsible_user_id ?? "")) ?? "",
              cleanText(clientNameFromLead(lead)),
              cleanText(phoneFromLead(lead)),
              unixDate(lead.closest_task_at),
              unixDate(lead.updated_at),
            );
        }),
    );
  }

  if (tasks.length) {
    await db.batch(
      tasks
        .filter((task) => task.id)
        .map((task) =>
          db
            .prepare(
              "INSERT INTO sales_tasks (amo_task_id, amo_lead_id, entity_type, text, task_type_id, responsible_user_id, responsible_user_name, due_at, is_completed, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(amo_task_id) DO UPDATE SET amo_lead_id = excluded.amo_lead_id, entity_type = excluded.entity_type, text = excluded.text, task_type_id = excluded.task_type_id, responsible_user_id = excluded.responsible_user_id, responsible_user_name = excluded.responsible_user_name, due_at = excluded.due_at, is_completed = excluded.is_completed, updated_at = excluded.updated_at",
            )
            .bind(
              String(task.id),
              task.entity_type === "leads" || task.entity_type === "lead" ? String(task.entity_id ?? "") : "",
              cleanText(task.entity_type),
              cleanText(task.text, "", 900),
              String(task.task_type_id ?? ""),
              String(task.responsible_user_id ?? ""),
              userNames.get(String(task.responsible_user_id ?? "")) ?? "",
              unixDate(task.complete_till),
              task.is_completed ? 1 : 0,
              unixDate(task.updated_at),
            ),
        ),
    );
  }
}

function d1() {
  if (!env.DB) {
    throw new Error("D1 database binding DB is unavailable");
  }
  return env.DB;
}

async function ensureDatabase() {
  const db = d1();
  await db.batch(schemaStatements.map((statement) => db.prepare(statement)));

  for (const statement of compatibilityStatements) {
    try {
      await db.prepare(statement).run();
    } catch {
      // Existing deployed databases already have some of these columns.
    }
  }

  await db.batch(demoCleanupStatements.map((statement) => db.prepare(statement)));

  await db.prepare("PRAGMA optimize").run();
}

function cleanText(value: unknown, fallback = "", max = 480) {
  return String(value ?? fallback).trim().slice(0, max);
}

function extractMeasurer(text: string) {
  const match = text.match(/(?:замерщик|ответственный\s+за\s+замер)\s*[:\-\s]?\s*([А-ЯЁA-Z][а-яёa-z]+)/i);
  return match?.[1] ?? "";
}

function looksLikeMeasurementDeal(row: Record<string, unknown>) {
  const text = `${row.title ?? ""} ${row.statusName ?? ""} ${row.pipelineName ?? ""}`.toLowerCase();
  return text.includes("замер");
}

function looksLikeMeasurementTask(row: Record<string, unknown>) {
  const text = `${row.text ?? ""} ${row.dealTitle ?? ""}`.toLowerCase();
  return text.includes("замер");
}

function buildAmoMeasurementRows(
  salesRows: Array<Record<string, unknown>>,
  taskRows: Array<Record<string, unknown>>,
  existingLeadIds: Set<string>,
) {
  const byLeadId = new Map<string, Record<string, unknown>>();
  for (const row of salesRows) {
    const leadId = cleanText(row.amoLeadId);
    if (!leadId || existingLeadIds.has(leadId) || !looksLikeMeasurementDeal(row)) {
      continue;
    }
    byLeadId.set(leadId, row);
  }

  for (const task of taskRows) {
    const leadId = cleanText(task.amoLeadId);
    if (!leadId || existingLeadIds.has(leadId) || !looksLikeMeasurementTask(task)) {
      continue;
    }
    byLeadId.set(leadId, { ...(byLeadId.get(leadId) ?? {}), ...task });
  }

  return Array.from(byLeadId.entries()).map(([leadId, row]) => {
    const taskText = cleanText(row.text, "", 900);
    const title = cleanText(row.dealTitle) || cleanText(row.title) || `Сделка ${leadId}`;
    return {
      id: `amo-${leadId}`,
      clientName: cleanText(row.clientName) || title,
      phone: cleanText(row.phone),
      address: title,
      status: "from_amocrm",
      source: "amocrm",
      scheduledAt: cleanText(row.dueAt) || cleanText(row.nextTaskAt),
      measuredAt: "",
      soil: "",
      groundwater: "",
      pipeDepth: "",
      distanceToHouse: "",
      recommendedEquipment: "",
      photosCount: 0,
      telegramChatId: "",
      amoLeadId: leadId,
      sheetRowUrl: "",
      notes: taskText,
      taskText,
      measurer: extractMeasurer(taskText),
      manager: cleanText(row.responsibleUserName) || cleanText(row.responsibleUserId),
      createdAt: cleanText(row.updatedAt) || new Date().toISOString(),
    };
  });
}

export async function GET() {
  try {
    await ensureDatabase();
    try {
      await syncAmoSales();
    } catch {
      // The dashboard must remain available when amoCRM credentials expire.
    }
    const db = d1();
    const documents = await db
      .prepare(
        "SELECT documents.id, documents.type, documents.title, documents.status, documents.amount, documents.equipment, documents.file_url AS fileUrl, documents.mime_type AS mimeType, documents.drive_file_id AS driveFileId, documents.client_folder_url AS clientFolderUrl, documents.amo_lead_id AS amoLeadId, documents.due_date AS dueDate, documents.created_at AS createdAt, clients.name AS clientName, clients.phone, clients.address, clients.manager FROM documents JOIN clients ON clients.id = documents.client_id ORDER BY documents.updated_at DESC, documents.id DESC LIMIT 100",
      )
      .all();
    const measurements = await db
      .prepare(
        "SELECT measurements.id, measurements.status, measurements.source, measurements.scheduled_at AS scheduledAt, measurements.measured_at AS measuredAt, measurements.soil, measurements.groundwater, measurements.pipe_depth AS pipeDepth, measurements.distance_to_house AS distanceToHouse, measurements.recommended_equipment AS recommendedEquipment, measurements.photos_count AS photosCount, measurements.telegram_chat_id AS telegramChatId, measurements.amo_lead_id AS amoLeadId, measurements.sheet_row_url AS sheetRowUrl, measurements.notes, measurements.created_at AS createdAt, clients.name AS clientName, clients.phone, clients.address, clients.manager FROM measurements JOIN clients ON clients.id = measurements.client_id ORDER BY measurements.scheduled_at DESC, measurements.id DESC LIMIT 80",
      )
      .all();
    const montages = await db
      .prepare(
        "SELECT montages.id, montages.install_date AS installDate, montages.status, montages.equipment, montages.amount, montages.sand_tons AS sandTons, montages.gravel_tons AS gravelTons, montages.rings, montages.team, montages.manager, montages.proposal_url AS proposalUrl, montages.contract_url AS contractUrl, montages.reminder_at AS reminderAt, montages.reminder_status AS reminderStatus, montages.reminder_text AS reminderText, clients.name AS clientName, clients.phone, clients.address FROM montages JOIN clients ON clients.id = montages.client_id ORDER BY montages.install_date ASC, montages.id ASC LIMIT 80",
      )
      .all();
    const events = await db
      .prepare(
        "SELECT id, agent, title, status, document_id AS documentId, created_at AS createdAt FROM agent_events ORDER BY id DESC LIMIT 20",
      )
      .all();
    const sales = await db
      .prepare(
        "SELECT id, amo_lead_id AS amoLeadId, title, status_id AS statusId, status_name AS statusName, pipeline_id AS pipelineId, pipeline_name AS pipelineName, source, price, responsible_user_id AS responsibleUserId, responsible_user_name AS responsibleUserName, client_name AS clientName, phone, next_task_at AS nextTaskAt, updated_at AS updatedAt FROM sales_deals ORDER BY updated_at DESC, id DESC LIMIT 100",
      )
      .all();
    const salesPipelines = await db
      .prepare(
        "SELECT sales_pipelines.id, sales_pipelines.amo_pipeline_id AS amoPipelineId, sales_pipelines.name, COUNT(sales_deals.id) AS dealsCount, COALESCE(SUM(sales_deals.price), 0) AS amount FROM sales_pipelines LEFT JOIN sales_deals ON sales_deals.pipeline_id = sales_pipelines.amo_pipeline_id GROUP BY sales_pipelines.id, sales_pipelines.amo_pipeline_id, sales_pipelines.name ORDER BY sales_pipelines.sort ASC, sales_pipelines.id ASC",
      )
      .all();
    const salesTasks = await db
      .prepare(
        "SELECT sales_tasks.id, sales_tasks.amo_task_id AS amoTaskId, sales_tasks.amo_lead_id AS amoLeadId, sales_tasks.text, sales_tasks.responsible_user_id AS responsibleUserId, sales_tasks.responsible_user_name AS responsibleUserName, sales_tasks.due_at AS dueAt, sales_deals.title AS dealTitle, sales_deals.client_name AS clientName FROM sales_tasks LEFT JOIN sales_deals ON sales_deals.amo_lead_id = sales_tasks.amo_lead_id WHERE sales_tasks.is_completed = 0 ORDER BY sales_tasks.due_at ASC, sales_tasks.id DESC LIMIT 100",
      )
      .all();
    const measurementResults = (measurements.results ?? []) as Array<Record<string, unknown>>;
    const salesResults = (sales.results ?? []) as Array<Record<string, unknown>>;
    const salesTaskResults = (salesTasks.results ?? []) as Array<Record<string, unknown>>;
    const existingMeasurementLeadIds = new Set(measurementResults.map((row) => cleanText(row.amoLeadId)).filter(Boolean));
    const amoMeasurementRows = buildAmoMeasurementRows(salesResults, salesTaskResults, existingMeasurementLeadIds);
    const docStats = await db
      .prepare(
        "SELECT SUM(CASE WHEN type = 'proposal' THEN 1 ELSE 0 END) AS proposals, SUM(CASE WHEN type = 'contract' THEN 1 ELSE 0 END) AS contracts, SUM(CASE WHEN status IN ('signed', 'approved', 'issued') THEN amount ELSE 0 END) AS activeAmount, SUM(CASE WHEN status IN ('draft', 'needs_review', 'ready') THEN 1 ELSE 0 END) AS attention FROM documents",
      )
      .first();
    const operationStats = await db
      .prepare(
        "SELECT (SELECT COUNT(*) FROM measurements) AS measurements, (SELECT COUNT(*) FROM montages) AS montages, (SELECT SUM(CASE WHEN reminder_status = 'due_tomorrow' THEN 1 ELSE 0 END) FROM montages) AS tomorrowOrders, (SELECT SUM(amount) FROM montages) AS monthlyAmount",
      )
      .first();
    const salesStats = await db
      .prepare("SELECT COUNT(*) AS salesDeals, SUM(price) AS salesAmount FROM sales_deals")
      .first();

    return Response.json({
      stats: { ...docStats, ...operationStats, ...salesStats, measurements: measurementResults.length + amoMeasurementRows.length },
      documents: documents.results,
      measurements: [...measurementResults, ...amoMeasurementRows],
      montages: montages.results,
      sales: salesResults,
      salesPipelines: salesPipelines.results,
      salesTasks: salesTaskResults,
      events: events.results,
    });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Dashboard error" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    await ensureDatabase();
    const payload = (await request.json()) as IncomingDocument;
    const db = d1();
    const clientName = cleanText(payload.clientName);
    const title = cleanText(payload.title);
    const type = payload.type === "contract" ? "contract" : "proposal";
    const payloadAmoLeadId = cleanText(payload.amoLeadId);

    if (!clientName || !title) {
      return Response.json({ error: "clientName and title are required" }, { status: 400 });
    }

    const existing = await db
      .prepare("SELECT id, folder_url AS folderUrl, amo_lead_id AS amoLeadId FROM clients WHERE phone = ? OR name = ? ORDER BY id LIMIT 1")
      .bind(cleanText(payload.phone), clientName)
      .first<{ id: number; folderUrl: string; amoLeadId: string }>();
    let clientId = existing?.id;

    if (!clientId) {
      const created = await db
        .prepare("INSERT INTO clients (name, phone, address, manager, amo_lead_id) VALUES (?, ?, ?, ?, ?) RETURNING id")
        .bind(clientName, cleanText(payload.phone), cleanText(payload.address), "Кабинет", payloadAmoLeadId)
        .first<{ id: number }>();
      clientId = created?.id;
    } else if (payloadAmoLeadId && !existing?.amoLeadId) {
      await db.prepare("UPDATE clients SET amo_lead_id = ? WHERE id = ?").bind(payloadAmoLeadId, clientId).run();
    }

    const doc = await db
      .prepare(
        "INSERT INTO documents (client_id, type, title, status, amount, equipment, file_url, mime_type, client_folder_url, amo_lead_id, due_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
      )
      .bind(
        clientId,
        type,
        title,
        cleanText(payload.status, "draft"),
        Math.max(0, Number(payload.amount) || 0),
        cleanText(payload.equipment),
        cleanText(payload.fileUrl, "", 900),
        type === "contract" ? "application/pdf" : "image/png",
        cleanText(existing?.folderUrl, "", 900),
        payloadAmoLeadId || cleanText(existing?.amoLeadId),
        cleanText(payload.dueDate),
      )
      .first<{ id: number }>();

    await db
      .prepare("INSERT INTO agent_events (agent, title, status, document_id) VALUES (?, ?, ?, ?)")
      .bind("se.document_keeper", `${type === "contract" ? "Договор PDF" : "КП PNG"} добавлен в базу`, "ok", doc?.id ?? null)
      .run();

    return Response.json({ ok: true, id: doc?.id }, { status: 201 });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Create error" }, { status: 500 });
  }
}
