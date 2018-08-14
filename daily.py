import os
import sys
import subprocess
import datetime
import random
import asyncio
import logging
import json

import discord
from discord.ext import commands
import git
from numpy.random import choice

logger = logging.getLogger('dailies')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

def update_rando(settings_json):
    logger.info('\nStarted updating local OoT_Randomizer repository.\n')

    repo_name = settings_json['config']['repo_local_name']
    repo_branch = settings_json['config']['repo_branch']
    repo_url = settings_json['config']['repo_url']

    repo = git.Repo
    if not os.path.isdir(os.path.join(os.getcwd(), repo_name)):
        repo = git.Repo.clone_from(repo_url, repo_name)
        repo.git.checkout(repo_branch)
        repo.git.execute(['git','apply', os.path.join(os.getcwd(), 'patches/0001-output-string.patch')])
        logger.info('Cloned repository to %s and applied patch' % repo_name)
    else:
        repo = git.Repo(os.path.join(os.getcwd(), repo_name))
        repo.remotes.origin.fetch()
        commits_behind = repo.iter_commits(repo_branch + '..origin/' + repo_branch)
        count = sum(1 for c in commits_behind)
        if(count > 0):
            logger.info('%s commits behind %s, pulling latest version' % (count, repo_branch))
            repo = git.Repo(os.path.join(os.getcwd(), repo_name))
            repo.git.checkout(repo_branch)
            repo.git.reset('--hard')
            repo.remotes.origin.pull()
            repo.git.execute(['git','apply', os.path.join(os.getcwd(), 'patches/0001-output-string.patch')])
        logger.info('Repository is at the latest commit')
    logger.info('\nFinished updating local OoT_Randomizer repository.\n')

async def get_settings(settings_json):
    logger.info('\nStarted generating weighted random settings.\n')

    # Settings by weight
    generator_settings = []

    # Logic with multiple choices
    for setting in settings_json['settings_weighted']:
        logger.debug('Current setting group: %s' % setting)
        if setting == 'other':
            logger.debug('Skipping "other" for now\n')
            continue
        choices = []
        weights = []
        argument = ''
        value = ''

        this_setting = settings_json['settings_weighted'][setting]

        if 'argument' in this_setting:
            argument = this_setting['argument']
            logger.debug('Setting: %s Argument: %s' % (setting, argument))
        for options in this_setting['options']:
            choices.extend([options['name']])
            weights.extend([options['weight']])
            logger.debug('Added choice "%s" with weight %s' % (options['name'], options['weight']))

        result = choice(choices, p=weights)
        logger.debug('Result: %s\n' % result)
        if argument:
            value = result
            logger.debug('Argument: %s Value: %s\n' % (argument, value))
        else:
            value = ''

        # Find if an argument exists within a setting option and set it if so
        for option in this_setting['options']:
            if result == option['name']:
                if 'argument' in option:
                    argument = option['argument']

        if argument:
            # Split the argument string if more than one argument is contained and add to settings
            generator_settings.extend(argument.split(' '))
        if value:
            generator_settings.extend([value])

    # Other Logic
    for setting in settings_json['settings_weighted']['other']:
        if(random.random() < setting['weight']):
            generator_settings.extend(['--' + setting['name']])
            logger.debug('Adding setting: %s' % setting['name'])

    logger.info('\nFinished generating weighted random settings.\n')
    return generator_settings

