# ⏰ Personal Events & Reminders Bot

A Telegram bot to help users manage personal events, get reminders, and see statistics. Powered by `aiogram` and backed by either **PostgreSQL** or **MongoDB**, this bot provides a smooth and useful interface to organize your life.

---

## 🚀 Features

- 📝 Create events with title, description, date, time, and category
- 🔔 Sends automatic reminders before event time
- 📆 View upcoming events in a neat, readable format
- 📊 Get monthly statistics: event count, most-used category
- 🗃️ Built-in database models (PostgreSQL or MongoDB)

---

## 🛠️ Technologies Used

- 🐍 Python 3.11+
- 🤖 [Aiogram 3.x](https://docs.aiogram.dev)
- 🐘 PostgreSQL **or** 🍃 MongoDB
- 📦 Asyncpg / Motor (depending on DB)
- 🕘 APScheduler (for scheduled reminders)
- 🌐 Dotenv

---

## 🧱 PostgreSQL Database Schema

### 👤 Users

| Column      | Type      | Description       |
| ----------- | --------- | ----------------- |
| id          | SERIAL    | Primary key       |
| telegram_id | BIGINT    | Telegram user ID  |
| username    | TEXT      | Telegram username |
| joined_at   | TIMESTAMP | Registration time |

### 🗂️ Categories

| Column | Type   | Description        |
| ------ | ------ | ------------------ |
| id     | SERIAL | Primary key        |
| name   | TEXT   | e.g., Work, Health |

### 📅 Events

| Column      | Type                    | Description             |
| ----------- | ----------------------- | ----------------------- |
| id          | SERIAL                  | Primary key             |
| user_id     | INTEGER                 | FK → Users(id)          |
| category_id | INTEGER                 | FK → Categories(id)     |
| title       | TEXT                    | Event title             |
| description | TEXT                    | Event description       |
| event_time  | TIMESTAMP               | Scheduled time of event |
| remind_at   | TIMESTAMP               | When to send reminder   |
| created_at  | TIMESTAMP DEFAULT NOW() | When event created      |

---

## 🍃 MongoDB Collection Models (Alternative)

### `users`

```json
{
  "_id": ObjectId,
  "telegram_id": 123456789,
  "username": "user123",
  "joined_at": "2024-06-01T12:34:56"
}
```
