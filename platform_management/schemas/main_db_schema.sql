CREATE TABLE IF NOT EXISTS blogs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subdomain_name TEXT UNIQUE NOT NULL,
    blog_title TEXT NOT NULL,
    owner_user_id INTEGER NOT NULL, -- Corresponds to the user ID in their own instance_db
    owner_email TEXT UNIQUE NOT NULL,
    creation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    subscription_status TEXT DEFAULT 'trial', -- e.g., trial, active, past_due, canceled
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    last_payment_date DATETIME,
    trial_ends_at DATETIME
);

CREATE TABLE IF NOT EXISTS shared_posts_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_post_id_on_instance INTEGER NOT NULL,
    blog_instance_subdomain TEXT NOT NULL, -- e.g., "numeleautorului"
    post_title TEXT NOT NULL,
    post_creation_date DATETIME NOT NULL, -- Original creation date of the post
    post_link TEXT NOT NULL, -- Full URL to the post
    added_to_main_db_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (blog_instance_subdomain) REFERENCES blogs(subdomain_name) ON DELETE CASCADE
);
