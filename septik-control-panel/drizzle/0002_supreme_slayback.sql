CREATE TABLE `measurements` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`client_id` integer NOT NULL,
	`status` text NOT NULL,
	`source` text DEFAULT 'telegram' NOT NULL,
	`scheduled_at` text DEFAULT '' NOT NULL,
	`measured_at` text DEFAULT '' NOT NULL,
	`soil` text DEFAULT '' NOT NULL,
	`groundwater` text DEFAULT '' NOT NULL,
	`pipe_depth` text DEFAULT '' NOT NULL,
	`distance_to_house` text DEFAULT '' NOT NULL,
	`recommended_equipment` text DEFAULT '' NOT NULL,
	`photos_count` integer DEFAULT 0 NOT NULL,
	`telegram_chat_id` text DEFAULT '' NOT NULL,
	`amo_lead_id` text DEFAULT '' NOT NULL,
	`sheet_row_url` text DEFAULT '' NOT NULL,
	`notes` text DEFAULT '' NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL
);
--> statement-breakpoint
CREATE INDEX `idx_measurements_status_date` ON `measurements` (`status`,`scheduled_at`);--> statement-breakpoint
CREATE TABLE `montages` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`client_id` integer NOT NULL,
	`install_date` text NOT NULL,
	`status` text NOT NULL,
	`equipment` text DEFAULT '' NOT NULL,
	`amount` integer DEFAULT 0 NOT NULL,
	`sand_tons` integer DEFAULT 0 NOT NULL,
	`gravel_tons` integer DEFAULT 0 NOT NULL,
	`rings` text DEFAULT '' NOT NULL,
	`team` text DEFAULT '' NOT NULL,
	`manager` text DEFAULT '' NOT NULL,
	`proposal_url` text DEFAULT '' NOT NULL,
	`contract_url` text DEFAULT '' NOT NULL,
	`reminder_at` text DEFAULT '' NOT NULL,
	`reminder_status` text DEFAULT 'scheduled' NOT NULL,
	`reminder_text` text DEFAULT '' NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL
);
--> statement-breakpoint
CREATE INDEX `idx_montages_date_status` ON `montages` (`install_date`,`status`);--> statement-breakpoint
ALTER TABLE `clients` ADD `folder_url` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `clients` ADD `amo_contact_id` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `clients` ADD `amo_lead_id` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `documents` ADD `mime_type` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `documents` ADD `drive_file_id` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `documents` ADD `client_folder_url` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `documents` ADD `amo_lead_id` text DEFAULT '' NOT NULL;