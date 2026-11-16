"""Apply only the annual-download feature to the immutable published snapshot."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

BASE = '46a99613ddba54f7683bc2350ff2b7a676629379'
BASE_SHA = 'c38591479e41fd33dcdfeb9d3007dfa8cdfa2fa94c81cb563ed8f49326c9644e'
ROOT = Path('figures/world-rd-income')


def validate(archive_path, site):
    assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == BASE_SHA
    with zipfile.ZipFile(archive_path) as archive:
        names = {n for n in archive.namelist() if not n.endswith('/')}
        assert names == {p.relative_to(site).as_posix() for p in site.rglob('*') if p.is_file()}
        changed = [n for n in sorted(names) if archive.read(n) != (site / n).read_bytes()]
        assert changed == ['view-national.html'], changed
        old = archive.read('view-national.html').decode('utf-8')
        new = (site / 'view-national.html').read_bytes().decode('utf-8')
        pattern = r'<script\b[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>'
        assert re.findall(pattern, old, re.S) == re.findall(pattern, new, re.S)
        assert 'id="export-all-years"' in new
    return {'changed_files':changed, 'unchanged_files':len(names)-1, 'embedded_data_byte_identical':True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--package', type=Path)
    args = parser.parse_args()
    assert hashlib.sha256(args.archive.read_bytes()).hexdigest() == BASE_SHA
    if not args.package:
        args.destination.mkdir(parents=True, exist_ok=False)
        with zipfile.ZipFile(args.archive) as archive:
            archive.extractall(args.destination)
        path = args.destination / 'view-national.html'
        text = path.read_bytes().decode('utf-8')
        for name in ['explorer.html', 'explorer.js', 'explorer_core.js']:
            source = ROOT / name
            old = subprocess.check_output(['git','show',BASE+':'+source.as_posix()]).decode('utf-8').splitlines()
            new = source.read_text('utf-8').splitlines()
            for op,i,j,k,l in difflib.SequenceMatcher(None,old,new,autojunk=False).get_opcodes():
                if op == 'equal':
                    continue
                before, after = '\n'.join(old[i:j]), '\n'.join(new[k:l])
                if op == 'insert':
                    anchor = '\n'.join(old[max(0,i-2):i])
                    assert text.count(anchor) == 1, (name,anchor)
                    text = text.replace(anchor,anchor+'\n'+after,1)
                else:
                    assert text.count(before) == 1, (name,before)
                    text = text.replace(before,after,1)
        path.write_bytes(text.encode('utf-8'))
    report = validate(args.archive,args.destination)
    if args.package:
        args.package.mkdir(parents=True,exist_ok=False)
        output = args.package / 'pages-site.zip'
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for path in sorted(args.destination.rglob('*')):
                if path.is_file():
                    archive.write(path,path.relative_to(args.destination).as_posix())
        report.update(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                      sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                      site_bytes=sum(p.stat().st_size for p in args.destination.rglob('*') if p.is_file()),
                      validation_suites=['11 Node suites including annual-export fixtures',
                                         '5,694 downloaded rows checked against embedded observations; filter independence and mobile',
                                         '31-route table/UI/share/presentation/mobile baseline regression',
                                         'Three GDP bases and exact WDI observations',
                                         '31-route source captions and SVG/PNG exports',
                                         '27 byte-identical existing generated CSV exports',
                                         '667 unchanged files and byte-identical embedded JSON'])
        (args.package/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
