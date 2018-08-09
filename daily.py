import os
import sys
import subprocess
import datetime
import random
import asyncio
import logging
import json
from pathlib import Path

import discord
import git
from numpy.random import choice

logger = None

def update_rando(settings_json):
    repo = git.Repo
    print('git stuff')
    if not os.path.isdir(os.path.join(os.getcwd(), settings_json['config']['repo_local_name'])):
        print('git clone new')
        repo = git.Repo.clone_from(settings_json['config']['repo_url'], settings_json['config']['repo_local_name'])
        repo.git.checkout(settings_json['config']['repo_branch'])
    else:
        print('git update')
        repo = git.Repo(os.path.join(os.getcwd(), settings_json['config']['repo_local_name']))
        repo.remotes.origin.fetch()
        commits_behind = repo.iter_commits(settings_json['config']['repo_branch'] + '..origin/' + settings_json['config']['repo_branch'])
        count = sum(1 for c in commits_behind)
        if(count > 0):
            repo = git.Repo(os.path.join(os.getcwd(), settings_json['config']['repo_local_name']))
            repo.git.checkout(settings_json['config']['repo_branch'])
            repo.git.reset('--hard')
            repo.remotes.origin.pull()
            repo.git.execute(['git','apply', os.path.join(os.getcwd(), 'patches/0001-output-string.patch')])

async def get_settings(settings_json):
    # Settings by weight
    generator_settings = []

    # Logic with multiple choices
    for setting in settings_json['settings_weighted']:
        if setting == 'other':
            continue
        choices = []
        weights = []
        argument = ''
        value = ''

        if 'argument' in settings_json['settings_weighted'][setting]:
            argument = settings_json['settings_weighted'][setting]['argument']
        for i, option in enumerate(settings_json['settings_weighted'][setting]['options']):
            choices.extend([settings_json['settings_weighted'][setting]['options'][i]['name']])
            weights.extend([settings_json['settings_weighted'][setting]['options'][i]['weight']])

        result = choice(choices, p=weights)
        if argument:
            value = result
        else:
            value = ''
        for i, option in enumerate(settings_json['settings_weighted'][setting]['options']):
            if result == option['name']:
                if 'argument' in option:
                    argument = option['argument']

        if argument:
            generator_settings.extend(argument.split(' '))
        if value:
            generator_settings.extend([value])

    # Other Logic
    for i, setting in enumerate(settings_json['settings_weighted']['other']):
        if(random.random() < settings_json['settings_weighted']['other'][i]['weight']):
            generator_settings.extend(['--' + settings_json['settings_weighted']['other'][i]['name']])

    return generator_settings

async def create_daily(setting, settings_json):

    if(sys.platform == 'linux'):
        base_settings = ['python3', os.path.join(os.getcwd(), 'rando', 'OoTRandomizer.py'), '--rom', os.path.join(os.getcwd(), 'rom', settings_json['config']['base_rom_name']), '--output_dir', os.path.join(settings_json['config']['output_directory'], str(datetime.date.today())), '--hints', 'agony', '--no_escape_sequence', '--world_count', '1', '--player_num', '1']
        f = open('output', 'w')
        subprocess.call(base_settings + setting, stdout=f)
        f.close()

        strings = []
        f = open('output', 'r')
        for line in f:
            strings.extend([line])
        f.close()
        os.remove('output')

        settings_string = strings[0].strip()
        seed = strings[1].strip()

        rom_name = 'OoT_' + settings_string + '_' + seed
        process = await asyncio.create_subprocess_exec('Compress/Compress', os.path.join(os.path.join(settings_json['config']['output_directory'], str(datetime.date.today())), rom_name + '.z64'), cwd='./rando', stdout=asyncio.subprocess.PIPE)
        await process.wait()

        # Create Wad
        process = subprocess.call(['gzinject', '--cleanup', '-a', 'inject', '-w', os.path.join(os.getcwd(), 'rom', settings_json['config']['base_wad_name']), '-i', 'NDYE', '-t', 'OoT Randomized', '-o', os.path.join(os.path.join(settings_json['config']['output_directory'], str(datetime.date.today())), rom_name + '.wad'), '--rom', os.path.join(os.path.join(settings_json['config']['output_directory'], str(datetime.date.today())), rom_name + '-comp.z64'), '--disable-controller-remappings'])

    return rom_name, settings_string, seed

async def upload_daily(rom_name, settings_json):
    process = await asyncio.create_subprocess_exec('python3', 'upload.py', rom_name, os.path.join(settings_json['config']['output_directory'], str(datetime.date.today())), stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    if stderr:
        logger.error(stderr)
    link = stdout.decode().strip()

    return link

def main():
    logging.basicConfig(level = logging.INFO)
    logger = logging.getLogger('dailies')
    logger.setLevel(logging.INFO)

    with open('settings.json') as data_file:
        settings_json = json.loads(data_file.read())

    TOKEN = settings_json['config']['discord_token']

    client = discord.Client()

    # https://jacobbridges.github.io/post/how-many-seconds-until-midnight/
    def how_many_seconds_until_midnight():
        """Get the number of seconds until midnight."""
        tomorrow = datetime.datetime.utcnow() + datetime.timedelta(1)
        midnight = datetime.datetime(year=tomorrow.year, month=tomorrow.month, 
                            day=tomorrow.day, hour=0, minute=0, second=0)
        return (midnight - datetime.datetime.utcnow()).seconds
        
    @client.event
    async def send_daily():
        await client.wait_until_ready()
        channel = client.get_channel(settings_json['config']['discord_channel_id'])

        while not client.is_closed:
            # Create output directory
            if not os.path.isdir(os.path.join(settings_json['config']['output_directory'], str(datetime.date.today()))):
                if not os.path.isdir(os.path.join(os.getcwd(), 'dailies')):
                    os.mkdir(os.path.join(os.getcwd(), 'dailies'))

            # Create daily
            update_rando(settings_json)
            settings = await get_settings(settings_json)
            rom_name, settings_string, seed = await create_daily(settings, settings_json)

            version = open(os.path.join(os.getcwd(), settings_json['config']['repo_local_name'], 'version.py')).readline()
            version = version.split('\'')

            markdown = 'And now for ***DAILY SEED CHALLENGE ' + str(datetime.date.today()) + '***\n'
            markdown = markdown + 'Version ' + version[1] + ' - Settings: ' + settings_string + ' - Seed: REDACTED'

            message = await client.send_message(channel, content=markdown)

            # Sleep until midnight (UTC)
            logger.info('sleeping for ' + str(how_many_seconds_until_midnight()) + ' seconds')
            await asyncio.sleep(how_many_seconds_until_midnight())
            
            # Upload daily and add embed to message
            link = await upload_daily(rom_name, settings_json)
            markdown = markdown.replace('REDACTED', seed)
            embed=discord.Embed(title="Download the daily challenge now!", url=link, description="Daily " + rom_name)
            embed.set_author(name="Daily Randomizer Challenge", url=link)
            await client.edit_message(message, markdown, embed=embed)

    client.loop.create_task(send_daily())
    client.run(TOKEN)

if __name__ == "__main__":
    main()
