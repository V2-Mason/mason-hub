-- Video Review Database Schema
-- Mason 视频复盘系统 -- 4 节点追踪 (D7/D30/D60/D90)
-- 关联 mason-decision-system 形成赛道决策闭环

PRAGMA foreign_keys = ON;

-- ============================================================
-- 视频主表
-- ============================================================
CREATE TABLE IF NOT EXISTS videos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  platform TEXT NOT NULL CHECK(platform IN ('bilibili', 'xiaohongshu')),
  platform_id TEXT NOT NULL,           -- BV号 或 小红书 note_id
  title TEXT NOT NULL,
  publish_date DATE NOT NULL,
  url TEXT,
  duration_sec INTEGER,                -- 视频时长(秒)
  -- 内容分类
  topic TEXT,                          -- A1_xiaohongshu / B_qiafan / D_operations 等
  target_audience TEXT,                -- 35+转型者 / 行动力0 / Vibe Coder / 在职程序员
  content_pillar TEXT,                 -- 内容支柱（你定义的标签）
  -- 制作成本
  production_hours REAL,               -- 制作耗时(小时)
  -- 关联决策
  decision_id INTEGER,                 -- FK to decision_links
  hypothesis TEXT,                     -- 这条视频在验证什么假设
  -- 时间戳
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(platform, platform_id)
);

CREATE INDEX IF NOT EXISTS idx_videos_publish_date ON videos(publish_date);
CREATE INDEX IF NOT EXISTS idx_videos_platform ON videos(platform);
CREATE INDEX IF NOT EXISTS idx_videos_topic ON videos(topic);

-- ============================================================
-- 数据快照表（每个 checkpoint 一行）
-- ============================================================
CREATE TABLE IF NOT EXISTS snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id INTEGER NOT NULL,
  checkpoint TEXT NOT NULL CHECK(checkpoint IN ('D0', 'D7', 'D30', 'D60', 'D90', 'AD_HOC')),
  snapshot_date DATE NOT NULL,

  -- 自动抓取（B站 API）
  views INTEGER,                       -- 播放量
  likes INTEGER,                       -- 点赞
  coins INTEGER,                       -- 投币
  favorites INTEGER,                   -- 收藏
  shares INTEGER,                      -- 分享
  comments_count INTEGER,              -- 评论数
  danmaku INTEGER,                     -- 弹幕
  followers_total INTEGER,             -- 当时账号总粉丝（参考）

  -- 衍生指标（自动算）
  interaction_rate REAL,               -- (likes+coins+favs+shares+comments) / views
  charge_count INTEGER,                -- 充电数（B站后台）

  -- 流量来源（手动填，B站后台才有）
  traffic_search_pct REAL,
  traffic_recommend_pct REAL,
  traffic_homepage_pct REAL,
  traffic_followed_pct REAL,

  -- 手动填写的"金主友好型"指标
  quality_comment_pct REAL,            -- 优质评论比 ⭐
  quality_comment_examples TEXT,       -- JSON: 摘录的优质评论
  dm_inquiries INTEGER DEFAULT 0,      -- 私信咨询数
  conversion_signals INTEGER DEFAULT 0,-- 评论里的转化信号（提到"想要"/"求资料"）

  -- 长尾健康度（D30/D60/D90 才有意义）
  growth_since_d7 INTEGER,             -- 自 D7 以来的播放增长
  followers_from_video INTEGER,        -- 这条视频带来的累计涨粉
  still_growing BOOLEAN,               -- 是否还在涨粉

  -- 洞察
  insights TEXT,                       -- 这次复盘的发现
  next_actions TEXT,                   -- 下一步行动

  -- 时间戳
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
  UNIQUE(video_id, checkpoint)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_video ON snapshots(video_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_checkpoint ON snapshots(checkpoint);
CREATE INDEX IF NOT EXISTS idx_snapshots_date ON snapshots(snapshot_date);

-- ============================================================
-- 评论库（每次抓取归档，用于 quality_comment_pct 计算）
-- ============================================================
CREATE TABLE IF NOT EXISTS comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id INTEGER NOT NULL,
  fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  checkpoint TEXT,                     -- 哪个 checkpoint 抓的
  author TEXT,
  content TEXT NOT NULL,
  likes INTEGER DEFAULT 0,
  -- 人工或半自动判断
  is_quality BOOLEAN,                  -- 是否优质
  category TEXT,                       -- 'real_need'/'conversion_signal'/'request_resource'/'noise'
  notes TEXT,                          -- 你对这条评论的笔记
  FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_comments_video ON comments(video_id);
CREATE INDEX IF NOT EXISTS idx_comments_quality ON comments(is_quality);

-- ============================================================
-- 决策关联表（mason-decision-system 闭环）
-- ============================================================
CREATE TABLE IF NOT EXISTS decision_links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id INTEGER NOT NULL,
  decision_record_path TEXT NOT NULL,  -- 指向 ~/vault/decisions/YYYY-MM-DD-xxx.md
  decision_title TEXT,
  hypothesis TEXT NOT NULL,
  expected_outcome TEXT,               -- 预期结果
  validation_checkpoint TEXT DEFAULT 'D90',
  -- D90 自动判断结果
  validated_at TIMESTAMP,
  validation_result TEXT CHECK(validation_result IN (NULL, 'confirmed', 'partial', 'rejected')),
  validation_evidence TEXT,            -- 支持判断的具体数据
  FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_decision_links_video ON decision_links(video_id);

-- ============================================================
-- 提醒任务表（与 Google Calendar 同步）
-- ============================================================
CREATE TABLE IF NOT EXISTS reminders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id INTEGER NOT NULL,
  checkpoint TEXT NOT NULL,
  due_date DATE NOT NULL,
  gcal_event_id TEXT,                  -- Google Calendar event ID（用于更新/删除）
  status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'completed', 'skipped')),
  completed_at TIMESTAMP,
  FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
  UNIQUE(video_id, checkpoint)
);

CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(due_date);
CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status);

-- ============================================================
-- 视图：当前需要复盘的视频
-- ============================================================
CREATE VIEW IF NOT EXISTS pending_reviews AS
SELECT
  v.id as video_id,
  v.platform,
  v.platform_id,
  v.title,
  v.publish_date,
  r.checkpoint,
  r.due_date,
  julianday(r.due_date) - julianday('now') as days_until_due
FROM videos v
JOIN reminders r ON v.id = r.video_id
WHERE r.status = 'pending'
ORDER BY r.due_date ASC;

-- ============================================================
-- 视图：账号健康度仪表盘
-- ============================================================
CREATE VIEW IF NOT EXISTS account_dashboard AS
SELECT
  v.platform,
  COUNT(DISTINCT v.id) as total_videos,
  AVG(s.interaction_rate) as avg_interaction_rate,
  AVG(s.quality_comment_pct) as avg_quality_comment_pct,
  SUM(s.views) as total_views,
  SUM(s.followers_from_video) as total_followers_from_videos
FROM videos v
LEFT JOIN snapshots s ON v.id = s.video_id AND s.checkpoint = 'D90'
GROUP BY v.platform;