async def create_daily(setting, settings_json, seed):
    logger.info('\nStarted generating randomized ROM.\n')

    logger.debug('Platform is %s' % sys.platform)
    if(sys.platform == 'linux'):
        base_settings = ['python3']
    elif(sys.platform == 'win32'):
        base_settings = ['py', '-3']

    base_settings = base_settings + [os.path.join(os.getcwd(), 'rando', 'OoTRandomizer.py'), '--rom', os.path.join(os.getcwd(), 'rom', settings_json['config']['base_rom_name']), '--output_dir', os.path.join(settings_json['config']['output_directory'], str(datetime.date.today())), '--seed', seed, '--compress_rom', 'False']
    
    strings = []
    tempfile = 'output'
    with open(tempfile, 'w') as output:
        logger.debug('Create ROM with base settings: %s' % ' '.join(base_settings))
        logger.debug('Create ROM with weighted settings: %s' % ' '.join(setting))
        logger.debug('Output stdout to: %s' % output.name)
        subprocess.call(base_settings + setting, stdout=output)
    with open(tempfile, 'r') as output:
        for line in output:
            logger.debug('Reading stdout of OoT_Randomizer.py')
        strings.extend([line])
    logger.debug('Removing temporary file containing stdout of OoT_Randomizer.py')
    os.remove(tempfile)

    settings_string = strings[0].strip()
    seed = strings[1].strip()
    logger.debug('\nFrom OoT_Randomizer.py stdout - Setting String: %s Seed: %s' % (settings_string, seed))

    rom_name = 'OoT_' + settings_string + '_' + seed
    logger.debug('Rom name: %s' % rom_name)

    logger.info('\nFinished generating randomized ROM.\n')
    return rom_name, settings_string

async def compress_daily(rom_name, settings_json):
    logger.info('\nStarted compressing ROM')
    if sys.platform == 'linux':
        process = await asyncio.create_subprocess_exec('Compress/Compress', os.path.join(os.path.join(settings_json['config']['output_directory'], str(datetime.date.today())), rom_name + '.z64'), cwd='./rando', stdout=asyncio.subprocess.PIPE)
    elif sys.platform == 'win32':
        process = await asyncio.create_subprocess_exec(os.path.join(os.getcwd(), settings_json['config']['repo_local_name'], 'Compress', 'Compress.exe'), os.path.join(os.path.join(settings_json['config']['output_directory'], str(datetime.date.today())), rom_name + '.z64'), os.path.join(os.path.join(settings_json['config']['output_directory'], str(datetime.date.today())), rom_name + '-comp.z64'), stdout=asyncio.subprocess.PIPE)
    await process.wait()
    logger.info('Finished compressing ROM\n')

    # Create Wad
    logger.info('\nStarted creating WAD\n')
    if sys.platform == 'linux':
        gzinject = ['gzinject']
    elif sys.platform == 'win32':
        gzinject = ['gzinject.exe']
    if not os.path.isdir(os.path.join(os.getcwd(), 'rom', 'common-key.bin')):
        logger.debug('Generating common-key.bin')
        subprocess.run(gzinject + ['-a', 'genkey'], stdout=subprocess.PIPE, input=b'45e', cwd=os.path.join(os.getcwd(), 'rom'))
        logger.debug('Generated common-key.bin successfully')
    subprocess.call(gzinject + ['--cleanup', '-a', 'inject', '-w', os.path.join(os.getcwd(), 'rom', settings_json['config']['base_wad_name']), '-i', 'NDYE', '-t', 'OoT Randomized', '-o', os.path.join(settings_json['config']['output_directory'], str(datetime.date.today()), rom_name + '.wad'), '--rom', os.path.join(os.path.join(settings_json['config']['output_directory'], str(datetime.date.today())), rom_name + '-comp.z64'), '--disable-controller-remappings', '--key', os.path.join(os.getcwd(), 'rom', 'common-key.bin')])
    logger.info('\nFinished creating WAD\n')

