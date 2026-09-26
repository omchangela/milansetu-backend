-- Run this once in your MySQL database to create the auth tables
-- that Django's custom User model expects (managed = False means Django won't create them).

CREATE TABLE IF NOT EXISTS `users` (
    `id`           BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `password`     VARCHAR(128) NOT NULL,
    `last_login`   DATETIME(6) NULL,
    `is_superuser` TINYINT(1) NOT NULL DEFAULT 0,
    `email`        VARCHAR(254) NOT NULL UNIQUE,
    `phone`        VARCHAR(20) NULL UNIQUE,
    `is_active`    TINYINT(1) NOT NULL DEFAULT 1,
    `is_staff`     TINYINT(1) NOT NULL DEFAULT 0,
    `date_joined`  DATETIME(6) NOT NULL
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `user_profiles` (
    `id`                  BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `user_id`             BIGINT NOT NULL UNIQUE,
    `full_name`           VARCHAR(255) NULL,
    `age`                 INT NULL,
    `height_cm`           INT NULL,
    `religion`            VARCHAR(100) NULL,
    `mother_tongue`       VARCHAR(100) NULL,
    `marital_status`      VARCHAR(100) NULL,
    `father_occupation`   VARCHAR(255) NULL,
    `mother_occupation`   VARCHAR(255) NULL,
    `siblings_count`      INT NULL,
    `siblings_details`    TEXT NULL,
    `family_values`       VARCHAR(255) NULL,
    `industry`            VARCHAR(255) NULL,
    `education`           VARCHAR(255) NULL,
    `current_designation` VARCHAR(255) NULL,
    `current_company`     VARCHAR(255) NULL,
    `annual_income_min`   DECIMAL(10, 2) NULL,
    `annual_income_max`   DECIMAL(10, 2) NULL,
    `income_unit`         VARCHAR(20) NULL,
    `date_of_birth`       DATE NULL,
    `time_of_birth`       TIME(6) NULL,
    `birth_place`         VARCHAR(255) NULL,
    `zodiac_sign`         VARCHAR(100) NULL,
    `manglik_status`      VARCHAR(50) NULL,
    `kundali_url`         VARCHAR(500) NULL,
    `created_at`          DATETIME(6) NOT NULL,
    `updated_at`          DATETIME(6) NOT NULL,
    CONSTRAINT `fk_userprofile_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Django permission M2M tables for the custom User model
CREATE TABLE IF NOT EXISTS `users_groups` (
    `id`       BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `user_id`  BIGINT NOT NULL,
    `group_id` INT NOT NULL,
    UNIQUE KEY `users_groups_user_id_group_id` (`user_id`, `group_id`),
    CONSTRAINT `fk_usersgroups_user`  FOREIGN KEY (`user_id`)  REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_usersgroups_group` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS `users_user_permissions` (
    `id`            BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `user_id`       BIGINT NOT NULL,
    `permission_id` INT NOT NULL,
    UNIQUE KEY `users_user_perms_user_id_perm_id` (`user_id`, `permission_id`),
    CONSTRAINT `fk_usersperms_user` FOREIGN KEY (`user_id`)       REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_usersperms_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
