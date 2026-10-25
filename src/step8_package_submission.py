"""Yalnız güncel proje dosyalarıyla doğrulanmış teslim ZIP'i oluşturur."""
from pathlib import Path
import zipfile
from step7_verify_project import ROOT, main as verify


def main():
    verify()
    paths = [ROOT/name for name in ('README.md','report.pdf','requirements.txt','.gitignore')]
    for directory in ('data','src','results','docs','tests'):
        paths += [p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.zip'}]
    paths = sorted(paths)
    destination = ROOT/'structured-text-project-submission.zip'
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in paths:
            archive.write(path,arcname='structured-text-project/'+str(path.relative_to(ROOT)))
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(paths)
        for path in paths:
            assert archive.read('structured-text-project/'+str(path.relative_to(ROOT))) == path.read_bytes()
    print(f'Validated {len(paths)} current files in {destination} ({destination.stat().st_size} bytes).')


if __name__ == '__main__':
    main()
