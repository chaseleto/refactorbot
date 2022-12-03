from discord.ext import commands
import datetime
import yaml
import asyncio
import random
from Levenshtein import distance
import discord

class TypeGame(commands.Cog):
    
    timer = 30
    starttime = None
    current_game = False
    entry = None
    game_channel = None
    game_starting = False
    scores = {}
    avg_word_length = 0

    @commands.command(name='typegame', aliases=['tg'])
    async def typegame(self, ctx, difficulty='easy'):
        """Starts a game of type racer.

        Difficulty can be easy, medium, or hard. Defaults to easy. 
        The goal of the game is to type the provided text as fast and accurate as possible. You are scored on both accuracy and time spent typing.

        Parameters
        ----------
        difficulty: str
            The difficulty level of the game to be played. Defaults to easy.
        """

        if self.current_game or self.game_starting:
            await ctx.send('There is already a game running!')
            return
        
        self.game_starting = True
        try:
            with open("/home/src/config/typeracer.yml", "r") as f:
                typegame = yaml.safe_load(f)
            if difficulty == "easy":
                self.entry = random.choice(typegame["easy"])
            elif difficulty == "medium":
                self.entry = random.choice(typegame["medium"])
            elif difficulty == "hard":
                self.entry = random.choice(typegame["hard"])
            self.avg_word_length = await self.get_avg_word_length()

            await ctx.send(f"In 5 seconds I will send a prompt. Type it as fast as you can. You will have {self.timer} seconds to type it. Scores will be posted after the game ends. Good luck!")
            await asyncio.sleep(5)
            await ctx.send(f"{self.entry}")

            self.starttime = datetime.datetime.now()
            self.game_channel = ctx.channel
            self.current_game = True
            self.game_starting = False

            await asyncio.sleep(self.timer - 10)
            await ctx.send("10 seconds left!")
            await asyncio.sleep(5)
            await ctx.send("5 seconds left!")
            await asyncio.sleep(5)
            self.current_game = False
            self.entry = None
            self.starttime = None
            self.game_channel = None


            embed = discord.Embed(title=f"Scores", color=0x00ff00)
    
            for user in self.scores:
                embed.add_field(name=user.display_name, value=f"Score: {self.scores[user]['pct']}%\nTime: {int(self.scores[user]['time'])} seconds", inline=False)
            await ctx.send(embed=embed)
        except:
            self.game_starting = False
            return await ctx.send("An error occurred. Please try again later.")
            
            
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.channel != self.game_channel or message.content.startswith('!') or message.author in self.scores:
            return
        if self.current_game:
            dist = distance(self.entry, message.content)
            pct_correct = round(100*(1-(dist/len(self.entry))))
            elapsed = datetime.datetime.now() - self.starttime
            elapsed = elapsed.total_seconds()
            wpm = round(len(self.entry)/self.avg_word_length/5/(elapsed/100))

            await message.channel.send(f"Congratulations! {message.author.mention} finished the game in {int(elapsed)} seconds with a score of {dist} | {pct_correct}%!")
            self.scores[message.author] = {"pct": pct_correct, "time": elapsed, "wpm": wpm}
        else:
            return
    async def get_avg_word_length(self):
        total = 0
        for word in self.entry.split(' '):
            total += len(word)
        return total/len(self.entry.split(' '))

async def setup(bot):
    await bot.add_cog(TypeGame(bot))