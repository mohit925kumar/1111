import discord
from discord.ext import commands
from discord.ui import View, Button
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
import urllib.parse, urllib.request, re

def run_bot():
    load_dotenv()
    TOKEN = "MTQ0MDA0MjY3NTQ0ODU3ODI2MA.Gw5mbd.R0LlMuWVDtJv2rQuRvPAZSUvZrDMW7CAZF3lYQ"

    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix=".", intents=intents)

    queues = {}
    voice_clients = {}
    youtube_base_url = 'https://www.youtube.com/'
    youtube_results_url = youtube_base_url + 'results?'
    youtube_watch_url = youtube_base_url + 'watch?v='
    yt_dl_options = {"format": "bestaudio/best"}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn -filter:a "volume=0.25"'
    }

    @client.event
    async def on_ready():
        print(f'{client.user} abhiraj')

    async def play_next(ctx):
        if queues.get(ctx.guild.id):
            link = queues[ctx.guild.id].pop(0)
            await play(ctx, link=link)

    # =============================
    # 🎶 BUTTON SYSTEM
    # =============================
    class MusicButtons(View):
        def __init__(self, ctx, embed_message):
            super().__init__(timeout=None)
            self.ctx = ctx
            self.embed_message = embed_message

        @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.blurple)
        async def skip_button(self, interaction: discord.Interaction, button: Button):
            await interaction.response.send_message(f"⏭ Skipped by **{interaction.user.mention}**", delete_after=5)
            try:
                voice_clients[self.ctx.guild.id].stop()
            except:
                pass

        @discord.ui.button(label="⏸ Pause", style=discord.ButtonStyle.gray)
        async def pause_button(self, interaction: discord.Interaction, button: Button):
            try:
                voice_clients[self.ctx.guild.id].pause()
                await interaction.response.send_message(f"⏸ Paused by **{interaction.user.mention}**", delete_after=5)
            except:
                await interaction.response.send_message("Error pausing!", delete_after=5)

        @discord.ui.button(label="▶ Resume", style=discord.ButtonStyle.green)
        async def resume_button(self, interaction: discord.Interaction, button: Button):
            try:
                voice_clients[self.ctx.guild.id].resume()
                await interaction.response.send_message(f"▶ Resumed by **{interaction.user.mention}**", delete_after=5)
            except:
                await interaction.response.send_message("Error resuming!", delete_after=5)

        @discord.ui.button(label="⛔ Stop", style=discord.ButtonStyle.red)
        async def stop_button(self, interaction: discord.Interaction, button: Button):
            await interaction.response.send_message(f"⛔ Stopped by **{interaction.user.mention}**", delete_after=5)
            try:
                voice_clients[self.ctx.guild.id].stop()
                await voice_clients[self.ctx.guild.id].disconnect()
                del voice_clients[self.ctx.guild.id]
            except:
                pass

    # ======================================
    # MAIN PLAY COMMAND
    # ======================================
    @client.command(name="play")
    async def play(ctx, *, link):
        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[voice_client.guild.id] = voice_client
        except:
            pass

        try:
            if youtube_base_url not in link:
                query_string = urllib.parse.urlencode({'search_query': link})
                content = urllib.request.urlopen(youtube_results_url + query_string)
                search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())
                link = youtube_watch_url + search_results[0]

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))

            song = data['url']
            player = discord.FFmpegOpusAudio(song, **ffmpeg_options)

            # -----------------------
            # Embed With Logs + Buttons
            # -----------------------
            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"{data['title']}\n\n**🎧 Requested by:** {ctx.author.mention}",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=data['thumbnail'])

            embed_msg = await ctx.send(embed=embed)

            # Add Buttons Below Song
            view = MusicButtons(ctx, embed_msg)
            await embed_msg.edit(view=view)

            # Delete user command message
            try:
                await ctx.message.delete()
            except:
                pass

            # on finish
            def after_done(e):
                try:
                    delete_task = embed_msg.delete()
                    asyncio.run_coroutine_threadsafe(delete_task, client.loop)

                    nxt = play_next(ctx)
                    asyncio.run_coroutine_threadsafe(nxt, client.loop)
                except:
                    pass

            voice_clients[ctx.guild.id].play(player, after=after_done)

        except Exception as e:
            print(e)

    # ========================
    # QUEUE + BASIC COMMANDS
    # ========================
    @client.command(name="queue")
    async def queue(ctx, *, url):
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []
        queues[ctx.guild.id].append(url)
        await ctx.send("Added to queue!")

    @client.command(name="clear_queue")
    async def clear_queue(ctx):
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
            await ctx.send("Queue cleared!")
        else:
            await ctx.send("Queue empty!")

    @client.command(name="pause")
    async def pause(ctx):
        try:
            voice_clients[ctx.guild.id].pause()
            await ctx.send(f"⏸ Paused by {ctx.author.mention}")
        except:
            pass

    @client.command(name="resume")
    async def resume(ctx):
        try:
            voice_clients[ctx.guild.id].resume()
            await ctx.send(f"▶ Resumed by {ctx.author.mention}")
        except:
            pass

    @client.command(name="stop")
    async def stop(ctx):
        try:
            await ctx.send(f"⛔ Stopped by {ctx.author.mention}")
            voice_clients[ctx.guild.id].stop()
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
        except:
            pass

    client.run(TOKEN)

run_bot()
