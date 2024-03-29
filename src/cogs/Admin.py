import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
import os
import socket
from discord import Color
class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    mg = MongoClient('mongodb', 27017,
                     username=os.environ['MONGO_USER'],
                     password=os.environ['MONGO_PASSWORD'])

    @commands.command(name='restartbot', description='Restarts the bot.')
    @commands.is_owner()
    async def restartbot(self, ctx):
        if not ctx.author.id == 238047264839303179:
            return
        await ctx.send('Restarting... this process may take up to 2 minutes.')
        #add restart bool and channel id to database
        try:
            collection = self.mg['discord']['guilds']
            collection.find_one_and_update({"guild_id": ctx.guild.id},
                                           {"$set": {"restarted": True, "restart_channel_id": ctx.channel.id}})
        except:
            try:
                collection = self.mg['discord']['guilds']
                collection.insert_one({"guild_id": ctx.guild.id, "restarted": True, "restart_channel_id": ctx.channel.id})
            except:
                await ctx.send("Error adding restart data to database. Bot will still restart but no notification will be sent on successful restart.")
        try:
            command = 'restart'
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_address = ('34.171.240.203', 9999)
            sock.connect(server_address)
            await ctx.send('Connected to server.')
            sock.sendall(command.encode())
            response = sock.recv(1024)
            await ctx.send("Response from server: {}".format(response.decode()))
            sock.close()
        except Exception as e:
            await ctx.send(f'Error: {e}')

    #############################################################################################################################################################
    #                                                                         Channel Setup Commands                                                            #
    #############################################################################################################################################################

    # SETUP MUSIC CHANNEL COMMAND
    @app_commands.command(name='setup_music', description='Sets the music channel for the server.')
    @commands.has_permissions(administrator=True)
    async def setup_music(ctx, channel: discord.TextChannel):
        await ctx.send(f'Channel {channel} set as music channel.')

    @app_commands.command(name='setup_music', description='Sets the music channel for the server.')
    @commands.has_permissions(administrator=True)
    async def setup_music(self, interaction: discord.Interaction, channel: discord.TextChannel):
        collection = self.mg['discord']['guilds']
        collection.find_one_and_update({"guild_id": interaction.guild.id},
                                       {"$set": {"music_channel_id": channel.id}})
        await interaction.response.send_message(f'Channel {channel} set as music channel.')

    #############################################################################################################################################################
    #                                                                         Informational Commands                                                            #
    #############################################################################################################################################################

    # LATENCY COMMAND

    @commands.command(name="ping", description="Returns the bot's latency.")
    async def ping(self, ctx):
        await ctx.send(f"Latency: {self.bot.latency * 1000:.2f}ms.")

    @app_commands.command(name="ping", description="Pings the bot")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Latency: {self.bot.latency * 1000:.2f}ms.")

    # USER INFO COMMAND
    @commands.command(name="user", description="Gets a user's info")
    async def user(self, ctx, user: discord.User):
        embed = discord.Embed(title=f"{user.name}#{user.discriminator}",
                              description=f"{user.mention} ({user.id})", color=0x00ff00)
        embed.add_field(name="Created At", value=user.created_at.strftime(
            "%a, %#d %B %Y, %I:%M %p UTC"), inline=False)
        embed.add_field(name="Bot?", value=user.bot, inline=False)
        embed.set_thumbnail(url=user.display_avatar)
        await ctx.send(embed=embed)

    @app_commands.command(name="user", description="Gets a user's info")
    async def user(self, interaction: discord.Interaction, user: discord.User):
        embed = discord.Embed(title=f"{user.name}#{user.discriminator}",
                              description=f"{user.mention} ({user.id})", color=0x00ff00)
        embed.add_field(name="Created At", value=user.created_at.strftime(
            "%a, %#d %B %Y, %I:%M %p UTC"), inline=False)
        embed.add_field(name="Bot?", value=user.bot, inline=False)
        embed.set_image(url=user.display_avatar)
        await interaction.response.send_message(embed=embed)

    # MEMBER INFO COMMAND
    @commands.command(name="info", description="Gets info about the member")
    async def info(self, ctx, member: discord.Member):
        embed = discord.Embed(title=f"{member.name}#{member.discriminator}",
                              description=f"{member.mention} ({member.id})", color=0x00ff00)
        embed.add_field(name="Joined At", value=member.joined_at.strftime(
            "%a, %#d %B %Y, %I:%M %p UTC"), inline=False)
        embed.add_field(name="Roles", value=", ".join(
            [role.mention for role in member.roles if role != ctx.guild.default_role]), inline=False)
        embed.add_field(name="Top Role",
                        value=member.top_role.mention, inline=False)
        embed.add_field(name="Bot?", value=member.bot, inline=False)
        embed.set_thumbnail(url=member.display_avatar)
        await ctx.send(embed=embed)

    @app_commands.command(name="info", description="Gets info about the member")
    async def info(self, interaction: discord.Interaction, member: discord.Member):
        embed = discord.Embed(title=f"{member.name}#{member.discriminator}",
                              description=f"{member.mention} ({member.id})", color=0x00ff00)
        embed.add_field(name="Joined At", value=member.joined_at.strftime(
            "%a, %#d %B %Y, %I:%M %p UTC"), inline=False)
        embed.add_field(name="Roles", value=", ".join(
            [role.mention for role in member.roles if role != interaction.guild.default_role]), inline=False)
        embed.add_field(name="Top Role",
                        value=member.top_role.mention, inline=False)
        embed.add_field(name="Bot?", value=member.bot, inline=False)
        embed.set_image(url=member.display_avatar)
        await interaction.response.send_message(embed=embed)

    # SERVER INFO COMMAND
    @commands.command(name="server", description="Gets info about the server")
    async def server(self, ctx):
        embed = discord.Embed(title=f"{ctx.guild.name} ({ctx.guild.id})",
                              description=ctx.guild.description, color=0x00ff00)
        embed.add_field(
            name="Owner", value=ctx.guild.owner.mention, inline=False)
        embed.add_field(name="Created At", value=ctx.guild.created_at.strftime(
            "%a, %#d %B %Y, %I:%M %p UTC"), inline=False)
        embed.add_field(
            name="Members", value=ctx.guild.member_count, inline=False)
        embed.add_field(name="Roles", value=len(ctx.guild.roles), inline=False)
        embed.add_field(name="Channels", value=len(
            ctx.guild.channels), inline=False)
        embed.set_thumbnail(url=ctx.guild.icon)
        await ctx.send(embed=embed)

    @app_commands.command(name="server", description="Gets info about the server")
    async def server(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"{interaction.guild.name} ({interaction.guild.id})",
                              description=interaction.guild.description, color=0x00ff00)
        embed.add_field(
            name="Owner", value=interaction.guild.owner.mention, inline=False)
        embed.add_field(name="Created At", value=interaction.guild.created_at.strftime(
            "%a, %#d %B %Y, %I:%M %p UTC"), inline=False)
        embed.add_field(
            name="Members", value=interaction.guild.member_count, inline=False)
        embed.add_field(name="Roles", value=len(
            interaction.guild.roles), inline=False)
        embed.add_field(name="Channels", value=len(
            interaction.guild.channels), inline=False)
        embed.set_thumbnail(url=interaction.guild.icon)
        await interaction.response.send_message(embed=embed)

    # PROFILE PICTURE COMMAND
    @commands.command(name="pfp", description="Gets a user's profile picture")
    async def pfp(self, ctx, user: discord.Member):
        embed = discord.Embed(title=f"{user.name}#{user.discriminator}",
                              description=f"{user.mention} ({user.id})", color=0x00ff00)
        embed.set_image(url=user.display_avatar)
        await ctx.send(embed=embed)

    # CHANGE NAME COLOR COMMAND
    @app_commands.command(name="color", description="Changes your name color")
    async def colorslash(self, interaction: discord.Interaction, color: str):
        # creates a role with the color
        role = await interaction.guild.create_role(name=f"{interaction.user.name}'s Color", color=color)
        # adds the role to the user
        await interaction.user.add_roles(role)
        # sends a message
        await interaction.response.send_message(f"Changed your name color to {color}")
    @commands.command(name="colorme", description="Changes your name color")
    async def color(self, ctx, color: str):
        # creates a role with the color
        color = discord.Color(value=int(color.strip("#"), 16))
        role = await ctx.guild.create_role(name=f"{ctx.author.name}'s Color", color=color)
        # adds the role to the user
        await ctx.author.add_roles(role)
        # sends a message
        await ctx.send(f"Changed your name color to {color}")
    @commands.command(name="untimeout", description="Changes your name color")
    async def untimeout(self, ctx, user: discord.Member):
        pass

async def setup(bot):
    await bot.add_cog(Admin(bot))
