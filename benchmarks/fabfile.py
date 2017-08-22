from hashlib import md5
from pathlib import Path

from invoke import task


def as_user(ctx, user, cmd, *args, **kwargs):
    ctx.run('sudo --set-home --preserve-env --user {} --login '
            '{}'.format(user, cmd), *args, **kwargs)


def as_bench(ctx, cmd, *args, **kwargs):
    as_user(ctx, 'bench', cmd)


def sudo_put(ctx, local, remote, chown=None):
    tmp = str(Path('/tmp') / md5(remote.encode()).hexdigest())
    ctx.put(local, tmp)
    ctx.run('sudo mv {} {}'.format(tmp, remote))
    if chown:
        ctx.run('sudo chown {} {}'.format(chown, remote))


def put_dir(ctx, local, remote):
    exclude = ['/.', '__pycache__', '.egg-info', '/tests']
    local = Path(local)
    remote = Path(remote)
    for path in local.rglob('*'):
        relative_path = path.relative_to(local)
        if any(pattern in str(path) for pattern in exclude):
            continue
        if path.is_dir():
            as_bench(ctx, 'mkdir -p {}'.format(remote / relative_path))
        else:
            sudo_put(ctx, path, str(remote / relative_path),
                     chown='bench:users')


@task
def bench(ctx, tools='', names=''):
    as_bench(ctx, '/bin/bash -c ". /srv/bench/venv/bin/activate && '
                  'cd /srv/bench/src/benchmarks && ./bench.sh '
                  f'\"{tools}\" \"{names}\""')


@task
def system(ctx):
    ctx.run('sudo apt update')
    ctx.run('sudo apt install python3.6 python3.6-dev wrk apache2-utils '
            'python-virtualenv build-essential httpie --yes')
    ctx.run('sudo useradd -N bench -m -d /srv/bench/ || exit 0')
    ctx.run('sudo chsh -s /bin/bash bench')


@task
def venv(ctx):
    as_bench(ctx, 'virtualenv /srv/bench/venv --python=python3.6')
    as_bench(ctx, '/srv/bench/venv/bin/pip install pip -U')


@task
def bootstrap(ctx):
    system(ctx)
    venv(ctx)
    deploy(ctx)


@task
def deploy(ctx):
    as_bench(ctx, 'rm -rf /srv/bench/src')
    # Push local code so we can benchmark local changes easily.
    put_dir(ctx, Path(__file__).parent.parent, '/srv/bench/src')
    as_bench(ctx, '/srv/bench/venv/bin/pip install -r '
                  '/srv/bench/src/benchmarks/requirements.txt')
    as_bench(ctx, '/bin/bash -c "cd /srv/bench/src/; '
                  '/srv/bench/venv/bin/python setup.py develop"')
