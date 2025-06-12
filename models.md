MongoDB Models for Event Reminder Bot
Collections
The bot uses three MongoDB collections: users, categories, and events. Below are their structures and purposes.
Users
Stores user information.

user_id: String (Telegram user ID, primary identifier)
username: String (optional, Telegram username)
first_name: String (optional)
last_name: String (optional)
created_at: DateTime (when user was registered)
Example:{
"user_id": "123456789",
"username": "john_doe",
"first_name": "John",
"last_name": "Doe",
"created_at": "2025-06-12T06:47:00Z"
}

Categories
Stores event categories for each user.

\_id: ObjectId (MongoDB-generated ID)
user_id: String (Telegram user ID)
name: String (category name, e.g., "Work")
created_at: DateTime
Example:{
"\_id": "60a7b8c9d4e3f2a1b2c3d4e5",
"user_id": "123456789",
"name": "Work",
"created_at": "2025-06-12T06:47:00Z"
}

Events
Stores user events with reminder details.

\_id: ObjectId (MongoDB-generated ID)
user_id: String (Telegram user ID)
title: String (event title)
description: String (event description)
date_time: DateTime (event date and time)
category_id: ObjectId (reference to Categories collection)
created_at: DateTime
notified: Boolean (whether reminder was sent)
Example:{
"\_id": "60a7b8c9d4e3f2a1b2c3d4e6",
"user_id": "123456789",
"title": "Team Meeting",
"description": "Discuss project milestones",
"date_time": "2025-06-15T14:30:00Z",
"category_id": "60a7b8c9d4e3f2a1b2c3d4e5",
"created_at": "2025-06-12T06:47:00Z",
"notified": false
}

Notes

No explicit schema creation is needed in MongoDB; collections are created automatically when data is inserted.
The bot initializes default categories ("Work", "Personal", "Health", "Other") for each user upon registration.
Indexes on user_id and date_time can be added for performance:db.events.createIndex({"user_id": 1, "date_time": 1});
db.categories.createIndex({"user_id": 1});
