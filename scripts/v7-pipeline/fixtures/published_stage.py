"""Small in-process fixture for the canonical directory publication protocol."""
from pathlib import Path

from execution_state import _publication_module


def main(argv=None, *, emit=print):
    source, destination = map(Path, argv)
    work = destination.with_name(destination.name + '.partial')
    work.mkdir()
    (work / 'result.bin').write_bytes(source.read_bytes())
    _publication_module().move_noreplace(work, destination)
