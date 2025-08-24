CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    text_content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    views INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
CREATE INDEX IF NOT EXISTS idx_articles_title ON articles(title);
CREATE INDEX IF NOT EXISTS idx_articles_scraped_at ON articles(scraped_at);
CREATE INDEX IF NOT EXISTS idx_articles_views ON articles(views);
CREATE INDEX IF NOT EXISTS idx_articles_score ON articles(score);
