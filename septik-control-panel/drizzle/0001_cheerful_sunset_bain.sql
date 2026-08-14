CREATE INDEX `idx_agent_events_created` ON `agent_events` (`created_at`);--> statement-breakpoint
CREATE INDEX `idx_documents_type_status` ON `documents` (`type`,`status`);--> statement-breakpoint
CREATE INDEX `idx_documents_client_created` ON `documents` (`client_id`,`created_at`);