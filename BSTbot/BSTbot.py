import discord
import random
import requests
import csv
import re
import os
from io import StringIO
from discord.ext import commands
from sympy import sympify

# Load token from environment variable
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store user-linked Sheets with names
user_sheets = {}

# Function to extract Sheet ID from URL
def extract_sheet_id(url):
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    return match.group(1) if match else None

# Function to fetch Google Sheets data as a list of rows
def fetch_google_sheet(sheet_id):
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
    try:
        response = requests.get(csv_url)
        response.raise_for_status()
        csv_reader = csv.reader(StringIO(response.text))
        return list(csv_reader)  # Returns rows as a list
    except Exception as e:
        print(f"Error fetching Google Sheet: {e}")
        return None

# Function to parse dice notation (e.g., "2d6+3" → sum of two rolls of 1d6 + 3)
def roll_dice(dice_notation):
    match = re.match(r"(\d*)d(\d+)([+-]\d+)?", dice_notation)
    if not match:
        return None
    num_dice = int(match.group(1)) if match.group(1) else 1
    dice_sides = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0
    return sum(random.randint(1, dice_sides) for _ in range(num_dice)) + modifier

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def link(ctx, url: str, sheet_name: str):
    """Links a Google Sheet to a user."""
    sheet_id = extract_sheet_id(url)
    if not sheet_id:
        await ctx.send("Invalid Google Sheets link. Please provide a valid link.")
        return
    user_sheets.setdefault(ctx.author.id, {})[sheet_name] = sheet_id
    await ctx.send(f"Google Sheet `{sheet_name}` linked successfully!")

@bot.command()
async def roll(ctx, command: str, sheet_name: str):
    """Fetches a formula from the Google Sheet and rolls the dice."""
    if ctx.author.id not in user_sheets or sheet_name not in user_sheets[ctx.author.id]:
        await ctx.send(f"You haven't linked a sheet named `{sheet_name}`! Use `!link [URL] SheetName` to add it.")
        return

    sheet_id = user_sheets[ctx.author.id][sheet_name]
    data = fetch_google_sheet(sheet_id)
    if not data:
        await ctx.send(f"Failed to retrieve data from `{sheet_name}`.")
        return

    for row in data:
        if len(row) >= 3 and row[0].strip().lower() == command.lower():
            formula = row[2]  # Column C (third column)
            dice_match = re.search(r"(\d*d\d+[+-]?\d*)", formula)
            dice_roll = roll_dice(dice_match.group(1)) if dice_match else None
            if dice_match:
                if dice_roll is None:
                    await ctx.send(f"Invalid dice notation in formula: `{formula}`")
                    return
                formula = formula.replace(dice_match.group(1), str(dice_roll))
            try:
                result = sympify(formula).evalf()
            except Exception as e:
                await ctx.send(f"Error in formula: {e}")
                return

            await ctx.send(f"`{command}` from `{sheet_name}` → Formula: `{formula}` | Roll: `{dice_roll}` | Result: `{result}`")
            return

    await ctx.send(f"Command `{command}` not found in `{sheet_name}`. Make sure it exists in Column A!")

# Run bot
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_BOT_TOKEN not set in environment variables.")
