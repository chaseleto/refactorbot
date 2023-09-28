import discord
from discord.ext import commands
import asyncio
import logging
import os
import yaml
from pymongo import MongoClient
import datetime
import http.client as httplib
import json
# Logging
logger = logging.getLogger('discord')
logger.setLevel(logging.ERROR)
handler = logging.FileHandler(filename='/home/src/discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
#test
#configs
with open('/home/src/config/cfg.yml', 'r') as f:
    config = yaml.safe_load(f)

#MongoDB
mg = MongoClient('mongodb', 27017,
                username=os.environ['MONGO_USER'],
                password=os.environ['MONGO_PASSWORD'])

# Bot
bot = commands.Bot(command_prefix=config['Bot_prefix'], description='SER Bot refactored.', case_insensitive=True, owner_id=238047264839303179, intents=discord.Intents.all())

#Load cogs
async def load():
    for file in os.listdir('/home/src/cogs'):
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
    try:
        print(guild.name)
        collection = mg['discord']['guilds']
        collection.insert_one({
            'guild_id': guild.id,
            'guild_name': guild.name,
            'guild_owner': guild.owner.id,
            'guild_owner_name': guild.owner.name,
            'guild_member_count': guild.member_count,
            'guild_created_at': guild.created_at,
            'bot_join_date': datetime.datetime.utcnow(),
            'has_api_key': False, 'google_api_key': None,
            'music_channel_id': None,
            'play_tracking_message_id': None,
            'autoplay_max_duration': None,
            'dj_lock': False,
            'dj_role_id': None,
            'dj_ids': [],
            'autoplay': False,
            
            })
    except:
        print("Guild already in database.")
    #find my server and my channel and send a message to it
    for guilds in bot.guilds:
        if guilds.id == 1058867981268041850:
            for channel in guilds.channels:
                if channel.id == 1058940782238777345:
                    await channel.send(f"Joined {guild.name}\nOwner: {guild.owner.name}#{guild.owner.discriminator}\nMember Count: {guild.member_count}\nCreated at: {guild.created_at}\nBot Join Date: {datetime.datetime.utcnow()}\n------------------------------------------------")
@bot.event
async def on_guild_remove(guild):
    try:
        print(guild.name)
        collection = mg['discord']['guilds']
        collection.delete_one({'guild_id': guild.id})
    except:
        print("Guild not in database.")
    #find my server and my channel and send a message to it
    for guilds in bot.guilds:
        if guilds.id == 1058867981268041850:
            for channel in guilds.channels:
                if channel.id == 1058940782238777345:
                    await channel.send(f"Left {guild.name}\nOwner: {guild.owner.name}#{guild.owner.discriminator}\nMember Count: {guild.member_count}\nCreated at: {guild.created_at}\nBot Join Date: {datetime.datetime.utcnow()}\n------------------------------------------------")
@bot.event
async def on_guild_update(before, after):
    try:
        collection = mg['discord']['guilds']
        collection.update_one({'guild_id': before.id}, {'$set': {'guild_name': after.name}, '$set': {'guild_owner': after.owner.id}, '$set': {'guild_owner_name': after.owner.name}, '$set': {'guild_member_count': after.member_count}, '$set': {'guild_created_at': after.created_at}})
    except:
        print("Guild not in database.")
@bot.event
async def on_ready():
    #sends reconnect message to the channel that the restartbot command was given in (if it was given)
    #new comment for testing cl
    try:
        for guild in bot.guilds:
            collection = mg['discord']['guilds']
            
            restarted = collection.find_one({'guild_id': guild.id})['restarted']
            if restarted == True or restarted == "True" or restarted == "true":
                channel = bot.get_channel(collection.find_one({'guild_id': guild.id})['restart_channel_id'])
                collection.update_one({'guild_id': guild.id}, {'$set': {'restarted': False}})
                try:
                    await channel.send(f"Successfully restarted. Last code change message: ```{retrieve_latest_commit_message_for_github_repository('chaseleto', 'refactorbot')}```")
                except:
                    await channel.send(f"Successfully restarted. No code change message found.")

    except Exception as e:
        print("No restart channel found.")
        print(e)

#Gets last commit message from github
def retrieve_latest_commit_message_for_github_repository(in_username, in_repository_name):
    github_user = "chaseleto"
    github_api_https_connection = httplib.HTTPSConnection('api.github.com')
    repository_last_commit_msg = None
    github_http_request_headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": github_user}
 
    try:
        # Request only the one last commit for the supplied user's repository with supplied name.
        github_request_path = "/repos/" + in_username + "/" + in_repository_name + "/commits?page=1&per_page=1"
        github_api_https_connection.request("GET", github_request_path, None, github_http_request_headers)
        github_repository_last_commit_response = github_api_https_connection.getresponse()
 
        if github_repository_last_commit_response.status == 200:
            # Response was successful, now read and parse the JSON data.
            github_repository_last_commit_response_text = github_repository_last_commit_response.read()
            github_repository_last_commit_response_object = json.loads(github_repository_last_commit_response_text)
            repository_last_commit_msg = github_repository_last_commit_response_object[0]['commit']['message']
        else:
            message = "ERROR: Request to GitHub failed with status %s and the reason was %s" % \
                      (github_repository_last_commit_response.status,
                       github_repository_last_commit_response.reason)
            print(message)
    finally:
        github_api_https_connection.close()
 
    return repository_last_commit_msg


#command to send message to all guilds general channels
@bot.command()
async def send(ctx, *, message):
    if ctx.author.id == 238047264839303179:
        for guild in bot.guilds:
            for channel in guild.channels:
                if channel.name == "general" or channel.name == "𝙂𝙀𝙉𝙀𝙍𝘼𝙇":
                    await channel.send(message)
    else:
        await ctx.send("You do not have permission to use this command.")
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
    token = os.getenv("DISCORD_SECRET")
    await bot.start(token)

#Run the bot
asyncio.run(main())
