import { sql } from "drizzle-orm";
import { index, integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const clients = sqliteTable("clients", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  name: text("name").notNull(),
  phone: text("phone").notNull().default(""),
  address: text("address").notNull().default(""),
  manager: text("manager").notNull().default(""),
  folderUrl: text("folder_url").notNull().default(""),
  amoContactId: text("amo_contact_id").notNull().default(""),
  amoLeadId: text("amo_lead_id").notNull().default(""),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const documents = sqliteTable(
  "documents",
  {
    id: integer("id").primaryKey({ autoIncrement: true }),
    clientId: integer("client_id").notNull(),
    type: text("type").notNull(),
    title: text("title").notNull(),
    status: text("status").notNull(),
    amount: integer("amount").notNull().default(0),
    equipment: text("equipment").notNull().default(""),
    fileUrl: text("file_url").notNull().default(""),
    mimeType: text("mime_type").notNull().default(""),
    driveFileId: text("drive_file_id").notNull().default(""),
    clientFolderUrl: text("client_folder_url").notNull().default(""),
    amoLeadId: text("amo_lead_id").notNull().default(""),
    dueDate: text("due_date").notNull().default(""),
    createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
    updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  },
  (table) => [
    index("idx_documents_type_status").on(table.type, table.status),
    index("idx_documents_client_created").on(table.clientId, table.createdAt),
  ],
);

export const measurements = sqliteTable(
  "measurements",
  {
    id: integer("id").primaryKey({ autoIncrement: true }),
    clientId: integer("client_id").notNull(),
    status: text("status").notNull(),
    source: text("source").notNull().default("telegram"),
    scheduledAt: text("scheduled_at").notNull().default(""),
    measuredAt: text("measured_at").notNull().default(""),
    soil: text("soil").notNull().default(""),
    groundwater: text("groundwater").notNull().default(""),
    pipeDepth: text("pipe_depth").notNull().default(""),
    distanceToHouse: text("distance_to_house").notNull().default(""),
    recommendedEquipment: text("recommended_equipment").notNull().default(""),
    photosCount: integer("photos_count").notNull().default(0),
    telegramChatId: text("telegram_chat_id").notNull().default(""),
    amoLeadId: text("amo_lead_id").notNull().default(""),
    sheetRowUrl: text("sheet_row_url").notNull().default(""),
    notes: text("notes").notNull().default(""),
    createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
    updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  },
  (table) => [index("idx_measurements_status_date").on(table.status, table.scheduledAt)],
);

export const montages = sqliteTable(
  "montages",
  {
    id: integer("id").primaryKey({ autoIncrement: true }),
    clientId: integer("client_id").notNull(),
    installDate: text("install_date").notNull(),
    status: text("status").notNull(),
    equipment: text("equipment").notNull().default(""),
    amount: integer("amount").notNull().default(0),
    sandTons: integer("sand_tons").notNull().default(0),
    gravelTons: integer("gravel_tons").notNull().default(0),
    rings: text("rings").notNull().default(""),
    team: text("team").notNull().default(""),
    manager: text("manager").notNull().default(""),
    proposalUrl: text("proposal_url").notNull().default(""),
    contractUrl: text("contract_url").notNull().default(""),
    reminderAt: text("reminder_at").notNull().default(""),
    reminderStatus: text("reminder_status").notNull().default("scheduled"),
    reminderText: text("reminder_text").notNull().default(""),
    createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
    updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  },
  (table) => [index("idx_montages_date_status").on(table.installDate, table.status)],
);

export const salesDeals = sqliteTable(
  "sales_deals",
  {
    id: integer("id").primaryKey({ autoIncrement: true }),
    amoLeadId: text("amo_lead_id").notNull().unique(),
    title: text("title").notNull().default(""),
    statusId: text("status_id").notNull().default(""),
    statusName: text("status_name").notNull().default(""),
    pipelineId: text("pipeline_id").notNull().default(""),
    pipelineName: text("pipeline_name").notNull().default(""),
    source: text("source").notNull().default(""),
    price: integer("price").notNull().default(0),
    responsibleUserId: text("responsible_user_id").notNull().default(""),
    responsibleUserName: text("responsible_user_name").notNull().default(""),
    clientName: text("client_name").notNull().default(""),
    phone: text("phone").notNull().default(""),
    nextTaskAt: text("next_task_at").notNull().default(""),
    updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  },
  (table) => [
    index("idx_sales_deals_status").on(table.pipelineId, table.statusId),
    index("idx_sales_deals_updated").on(table.updatedAt),
    index("idx_sales_deals_source").on(table.source),
  ],
);

export const salesPipelines = sqliteTable("sales_pipelines", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  amoPipelineId: text("amo_pipeline_id").notNull().unique(),
  name: text("name").notNull().default(""),
  sort: integer("sort").notNull().default(0),
  isMain: integer("is_main").notNull().default(0),
  updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const salesTasks = sqliteTable(
  "sales_tasks",
  {
    id: integer("id").primaryKey({ autoIncrement: true }),
    amoTaskId: text("amo_task_id").notNull().unique(),
    amoLeadId: text("amo_lead_id").notNull().default(""),
    entityType: text("entity_type").notNull().default(""),
    text: text("text").notNull().default(""),
    taskTypeId: text("task_type_id").notNull().default(""),
    responsibleUserId: text("responsible_user_id").notNull().default(""),
    responsibleUserName: text("responsible_user_name").notNull().default(""),
    dueAt: text("due_at").notNull().default(""),
    isCompleted: integer("is_completed").notNull().default(0),
    updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  },
  (table) => [index("idx_sales_tasks_due").on(table.dueAt, table.isCompleted)],
);

export const agentEvents = sqliteTable(
  "agent_events",
  {
    id: integer("id").primaryKey({ autoIncrement: true }),
    agent: text("agent").notNull(),
    title: text("title").notNull(),
    status: text("status").notNull(),
    documentId: integer("document_id"),
    createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  },
  (table) => [index("idx_agent_events_created").on(table.createdAt)],
);
