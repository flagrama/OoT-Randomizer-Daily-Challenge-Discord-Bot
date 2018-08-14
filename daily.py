import logging
import os
import sys
import subprocess
import datetime
import asyncio
import struct

def create_daily(setting, settings_json, seed):
    logging.getLogger('daily-bot').info('\nStarted generating randomized ROM.\n')

    logging.getLogger('daily-bot').debug('Platform is %s' % sys.platform)
    if(sys.platform == 'linux'):
        base_settings = ['python3']
    elif(sys.platform == 'win32'):
        base_settings = ['py', '-3']

    zootdec = os.path.join(os.getcwd(), 'rando', 'ZOOTDEC.z64')

    if os.path.isfile(zootdec):
        base_rom = zootdec
    else:
        base_rom = settings_json['config']['base_rom_name']

    base_settings = base_settings + \
        [os.path.join(os.getcwd(), 'rando', 'OoTRandomizer.py'), \
        '--rom', os.path.join(os.getcwd(), 'rom', settings_json['config']['base_rom_name']), \
        '--output_dir', os.path.join(settings_json['config']['output_directory'], str(datetime.date.today())), \
        '--seed', seed, \
        '--compress_rom', 'False']
    
    strings = []
    tempfile = 'output'
    with open(tempfile, 'w') as output:
        logging.getLogger('daily-bot').debug('Create ROM with base settings: %s' % ' '.join(base_settings))
        logging.getLogger('daily-bot').debug('Create ROM with weighted settings: %s' % ' '.join(setting))
        logging.getLogger('daily-bot').debug('Output stdout to: %s' % output.name)
        subprocess.call(base_settings + setting, cwd=os.path.join(os.getcwd(), 'rando'), stdout=output)

        extra_zootdec = os.path.join(settings_json['config']['output_directory'], str(datetime.date.today()), 'ZOOTDEC.z64')
        if os.path.isfile(extra_zootdec):
            os.rename(extra_zootdec, zootdec)
            
    with open(tempfile, 'r') as output:
        for line in output:
            logging.getLogger('daily-bot').debug('Reading stdout of OoT_Randomizer.py')
            strings.extend([line])
    logging.getLogger('daily-bot').debug('Removing temporary file containing stdout of OoT_Randomizer.py')
    os.remove(tempfile)

    settings_string = strings[0].strip()
    seed = strings[1].strip()
    logging.getLogger('daily-bot').debug('\nFrom OoT_Randomizer.py stdout - Setting String: %s Seed: %s' % (settings_string, seed))

    rom_name = 'OoT_' + settings_string + '_' + seed
    logging.getLogger('daily-bot').debug('Rom name: %s' % rom_name)

    logging.getLogger('daily-bot').info('\nFinished generating randomized ROM.\n')
    return rom_name, settings_string

async def compress_daily(rom_name, settings_json):
    logging.getLogger('daily-bot').info('\nStarted compressing ROM')

    if sys.platform == 'linux':
        executable = 'Compress/Compress'
    elif sys.platform == 'win32':
        if 8 * struct.calcsize("P") == 64:
            executable = os.path.join(os.getcwd(), settings_json['config']['repo_local_name'], 'Compress', 'Compress.exe')
        else:
            executable = os.path.join(os.getcwd(), settings_json['config']['repo_local_name'], 'Compress', 'Compress32.exe')
    
    process = await asyncio.create_subprocess_exec(executable, \
                        os.path.join(os.path.join(settings_json['config']['output_directory'], \
                        str(datetime.date.today())), rom_name + '.z64'), \
                        os.path.join(os.path.join(settings_json['config']['output_directory'], str(datetime.date.today())), rom_name + '-comp.z64'), \
                        cwd=os.path.join(os.getcwd(), 'rando'), \
                        stdout=asyncio.subprocess.PIPE)
    await process.wait()
    logging.getLogger('daily-bot').info('Finished compressing ROM\n')

    # Create Wad
    logging.getLogger('daily-bot').info('\nStarted creating WAD\n')
    if sys.platform == 'linux':
        gzinject = ['gzinject']
    elif sys.platform == 'win32':
        gzinject = ['gzinject.exe']
    if not os.path.isdir(os.path.join(os.getcwd(), 'rom', 'common-key.bin')):
        logging.getLogger('daily-bot').debug('Generating common-key.bin')
        subprocess.run(gzinject + ['-a', 'genkey'], stdout=subprocess.PIPE, input=b'45e', cwd=os.path.join(os.getcwd(), 'rom'))
        logging.getLogger('daily-bot').debug('Generated common-key.bin successfully')
    subprocess.call(gzinject + ['--cleanup', '-a', 'inject', '-w', os.path.join(os.getcwd(), 'rom', settings_json['config']['base_wad_name']), '-i', 'NDYE', '-t', 'OoT Randomized', '-o', os.path.join(settings_json['config']['output_directory'], str(datetime.date.today()), rom_name + '.wad'), '--rom', os.path.join(os.path.join(settings_json['config']['output_directory'], str(datetime.date.today())), rom_name + '-comp.z64'), '--disable-controller-remappings', '--key', os.path.join(os.getcwd(), 'rom', 'common-key.bin')])
    logging.getLogger('daily-bot').info('\nFinished creating WAD\n')

async def upload_daily(rom_name, output_dir):
    logging.getLogger('daily-bot').info('\nStarted uploading %s.zip\n' % datetime.date.today())
    executable = list()
    if sys.platform == 'linux':
        executable.append('python3')
    elif sys.platform == 'win32':
        executable.append('py')
        executable.append('-3')

    process = await asyncio.create_subprocess_exec(*executable, 'upload.py', rom_name, os.path.join(output_dir, str(datetime.date.today())), stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    
    if stderr:
        logging.getLogger('daily-bot').error(stderr)
    link = stdout.decode().strip()
    link = link.split('\n')
    link = link[len(link) - 1]
    logging.getLogger('daily-bot').info('File uploaded to %s' % link)

    logging.getLogger('daily-bot').info('\nFinished uploading %s.zip\n' % datetime.date.today())
    return link

# https://jacobbridges.github.io/post/how-many-seconds-until-midnight/
def how_many_seconds_until_midnight():
    """Get the number of seconds until midnight."""
    tomorrow = datetime.datetime.utcnow() + datetime.timedelta(1)
    midnight = datetime.datetime(year=tomorrow.year, month=tomorrow.month, 
                        day=tomorrow.day, hour=0, minute=0, second=0)
    return (midnight - datetime.datetime.utcnow()).seconds
