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
    @commands.command(name='track', aliases=['tra'])
    async def track(self, ctx, *, message):
        lol_watcher = LolWatcher(os.environ['LOLAPI'])
        my_region = 'na1'
        ingame = "Not in game"
        color = 0xFF0000
        me = lol_watcher.summoner.by_name(my_region, message)
        current_champ = ""
        patch = "https://ddragon.leagueoflegends.com/cdn/13.6.1/data/en_US/champion.json"
        rank = lol_watcher.league.by_summoner(my_region, me['id'])
        rank = rank[0]['tier'] + ' ' + rank[0]['rank']
        try:
            spectator = lol_watcher.spectator.by_summoner(my_region, me['id'])
            response = requests.get(patch)
            if response.status_code == 200:
                data = json.loads(response.text)
            for player in spectator['participants']:
                if player['summonerName'] == message:
                    print(player['championId'])
                    for champ in data['data']:
                        if data['data'][champ]['key'] == str(player['championId']):
                            print(data['data'][champ]['name'])
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

        match_stats = []
        for match in my_matches[:10]:
            match_detail = lol_watcher.match.by_id(my_region, match)
            for player in match_detail['info']['participants']:
                if player['summonerName'] == message:
                    result = "Won" if player['win'] else "Lost"
                    kills, deaths, assists = player['kills'], player['deaths'], player['assists']
                    match_stats.append(f"{player['championName']}: {result} ({kills}/{deaths}/{assists})")
        print(match_stats)
        #await ctx.send("Last 10 games\n " + ",\n ".join(match_stats))



        most_played_champ = ""
        champ_count = {}
        embed = discord.Embed(title=f"{message} | {rank}", color=color, description=ingame)
        for idx, match in enumerate(my_matches[:10]):
            match_detail = lol_watcher.match.by_id(my_region, match)
            for player in match_detail['info']['participants']:
        # Check if the player is Ozu
                if player['summonerName'] == message:
            # Get the champion name and KDA
                    champion_name = player['championName']
                    kills = player['kills']
                    deaths = player['deaths']
                    assists = player['assists']
                    kda = '{}/{}/{}'.format(kills, deaths, assists)

            # Get the win status
                    win = player['win']
                    win_status = 'Won' if win else 'Lost'

            # Add a new field to the embed with the champion name, KDA, and win status
                    field_name = f"{idx+1}. {champion_name}"
                    embed.add_field(name=field_name, value=f'{kda}\n{win_status}', inline=True)
                    champ_count[champion_name] = champ_count.get(champion_name, 0) + 1
        if champ_count:
            most_played_champ = max(champ_count, key=champ_count.get)
        
        if len(champ_count) == 10:
            match_detail = lol_watcher.match.by_id(my_region, my_matches[0])
            for player in match_detail['info']['participants']:
                if player['summonerName'] == message:
                    most_played_champ = player['championName']

        if current_champ:
            most_played_champ = current_champ
        print(f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{most_played_champ}_0.jpg")
        embed.set_image(url=f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{most_played_champ}_0.jpg")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(tracker(bot))
