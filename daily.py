import os
import sys
import subprocess
import datetime
import random
import asyncio
import logging
from pathlib import Path

import discord
import git
from numpy.random import choice

REPO_URL = 'https://github.com/TestRunnerSRL/OoT-Randomizer.git'
BRANCH = 'Dev'
LOCAL_REPO = 'rando'
CHANNEL_ID = '216764726988767232'
ROM = os.path.join(os.getcwd(), 'rom', 'Legend of Zelda, The - Ocarina of Time (U) (V1.0).z64')
WAD = os.path.join(os.getcwd(), 'rom', 'Legend of Zelda, The - Ocarina of Time (U) (V1.2) [Wii VC].wad')
OUTPUT_DIR = os.path.join(os.getcwd(), 'dailies', str(datetime.date.today()))

def update_rando():
    repo = git.Repo

    if not os.path.isdir(os.path.join(os.getcwd(), LOCAL_REPO)):
        repo = git.Repo.clone_from(REPO_URL, LOCAL_REPO)
        repo.git.checkout(BRANCH)
    else:
        repo = git.Repo(os.path.join(os.getcwd(), LOCAL_REPO))
        commits_behind = repo.iter_commits(BRANCH + '..origin/' + BRANCH)
        count = sum(1 for c in commits_behind)
        if(count > 0):
            repo = git.Repo(os.path.join(os.getcwd(), LOCAL_REPO))
            repo.git.checkout(BRANCH)
            repo.git.reset('--hard')
            repo.remotes.origin.pull()
            repo.git.execute(['git','apply', os.path.join(os.getcwd(), 'patches/0001-output-string.patch')])

async def get_settings():
    # Settings by weight
    settings = []

    # Create output directory
    if not os.path.isdir(OUTPUT_DIR):
        if not os.path.isdir(os.path.join(os.getcwd(), 'dailies')):
            os.mkdir(os.path.join(os.getcwd(), 'dailies'))

    # Openess
    openness_choices = [                    'closed',   'opendoor',     'openforest',   'open']
    openness = choice(openness_choices, p=[ 0.25,       0.25,           0.25,           0.25])
    if(openness == 'opendoor'):
        settings.extend(['--open_door_of_time'])
    elif(openness == 'openforest'):
        settings.extend(['--open_forest'])
    elif(openness == 'open'):
        settings.extend(['--open_forest', '--open_door_of_time'])

    # Bridge Requirements
    bridge_choices = [                  'medallions',   'vanilla',  'dungeons',     'open']
    bridge = choice(bridge_choices, p=[ 0.30,           0.25,       0.20,           0.25])
    if(bridge == 'vanilla'):
        settings.extend(['--bridge', 'vanilla'])
    elif(bridge == 'dungeons'):
        settings.extend(['--bridge', 'dungeons'])
    elif(bridge == 'open'):
        settings.extend(['--bridge', 'open'])

    # Number of Trials
    trial_chocies = list(range(7))
    trials = choice(trial_chocies, p=[0.30, 0.05, 0.05, 0.20, 0.05, 0.05, 0.30])
    settings.extend(['--trials', str(trials)])

    # Tokensanity
    tokensanity_choices = [                         'off',  'dungeons',     'all']
    tokensanity = choice(tokensanity_choices, p=[   0.75,   0.15,           0.10])
    if(tokensanity == 'dungeons'):
        settings.extend(['--tokensanity', 'dungeons'])
    elif(tokensanity == 'all'):
        settings.extend(['--tokensanity', 'all'])

    # Other Logic
    if(random.random() < 0.5):
        settings.extend(['--bombchus_in_logic'])
    if(random.random() < 0.5):
        settings.extend(['--all_reachable'])
    if(random.random() < 0.15):
        settings.extend(['--keysanity'])
    if(random.random() < 0.30):
        settings.extend(['--shuffle_gerudo_card'])
    if(random.random() < 0.30):
        settings.extend(['--shuffle_ocarinas'])
    if(random.random() < 0.30):
        settings.extend(['--shuffle_weird_egg'])
    if(random.random() < 0.05):
        settings.extend(['--ocarina_songs'])
    if(random.random() < 0.30):
        settings.extend(['--correct_chest_sizes'])
    if(random.random() < 0.01):
        settings.extend(['--ohko'])
    if(random.random() < 0.25):
        settings.extend(['--nodungeonitems'])
    if(random.random() < 0.30):
        settings.extend(['--progressive_bombchus'])

    return settings

async def create_daily(settings):

    if(sys.platform == 'linux'):
        base_settings = ['python3', os.path.join(os.getcwd(), 'rando', 'OoTRandomizer.py'), '--rom', ROM, '--output_dir', OUTPUT_DIR, '--hints', 'agony', '--no_escape_sequence', '--world_count', '1', '--player_num', '1']
        f = open('output', 'w')
        subprocess.call(base_settings + settings, stdout=f)
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
        process = await asyncio.create_subprocess_exec('Compress/Compress', os.path.join(OUTPUT_DIR, rom_name + '.z64'), cwd='./rando', stdout=asyncio.subprocess.PIPE)
        await process.wait()

        # Create Wad
        process = subprocess.call(['gzinject', '--cleanup', '-a', 'inject', '-w', WAD, '-i', 'NDYE', '-t', 'OoT Randomized', '-o', os.path.join(OUTPUT_DIR, rom_name + '.wad'), '--rom', os.path.join(OUTPUT_DIR, rom_name + '-comp.z64'), '--disable-controller-remappings'])

    return rom_name, settings_string, seed

async def upload_daily(rom_name):
    process = await asyncio.create_subprocess_exec('python3', 'upload.py', rom_name, OUTPUT_DIR, stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    link = stdout.decode().strip()

    return link

def main():
    logging.basicConfig(level = logging.INFO)
    logger = logging.getLogger('dailies')
    logger.setLevel(logging.INFO)

    TOKEN = 'bot-token-here'

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
        channel = client.get_channel(CHANNEL_ID)

        while not client.is_closed:
            logger.info('sleeping for ' + str(how_many_seconds_until_midnight()) + ' seconds')
            await asyncio.sleep(how_many_seconds_until_midnight())

            update_rando()
            settings = await get_settings()
            rom_name, settings_string, seed = await create_daily(settings)

            message = await client.send_message(channel, content='Settings: ' + settings_string + '\n' + 'Seed: ' + seed)
            
            link = await upload_daily(rom_name)
            embed=discord.Embed(title="Download " + rom_name + " now!", url=link, description="Daily " + rom_name)
            embed.set_author(name="Daily Randomizer Challenge", url=link)
            await client.edit_message(message, embed=embed)

    client.loop.create_task(send_daily())
    client.run(TOKEN)

if __name__ == "__main__":
    main()
