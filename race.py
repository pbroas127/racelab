"""Racelab: race AI coding agents on the same planted bugs.

  python race.py setup fable opus sonnet haiku   one bugged copy of qs per name, in races/<name>, fresh git history
  python race.py score                           tests + time / tool calls / output tokens per copy
  python race.py selftest                        checks the token counter and the planted bugs
"""
import json, os, pathlib, re, shutil, stat, subprocess, sys
from datetime import datetime

import plant

ROOT = pathlib.Path(__file__).resolve().parent
QS = ROOT / 'qs'
RACES = ROOT / 'races'
# ponytail: string match on tool inputs, not a sandbox. Catches the answer key, the clean copy, and any ../ escape.
PEEK = ('plant.py', 'check.json', '../', '..\\\\', str(QS).replace('\\', '/').lower(), json.dumps(str(QS))[1:-1].lower())


def sh(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)


def ensure_deps():
    if not (QS / 'node_modules' / 'tape').exists():
        print('installing qs dev dependencies once (npm install)...', flush=True)
        r = sh('npm install --no-audit --no-fund', QS)
        if r.returncode:
            sys.exit(r.stdout + r.stderr)


def tests(d):
    out = sh('npx tape "test/**/*.js"', d)
    out = out.stdout + out.stderr
    n = {k: int(m.group(1)) for k in ('pass', 'fail') if (m := re.search(rf'^# {k}\s+(\d+)', out, re.M))}
    if 'pass' not in n:
        raise RuntimeError(f'no tape summary in {d}:\n{out[-800:]}')
    return n['pass'], n.get('fail', 0)


def link_modules(dst):
    try:
        dst.symlink_to(QS / 'node_modules', target_is_directory=True)
    except OSError:  # Windows without developer mode: a junction needs no rights
        r = sh(f'mklink /J "{dst}" "{QS / "node_modules"}"', ROOT)
        if r.returncode:
            sys.exit(r.stdout + r.stderr)


def remove(d):
    nm = d / 'node_modules'
    if os.path.lexists(nm):  # drop the link itself first so the shared modules are never walked
        try:
            os.unlink(nm)
        except OSError:
            os.rmdir(nm)
    shutil.rmtree(d, onerror=lambda f, p, e: (os.chmod(p, stat.S_IWRITE), f(p)))  # git objects are read only on Windows


def setup(names):
    ensure_deps()
    for name in names:
        d = RACES / name
        if d.exists():
            remove(d)
        shutil.copytree(QS, d, ignore=shutil.ignore_patterns('node_modules'))
        link_modules(d / 'node_modules')  # shared, read only use; qs's .gitignore keeps it out of git
        plant.apply(d)
        for c in ('git init -q', 'git add -A', 'git -c user.name=racelab -c user.email=racelab@localhost commit -qm start'):
            r = sh(c, d)
            if r.returncode:
                sys.exit(f'{name}: {c} failed\n{r.stderr}')
        p, f = tests(d)
        print(f'{name}: ready in {d.relative_to(ROOT)}  ({f} of {p + f} assertions failing)', flush=True)


def transcript_dir(d):
    # Claude Code keeps one folder per working directory, the path with every non alphanumeric char turned into '-'
    return pathlib.Path.home() / '.claude' / 'projects' / re.sub(r'[^A-Za-z0-9]', '-', str(d))


def stats(rows):
    """Time from the first typed prompt to the last answer, tool calls, output tokens, and whether the answer key was opened.
    Claude Code writes one row per content block and repeats the message usage on each, so tokens count once per message id."""
    prompts = [r for r in rows if r.get('type') == 'user' and isinstance(r['message'].get('content'), str)]
    answers = [r for r in rows if r.get('type') == 'assistant']
    if not prompts or not answers:
        return None
    tokens, tools, peeked = {}, set(), False
    for r in answers:
        m = r['message']
        tokens[m['id']] = (m.get('usage') or {}).get('output_tokens', 0)
        for b in m.get('content') or []:
            if b.get('type') == 'tool_use':
                tools.add(b['id'])
                peeked |= any(k in json.dumps(b.get('input')).lower() for k in PEEK)
    t = lambda r: datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00'))
    return {'seconds': (t(answers[-1]) - t(prompts[0])).total_seconds(), 'tools': len(tools), 'tokens': sum(tokens.values()), 'peeked': peeked}


def newest_transcript(d):
    files = sorted(transcript_dir(d).glob('*.jsonl'), key=lambda f: f.stat().st_mtime)
    if not files:
        return None
    return [json.loads(l) for l in files[-1].open(encoding='utf-8') if l.strip()]


def score():
    dirs = sorted(p for p in RACES.glob('*') if p.is_dir()) if RACES.exists() else []
    if not dirs:
        sys.exit('no races yet: python race.py setup <name> <name> ...')
    print(f'{"copy":<12}{"tests":>18}{"time":>8}{"tools":>7}{"out tokens":>12}  note')
    for d in dirs:
        p, f = tests(d)
        rows = newest_transcript(d)
        s = stats(rows) if rows else None
        cols = ('%d:%02d' % divmod(round(s['seconds']), 60), s['tools'], f'{s["tokens"]:,}') if s else ('-', '-', '-')
        note = 'OPENED THE ANSWER KEY' if s and s['peeked'] else ('' if s else 'no Claude Code transcript: pass/fail only')
        print(f'{d.name:<12}{f"{p:,}/{p + f:,} pass":>18}{cols[0]:>8}{cols[1]:>7}{cols[2]:>12}  {note}')


def selftest():
    msg = lambda i, out, blocks: {'type': 'assistant', 'timestamp': f'2026-01-01T00:0{i}:00Z',
                                  'message': {'id': f'm{out}', 'usage': {'output_tokens': out}, 'content': blocks}}
    rows = [{'type': 'user', 'timestamp': '2026-01-01T00:00:00Z', 'message': {'content': 'fix it'}},
            msg(1, 100, [{'type': 'text'}]),
            msg(1, 100, [{'type': 'tool_use', 'id': 't1', 'input': {'cmd': 'ls'}}]),  # same message, usage repeated
            msg(2, 50, [{'type': 'tool_use', 'id': 't2', 'input': {'file_path': 'lib/parse.js'}}]),
            msg(3, 7, [{'type': 'text'}])]
    s = stats(rows)
    assert s == {'seconds': 180, 'tools': 2, 'tokens': 157, 'peeked': False}, s
    rows[3]['message']['content'][0]['input'] = {'file_path': '../../plant.py'}
    assert stats(rows)['peeked']
    rows[3]['message']['content'][0]['input'] = {'file_path': str(QS / 'lib' / 'parse.js')}
    assert stats(rows)['peeked']
    ensure_deps()
    rep = plant.check()
    broke = [n for n, label in rep if n > 0]
    control = [n for n, label in rep if label.startswith('control')]
    assert len(broke) == 6 and sum(broke) == 31 and control == [0], rep
    print('ok')


if __name__ == '__main__':
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ('', [])
    if cmd == 'setup' and args:
        setup(args)
    elif cmd == 'score':
        score()
    elif cmd == 'selftest':
        selftest()
    else:
        sys.exit(__doc__)