async def upload_daily(rom_name, output_dir):
    logger.info('\nStarted uploading %s.zip\n' % datetime.date.today())
    if sys.platform == 'linux':
        process = await asyncio.create_subprocess_exec('python3', 'upload.py', rom_name, os.path.join(output_dir, str(datetime.date.today())), stdout=asyncio.subprocess.PIPE)
    elif sys.platform == 'win32':
        process = await asyncio.create_subprocess_exec('py', '-3', 'upload.py', rom_name, os.path.join(output_dir, str(datetime.date.today())), stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    if stderr:
        logger.error(stderr)
    link = stdout.decode().strip()
    logger.info('File uploaded to %s' % link)

    logger.info('\nFinished uploading %s.zip\n' % datetime.date.today())
    return link

def main():
    with open('settings.json') as data_file:
        settings_json = json.loads(data_file.read())

    try: 
        if settings_json['config']['debug'] != 'true':
            sys.tracebacklimit = 0
            print(logger)
            logger.setLevel(logging.ERROR)
    except KeyError:
        sys.tracebacklimit = 0
        logger.setLevel(logging.ERROR)
    logger.info('JSON loaded')

    TOKEN = settings_json['config']['discord_token']

    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        logger.info('Windows event loop set to ProactorEventLoop')

    client = commands.Bot(command_prefix='!', description='A bot that generates daily seeds for Ocarina of Time Randomizer')
    logger.info('Bot client established')

    # https://jacobbridges.github.io/post/how-many-seconds-until-midnight/
    def how_many_seconds_until_midnight():
        """Get the number of seconds until midnight."""
        tomorrow = datetime.datetime.utcnow() + datetime.timedelta(1)
        midnight = datetime.datetime(year=tomorrow.year, month=tomorrow.month, 
                            day=tomorrow.day, hour=0, minute=0, second=0)
        return (midnight - datetime.datetime.utcnow()).seconds
        
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
        logger.info('\nStarted sending spoiler file to spoil users.\n')
        spoiler_name = rom_name.split('.')
        spoiler_name = spoiler_name[0]
        spoiler_name += '_Spoiler.txt'

        spoiler = discord.File(fp=os.path.join(output_dir, str(datetime.date.today()), spoiler_name),filename=spoiler_name)
        spoiler_users = []
        for spoil_users in users:
            for user in spoil_users:
                spoiler_users.extend([str(user).lower()])

        if not str(ctx.message.author.id) in spoiler_users:
            logger.debug('Adding command author to spoil users')
            spoiler_users.extend([str(ctx.message.author.id)])
        logger.debug('Spoiler users: %s' % spoiler_users)
            
        for spoil_user in spoiler_users:
            user = client.get_user(int(spoil_user))
            if user is not None:
                logger.debug('Sending spoiler file')
                await user.send(file=spoiler, delete_after=3600)

        logger.info('\nFinished sending file to spoil users.')

    @client.command(pass_context=True)
    # pylint: disable=unused-variable
    async def makedaily(ctx, seed):
        await client.wait_until_ready()

        # Update JSON from file
        with open('settings.json') as data_file:
            settings_json = json.loads(data_file.read())
            logger.info('JSON settings refreshed')

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
        update_rando(settings_json)
        settings = await get_settings(settings_json)
        rom_name, settings_string = await create_daily(settings, settings_json, seed)

        # Create Discord message
        logger.debug('Obtaining randomizer version')
        version = open(os.path.join(os.getcwd(), settings_json['config']['repo_local_name'], 'version.py')).readline()
        version = version.split('\'')
        logger.debug('Randomizer version %s' % version[1])

        markdown = """And now for today's ***DAILY SEED CHALLENGE***\n"""
        markdown = markdown + """Version %s - Settings: %s - Seed: REDACTED""" % (version[1], settings_string)

        message = await ctx.message.channel.send(markdown)
        await send_spoiler(ctx, output_directory, rom_name, settings_json['config']['spoiler_users'])

        # Sleep until midnight (UTC)
        logger.info('sleeping for ' + str(how_many_seconds_until_midnight()) + ' seconds')
        await asyncio.sleep(how_many_seconds_until_midnight())
            
        # Compress daily and create WAD
        await compress_daily(rom_name, settings_json)
            
        # Upload daily and add embed to message
        link = await upload_daily(rom_name, output_directory)
        markdown = markdown.replace('REDACTED', seed)
        embed=discord.Embed(title="Download the daily challenge now!", url=link, description="Daily " + rom_name)
        embed.set_author(name="Daily Randomizer Challenge", url=link)
        logger.debug('Adding embed with link %s to daily seed message' % link)
        await message.edit(content=markdown, embed=embed)

    client.run(TOKEN)

if __name__ == "__main__":
    main()
