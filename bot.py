import os
import sys
import datetime
import asyncio
import logging
import json

import repo
import weightedsettings
import daily

import discord
from discord.ext import commands

def main():
    ch = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(levelname)s:%(name)s: %(message)s')
    logger = logging.getLogger('daily-bot')

    with open('settings.json') as data_file:
        settings_json = json.loads(data_file.read())

    try: 
        if settings_json['config']['debug']:
            ch.setLevel(logging.DEBUG)
            logger.setLevel(logging.DEBUG)
        else:
            sys.tracebacklimit = 0
    except KeyError:
        sys.tracebacklimit = 0
        
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logging.getLogger('daily-bot').info('JSON loaded')

    TOKEN = settings_json['config']['discord_token']

    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        logging.getLogger('daily-bot').info('Windows event loop set to ProactorEventLoop')

    client = commands.Bot(command_prefix='!', description='A bot that generates daily seeds for Ocarina of Time Randomizer')
    logging.getLogger('daily-bot').info('Bot client established')
        
    def is_allowed(ctx, *roles):
        allowed_roles = []
        for allowed_role in roles:
            for role in allowed_role:
                allowed_roles.extend([str(role).lower()])
        author_roles = []
        for author_role in ctx.message.author.roles:
            author_roles.extend([author_role.name.lower()])
        allowed = bool(set(allowed_roles) & set(author_roles))

        return allowed or ctx.message.author == ctx.guild.owner

    async def send_spoiler(ctx, output_dir, rom_name, *users):
        logging.getLogger('daily-bot').info('Started sending spoiler file to spoil users.')
        spoiler_name = rom_name.split('.')
        spoiler_name = spoiler_name[0]
        spoiler_name += '_Spoiler.txt'

        spoiler = discord.File(fp=os.path.join(output_dir, str(datetime.date.today()), spoiler_name),filename=spoiler_name)
        spoiler_users = []
        for spoil_users in users:
            for user in spoil_users:
                spoiler_users.extend([str(user).lower()])

        if not str(ctx.message.author.id) in spoiler_users:
            logging.getLogger('daily-bot').debug('Adding command author to spoil users')
            spoiler_users.extend([str(ctx.message.author.id)])
        logging.getLogger('daily-bot').debug('Spoiler users: %s' % spoiler_users)
            
        for spoil_user in spoiler_users:
            user = client.get_user(int(spoil_user))
            if user is not None:
                logging.getLogger('daily-bot').debug('Sending spoiler file')
                await user.send(file=spoiler, delete_after=3600)

        logging.getLogger('daily-bot').info('Finished sending file to spoil users.')

    @client.command(pass_context=True)
    # pylint: disable=unused-variable
    async def makedaily(ctx, *seed_placeholder):
        await client.wait_until_ready()

        # Update JSON from file
        with open('settings.json') as data_file:
            settings_json = json.loads(data_file.read())
            logging.getLogger('daily-bot').info('JSON settings refreshed')

        allowed_roles = settings_json['config']['allowed_roles']
        output_directory = settings_json['config']['output_directory']

        if not is_allowed(ctx, allowed_roles):
            logging.warning('User %s was denied permission to !makedaily' % ctx.message.author.name)
            return

        # Create output directory
        if not os.path.isdir(os.path.join(output_directory, str(datetime.date.today()))):
            if not os.path.isdir(os.path.join(os.getcwd(), 'dailies')):
                os.mkdir(os.path.join(os.getcwd(), 'dailies'))
                logging.info('Created default output directory')

        # Create daily
        repo.update_rando(settings_json)
        settings = weightedsettings.get_settings(settings_json)
        rom_name, settings_string, seed = daily.create_daily(settings, settings_json)

        # Create Discord message
        logging.getLogger('daily-bot').debug('Obtaining randomizer version')
        version = open(os.path.join(os.getcwd(), settings_json['config']['repo_local_name'], 'version.py')).readline()
        version = version.split('\'')
        logging.getLogger('daily-bot').debug('Randomizer version %s' % version[1])

        markdown = """And now for today's ***DAILY SEED CHALLENGE***\n"""
        markdown = markdown + """Version %s - Settings: %s - Seed: %s""" % (version[1], settings_string, ' '.join(seed_placeholder))

        message = await ctx.message.channel.send(markdown)
        await send_spoiler(ctx, output_directory, rom_name, settings_json['config']['spoiler_users'])

        # Compress daily and create WAD
        await daily.compress_daily(rom_name, settings_json)
            
        # Upload daily and add embed to message
        daily.scrub_seed_daily(rom_name, output_directory)
        link = await daily.upload_daily(rom_name, output_directory)
        embed=discord.Embed(title='Download the daily challenge now!', url=link, description='The daily for %s is now available!' % datetime.date.today())
        embed.set_author(name='Daily Randomizer Challenge', url=link)
        logging.getLogger('daily-bot').debug('Adding embed with link %s to daily seed message' % link)
        await message.edit(embed=embed)
        daily.clean_daily(output_directory)

        if settings_json['config']['replace_placeholder']:
            # Sleep until midnight (UTC) and reveal seed
            seconds = daily.how_many_seconds_until_midnight()
            logging.getLogger('daily-bot').info('sleeping for %s seconds' % seconds)
            await asyncio.sleep(seconds)
            markdown = markdown.replace(seed_placeholder, seed)
            await message.edit(content=markdown)

    client.run(TOKEN)

if __name__ == "__main__":
    main()
