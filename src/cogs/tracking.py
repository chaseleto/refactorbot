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
    @commands.command(name='track', aliases=['t'])
    async def track(self, ctx, *, message):
        lol_watcher = LolWatcher('RGAPI-954e69d4-4c5d-4c07-b548-412f0f98010b')
        my_region = 'na1'
        
        me = lol_watcher.summoner.by_name(my_region, message)
        

        try:
            spectator = lol_watcher.spectator.by_summoner(my_region, me['id'])
            await ctx.send(f'{message} is in game')

        except ApiError as err:
            if err.response.status_code == 404:
                await ctx.send(f'{message} is not in game')
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

        await ctx.send("Last 10 games " + ",\n ".join(match_stats))

async def setup(bot):
    await bot.add_cog(tracker(bot))
