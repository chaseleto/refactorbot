import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import datetime
import asyncio
import yaml
from googleapiclient.discovery import build

class Music(commands.Cog):

    #############################################################################################################################################################
    #                                                                         Initialization                                                                    #
    #############################################################################################################################################################
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    with open('config/cfg.yml', 'r') as f:
        config = yaml.safe_load(f)
        
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
    GOOGLE_API_KEY = config['GOOGLE_API_KEY']
    youtube = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)

    @commands.command(name='play', description='Plays a song')
    async def play(self, ctx, *, query):
        """Play a song."""
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

        #Add track to queue or play if queue is empty and not playing
        if not vc.is_playing() and self.queue.is_empty:
            await vc.play(track)
            await asyncio.sleep(1)
            await self.now_playing_embed(vc)
            self.context = ctx
        else:
            self.queue.put(track)
            await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player: wavelink.Player, track: wavelink.Track, reason: str):
        """Event fired when a track has finished playing."""
        if self.queue.is_empty and reason == 'FINISHED':
            return await player.disconnect()
        await player.play(self.queue.pop())
        await self.now_playing_embed(player, 1, self.play_tracking_message)
        
    @commands.command(name='skip', description='Skips the current song')
    async def skip(self, ctx):
        """Skip a song."""
        vc: wavelink.Player = ctx.voice_client
        if not vc.is_playing():
            return await ctx.send('I am not playing anything right now.')
        if self.queue.is_empty:
            await vc.stop()
        else:
            await vc.seek(vc.track.length * 1000)
            await ctx.send('Skipped the current song.')
            if vc.is_paused:
                vc.resume()

    @commands.hybrid_command(name='playing', description='Shows the current song', with_app_command=True)
    async def playing(self, ctx):
        """Shows the current song."""
        vc: wavelink.Player = ctx.voice_client
        await self.now_playing_embed(ctx.voice_client)

    @commands.command(name='pause', description='Pauses the current song')
    async def pause(self, ctx):
        """Pause a song."""
        vc: wavelink.Player = ctx.voice_client
        if not vc.is_playing():
            return await ctx.send('I am not playing anything right now.')
        await vc.pause()
        await ctx.send('Paused the current song.')

    @commands.command(name='resume', description='Resumes the current song')
    async def resume(self, ctx):
        """Resume a song."""
        vc: wavelink.Player = ctx.voice_client
        if not vc.is_playing():
            return await ctx.send('I am not playing anything right now.')
        if not vc.is_paused:
            return await ctx.send('I am not paused.')
        await vc.resume()
        await ctx.send('Resumed the current song.')

    @commands.hybrid_command(name='seek', description='Seeks to a position in the current song', with_app_command=True)
    async def seek(self, ctx, position: int):
        """Seek to a position in the current song."""
        vc: wavelink.Player = ctx.voice_client
        if not vc.is_playing():
            return await ctx.send('I am not playing anything right now.')
        if position > vc.track.length:
            return await ctx.send('Position is longer than the song.')
        await vc.seek(position * 1000)
        seek = position
        await self.now_playing_embed(ctx.voice_client, int(seek), self.play_tracking_message)
    
    @commands.command(name='queue', description='Shows the current queue')
    async def queued(self, ctx):
        """Shows the current queue."""
        vc: wavelink.Player = ctx.voice_client
        if self.queue.is_empty:
            return await ctx.send('The queue is empty.')
        queue = self.queue
        embed = discord.Embed(title='Queue', color=discord.Color.green())
        for i, track in enumerate(queue):
            embed.add_field(name=f'{i + 1}. {track.title}', value=f'Duration: {track.duration}')
        await ctx.send(embed=embed)

    async def now_playing_embed(self, voice_player, seeked_to = None, play_tracking_message = None):
        """Create an embed for the current song."""
        vc: wavelink.Player = voice_player
        music_channel = voice_player.guild.get_channel(int(self.music_channel))
        current_seconds = datetime.timedelta(seconds=int(vc.position))
        track_length = vc.track.length
        if not vc.is_playing():
            return await music_channel.send('I am not playing anything right now.')
        if seeked_to and self.play_tracking:
            current_seconds = datetime.timedelta(seconds=seeked_to)
            await play_tracking_message.delete()
        elif seeked_to and not self.play_tracking:
            current_seconds = datetime.timedelta(seconds=0)
        
        embed = discord.Embed(title=f'**{vc.track}**', description=f'{vc.track.author}\n▶️ ({str(current_seconds)}/{str(datetime.timedelta(seconds=vc.track.length))})', color=discord.Color.from_str("#ff0101"), url=str(vc.track.uri))
        embed.set_thumbnail(url=vc.track.thumb)
        msg = await music_channel.send(embed=embed)
        self.play_tracking_message = msg
        self.play_tracking = True
        while datetime.timedelta(seconds=int(vc.position)) < datetime.timedelta(seconds=vc.track.length):
            
            embed.description = f'**{vc.track.author}**\n\n▶️ (__*{datetime.timedelta(seconds=int(vc.position))}/{str(datetime.timedelta(seconds=track_length))}*__) ◀️'
            try:
                await msg.edit(embed=embed)
            except:
                break
            await asyncio.sleep(0.9)

    @commands.command(name='autoplay', description='Toggles autoplay')
    async def autoplay_toggle(self, ctx):
        """Toggle autoplay."""
        if self.autoplay_:
            self.autoplay_ = False
            await ctx.send('Autoplay has been disabled.')
        else:
            self.autoplay_ = True
            if await self.check_api_key():
                await ctx.send('Autoplay has been enabled.')
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
        request = self.youtube.search().list(
                        part='snippet',
                        relatedToVideoId=str(video_id),
                        type="video",
                    )
        response = request.execute()
        ls_ids = []
        for item in response['items']:
            ls_ids.append(item['id']['videoId'])
        return ls_ids
    
    @commands.Cog.listener()
    async def on_wavelink_track_start(self, player: wavelink.Player, track: wavelink.Track):
        """Track start event."""
        print("track started")
        if self.autoplay_:
            for related_video in await self.get_related_videos(track.identifier):
                try:
                    track = await wavelink.YouTubeTrack.search("https://www.youtube.com/watch?v=" + related_video, return_first=True)
                    self.queue.put(track)
                except :
                    print("Couldn't add related video to queue.")
        else:
            return

async def setup(bot):
    await bot.add_cog(Music(bot))