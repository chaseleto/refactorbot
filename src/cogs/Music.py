import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import datetime
import asyncio
import yaml
from googleapiclient.discovery import build
from pymongo import MongoClient
import urllib.parse
import os

class Music(commands.Cog):

    #############################################################################################################################################################
    #                                                                         Initialization                                                                    #
    #############################################################################################################################################################
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    with open('config/cfg.yml', 'r') as f:
        config = yaml.safe_load(f)
    
    mg = MongoClient('34.171.240.203', 27017,
                 username=os.environ['MONGO_USER'],
                 password=os.environ['MONGO_PASSWORD'])

    async def connect_nodes(self):
        """Connect to our Lavalink nodes."""
        await self.bot.wait_until_ready()

        await wavelink.NodePool.create_node(bot=self.bot,
                                            host='localhost',
                                            port=2333,
                                            password='youshallnotpass')
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.loop.create_task(self.connect_nodes())

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        """Event fired when a node has finished connecting."""
        print(f'Node: <{node.identifier}> is ready!')
    

    #############################################################################################################################################################
    #                                                                         Music Commands                                                                    #
    #############################################################################################################################################################
    queue = wavelink.Queue()
    context = None
    play_tracking = False
    play_tracking_message = None
    music_channel = config['temp_music_channel']
    autoplay_ = False
    GOOGLE_API_KEY = None
    youtube = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)
    max_duration = None

    @commands.command(name='play', aliases=['p'])
    async def play(self, ctx, *, query):
        """Plays a song from youtube.

        Parameters
        ----------
        query: str
            The name of the song to search from youtube.
        """
        #Get playable object from query
        track = await wavelink.YouTubeTrack.search(query=query, return_first=True)

        #Check if the bot has a player in the guild
        if not ctx.voice_client:
            vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            vc: wavelink.Player = ctx.voice_client

        embed = discord.Embed(
            type="rich",
            title=f"{track.title}",
            description=f"Queued by {ctx.author.mention}",
            color=discord.Color.from_str("#ff0101"),
            timestamp=datetime.datetime.now(),
            url=f"{track.uri}"
        )
        embed.set_thumbnail(url=f"{track.thumb}")

        embed.add_field(
            name=f"Uploaded by: {track.author}",
            value=f"Duration: {str(datetime.timedelta(seconds=track.duration))}",
            inline=True
        )
        track.requester = ctx.author
        #Add track to queue or play if queue is empty and not playing
        if not vc.is_playing() and self.queue.is_empty:
            await vc.play(track)
            await asyncio.sleep(1)
            await self.now_playing_embed(vc)
            self.context = ctx
        else:
            self.queue.put(track)
            await ctx.send(content="Added to queue:", embed=embed)
    
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player: wavelink.Player, track: wavelink.Track, reason: str):
        """Event fired when a track has finished playing."""
        if self.queue.is_empty:
            return await player.disconnect()
        await player.play(self.queue.get())
        await self.now_playing_embed(player)
        
    @commands.command(name='skip')
    async def skip(self, ctx):
        """Skips the current song.

        Parameters
        ----------

        """
        vc: wavelink.Player = ctx.voice_client
        if not vc.is_playing():
            return await ctx.send('I am not playing anything right now.')
        if self.queue.is_empty:
            await vc.stop()
        else:
            await vc.seek(vc.track.length * 1000)
            await ctx.send('Skipped the current song.')
            if vc.is_paused:
                await vc.resume()

    @commands.hybrid_command(name='playing', with_app_command=True, aliases=['song', 'np'])
    async def playing(self, ctx):
        """Displays the song that is currently playing.

        Parameters
        ----------

        """
        vc: wavelink.Player = ctx.voice_client
        await self.now_playing_embed(ctx.voice_client)

    @commands.command(name='pause', aliases=['stop'])
    async def pause(self, ctx):
        """Pauses the current player.

        Parameters
        ----------

        """
        vc: wavelink.Player = ctx.voice_client
        if not vc.is_playing():
            return await ctx.send('I am not playing anything right now.')
        await vc.pause()
        await ctx.send('Paused the current song.')

    @commands.command(name='resume', description='Resumes the current song')
    async def resume(self, ctx):
        """Resumes the current player.

        Parameters
        ----------

        """
        vc: wavelink.Player = ctx.voice_client
        if not vc.is_playing():
            return await ctx.send('I am not playing anything right now.')
        if not vc.is_paused:
            return await ctx.send('I am not paused.')
        await vc.resume()
        await ctx.send('Resumed the current song.')

    @commands.hybrid_command(name='seek', with_app_command=True)
    async def seek(self, ctx, position: int):
        """Seek to a position in the current song.

        Parameters
        ----------
        position: int
            The position in seconds to seek to
        """
        vc: wavelink.Player = ctx.voice_client
        if not vc.is_playing():
            return await ctx.send('I am not playing anything right now.')
        if position > vc.track.length:
            return await ctx.send('Position is longer than the song.')
        await vc.seek(position * 1000)
        seek = position
        await self.now_playing_embed(ctx.voice_client)
    
    @commands.command(name='queue', aliases=['q', 'cue', 'qu'])
    async def queued(self, ctx):
        """Displays the current song queue.

        Parameters
        ----------

        """
        vc: wavelink.Player = ctx.voice_client
        if self.queue.is_empty:
            return await ctx.send('The queue is empty.')
        queue = self.queue
        total_time_in_queue = 0
        for track in self.queue:
            total_time_in_queue += track.duration
        
        embed = discord.Embed(
                type="rich",
                title=f"Now Playing: {vc.track.title}",
                description=f"Total queued time: {str(datetime.timedelta(seconds=total_time_in_queue))}\n\nUp next:",
                color=discord.Color.random(),
                timestamp=datetime.datetime.now(),
                url=f"{vc.track.uri}"
            )
        for count, song in enumerate(self.queue):
            requester = "Unknown"
            try:
                requester = song.requester.mention
            except:
                requester = "AutoPlayed"
            embed.add_field(
                name=f"{count+1}) {song}",
                value=f"Duration: {str(datetime.timedelta(seconds=song.duration))}\nRequested by: {requester}",
                inline=True
            )
        thumb = f"http://img.youtube.com/vi/{vc.track.identifier}/hqdefault.jpg"
        embed.set_thumbnail(url=f"{thumb}")
        await ctx.send(embed=embed)

    async def now_playing_embed(self, voice_player):
        """Create an embed for the current song."""
        vc: wavelink.Player = voice_player
        music_channel = voice_player.guild.get_channel(int(self.music_channel))
        current_seconds = datetime.timedelta(seconds=int(vc.position))
        track_length = vc.track.length
        if not vc.is_playing():
            return await music_channel.send('I am not playing anything right now.')
        if self.play_tracking_message:
            await self.play_tracking_message.delete()
        requester = "Unknown"
        try:
            requester = vc.track.requester.mention
        except:
            requester = "AutoPlayed"
        embed = discord.Embed(title=f'**{vc.track}**', description=f'{vc.track.author}\n\n**Queued by: {requester}\nAutoPlay: {self.autoplay_}**\n\n▶️ ({str(current_seconds)}/{str(datetime.timedelta(seconds=vc.track.length))})', color=discord.Color.from_str("#ff0101"), url=str(vc.track.uri))
        thumb = f"http://img.youtube.com/vi/{vc.track.identifier}/hqdefault.jpg"
        embed.set_thumbnail(url=f"{thumb}")
        msg = await music_channel.send(content="ɴᴏᴡ ᴘʟᴀʏɪɴɢ", embed=embed)
        self.play_tracking_message = msg
        self.play_tracking = True
        await msg.add_reaction('⏮')
        await msg.add_reaction('⏪')
        await msg.add_reaction('▶')
        await msg.add_reaction('⏸')
        await msg.add_reaction('⏩')
        await msg.add_reaction('⏭')
        

        while datetime.timedelta(seconds=int(vc.position)) < datetime.timedelta(seconds=vc.track.length):
            
            embed.description = f'{vc.track.author}\n\n**Queued by: {requester}\nAutoPlay: {self.autoplay_}**\n\n▶️ (__*{datetime.timedelta(seconds=int(vc.position))}/{str(datetime.timedelta(seconds=track_length))}*__) ◀️'
            try:
                await msg.edit(embed=embed)
            except:
                break
            await asyncio.sleep(0.9)

    @commands.command(name='autoplay')
    async def autoplay_toggle(self, ctx, max_duration: int = None):
        """Toggles autoplay on or off. If on, the bot will automatically find songs related to the current song and add them to the queue. 
        If a max duration is specified, the bot will ONLY add songs that are shorter than the specified duration.

        You MUST pass a google api key to the bot for this to work. You can get one here: https://developers.google.com/youtube/v3/getting-started. 
        Once you have your key, run the command `!set google_api_key <your key here>`. You will only need to do this once but you may update it as much as you would like. 

        Each key has a quota of 10,000 units per day. Each call to the API is 100 units. If you are using the bot in a large server, you may want to consider getting a key with a higher quota.

        when autoplay is turned on, the bot will check to make sure the key is valid, this will use 100 units. 

        The bot will add 2-6 songs to the queue at a time. Each time this is done it will only use 100 units. When the queue reaches 2 songs left, it will add another 2-6 songs, using another 100 units.

        If autoplay is used once and playing songs consecutively, you should be able to get around 200-500 songs in a day.

        Parameters
        ----------
        max_duration: int
            The maximum duration of songs to add to the queue automatically 
        """

        enabled_message = 'Autoplay has been enabled.'
        

        if max_duration:
            max_duration = max_duration * 60
            self.max_duration = max_duration
            enabled_message += f' Songs will be limited to {int(max_duration/60)} minutes.'

        if self.autoplay_:
            self.autoplay_ = False
            await ctx.send('Autoplay has been disabled.')
            self.queue.clear()
        else:
            self.autoplay_ = True
            if await self.check_api_key():
                await ctx.send(enabled_message)
                if ctx.voice_client.is_playing():
                    vc: wavelink.Player = ctx.voice_client
                    track = vc.track
                    for related_video in await self.get_related_videos(track.identifier):
                        try:                            
                            track = await wavelink.YouTubeTrack.search("https://www.youtube.com/watch?v=" + related_video, return_first=True)
                            if max_duration and track.length <= max_duration:
                                self.queue.put(track)
                            elif not max_duration:
                                self.queue.put(track)
                        except :
                            print("Couldn't add related video to queue.")
            elif not self.GOOGLE_API_KEY:
                await ctx.send('You need to set an API key to use this command.')
                self.autoplay_ = False
            elif not await self.check_api_key():
                await ctx.send('Your API key is invalid.')
                self.autoplay_ = False

    async def check_api_key(self):
        """Autoplay."""
        if self.autoplay_:
            if self.GOOGLE_API_KEY:
                try:
                    request = self.youtube.search().list(
                        part='snippet',
                        relatedToVideoId="mRzv6Zcowz0",
                        type="video",
                    )
                    response = request.execute()
                except:
                    return False
            return True

    async def get_related_videos(self, video_id):
        """Get related videos."""
        try:
            request = self.youtube.search().list(
                            part='snippet',
                            relatedToVideoId=str(video_id),
                            type="video",
                            relevanceLanguage="en",
                        )
            response = request.execute()
            ls_ids = []
            for item in response['items']:
                ls_ids.append(item['id']['videoId'])
            return ls_ids
        except:
            return None
    
    @commands.Cog.listener()
    async def on_wavelink_track_start(self, player: wavelink.Player, track: wavelink.Track):
        """Track start event."""
        print("track started")
        if self.autoplay_ and self.queue.count <= 2:
            related = await self.get_related_videos(track.identifier)
            if not related:
                await self.music_channel.send("Could not add related video to queue. This is likely due to exceeding your daily quota of 10,000 units. Please try again tomorrow or update your Google API Key. More: !help autoplay")
                self.autoplay_ = False
                return
            for related_video in related:
                try:
                    track = await wavelink.YouTubeTrack.search("https://www.youtube.com/watch?v=" + related_video, return_first=True)
                    if self.max_duration and track.duration <= self.max_duration:
                        self.queue.put(track)
                    elif not self.max_duration:
                        self.queue.put(track)
                except :
                    print("Couldn't add related video to queue.")
        else:
            return

    @commands.command(name='clear')
    async def clear_queue(self, ctx):
        """Clears the current queue.

        Parameters
        ----------

        """
        self.queue.clear()
        await ctx.send('Cleared the queue.')
    
    @commands.command(name='disconnect', aliases=['dc', 'leave'])
    async def disconnect(self, ctx):
        """Disconnects the bot from its current voice channel and clears the queue.

        Parameters
        ----------

        """
        vc: wavelink.Player = ctx.voice_client
        if not vc:
            return await ctx.send('I am not connected to a voice channel.')
        await vc.disconnect()
        await ctx.send('Disconnected from the voice channel.')
        self.queue.clear()
    
    @commands.command(name='volume', aliases=['vol'])
    async def volume(self, ctx, volume: int):
        """Sets the volume of the bot's player.

        Parameters
        ----------
        volume: int
            The volume to set the player to. Must be between 1 and 100.
        """
        vc: wavelink.Player = ctx.voice_client
        if not vc:
            return await ctx.send('I am not connected to a voice channel.')
        if not 0 < volume < 101:
            return await ctx.send('Please enter a value between 1 and 100.')
        await vc.set_volume(volume)
        await ctx.send(f'Set the volume to {volume}.')
    @commands.command(name='join', aliases=['connect'])
    async def join(self, ctx):
        """Connects the bot to whichever voice channel you are in.

        Parameters
        ----------

        """
        vc: wavelink.Player = ctx.voice_client
        if not vc:
            try:
                await ctx.author.voice.channel.connect(cls=wavelink.Player)
            except:
                return await ctx.send('I am not connected to a voice channel.')
        else:
            await vc.move_to(ctx.author.voice.channel)
        await ctx.send(f'Joined {ctx.author.voice.channel}.')
    @commands.command(name='select', aliases=['choose', 'pick'])
    async def select(self, ctx, index: int):
        """Selects a song from the queue to play next.

        Parameters
        ----------
        index: int
            The index of the song to play next.
        """
        vc: wavelink.Player = ctx.voice_client
        if not vc:
            return await ctx.send('I am not connected to a voice channel.')
        if not 0 < index <= self.queue.count:
            return await ctx.send('Please enter a valid index.')
        track = self.queue[index - 1]
        self.queue.__delitem__(index - 1)
        self.queue.put_at_front(track)

        embed = discord.Embed(
            type="rich",
            title=f"{track.title}",
            description=f"Queued by {ctx.author.mention}",
            color=discord.Color.from_str("#ff0101"),
            timestamp=datetime.datetime.now(),
            url=f"{track.uri}"
        )
        embed.set_thumbnail(url=f"{track.thumb}")

        embed.add_field(
            name=f"Uploaded by: {track.author}",
            value=f"Duration: {str(datetime.timedelta(seconds=track.duration))}",
            inline=True
        )

        await ctx.send(content="ᴘʟᴀʏɪɴɢ ɴᴇxᴛ", embed=embed)
    @commands.command(name='next')
    async def next(self, ctx, *, query: str):
        """Same as play command but puts the requested track to the front of the queue.

        Parameters
        ----------
        query: str
            The query to search for.
        """
        track = await wavelink.YouTubeTrack.search(query=query, return_first=True)
        self.queue.put_at_front(track)
        embed = discord.Embed(
            type="rich",
            title=f"{track.title}",
            description=f"Queued by {ctx.author.mention}",
            color=discord.Color.from_str("#ff0101"),
            timestamp=datetime.datetime.now(),
            url=f"{track.uri}"
        )
        embed.set_thumbnail(url=f"{track.thumb}")

        embed.add_field(
            name=f"Uploaded by: {track.author}",
            value=f"Duration: {str(datetime.timedelta(seconds=track.duration))}",
            inline=True
        )
        track.requester = ctx.author
        await ctx.send(content='ᴘʟᴀʏɪɴɢ ɴᴇxᴛ', embed=embed)
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user == self.bot.user:
            return
        if reaction.message != self.play_tracking_message:
            return
        if reaction.message.guild.voice_client:
            vc: wavelink.Player = reaction.message.guild.voice_client
        else:
            return
        if reaction.emoji == "⏮":
            await vc.seek(0)
        elif reaction.emoji == "⏪":
            if vc.position < 15:
                await vc.seek(0)
            else:
                await vc.seek((vc.position - 15) * 1000)
        elif reaction.emoji == "▶":
            await vc.resume()
        elif reaction.emoji == "⏸":
            await vc.pause()
        elif reaction.emoji == "⏩":
            if vc.position + 15 > vc.track.duration:
                await vc.seek(vc.track.duration * 1000)
            else:
                await vc.seek((vc.position + 15) * 1000)
        elif reaction.emoji == "⏭":
            await vc.seek(vc.track.duration * 1000)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if user == self.bot.user:
            return
        if reaction.message != self.play_tracking_message:
            return
        if reaction.message.guild.voice_client:
            vc: wavelink.Player = reaction.message.guild.voice_client
        else:
            return
        if reaction.emoji == "⏮":
            print("attempting to restart")
            await vc.seek(0)
        elif reaction.emoji == "⏪":
            print("attempting to rewind")
            if vc.position < 15:
                await vc.seek(0)
            else:
                await vc.seek((vc.position - 15) * 1000)
        elif reaction.emoji == "▶":
            print("attempting to resume")
            await vc.resume()
        elif reaction.emoji == "⏸":
            print("attempting to pause")
            await vc.pause()
        elif reaction.emoji == "⏩":
            print(f"attempting to skip forward {vc.position}, {vc.position + 15}, {vc.track.duration}")
            if vc.position + 15 >= vc.track.duration:
                await vc.seek(vc.track.duration * 1000)
            else:
                await vc.seek((vc.position + 15) * 1000)
        elif reaction.emoji == "⏭":
            print("attempting to skip to end")
            await vc.seek(vc.track.duration * 1000)
    @commands.command(name='pass_api_key')
    async def pass_api_key(self, ctx, *, api_key: str):
        """Passes the API key to the bot.

        Parameters
        ----------
        api_key: str
            The API key to pass to the bot.
        """
        self.GOOGLE_API_KEY = api_key
        await ctx.send("API key passed.")

        
async def setup(bot):
    await bot.add_cog(Music(bot))