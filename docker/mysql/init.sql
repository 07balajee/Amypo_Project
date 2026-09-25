-- Runs once, on the first start of the bundled MySQL container (empty data volume).
-- The entrypoint has already created MYSQL_USER (DB_USER in .env, default 'amypo') so give it both
-- platform databases. If you change DB_USER, change the user name below to match.
CREATE DATABASE IF NOT EXISTS amypo_ops CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS amypo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON amypo_ops.* TO 'amypo'@'%';
GRANT ALL PRIVILEGES ON amypo.* TO 'amypo'@'%';
FLUSH PRIVILEGES;
