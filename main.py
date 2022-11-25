import discord
from discord.ext import commands
import asyncio
import logging
import os
import yaml

# Logging
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

#config
with open('config/cfg.yml', 'r') as f:
    config = yaml.safe_load(f)

# Bot
bot = commands.Bot(command_prefix=config['Bot_prefix'], description='SER Bot refactored.', case_insensitive=True, owner_id=238047264839303179, intents=discord.Intents.all())

#Load cogs
async def load():
    for file in os.listdir('./cogs'):
        if file.endswith('.py'):
            await bot.load_extension(f'cogs.{file[:-3]}')
            print(f'{file[:-3]} cog loaded.')

#Runs on every message sent in a server, checks if the message is a command and if so, runs it.
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)
@bot.event
async def on_guild_join(guild):
    #database implementation here
    print(f'Joined {guild.name} ({guild.id})')

#When login is successful
@bot.event
async def on_connect():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    await load()

    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands.')
    except Exception as e:
        print(f'Failed to sync commands: {e}')


#Login and connect
async def main():
    token = config['Token']
    await load()
    await bot.start(token)

#Run the bot
asyncio.run(main())