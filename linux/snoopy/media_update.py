"""Verified shared idle-media upgrade. Old assets survive any failed download."""
import hashlib,json,os,re,shutil,stat,tempfile,zipfile
from pathlib import Path
from urllib.request import Request,urlopen

URL='https://github.com/iliamch/snoopy-updates/releases/download/v2026.09.24/SnoopyIdleAssets-2.zip'
SHA='5b85da61f339712f7684f3f988641013aebaf84939b71cab225fdbc8f748b5e5'
SIZE=2189200473
PARTS=[{'name': 'SnoopyIdleAssets-2.zip.001', 'size': 1100000000, 'sha256': '852d8d9fd316b04603d9fac3a5cdcee6906c33e4a48597c8d88a2d641cd9eb2e'}, {'name': 'SnoopyIdleAssets-2.zip.002', 'size': 1089200473, 'sha256': '0c8d1265ec04790051a7c82be948c5f5389d5be53e644216caf3c626e08233fa'}]
MANIFEST_SHA='5b85da61f339712f7684f3f988641013aebaf84939b71cab225fdbc8f748b5e5'

def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def complete(media):
    root=Path(media)/'IdleAssets'
    try:return (root/'installed-package.txt').read_text()==SHA and (root/'interactions.json').is_file()
    except OSError:return False

def safe(name):
    return name in ('catalog.json','interactions.json') or bool(re.fullmatch(r'(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.png',name))

def extract(archive,stage):
    if digest(archive)!=SHA:raise ValueError('Idle media checksum mismatch')
    stage=Path(stage)
    with zipfile.ZipFile(archive) as package:
        entries=package.infolist();names=[x.filename for x in entries]
        if len(names)!=len(set(names)) or len(names)>50001 or sum(x.file_size for x in entries)>3*1024**3:raise ValueError('Invalid media layout')
        payload=package.read('package-manifest.json')
        if len(payload)>8*1024**2 or hashlib.sha256(payload).hexdigest()!=MANIFEST_SHA:raise ValueError('Invalid media manifest')
        manifest=json.loads(payload)
        if manifest['Version']!='2' or set(names)!={'package-manifest.json',*manifest['Files']} or not {'catalog.json','interactions.json'}<=manifest['Files'].keys():raise ValueError('Invalid media inventory')
        for entry in entries:
            if entry.filename=='package-manifest.json':continue
            if not safe(entry.filename) or entry.file_size>32*1024**2 or stat.S_ISLNK(entry.external_attr>>16):raise ValueError('Unsafe media entry')
            dest=stage/entry.filename;dest.parent.mkdir(parents=True,exist_ok=True)
            with package.open(entry) as source,dest.open('wb') as target:shutil.copyfileobj(source,target,1024**2)
            if digest(dest)!=manifest['Files'][entry.filename]:raise ValueError('Media file checksum mismatch')
    (stage/'installed-package.txt').write_text(SHA)

def ensure(media):
    media=Path(media)
    if complete(media):return str(media)
    if not (media/'scenes.json').is_file():raise ValueError('Choose your existing animation library first')
    if shutil.disk_usage(media).free<5*1024**3:raise ValueError('Free 5 GB to install the new idle scenes')
    with tempfile.TemporaryDirectory(prefix='.idle-upgrade-',dir=media) as temp:
        temp=Path(temp);archive=temp/'idle.zip';total=0
        with archive.open('wb') as output:
            for part in PARTS:
                h=hashlib.sha256();count=0
                url=URL.rsplit('/',1)[0]+'/'+part['name']
                with urlopen(Request(url,headers={'User-Agent':'SnoopyLinux'}),timeout=60) as response:
                    if not response.url.startswith('https://'):raise ValueError('Insecure media redirect')
                    while True:
                        block=response.read(1024**2)
                        if not block:break
                        total+=len(block);count+=len(block);h.update(block)
                        if count>part['size'] or total>SIZE:raise ValueError('Media exceeds expected size')
                        output.write(block)
                if count!=part['size'] or h.hexdigest()!=part['sha256']:raise ValueError('Media part checksum mismatch')
        if total!=SIZE:raise ValueError('Incomplete media download')
        ready=temp/'ready';ready.mkdir();extract(archive,ready)
        dest=media/'IdleAssets';backup=media/('IdleAssets-backup-'+os.urandom(4).hex());moved=False
        try:
            if dest.exists():dest.rename(backup);moved=True
            ready.rename(dest)
        except Exception:
            if moved and not dest.exists():backup.rename(dest)
            raise
    return str(media)
