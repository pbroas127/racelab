"""Plant realistic bugs in a clean qs checkout. `python plant.py check` tries each bug alone against the test suite
and reports how many assertions it breaks; `python plant.py apply <dir>` applies every bug that breaks something.
The answer key stays here, outside the race folders."""
import json, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).parent
CLEAN = ROOT / 'qs'
BUGS = [
    ('lib/parse.js', '    depth: 5,', '    depth: 4,', 'default nesting depth off by one'),
    ('lib/parse.js', '0xDC00 | (c & 0x3FF)', '0xDC00 | (c & 0x3FE)', 'numeric entity surrogate low bits masked wrong'),
    ('lib/parse.js', 'if (commaCount >= options.arrayLimit) {', 'if (commaCount > options.arrayLimit) {', 'comma array limit lets one extra through'),
    ('lib/parse.js', "part.indexOf('=') : bracketEqualsPos + 1;", "part.indexOf('=') : bracketEqualsPos;", 'key/value split one char early after ]='),
    ('lib/parse.js', '} else if (isValidArrayIndex && index < options.arrayLimit) {', '} else if (isValidArrayIndex && index <= options.arrayLimit) {', 'array index limit off by one'),
    ('lib/parse.js', "if (chain.length > 0 && chain[chain.length - 1] === '[]') {", "if (chain.length > 0 && chain[0] === '[]') {", 'checks the first segment instead of the last'),
    ('lib/utils.js', '|| c === 0x5F // _', '|| c === 0x5E // _', 'underscore treated as unsafe, caret as safe'),
    ('lib/utils.js', 'if (c < 0x800) {', 'if (c <= 0x800) {', 'utf-8 2 byte boundary off by one'),
    ('lib/utils.js', '+ hexTable[0x80 | ((c >> 12) & 0x3F)]', '+ hexTable[0x80 | ((c >> 12) & 0x1F)]', '4 byte utf-8 continuation mask wrong'),
    ('lib/stringify.js', 'objKeys = sort ? keys.sort(sort) : keys;', 'objKeys = sort ? keys.sort() : keys;', 'custom sort comparator ignored'),
    ('lib/stringify.js', "return prefix + '[' + key + ']';", "return prefix + '[' + key + ']' + '';", 'control (no-op, should break nothing)'),
]


def tests(d):
    r = subprocess.run('npx tape "test/**/*.js"', cwd=d, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
    out = r.stdout + r.stderr
    fail = next((int(l.split()[-1]) for l in out.splitlines() if l.startswith('# fail')), 0)
    return fail


def check():
    work = ROOT / 'work'
    rep = []
    for f, old, new, label in BUGS:
        src = (CLEAN / f).read_text(encoding='utf-8')
        assert src.count(old) == 1, f'{label}: not unique/found'
        (CLEAN / f).write_text(src.replace(old, new), encoding='utf-8')
        try:
            n = tests(CLEAN)
        finally:
            (CLEAN / f).write_text(src, encoding='utf-8')
        rep.append((n, label))
        print(f'{n:4d} failing  {label}', flush=True)
    assert tests(CLEAN) == 0, 'clean copy no longer passes'
    json.dump(rep, open(ROOT / 'check.json', 'w'))
    return rep


def apply(dest):
    rep = dict((l, n) for n, l in json.load(open(ROOT / 'check.json')))
    dest = pathlib.Path(dest)
    for f, old, new, label in BUGS:
        if rep.get(label, 0) > 0:
            p = dest / f
            s = p.read_text(encoding='utf-8')
            p.write_text(s.replace(old, new), encoding='utf-8')
            print('planted:', label)


if __name__ == '__main__':
    check() if sys.argv[1] == 'check' else apply(sys.argv[2])
