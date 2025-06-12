import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from typing import Optional
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from bson import ObjectId
from dateutil.parser import parse as parse_date

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN: Optional[str] = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env file")
MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME: str = os.getenv("DB_NAME", "event_reminder_bot")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Initialize MongoDB client
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[DB_NAME]

# Define FSM states
class CreateEventForm(StatesGroup):
    title = State()
    description = State()
    date_time = State()
    category = State()

# Create main menu keyboard
def get_main_menu() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Create Event"), KeyboardButton(text="🔔 Upcoming Events")],
            [KeyboardButton(text="📊 Statistics"), KeyboardButton(text="📋 Categories")]
        ],
        resize_keyboard=True
    )
    return keyboard

# Create category keyboard
async def get_category_keyboard(user_id: str) -> InlineKeyboardMarkup:
    categories = await db.categories.find({"user_id": user_id}).to_list(None)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cat["name"], callback_data=f"cat_{cat['_id']}")]
        for cat in categories
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="➕ Add Category", callback_data="add_category")])
    return keyboard

# Register user
async def register_user(user: types.User) -> None:
    await db.users.update_one(
        {"user_id": str(user.id)},
        {
            "$set": {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "created_at": datetime.now(pytz.UTC)
            }
        },
        upsert=True
    )
    # Ensure default categories
    default_categories = ["Work", "Personal", "Health", "Other"]
    for cat in default_categories:
        await db.categories.update_one(
            {"user_id": str(user.id), "name": cat},
            {"$set": {"name": cat}},
            upsert=True
        )

# Create event
async def create_event(user_id: str, title: str, description: str, date_time: datetime, category_id: str) -> ObjectId:
    event = {
        "user_id": user_id,
        "title": title,
        "description": description,
        "date_time": date_time,
        "category_id": ObjectId(category_id),
        "created_at": datetime.now(pytz.UTC),
        "notified": False
    }
    result = await db.events.insert_one(event)
    return result.inserted_id

# Get upcoming events
async def get_upcoming_events(user_id: str) -> list:
    now = datetime.now(pytz.UTC)
    events = await db.events.find({
        "user_id": user_id,
        "date_time": {"$gte": now},
        "notified": False
    }).sort("date_time", 1).to_list(None)
    return events

# Get statistics
async def get_statistics(user_id: str) -> dict:
    now = datetime.now(pytz.UTC)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    events_this_month = await db.events.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": start_of_month}
    })
    
    most_used_category = await db.events.aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$category_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1},
        {"$lookup": {
            "from": "categories",
            "localField": "_id",
            "foreignField": "_id",
            "as": "category"
        }},
        {"$unwind": "$category"}
    ]).to_list(None)
    
    most_used = most_used_category[0]["category"]["name"] if most_used_category else "None"
    most_used_count = most_used_category[0]["count"] if most_used_category else 0
    
    return {
        "events_this_month": events_this_month,
        "most_used_category": most_used,
        "most_used_count": most_used_count
    }

# Background task for reminders
async def reminder_task() -> None:
    while True:
        now = datetime.now(pytz.UTC)
        events = await db.events.find({
            "date_time": {"$lte": now + timedelta(minutes=5)},
            "notified": False
        }).to_list(None)
        
        for event in events:
            user_id = event["user_id"]
            category = await db.categories.find_one({"_id": event["category_id"]})
            if category:
                try:
                    await bot.send_message(
                        user_id,
                        f"🔔 Reminder: *{event['title']}*\n"
                        f"Category: {category['name']}\n"
                        f"Description: {event['description']}\n"
                        f"Time: {event['date_time'].strftime('%Y-%m-%d %H:%M')}",
                        parse_mode="Markdown"
                    )
                    await db.events.update_one(
                        {"_id": event["_id"]},
                        {"$set": {"notified": True}}
                    )
                except Exception as e:
                    logger.error(f"Failed to send reminder to {user_id}: {e}")
        
        await asyncio.sleep(60)  # Check every minute

# Command handlers
@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    if not message.from_user:
        await message.answer("Error: User information not available.")
        return
    await register_user(message.from_user)
    await message.answer(
        "Welcome to the Event Reminder Bot! 🎉\n"
        "Manage your events and get timely reminders. What would you like to do?",
        reply_markup=get_main_menu()
    )

