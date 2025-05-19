CREATE TABLE IF NOT EXISTS users ( -- Primarily for the blog owner
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    blog_title TEXT NOT NULL, -- The title they chose for their blog
    registration_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL, -- Owner of the post
    title TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL, -- For clean URLs
    content TEXT NOT NULL,
    creation_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_modified_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_published BOOLEAN DEFAULT TRUE, -- Could be used for drafts
    view_count INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    slug TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS post_tags (
    post_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (post_id, tag_id),
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    commenter_name TEXT NOT NULL,
    commenter_email TEXT, -- Optional, but good for notifications if owner wants
    content TEXT NOT NULL,
    submission_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_approved BOOLEAN DEFAULT FALSE,
    approved_by_user_id INTEGER, -- The user_id of the blog owner who approved it
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS likes ( -- "Aprecieri"
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    liker_identifier TEXT NOT NULL, -- Could be IP address + User-Agent hash for anonymous, or user_id if you implement reader accounts
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (post_id, liker_identifier), -- Prevent multiple likes from same identifier per post
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);
