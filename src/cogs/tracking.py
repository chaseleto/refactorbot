from discord.ext import commands
import discord
import asyncio
import requests
import json
import os
import time
import datetime
import random
import re
import sys
from riotwatcher import LolWatcher, ApiError
class tracker(commands.Cog):
    @commands.command(name='lol', aliases=['league', 'opgg', 'track'])
    async def track(self, ctx, *, message):
        waitmsg = await ctx.send("Retrieving data...")
        lol_watcher = LolWatcher(os.environ['LOLAPI'])
        my_region = 'na1'
        ingame = "Not in game"
        color = 0xFF0000
        try:
            me = lol_watcher.summoner.by_name(my_region, message)
            summoner_id = me['id']
        except ApiError as err:
            if err.response.status_code == 404:
                await waitmsg.edit(content=f'Summoner {message} does not exist.')
                return
            elif err.response.status_code == 403:
                await waitmsg.edit(content=f'API Key has expired or otherwise unauthorized. Please contact the bot owner.')
                return
            else:
                await waitmsg.edit(content=f'Unable to retrieve data.')
                asyncio.sleep(5)
                await waitmsg.delete()
                return
        current_champ = ""
        patch = "https://ddragon.leagueoflegends.com/cdn/13.6.1/data/en_US/champion.json"
        rank = lol_watcher.league.by_summoner(my_region, me['id'])
        try:
            for i in rank:
                if i['queueType'] == 'RANKED_SOLO_5x5':
                    rank = i['tier'] + ' ' + i['rank']
        except:
            rank = "Unranked"
        try:
            spectator = lol_watcher.spectator.by_summoner(my_region, me['id'])
            response = requests.get(patch)
            if response.status_code == 200:
                data = json.loads(response.text)
            for player in spectator['participants']:
                if player['summonerName'] == message:
                    #print(player['championId'])
                    for champ in data['data']:
                        if data['data'][champ]['key'] == str(player['championId']):
                            #print(data['data'][champ]['name'])
                            current_champ = data['data'][champ]['name']
            ingame = "In game"
            color = 0x00FF00
        except ApiError as err:
            if err.response.status_code == 404:
                #await ctx.send(f'{message} is not in game')
                pass
            else:
                raise

        my_matches = lol_watcher.match.matchlist_by_puuid(my_region, me['puuid'])
        #print(my_matches)
        if not my_matches:
            await waitmsg.edit(content=f'{message} has not played any games recently or does not exist.')
            return
        most_played_champ = ""
        champ_count = {}
        embed = discord.Embed(title=f"{message} | {rank}", color=color, description=ingame, url=f"https://na.op.gg/summoner/userName={message}")
        for idx, match1 in enumerate(my_matches[:10]):
            match_detail = lol_watcher.match.by_id(my_region, match1)
            #print(match_detail)
            queueType = ''
            queueId = match_detail['info']['queueId']
            if queueId == 0:
                queueType = "Custom"
            elif queueId == 430:
                queueType = "Blind Pick"
            elif queueId == 420:
                queueType = "Ranked Solo"
            elif queueId == 32:
                queueType = "Co-op vs AI Beginner"
            elif queueId == 33:
                queueType = "Co-op vs AI Intermediate"
            elif queueId == 400:
                queueType = "Draft Pick"
            elif queueId == 440:
                queueType = "Ranked Flex"
            elif queueId == 450:
                queueType = "ARAM"
            elif queueId == 700:
                queueType = "Clash"
            else:
                queueType = "Unknown"
            for player in match_detail['info']['participants']:
        # Check if the player is Ozu
                if player['summonerId'] == summoner_id:
            # Get the champion name and KDA
                    champion_name = player['championName']
                    kills = player['kills']
                    deaths = player['deaths']
                    assists = player['assists']
                    kda = '{}/{}/{}'.format(kills, deaths, assists)

            # Get the win status
                    win = player['win']
                    win_status = 'Victory' if win else 'Defeat'

            # Add a new field to the embed with the champion name, KDA, and win status
                    field_name = f"{idx+1}. {champion_name} \n[{queueType}]"
                    embed.add_field(name=field_name, value=f'{kda}\n{win_status}', inline=True)
                    champ_count[champion_name] = champ_count.get(champion_name, 0) + 1
        if champ_count:
            most_played_champ = max(champ_count, key=champ_count.get)
        
        if len(champ_count) == 10:
            match_detail = lol_watcher.match.by_id(my_region, my_matches[0])
            for player in match_detail['info']['participants']:
                if player['summonerId'] == summoner_id:
                    most_played_champ = player['championName']

        if current_champ:
            most_played_champ = current_champ

        embed.set_image(url=f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{most_played_champ}_0.jpg")
        await waitmsg.edit(content="", embed=embed)

async def setup(bot):
    await bot.add_cog(tracker(bot))
