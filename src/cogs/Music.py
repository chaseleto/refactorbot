import math
import time
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
        
    with open('/home/src/config/cfg.yml', 'r') as f:
        config = yaml.safe_load(f)
    
    mg = MongoClient('mongodb', 27017,
                 username=os.environ['MONGO_USER'],
                 password=os.environ['MONGO_PASSWORD'])

    async def connect_nodes(self):
        """Connect to our Lavalink nodes."""
        await self.bot.wait_until_ready()

        await wavelink.NodePool.create_node(bot=self.bot,
                                            host='lavalink',
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


    @commands.command(name='play', aliases=['p'])
    async def play(self, ctx, *, query):
        """Plays a song from youtube.

        Parameters
        ----------
        query: str
            The name of the song to search from youtube.
        """
        collection = self.mg['discord']['guilds']
        try:
            dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
            dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
            if dj_ids is not None and dj_lock:
                if ctx.author.id not in dj_ids:
                    await ctx.send("You are not a DJ. Please ask a DJ to add you to the list of DJ's.")
                    return
        except:
            print("something went wrong")

        
        music_channel = None
        try:
            music_channel = ctx.guild.get_channel(int(collection.find_one({'guild_id': ctx.guild.id})['music_channel_id']))
        except:
            print("something went wrong")
        if music_channel is None or music_channel == '':
            await ctx.send("Please set a music channel by using the /setup_music slash command and selecting the desired channel.")
            return
        #Get playable object from query
        track = await wavelink.YouTubeTrack.search(query=query, return_first=True)

        #Check if the bot has a player in the guild
        if not ctx.voice_client:
            try:
                vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            except AttributeError:
                await ctx.send("You are not in a voice channel.")
                return
            if ctx.author.id not in dj_ids:
                collection.find_one_and_update({'guild_id': ctx.guild.id}, {'$push': {'dj_ids': ctx.author.id}})
            await vc.set_volume(50)
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
        
        if not vc.is_playing() and vc.queue.is_empty:
            await vc.play(track)
            await asyncio.sleep(1)
        else:
            vc.queue.put_at_index(self.find_index_not_autoplay(vc.queue), track)
            await ctx.send(content="Added to queue:", embed=embed)
    
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player: wavelink.Player, track: wavelink.Track, reason: str):
        """Event fired when a track has finished playing."""
        if player.queue.is_empty:
            collection = self.mg['discord']['guilds']
            collection.find_one_and_update({'guild_id': player.guild.id}, {'$set': {'dj_ids': []}})
            collection.find_one_and_update({'guild_id': player.guild.id}, {'$set': {'dj_lock': False}})
            now_playing_msg = collection.find_one({'guild_id': player.guild.id})['play_tracking_message_id']
            music_channel_id = int(collection.find_one({'guild_id': player.guild.id})['music_channel_id'])
            music_channel = player.guild.get_channel(music_channel_id)
            if now_playing_msg is not None:
                try:
                    await asyncio.sleep(5)
                    msg = await music_channel.fetch_message(now_playing_msg)
                    await msg.delete()
                except:
                    print("Message not found")
            return await player.disconnect()
        await player.play(player.queue.get())
        
    @commands.command(name='skip')
    async def skip(self, ctx):
        """Skips the current song.

        Parameters
        ----------

        """
        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
        if dj_ids is not None and dj_lock:
            if ctx.author.id not in dj_ids:
                await ctx.send("You are not a DJ. Please ask a DJ to add you to the list of DJ's.")
                return
        try:
            vc: wavelink.Player = ctx.voice_client
        except:
            return await ctx.send('I am not in a voice channel.')
        if not vc.is_playing():
            return await ctx.send('I am not playing anything right now.')
        if vc.queue.is_empty:
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
        music_channel = None
        if music_channel is None or music_channel == '':
            collection = self.mg['discord']['guilds']
            music_channel = None
            try:
                music_channel = ctx.guild.get_channel(int(collection.find_one({'guild_id': ctx.guild.id})['music_channel_id']))
            except:
                print("something went wrong")
            if music_channel is None or music_channel == '':
                await ctx.send("Please set a music channel by using the /setup_music slash command and selecting the desired channel.")
                return
        try:
            vc: wavelink.Player = ctx.voice_client
        except:
            return await ctx.send('I am not in a voice channel.')
        await self.now_playing_embed(ctx.voice_client)

    @commands.command(name='pause', aliases=['stop'])
    async def pause(self, ctx):
        """Pauses the current player.

        Parameters
        ----------

        """
        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
        if dj_ids is not None and dj_lock:
            if ctx.author.id not in dj_ids:
                await ctx.send("You are not a DJ. Please ask a DJ to add you to the list of DJ's.")
                return
        try:
            vc: wavelink.Player = ctx.voice_client
        except:
            return await ctx.send('I am not in a voice channel.')
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
        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
        if dj_ids is not None and dj_lock:
            if ctx.author.id not in dj_ids:
                await ctx.send("You are not a DJ. Please ask a DJ to add you to the list of DJ's.")
                return
        try:
            vc: wavelink.Player = ctx.voice_client
        except:
            return await ctx.send('I am not in a voice channel.')
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
        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
        if dj_ids is not None and dj_lock:
            if ctx.author.id not in dj_ids:
                await ctx.send("You are not a DJ. Please ask a DJ to add you to the list of DJ's.")
                return
        try:
            vc: wavelink.Player = ctx.voice_client
        except:
            return await ctx.send('I am not in a voice channel.')
        if not vc.is_playing():
            return await ctx.send('I am not playing anything right now.')
        if position > vc.track.length:
            return await ctx.send('Position is longer than the song.')
        await vc.seek(position * 1000)
        seek = position
        await self.now_playing_embed(ctx.voice_client)
    
    @commands.command(name='queue', aliases=['q', 'cue', 'qu'])
    async def queued(self, ctx, page: int = 1):
        """Displays the current song queue. Displays 9 songs per page.

        Parameters
        ----------
        page: int
            The page to display
        """
        music_channel = None
        if music_channel is None or music_channel == '':
            collection = self.mg['discord']['guilds']
            try:
                music_channel = ctx.guild.get_channel(int(collection.find_one({'guild_id': ctx.guild.id})['music_channel_id']))
            except:
                print("something went wrong")
            if music_channel is None or music_channel == '':
                await ctx.send("Please set a music channel by using the /setup_music slash command and selecting the desired channel.")
                return
        try:
            vc: wavelink.Player = ctx.voice_client
        except:
            return await ctx.send('I am not in a voice channel.')
        if vc.queue.is_empty:
            return await ctx.send('The queue is empty.')
        queue = vc.queue
        total_time_in_queue = 0
        for track in vc.queue:
            total_time_in_queue += track.duration
        startIndex = (page - 1) * 9
        totalPages = math.ceil(len(vc.queue) / 9)
        if startIndex >= len(vc.queue):
            return await ctx.send(f"Page {page} doesn't exist.")
        embed = discord.Embed(
                type="rich",
                title=f"Now Playing: {vc.track.title}",
                description=f"Total songs: {len(vc.queue)}\nTotal queued time: {str(datetime.timedelta(seconds=total_time_in_queue))}\n\nUp next (page {page} of {totalPages}):",
                color=discord.Color.random(),
                timestamp=datetime.datetime.now(),
                url=f"{vc.track.uri}"
            )
        for count, song in enumerate(vc.queue):
            if count < startIndex or count >= startIndex + 9:
                continue
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
        collection = self.mg['discord']['guilds']
        autoplay = collection.find_one({'guild_id': voice_player.guild.id})['autoplay']
        music_channel_id = collection.find_one({'guild_id': voice_player.guild.id})['music_channel_id']
        dj_ids = collection.find_one({'guild_id': voice_player.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': voice_player.guild.id})['dj_lock']
        music_channel = voice_player.guild.get_channel(int(music_channel_id))
        guild = voice_player.guild.id
        try:
            play_tracking_message = await music_channel.fetch_message(int(collection.find_one({'guild_id': guild})['play_tracking_message_id']))
        except:
            play_tracking_message = None
        try:
            vc: wavelink.Player = voice_player
        except:
            return
        music_channel = None
        try:
            music_channel = voice_player.guild.get_channel(int(collection.find_one({'guild_id': guild})['music_channel_id']))
        except:
            print("something went wrong")
        if music_channel is None or music_channel == '':
            return
        current_seconds = datetime.timedelta(seconds=int(vc.position))
        track_length = vc.track.length
        if not vc.is_playing():
            return await music_channel.send('I am not playing anything right now.')
        if play_tracking_message:
            try:
                await play_tracking_message.delete()
            except:
                print("No play tracking message found")
        requester = "Unknown"
        try:
            requester = vc.track.requester.mention
        except:
            requester = "AutoPlayed"
            vc.track.requester = "AutoPlayed"
        
        embed = discord.Embed(title=f'**{vc.track}**', description=f'{vc.track.author}\n\n**Queued by: {requester}\nAutoPlay: {autoplay}\nVolume: {vc.volume}%**\n\n▶️ ({str(current_seconds)}/{str(datetime.timedelta(seconds=vc.track.length))})', color=discord.Color.from_str("#ff0101"), url=str(vc.track.uri))
        thumb = f"http://img.youtube.com/vi/{vc.track.identifier}/hqdefault.jpg"
        embed.set_thumbnail(url=f"{thumb}")
        msg = await music_channel.send(content="ɴᴏᴡ ᴘʟᴀʏɪɴɢ", embed=embed)
        collection.find_one_and_update({'guild_id': guild}, {'$set': {'play_tracking_message_id': msg.id}})
        #self.play_tracking_message = msg
        #self.play_tracking = True
        await msg.add_reaction('⏮')
        await msg.add_reaction('⏪')
        await msg.add_reaction('⏯')
        await msg.add_reaction('⏩')
        await msg.add_reaction('⏭')
        

        while datetime.timedelta(seconds=int(vc.position)) < datetime.timedelta(seconds=vc.track.length):
            current_djs = "None"
            if dj_lock:
                current_djs = ""
                for dj in dj_ids:
                    current_djs += f"{voice_player.guild.get_member(dj).mention}, "
                if current_djs == "":
                    current_djs = "None"
            embed.description = f'{vc.track.author}\n\n**Queued by:** {requester}\n**AutoPlay:** {autoplay}\n**Volume:** {vc.volume}%\n**Current DJs:** {current_djs}\n\n▶️ (__*{datetime.timedelta(seconds=int(vc.position))}/{str(datetime.timedelta(seconds=track_length))}*__) ◀️'
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
        Once you have your key, run the command `/set_google_api_key <your key here>`. You will only need to do this once but you may update it as much as you would like. 

        Each key has a quota of 10,000 units per day. Each call to the API is 100 units. If you are using the bot in a large server, you may want to consider getting a key with a higher quota.

        when autoplay is turned on, the bot will check to make sure the key is valid, this will use 100 units. 

        The bot will add 2-6 songs to the queue at a time. Each time this is done it will only use 100 units. When the queue reaches 2 songs left, it will add another 2-6 songs, using another 100 units.

        If autoplay is used once and playing songs consecutively, you should be able to get around 200-500 songs in a day.

        Parameters
        ----------
        max_duration: int
            The maximum duration of songs to add to the queue automatically 
        """
        music_channel = None
        collection = self.mg['discord']['guilds']
        autoplay = collection.find_one({'guild_id': ctx.guild.id})['autoplay']
        if music_channel is None or music_channel == '':
            try:
                music_channel = ctx.guild.get_channel(int(collection.find_one({'guild_id': ctx.guild.id})['music_channel_id']))
            except:
                print("something went wrong")
            if music_channel is None or music_channel == '':
                await ctx.send("Please set a music channel by using the /setup_music slash command and selecting the desired channel.")
                return
        enabled_message = 'Autoplay has been enabled.'
        
        
        if max_duration:
            max_duration = max_duration * 60
            collection.find_one_and_update({'guild_id': ctx.guild.id}, {'$set': {'autoplay_max_duration': max_duration}})
            enabled_message += f' Songs will be limited to {int(max_duration/60)} minutes.'
        try:
            vc: wavelink.Player = ctx.voice_client
        except:
            await ctx.send("I am not in a voice channel.")
            return
        if autoplay:
            collection.find_one_and_update({'guild_id': ctx.guild.id}, {'$set': {'autoplay': False}})
            await ctx.send('Autoplay has been disabled.')
            removeList = []
            for song in vc.queue._queue:
                if song.requester == "AutoPlayed":
                    removeList.append(song)
                    print(f"removing: {song} because requester: {song.requester}")
            for track in removeList:
                try:
                    del vc.queue._queue[vc.queue.find_position(track)]
                    print(f"Removed {track}")
                except:
                    print(f"failed to remove track {track}")
        else:
            collection.find_one_and_update({'guild_id': ctx.guild.id}, {'$set': {'autoplay': True}})
            if await self.check_api_key(ctx):
                await ctx.send(enabled_message)
                if vc.is_playing():
                    track = vc.track
                    for related_video in await self.get_related_videos(track.identifier, ctx.guild.id):
                        try:                            
                            track = await wavelink.YouTubeTrack.search("https://www.youtube.com/watch?v=" + related_video, return_first=True)
                            track.requester = "AutoPlayed"
                            if max_duration and track.length <= max_duration:
                                vc.queue.put(track)
                            elif not max_duration:
                                vc.queue.put(track)
                        except :
                            print("Couldn't add related video to queue.")

            elif not await self.check_api_key(ctx):
                await ctx.send('Your API key is invalid. Please set it by using the slash command `/set_google_api_key <your key here>`.')
                collection.find_one_and_update({'guild_id': ctx.guild.id}, {'$set': {'autoplay': False}})

    async def check_api_key(self, ctx):
        """Autoplay."""
        collection = self.mg['discord']['guilds']
        autoplay = False
        try:
            autoplay = collection.find_one({'guild_id': ctx.guild.id})['autoplay']
        except:
            print("something went wrong")
        if autoplay:
            
            api_key = collection.find_one({'guild_id': ctx.guild.id})['google_api_key']
            if api_key:
                youtube = build('youtube', 'v3', developerKey=api_key)
                try:
                    request = youtube.search().list(
                        part='snippet',
                        relatedToVideoId="mRzv6Zcowz0",
                        type="video",
                    )
                    response = request.execute()
                except:
                    return False
            else:
                return False
            return True

    async def get_related_videos(self, video_id, guild):
        """Get related videos."""
        try:
            collection = self.mg['discord']['guilds']
            api_key = collection.find_one({'guild_id': guild})['google_api_key']
            print(api_key)
            youtube = build('youtube', 'v3', developerKey=api_key)
            request = youtube.search().list(
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
        collection = self.mg['discord']['guilds']
        #check djTimer and remove if expired
        try:
            djTimer: datetime = collection.find_one({'guild_id': player.guild.id})['djTimer']
        except Exception as e:
            print(e)
            djTimer = None
        try:
            if djTimer:
                if datetime.datetime.now() - djTimer >= datetime.timedelta(minutes=30):
                    collection.find_one_and_update({'guild_id': player.guild.id}, {'$set': {'djTimer': None}})
                    collection.find_one_and_update({'guild_id': player.guild.id}, {'$set': {'dj_ids': []}})
                    collection.find_one_and_update({'guild_id': player.guild.id}, {'$set': {'dj_lock': False}})
                    
        except Exception as e:
            print(e)
        try:
            max_duration = int(collection.find_one({'guild_id': player.guild.id})['autoplay_max_duration'])
        except:
            max_duration = None
        autoplay = collection.find_one({'guild_id': player.guild.id})['autoplay']
        music_channel = None
        await self.now_playing_embed(player)
        try:
            music_channel = player.guild.get_channel(int(collection.find_one({'guild_id': player.guild.id})['music_channel_id']))
        except:
            print("something went wrong")
        if music_channel is None or music_channel == '':
            return
        guild = player.guild.id
        if autoplay and player.queue.count <= 2:
            related = await self.get_related_videos(track.identifier, guild)
            if not related:
                await music_channel.send("Could not add related video to queue. This is likely due to exceeding your daily quota of 10,000 units. Please try again tomorrow or update your Google API Key. More: !help autoplay")
                autoplay = False
                return
            for related_video in related:
                try:
                    track = await wavelink.YouTubeTrack.search("https://www.youtube.com/watch?v=" + related_video, return_first=True)
                    track.requester = "AutoPlayed"
                    if max_duration and track.duration <= max_duration:
                        player.queue.put(track)
                    elif not max_duration:
                        player.queue.put(track)
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
        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
        try:
            vc: wavelink.Player = ctx.voice_client
        except:
            await ctx.send("I am not connected to a voice channel.")
            return
        if dj_ids is not None and dj_lock:
            if ctx.author.id not in dj_ids:
                await ctx.send("You are not a DJ. Please ask a DJ to add you to the list of DJ's.")
                return

        vc.queue.clear()
        await ctx.send('Cleared the queue.')
    
    @commands.command(name='disconnect', aliases=['dc', 'leave'])
    async def disconnect(self, ctx):
        """Disconnects the bot from its current voice channel and clears the queue.

        Parameters
        ----------

        """
        collection = self.mg['discord']['guilds']
        autoplay = collection.find_one({'guild_id': ctx.guild.id})['autoplay']
        dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
        if dj_ids is not None and dj_lock:
            if ctx.author.id not in dj_ids:
                await ctx.send("You are not a DJ. Please ask a DJ to add you to the list of DJ's.")
                return
        try:
            vc: wavelink.Player = ctx.voice_client
        except:
            await ctx.send("I am not connected to a voice channel.")
            return
        if not vc:
            return await ctx.send('I am not connected to a voice channel.')
        await vc.disconnect()
        await ctx.send('Disconnected from the voice channel.')
        vc.queue.clear()
        collection.find_one_and_update({'guild_id': ctx.guild.id}, {'$set': {'dj_ids': []}})
        collection.find_one_and_update({'guild_id': ctx.guild.id}, {'$set': {'dj_lock': False}})
        if autoplay: autoplay = False
    
    @commands.command(name='volume', aliases=['vol'])
    async def volume(self, ctx, volume: int):
        """Sets the volume of the bot's player.

        Parameters
        ----------
        volume: int
            The volume to set the player to. Must be between 1 and 100.
        """
        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
        if dj_ids is not None and dj_lock:
            if ctx.author.id not in dj_ids:
                await ctx.send("You are not a DJ. Please ask a DJ to add you to the list of DJ's.")
                return
        try:
            vc: wavelink.Player = ctx.voice_client
        except:
            await ctx.send("I am not connected to a voice channel.")
            return
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
        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
        if dj_ids is not None and dj_lock:
            if ctx.author.id not in dj_ids:
                await ctx.send("You are not a DJ. Please ask a DJ to add you to the list of DJ's.")
                return
        if ctx.author.id not in dj_ids:
            collection.find_one_and_update({'guild_id': ctx.guild.id}, {'$push': {'dj_ids': ctx.author.id}})
        try:
            vc: wavelink.Player = ctx.voice_client
        except:
            await ctx.send("I am not connected to a voice channel.")
            return
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
        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
        if dj_ids is not None and dj_lock:
            if ctx.author.id not in dj_ids:
                await ctx.send("You are not a DJ. Please ask a DJ to add you to the list of DJ's.")
                return
        try:
            vc: wavelink.Player = ctx.voice_client
        except:
            await ctx.send("I am not connected to a voice channel.")
            return
        if not vc:
            return await ctx.send('I am not connected to a voice channel.')
        if not 0 < index <= vc.queue.count:
            return await ctx.send('Please enter a valid index.')
        track = vc.queue[index - 1]
        vc.queue.__delitem__(index - 1)
        vc.queue.put_at_front(track)

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
        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
        if dj_ids is not None and dj_lock:
            if ctx.author.id not in dj_ids:
                await ctx.send("You are not a DJ. Please ask a DJ to add you to the list of DJ's.")
                return
        try:
            vc: wavelink.Player = ctx.voice_client
        except:
            await ctx.send("I am not connected to a voice channel.")
            return
        if ctx.author.id not in dj_ids:
            collection.find_one_and_update({'guild_id': ctx.guild.id}, {'$push': {'dj_ids': ctx.author.id}})
        music_channel = None
        if music_channel is None or music_channel == '':
            collection = self.mg['discord']['guilds']
            try:
                music_channel = ctx.guild.get_channel(int(collection.find_one({'guild_id': ctx.guild.id})['music_channel_id']))
            except:
                print("something went wrong")
            if music_channel is None or music_channel == '':
                await ctx.send("Please set a music channel by using the /setup_music slash command and selecting the desired channel.")
                return
        if not vc.queue:
            return await ctx.send('There is nothing in the queue.')
        track = await wavelink.YouTubeTrack.search(query=query, return_first=True)
        vc.queue.put_at_front(track)
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
        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': reaction.message.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': reaction.message.guild.id})['dj_lock']
        if dj_ids is not None and dj_lock:
            if user.id not in dj_ids:
                return
        
        try:
            music_channel = reaction.message.guild.get_channel(int(collection.find_one({'guild_id': reaction.message.guild.id})['music_channel_id']))
            play_tracking_message = await music_channel.fetch_message(collection.find_one({'guild_id': reaction.message.guild.id})['play_tracking_message_id'])
        except:
            print("something went wrong")
            return
        if user == self.bot.user:
            return
        if reaction.message != play_tracking_message:
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
        elif reaction.emoji == "⏯":

            if vc.is_paused():
                print("Already paused.")
                await vc.resume()
            elif not vc.is_paused():
                print("not paused")
                await vc.pause()
            await vc.pause()
        elif reaction.emoji == "⏩":
            if vc.position + 15 > vc.track.duration:
                await vc.seek(vc.track.duration * 1000)
            else:
                await vc.seek((vc.position + 15) * 1000)
        elif reaction.emoji == "⏭":
            skipped_at = int(round(datetime.timedelta(seconds=vc.position).total_seconds(), 0))
            if vc.queue:
                skip_msg = await reaction.message.channel.send(f"{user.mention} skipped {vc.track.title} {str(skipped_at)} seconds in, and is now playing {vc.queue[0].title}")
            else:
                skip_msg = await reaction.message.channel.send(f"{user.mention} skipped {vc.track.title} {str(skipped_at)} seconds in, and the queue is now empty.")
            await vc.seek(vc.track.duration * 1000)
            await asyncio.sleep(15)
            await skip_msg.delete()

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': reaction.message.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': reaction.message.guild.id})['dj_lock']
        if dj_ids is not None and dj_lock:
            if user.id not in dj_ids:
                return
        
        try:
            music_channel = reaction.message.guild.get_channel(int(collection.find_one({'guild_id': reaction.message.guild.id})['music_channel_id']))
            play_tracking_message = await music_channel.fetch_message(int(collection.find_one({'guild_id': reaction.message.guild.id})['play_tracking_message_id']))
        except:
            print("something went wrong")
            return
        if user == self.bot.user:
            return
        if reaction.message != play_tracking_message:
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
        elif reaction.emoji == "⏯":
            if vc.is_paused():
                #print("Already paused.")
                await vc.resume()
            elif not vc.is_paused():
                #print("not paused")
                await vc.pause()
        elif reaction.emoji == "⏩":
            print(f"attempting to skip forward {vc.position}, {vc.position + 15}, {vc.track.duration}")
            if vc.position + 15 >= vc.track.duration:
                await vc.seek(vc.track.duration * 1000)
            else:
                await vc.seek((vc.position + 15) * 1000)
        elif reaction.emoji == "⏭":
            skipped_at = round(datetime.timedelta(seconds=vc.position * 1000).total_seconds(), 2)
            if vc.queue:
                skip_msg = await reaction.message.channel.send(f"{user.mention} skipped {vc.track.title} {str(skipped_at)[:1]} in, and is now playing {vc.queue[0].title}")
            else:
                skip_msg = await reaction.message.channel.send(f"{user.mention} skipped {vc.track.title} {str(skipped_at)[:1]} in, and the queue is now empty.")
            await vc.seek(vc.track.duration * 1000)
            await asyncio.sleep(10)
            await skip_msg.delete()
    @app_commands.command(name='pass_api_key')
    async def pass_api_key(self, interaction: discord.Interaction, api_key: str):
        """Passes the google API key to the bot.

        Parameters
        ----------
        api_key: str
            The API key to pass to the bot.
        """
        collection = self.mg['discord']['guilds']
        collection.find_one_and_update({"guild_id": interaction.guild.id}, 
                                 {"$set": {"google_api_key": api_key}})
        collection.find_one_and_update({"guild_id": interaction.guild.id}, 
                                 {"$set": {"has_api_key": True}})
        await interaction.response.send_message("API key passed.", ephemeral=True)
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        empty_channel = False
        collection = self.mg['discord']['guilds']
        if member == self.bot.user and before.channel is not None and after.channel is None:
            collection.find_one_and_update({'guild_id': member.guild.id}, {'$set': {'dj_ids': []}})
            collection.find_one_and_update({'guild_id': member.guild.id}, {'$set': {'autoplay': False}})
            collection.find_one_and_update({'guild_id': member.guild.id}, {'$set': {'djTimer': False}})
            return
        try:
            if before.channel == member.guild.voice_client.channel and after.channel is not member.guild.voice_client.channel:
                print("left same channel as bot")
                if len(before.channel.members) == 1:
                    empty_channel = True
                    print("no one left in channel")
                    await asyncio.sleep(60)
                    if len(before.channel.members) == 1:
                        await member.guild.voice_client.disconnect()
        
        except Exception as e:
            return
        else:
            return
    @commands.command(name='remove', aliases=['rm', 'delete', 'del'])
    async def remove(self, ctx, index: int):
        """Removes a track from the queue.

        Parameters
        ----------
        index: int
            The index of the track to remove. Default to last in queue.
        """
        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
        if dj_ids is not None and dj_lock:
            if ctx.author.id not in dj_ids:
                await ctx.send("You are not a DJ. Please ask a DJ to add you to the list of DJ's.")
                return
        try:
            vc: wavelink.Player = ctx.guild.voice_client
        except AttributeError:
            await ctx.send("I am not currently in a voice channel.")
            return
        try:
            track = vc.queue[index - 1]
            del vc.queue._queue[index - 1]
            await ctx.send(f"Removed {track.title} from the queue.")
        except IndexError:
            await ctx.send("Invalid index.")
    @commands.command(name='add', aliases=['a'])
    async def addSongs(self, ctx, *, query: str):
        """Adds multiple songs to the queue, seperated by commas (,). Ex. .add song1, song2, song3.
        
        Parameters
        ----------
        query: str
            The queries to search for.
        """
        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
        if dj_ids is not None and dj_lock:
            if ctx.author.id not in dj_ids:
                await ctx.send("You are not a DJ. Please ask a DJ to add you to the list of DJ's.")
                return
        try:
            vc: wavelink.Player = ctx.guild.voice_client
        except:
            print("no player found")
        if ctx.author.id not in dj_ids:
            collection.find_one_and_update({"guild_id": ctx.guild.id}, 
                                     {"$push": {"dj_ids": ctx.author.id}})
        music_channel=None
        if music_channel is None or music_channel == '':
            collection = self.mg['discord']['guilds']
            try:
                music_channel = ctx.guild.get_channel(int(collection.find_one({'guild_id': ctx.guild.id})['music_channel_id']))
            except:
                print("something went wrong")
            if music_channel is None or music_channel == '':
                await ctx.send("Please set a music channel by using the /setup_music slash command and selecting the desired channel.")
                return
        songs = []
        for song in query.split(","):
            try:
                if song == " " or song == "":
                    continue
                songs.append(await wavelink.YouTubeTrack.search(query=song, return_first=True))
            except wavelink.NoTracksFound:
                print("No track found for {song}.")
        if ctx.voice_client:
            if songs == []:
                await ctx.send("No songs found.")
                return
            for track in songs:
                track.requester = ctx.author
                vc.queue.put(track)
            await ctx.send(f"Added {len(songs)} songs to the queue.")
        else:
            if songs == []:
                await ctx.send("No songs found.")
                return
                #Check if the bot has a player in the guild
            if not ctx.voice_client:
                try:
                    vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
                    await vc.set_volume(50)
                except:
                    await ctx.send("You are not in a voice channel.")
                    return
            else:
                vc: wavelink.Player = ctx.voice_client
            
            for track in songs:
                track.requester = ctx.author
                vc.queue.put(track)
            await ctx.send(f"Added {len(songs)} songs to the queue.")
            await vc.play(vc.queue.get())

    @commands.command(name='lock', aliases=['l'])
    async def lock(self, ctx):
        """Locks the queue so only DJ's can add songs."""

        startTime = datetime.datetime.now()

        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
        try:
            djCooldownID = collection.find_one({'guild_id': ctx.guild.id})['djCooldownID']
            djCooldownTime = collection.find_one({'guild_id': ctx.guild.id})['djCooldownTime']
            if djCooldownID: 
                if ctx.author.id == djCooldownID:
                    if datetime.datetime.now() - djCooldownTime < datetime.timedelta(minutes=5):
                        await ctx.send(f"You are on cooldown. Please wait {(datetime.datetime.now() - djCooldownTime).minutes} minutes To become the only DJ again.")
                        return
                    else:
                        collection.find_one_and_update({"guild_id": ctx.guild.id}, 
                                     {"$set": {"djCooldownID": None}})
                        collection.find_one_and_update({"guild_id": ctx.guild.id},
                                        {"$set": {"djCooldownTime": None}})
        except:
            pass
        if dj_lock:
            await ctx.send("The queue is already locked.")
            return
        if dj_ids is not None and dj_lock:
            if ctx.author.id not in dj_ids:
                await ctx.send("You are not a DJ. Please ask a DJ to add you to the list of DJ's.")
                return
        if ctx.author.id not in dj_ids:
            collection.find_one_and_update({"guild_id": ctx.guild.id}, 
                                     {"$push": {"dj_ids": ctx.author.id}})
        collection.find_one_and_update({"guild_id": ctx.guild.id}, 
                                     {"$set": {"dj_lock": True}})
        collection.find_one_and_update({"guild_id": ctx.guild.id}, 
                                     {"$set": {"djTimer": startTime}})
        collection.find_one_and_update({"guild_id": ctx.guild.id}, 
                                     {"$set": {"djCooldownID": ctx.author.id}})
        collection.find_one_and_update({"guild_id": ctx.guild.id}, 
                                     {"$set": {"djCooldownTime": datetime.datetime.now()}})
        await ctx.send("Locked the queue. Only DJ's can add songs now. The queue will unlock in 30 minutes. If you want to unlock the queue early, use the .unlock command. To add a DJ, use the .dj @user command. To see a list of DJ's, use the .djs command.")
    @commands.command(name='unlock', aliases=['ul'])
    async def unlock(self, ctx):
        """Unlocks the queue so anyone can add songs."""
        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
        if dj_ids is not None and dj_lock:
            if ctx.author.id not in dj_ids:
                await ctx.send("You are not a DJ. Please ask a DJ to add you to the list of DJ's.")
                return
        collection.find_one_and_update({"guild_id": ctx.guild.id}, 
                                     {"$set": {"dj_lock": False}})
        collection.find_one_and_update({"guild_id": ctx.guild.id}, 
                                     {"$pull": {"dj_ids": ctx.author.id}})
        collection.find_one_and_update({"guild_id": ctx.guild.id}, 
                                     {"$set": {"djTimer": False}})
        collection.find_one_and_update({"guild_id": ctx.guild.id}, 
                                     {"$set": {"djCooldownID": False}})
        await ctx.send("Unlocked the queue.")
    @commands.command(name='dj', aliases=['d', 'allow', 'let'])
    async def dj(self, ctx, member: discord.Member):
        """Adds a member to the list of DJ's."""
        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
        if dj_ids is not None and dj_lock:
            if ctx.author.id not in dj_ids:
                await ctx.send("You are not a DJ. Please ask a DJ to add you to the list of DJ's.")
                return
        if member.id in dj_ids:
            return
        collection.find_one_and_update({"guild_id": ctx.guild.id}, 
                                     {"$push": {"dj_ids": member.id}})
        await ctx.send(f"Added {member.name} to the list of DJ's.")
    @commands.command(name='djs', aliases=['ds', 'djslist', 'djlist'])
    async def djs(self, ctx):
        """Shows the list of DJ's."""
        collection = self.mg['discord']['guilds']
        
        dj_ids = list(collection.find_one({'guild_id': ctx.guild.id})['dj_ids'])

        if dj_ids is None:
            await ctx.send("There are no DJ's.")
            return
        if dj_ids == []:
            await ctx.send("There are no DJ's.")
            return
        djs = ""
        for dj in dj_ids:
            djs += f"{ctx.guild.get_member(dj).mention} "
        await ctx.send(f"DJ's: {djs}")
    @commands.command(name='djtimer', aliases=['dt'])
    async def djtimer(self, ctx):
        """Shows the time left for the DJ's."""
        collection = self.mg['discord']['guilds']
        dj_ids = collection.find_one({'guild_id': ctx.guild.id})['dj_ids']
        dj_lock = collection.find_one({'guild_id': ctx.guild.id})['dj_lock']
        if dj_ids is None or not dj_lock:
                await ctx.send("Music is not locked.")
                return
        if dj_lock:
            djTimer = collection.find_one({'guild_id': ctx.guild.id})['djTimer']
            djTimer = djTimer + datetime.timedelta(minutes=30)
            timeLeft = djTimer - datetime.datetime.now()
            timeLeft = timeLeft.seconds
            timeLeft = timeLeft / 60
            timeLeft = round(timeLeft)
            if timeLeft < 0 or timeLeft > 31: 
                await ctx.send("Less than a minute left, DJ will update after current song ends.")
            else:
                await ctx.send(f"DJ's have {timeLeft} minutes left.")
    @commands.command(name='test', aliases=['t'])
    async def test(self, ctx):
        vc: wavelink.Player = ctx.voice_client
        await ctx.send(int(self.find_index_not_autoplay(vc.queue)))
    def find_index_not_autoplay(self, queue):
        for i, item in enumerate(queue):
            if item.requester == "AutoPlayed":
                if i <= 0:
                    return 0
                else:
                    return i
        return len(queue)
async def setup(bot):
    await bot.add_cog(Music(bot))
