-- Initial schema for resume_builder (MySQL 8+)
-- Safe to run multiple times because of IF NOT EXISTS guards.

CREATE TABLE IF NOT EXISTS `user` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `email` VARCHAR(120) NOT NULL,
  `password_hash` VARCHAR(256) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `resume` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `resume_data` JSON NOT NULL,
  `template` VARCHAR(50) NOT NULL DEFAULT 'classic',
  `source_type` VARCHAR(20) NOT NULL DEFAULT 'manual',
  `parser_confidence` FLOAT NULL,
  `original_resume_file` VARCHAR(255) NULL,
  `parser_generated_at` DATETIME NULL,
  `parser_mapping_version` VARCHAR(64) NULL,
  `created_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_resume_user_id` (`user_id`),
  CONSTRAINT `fk_resume_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `occupations` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `onet_code` VARCHAR(32) NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `description` TEXT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_occupations_onet_code` (`onet_code`),
  KEY `ix_occupations_title` (`title`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `technology_skills` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `onet_code` VARCHAR(32) NOT NULL,
  `technology` VARCHAR(255) NOT NULL,
  `trendy` CHAR(1) NOT NULL DEFAULT 'N',
  `demand` CHAR(1) NOT NULL DEFAULT 'N',
  PRIMARY KEY (`id`),
  KEY `ix_technology_skills_onet_code` (`onet_code`),
  KEY `ix_technology_skills_demand` (`demand`),
  KEY `ix_technology_skills_trendy` (`trendy`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
