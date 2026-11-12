"""Move large download-only files out of Pages; retain all chart/runtime data.

Run after source/workbook/offline-archive validation, before Pages upload.
Only root-level research ZIP, Excel, CSV and PDF downloads are eligible.
HTML, JavaScript, JSON and JSON.gz chart partitions are never moved.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import quote, unquote, urlsplit

LIMIT = 1_000_000_000
HREF = re.compile(r'''(\bhref\s*=\s*)(["'])(.*?)\2''', re.I)


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def gh_json(arguments):
    return json.loads(subprocess.check_output([os.environ.get('GH_BIN', 'gh'), *arguments], text=True, encoding='utf-8'))


def local_target(page, href, site, repository):
    """Recognise both relative links and absolute links to this Pages project."""
    parsed = urlsplit(href)
    if not parsed.path:
        return None
    if parsed.scheme or parsed.netloc:
        owner, project = repository.split('/')
        prefix = '/' if project.lower() == owner.lower() + '.github.io' else '/' + project + '/'
        if parsed.scheme not in ('http', 'https', '') or parsed.hostname != owner.lower() + '.github.io' or not parsed.path.startswith(prefix):
            return None
        path = site / unquote(parsed.path[len(prefix):])
    else:
        path = page.parent / unquote(parsed.path)
    if parsed.path.endswith('/'):
        path = path / 'index.html'
    return path.resolve()


def prepare(site, assets, repository, release_tag, threshold=5_000_000, reuse=None):
    site, assets = Path(site).resolve(), Path(assets).resolve()
    if assets == site or site in assets.parents or assets in site.parents:
        raise ValueError('Website and release downloads must be separate directories')
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', repository) or not re.fullmatch(r'[\w.-]+', release_tag):
        raise ValueError('Invalid repository or release tag')
    assert (site / 'index.html').is_file()
    assert not (site / 'downloads_manifest.json').exists(), 'Distribution already prepared; use an untouched build'
    assets.mkdir(parents=True, exist_ok=True)
    assert not any(assets.iterdir()), 'Use an empty release-download directory'
    reuse = reuse or {}
    before = sum(p.stat().st_size for p in site.rglob('*') if p.is_file())
    files = {}
    for path in sorted(site.iterdir()):
        eligible = path.name == 'world-rd-income.zip' or path.name.endswith(('.xlsx', '.csv', '.csv.gz', '.pdf'))
        if not path.is_file() or not eligible or path.stat().st_size < threshold:
            continue
        checksum, size = digest(path), path.stat().st_size
        assert size < 2 * 1024 ** 3, 'Release asset must be smaller than 2 GiB: ' + path.name
        existing = reuse.get(path.name)
        if existing and existing.get('size') == size and existing.get('digest') == 'sha256:' + checksum:
            url = existing['browser_download_url']
            prefix = f'https://github.com/{repository}/releases/download/'
            assert url.startswith(prefix) and url.endswith('/' + quote(path.name)), url
            tag = unquote(url[len(prefix):].split('/')[0])
        else:
            tag = release_tag
            url = f'https://github.com/{repository}/releases/download/{quote(tag)}/{quote(path.name)}'
        files[path.name] = {'bytes': size, 'sha256': checksum, 'url': url, 'release_tag': tag,
                            'reused_existing_asset': tag != release_tag}
        # Keep an exact local copy outside Pages, including reused assets.
        shutil.copy2(path, assets / path.name)
        assert digest(assets / path.name) == checksum

    assert files, 'No large downloads found; nothing to publish'
    rewrites = 0
    for page in site.rglob('*.html'):
        def replace(match):
            nonlocal rewrites
            parsed = urlsplit(match[3])
            target = local_target(page, match[3], site, repository)
            if target is None or target.parent != site or target.name not in files:
                return match[0]
            rewrites += 1
            suffix = ('?' + parsed.query if parsed.query else '') + ('#' + parsed.fragment if parsed.fragment else '')
            return match[1] + match[2] + files[target.name]['url'] + suffix + match[2]
        text = page.read_bytes().decode('utf-8')
        updated = HREF.sub(replace, text)
        if updated != text:
            page.write_bytes(updated.encode('utf-8'))
    assert rewrites, 'No download links were rewritten'
    for name in files:
        (site / name).unlink()
    index = site / 'index.html'
    index.write_bytes(index.read_bytes().decode('utf-8').replace('</main>',
        '<p class="help">Large downloads are hosted on GitHub Releases. '
        '<a href="downloads_manifest.json">Download locations, sizes and SHA-256 checksums</a>.</p></main>').encode('utf-8'))
    manifest = {'format': 1, 'repository': repository, 'release_tag': release_tag,
                'prepared_utc': datetime.now(timezone.utc).isoformat(), 'threshold_bytes': threshold,
                'scope': 'Download-only files; interactive JSON and compressed chart partitions stay on Pages.',
                'staging_bytes_before': before, 'download_links_rewritten': rewrites, 'files': files}
    body = json.dumps(manifest, indent=2) + '\n'
    (site / 'downloads_manifest.json').write_text(body, encoding='utf-8')
    (assets / 'downloads_manifest.json').write_text(body, encoding='utf-8')
    verify(site, assets, manifest)
    return manifest


def verify(site, assets, manifest):
    site, assets = Path(site).resolve(), Path(assets).resolve()
    for name, info in manifest['files'].items():
        assert not (site / name).exists(), name
        assert (assets / name).stat().st_size == info['bytes'] and digest(assets / name) == info['sha256'], name
    links = 0
    for page in site.rglob('*.html'):
        for match in HREF.finditer(page.read_text('utf-8')):
            target = local_target(page, match[3], site, manifest['repository'])
            if target is None:
                continue
            assert target.is_relative_to(site) and target.is_file(), (page.name, match[3])
            links += 1
    size = sum(p.stat().st_size for p in site.rglob('*') if p.is_file())
    report = {'verification': 'passed', 'files_hosted_in_releases': len(manifest['files']),
              'unchanged_download_bytes': sum(i['bytes'] for i in manifest['files'].values()),
              'remaining_local_links_checked': links, 'site_bytes_before_report': size,
              'scope': 'Checksums, rewritten and remaining links, and final Pages size. Remote assets are checked at publication.'}
    path = site / 'download_distribution_verification.json'
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    assert sum(p.stat().st_size for p in site.rglob('*') if p.is_file()) < LIMIT, 'Pages exceeds 1 GB'
    return report


def publish(assets, manifest, target):
    repository, tag = manifest['repository'], manifest['release_tag']
    names = [name for name, info in manifest['files'].items() if not info['reused_existing_asset']]
    cli = os.environ.get('GH_BIN', 'gh')
    subprocess.run([cli, 'release', 'create', tag, *[str(Path(assets) / name) for name in names],
                    str(Path(assets) / 'downloads_manifest.json'), '--repo', repository,
                    '--target', target, '--latest=false', '--title', 'Dashboard downloads · ' + tag,
                    '--notes', 'Exact validated research downloads, hosted separately from GitHub Pages. '
                    'See downloads_manifest.json for SHA-256 checksums, sizes and build-specific URLs.'], check=True)
    for release_tag in {info['release_tag'] for info in manifest['files'].values()}:
        release = gh_json(['api', f'repos/{repository}/releases/tags/{release_tag}'])
        assert not release['draft']
        remote = {item['name']: item for item in release['assets']}
        for name, expected in manifest['files'].items():
            if expected['release_tag'] == release_tag:
                assert remote[name]['size'] == expected['bytes'], name
                assert remote[name]['digest'] == 'sha256:' + expected['sha256'], name
    print('All release asset sizes and GitHub SHA-256 digests match.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--release-tag', required=True)
    parser.add_argument('--threshold', type=int, default=5_000_000)
    parser.add_argument('--reuse-release', help='Reuse identical assets from this existing public release')
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--target', help='Commit for a new download release (required with --publish)')
    args = parser.parse_args()
    if args.publish and not args.target:
        parser.error('--publish requires --target')
    reuse = {}
    if args.reuse_release:
        release = gh_json(['api', f'repos/{args.repository}/releases/tags/{args.reuse_release}'])
        assert not release['draft']
        reuse = {item['name']: item for item in release['assets']}
    manifest = prepare(args.site, args.assets, args.repository, args.release_tag, args.threshold, reuse)
    if args.publish:
        publish(args.assets, manifest, args.target)
    print(json.dumps({'files': len(manifest['files']), 'moved_bytes': sum(i['bytes'] for i in manifest['files'].values()),
                      'pages_bytes': sum(p.stat().st_size for p in args.site.rglob('*') if p.is_file())}, indent=2), flush=True)


if __name__ == '__main__':
    main()
