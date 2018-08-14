import logging
import random
from numpy.random import choice

def get_settings(settings_json):
    logging.getLogger('daily-bot').info('Started generating weighted random settings.')

    # Settings by weight
    generator_settings = []

    # Logic with multiple choices
    for setting in settings_json['settings_weighted']:
        logging.getLogger('daily-bot').debug('Current setting group: %s' % setting)
        if setting == 'other':
            logging.getLogger('daily-bot').debug('Skipping "other" for now')
            continue
        choices = []
        weights = []
        argument = ''
        value = ''

        this_setting = settings_json['settings_weighted'][setting]

        if 'argument' in this_setting:
            argument = this_setting['argument']
            logging.getLogger('daily-bot').debug('Setting: %s Argument: %s' % (setting, argument))
        for options in this_setting['options']:
            choices.extend([options['name']])
            weights.extend([options['weight']])
            logging.getLogger('daily-bot').debug('Added choice "%s" with weight %s' % (options['name'], options['weight']))

        result = choice(choices, p=weights)
        logging.getLogger('daily-bot').debug('Result: %s' % result)
        if argument:
            value = result
            logging.getLogger('daily-bot').debug('Argument: %s Value: %s' % (argument, value))
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
            logging.getLogger('daily-bot').debug('Adding setting: %s' % setting['name'])

    logging.getLogger('daily-bot').info('Finished generating weighted random settings.')
    return generator_settings
    