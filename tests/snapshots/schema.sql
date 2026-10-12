-- index ix_items_user_created
CREATE INDEX ix_items_user_created ON items (user_id, created_at);

-- index ix_items_user_id
CREATE INDEX ix_items_user_id ON items (user_id);

-- index ix_users_username
CREATE UNIQUE INDEX ix_users_username ON users (username);

-- table items
CREATE TABLE items (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	title VARCHAR(300) NOT NULL,
	body TEXT NOT NULL,
	pinned BOOLEAN NOT NULL,
	done BOOLEAN NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- table settings
CREATE TABLE settings (
	"key" VARCHAR(50) NOT NULL,
	value VARCHAR(500) NOT NULL,
	PRIMARY KEY ("key")
);

-- table users
CREATE TABLE users (
	id INTEGER NOT NULL,
	username VARCHAR(80) NOT NULL,
	name VARCHAR(120),
	password_hash VARCHAR(256) NOT NULL,
	is_admin BOOLEAN NOT NULL,
	theme VARCHAR(10) NOT NULL,
	view_mode VARCHAR(10) NOT NULL,
	infinite_scroll BOOLEAN NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id)
);
