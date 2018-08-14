# OoTR Daily Bot

This is a Discord bot for generating daily challenge seeds for [the Ocarina of Time Randomizer Discord](https://discordapp.com/invite/GyRhrUj).

## Installation

For Windows use `py -3` in place of `python`. For other systems ensure you are using python 3.

### Install Requirements

A Git executable in your `PATH` is required.

Download [gzinject](https://github.com/krimtonz/gzinject/releases) and place it in the repo root or add its executable to your `PATH`

Place the Ocarina of Time 1.0 U ROM and Ocarina of Time 1.2 WAD in the rom directory. Update the `base_rom_name` and `base_wad_name` in `settings.json` if necessary.

```bash
python -m pip install -r ./requirements.txt
```

### Configure Settings

Rename `settings.json.default` to `settings.json` and then modify the configuration to suit your needs. By default no `discord_token`, `discord_channel_id` or `output_directory` are provided. There is also no limitation on which users can run commands. Ensure you replace `@everyone` with appropriate rules. Keep in mind only `@everyone` has the `@` in its role name normally. `spoiler_users` is a list of Discord User IDs as strings that will always be sent DMs containing the spoiler log for the generated seed.

In `settings_weighted` aside from `other` options all `weight` values in each section must add up to `1` or else an error will occur. You however do not need to keep all the options. You can remove any you don't want at all, just remember to keep the sum `weight` values `1`.

### Run Bot

```bash
python bot.py
```
