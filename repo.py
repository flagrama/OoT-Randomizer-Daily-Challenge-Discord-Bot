import logging
import git
import os

def update_rando(settings_json):
    logging.getLogger('daily-bot').info('\nStarted updating local OoT_Randomizer repository.\n')

    repo_name = settings_json['config']['repo_local_name']
    repo_branch = settings_json['config']['repo_branch']
    repo_url = settings_json['config']['repo_url']

    repo = git.Repo
    if not os.path.isdir(os.path.join(os.getcwd(), repo_name)):
        repo = git.Repo.clone_from(repo_url, repo_name)
        repo.git.checkout(repo_branch)
        repo.git.execute(['git','apply', os.path.join(os.getcwd(), 'patches/0001-output-string.patch')])
        logging.getLogger('daily-bot').info('Cloned repository to %s and applied patch' % repo_name)
    else:
        repo = git.Repo(os.path.join(os.getcwd(), repo_name))
        repo.remotes.origin.fetch()
        commits_behind = repo.iter_commits(repo_branch + '..origin/' + repo_branch)
        count = sum(1 for c in commits_behind)
        if(count > 0):
            logging.getLogger('daily-bot').info('%s commits behind %s, pulling latest version' % (count, repo_branch))
            repo = git.Repo(os.path.join(os.getcwd(), repo_name))
            repo.git.checkout(repo_branch)
            repo.git.reset('--hard')
            repo.remotes.origin.pull()
            repo.git.execute(['git','apply', os.path.join(os.getcwd(), 'patches/0001-output-string.patch')])
        logging.getLogger('daily-bot').info('Repository is at the latest commit')
    logging.getLogger('daily-bot').info('\nFinished updating local OoT_Randomizer repository.\n')
    