# Main menu handlers
@dp.message(lambda message: message.text == "📅 Create Event")
async def create_event_start(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Enter the event title:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(CreateEventForm.title)

@dp.message(lambda message: message.text == "🔔 Upcoming Events")
async def upcoming_events(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    if not message.from_user:
        await message.answer("Error: User information not available.")
        return
    events = await get_upcoming_events(str(message.from_user.id))
    if not events:
        await message.answer("No upcoming events. Create one with 'Create Event'!", reply_markup=get_main_menu())
        return

    response = "Upcoming Events:\n\n"
    for event in events:
        category = await db.categories.find_one({"_id": event["category_id"]})
        if category:
            response += (
                f"📅 *{event['title']}*\n"
                f"Category: {category['name']}\n"
                f"Time: {event['date_time'].strftime('%Y-%m-%d %H:%M')}\n"
                f"Description: {event['description']}\n\n"
            )
    await message.answer(response, parse_mode="Markdown", reply_markup=get_main_menu())

@dp.message(lambda message: message.text == "📊 Statistics")
async def statistics(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    if not message.from_user:
        await message.answer("Error: User information not available.")
        return
    stats = await get_statistics(str(message.from_user.id))
    response = (
        f"📊 Statistics:\n\n"
        f"Events created this month: {stats['events_this_month']}\n"
        f"Most used category: {stats['most_used_category']} ({stats['most_used_count']} events)"
    )
    await message.answer(response, reply_markup=get_main_menu())

@dp.message(lambda message: message.text == "📋 Categories")
async def categories(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    if not message.from_user:
        await message.answer("Error: User information not available.")
        return
    keyboard = await get_category_keyboard(str(message.from_user.id))
    await message.answer("Select a category or add a new one:", reply_markup=keyboard)

# Create event FSM handlers
@dp.message(CreateEventForm.title)
async def process_title(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Title cannot be empty. Please enter a title:")
        return
    await state.update_data(title=message.text)
    await message.answer("Enter the event description:")
    await state.set_state(CreateEventForm.description)

@dp.message(CreateEventForm.description)
async def process_description(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Description cannot be empty. Please enter a description:")
        return
    await state.update_data(description=message.text)
    await message.answer("Enter the event date and time (e.g., 2025-06-15 14:30):")
    await state.set_state(CreateEventForm.date_time)

@dp.message(CreateEventForm.date_time)
async def process_date_time(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Date and time cannot be empty. Use YYYY-MM-DD HH:MM (e.g., 2025-06-15 14:30):")
        return
    try:
        date_time = parse_date(message.text)
        if date_time < datetime.now(pytz.UTC):
            await message.answer("Please enter a future date and time:")
            return
        await state.update_data(date_time=date_time)
        if not message.from_user:
            await message.answer("Error: User information not available.")
            await state.clear()
            return
        keyboard = await get_category_keyboard(str(message.from_user.id))
        await message.answer("Select a category:", reply_markup=keyboard)
        await state.set_state(CreateEventForm.category)
    except ValueError:
        await message.answer("Invalid date format. Use YYYY-MM-DD HH:MM (e.g., 2025-06-15 14:30):")

@dp.callback_query(lambda c: c.data and c.data.startswith("cat_"), CreateEventForm.category)
async def process_category(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not callback.data or not callback.from_user or not callback.message:
        await callback.answer("Error: Invalid callback data.")
        return
    category_id = callback.data.split("_")[1]
    data = await state.get_data()
    try:
        event_id = await create_event(
            str(callback.from_user.id),
            data["title"],
            data["description"],
            data["date_time"],
            category_id
        )
        await callback.message.answer(
            f"Event '{data['title']}' created successfully! You'll be reminded at the set time.",
            reply_markup=get_main_menu()
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        await callback.message.answer("Failed to create event. Please try again.", reply_markup=get_main_menu())
        await state.clear()
    await callback.answer()

# Category management
@dp.callback_query(lambda c: c.data == "add_category")
async def add_category_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not callback.message:
        await callback.answer("Error: Message not available.")
        return
    await callback.message.answer("Enter the new category name:")
    await state.set_state("add_category")
    await callback.answer()

@dp.message(lambda message: message.state == "add_category")
async def process_category_name(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Category name cannot be empty. Try again:")
        return
    category_name = message.text.strip()
    if not category_name:
        await message.answer("Category name cannot be empty. Try again:")
        return
    if not message.from_user:
        await message.answer("Error: User information not available.")
        await state.clear()
        return
    try:
        await db.categories.insert_one({
            "user_id": str(message.from_user.id),
            "name": category_name,
            "created_at": datetime.now(pytz.UTC)
        })
        await message.answer("Category added successfully!", reply_markup=get_main_menu())
        await state.clear()
    except Exception as e:
        logger.error(f"Error adding category: {e}")
        await message.answer("Failed to add category. Please try again.", reply_markup=get_main_menu())
        await state.clear()

async def main() -> None:
    # Start reminder task
    asyncio.create_task(reminder_task())
    
    # Start polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        mongo_client.close()

if __name__ == "__main__":
    asyncio.run(main())