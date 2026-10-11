#!/usr/bin/env python3.12
"""Capture four normal-speed A500 gameplay clips with reproducible joystick input."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
KIT = Path(os.environ.get('AGK_KIT', str(Path.home() / 'Code/amiga/amiga-game-kit')))
sys.path.insert(0, str(KIT / 'harness'))
from agk import profiles, runner, scenario
from agk.image import Image, SCREEN_X0, SCREEN_Y0, SCREEN_W, SCREEN_H, WIDTH, HEIGHT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adf', type=Path, default=ROOT / 'game/build/astra.adf')
    parser.add_argument('--out', type=Path, default=ROOT / '.tmp/astra-gameplay')
    parser.add_argument('--label', default='Current built ADF')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    disk = out / 'capture.adf'
    shutil.copyfile(args.adf, disk)
    profile, rom, ext = profiles.resolve('a500')
    # Own cold boot and output folders: no user emulator or snapshot is touched.
    boot = out / 'boot'
    boot.mkdir()
    bootlines = runner._setup_lines(profile, rom, ext) + [
        f'regression run {disk}',
        f'waitserial {scenario.serial_text("AGK ready")} 6000',
        'wait 1 frames', f'agk snapsave {boot}/ready.vasnap']
    code, log, _ = runner._run_vamiga(bootlines, str(boot))
    if code:
        raise RuntimeError('Cold boot failed; see ' + str(boot / 'emulator.log'))
    manifest = {'label': args.label, 'adf': str(args.adf.resolve()), 'adf_sha256': sha(disk),
                'profile': 'a500', 'hardware': 'OCS, 512K chip + 512K slow, 68000',
                'capture_fps': 25, 'speed': 1, 'sync': 'PAL video frames, two per captured picture',
                'script_sha256': sha(Path(__file__)), 'clips': {}}
    for sector, name in enumerate(('graveyard', 'nebula', 'foundry', 'citadel')):
        folder = out / name
        folder.mkdir()
        prep = ['wait-serial "AGK language_ready" 600', 'press right 2', 'wait 24',
                'press fire 2', 'wait-serial "AGK title_ready" 1000']
        for _ in range(sector):
            prep += ['press right 2', 'wait 450']
        prep += ['press fire 2', 'wait-serial "AGK combat_ready" 1000']
        parsed = scenario.parse('\n'.join(prep), name)
        lines = runner._setup_lines(profile, rom, ext) + [
            f'agk snapload {boot}/ready.vasnap', *runner._display_lines(), 'wait 1 frames']
        lines += runner._sync_lines(parsed.lines, 'frames')
        lines += ['agk audio start']
        previous = None
        for frame in range(400):
            tick = frame * 2
            # Charge/release lances, then quick normal volleys, with vertical dodges.
            fire = tick % 150 < 60 or (tick % 150 >= 76 and tick % 16 < 8)
            direction = ('up', 'down', 'down', 'up')[(tick // 40) % 4]
            state = (fire, direction)
            if state != previous:
                lines += ['joystick2 ' + ('press 1' if fire else 'unpress 1'),
                          'joystick2 pull ' + direction]
                previous = state
            lines += ['wait 2 frames', f'agk screenshot {folder}/frame-{frame:04d}.raw']
        lines += [f'agk audio save {folder}/audio.wav', f'agk serial {folder}/serial.txt']
        print('CAPTURE', name, flush=True)
        code, log, elapsed = runner._run_vamiga(lines, str(folder))
        if code:
            raise RuntimeError(f'{name}: capture failed; see {folder}/emulator.log')
        serial = (folder / 'serial.txt').read_text()
        if 'AGK combat_ready' not in serial or any(e in serial for e in ('STACK SMASHED', 'allocation failure')):
            raise RuntimeError(f'{name}: invalid gameplay capture; inspect serial.txt')
        video = folder / 'gameplay.mp4'
        command = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pixel_format', 'rgb24',
                   '-video_size', '640x256', '-framerate', '25', '-i', '-',
                   '-i', str(folder / 'audio.wav'), '-map', '0:v', '-map', '1:a',
                   '-vf', 'scale=640:512:flags=neighbor,setsar=1', '-c:v', 'libx264',
                   '-crf', '16', '-preset', 'fast', '-pix_fmt', 'yuv420p',
                   '-af', 'volume=12dB', '-c:a', 'aac', '-b:a', '192k', '-t', '16',
                   '-movflags', '+faststart', str(video)]
        with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
            try:
                for frame in range(400):
                    path = folder / f'frame-{frame:04d}.raw'
                    raw = path.read_bytes()
                    if len(raw) != WIDTH * HEIGHT * 3:
                        raise ValueError(f'Bad raw frame: {path}')
                    if frame % 50 == 25:
                        Image.from_raw_file(str(path)).canonical12().screen().save_png(str(folder / f'review-{frame:04d}.png'))
                    for y in range(SCREEN_Y0, SCREEN_Y0 + SCREEN_H):
                        offset = (y * WIDTH + SCREEN_X0) * 3
                        encoder.stdin.write(raw[offset:offset + SCREEN_W * 2 * 3])
                    path.unlink()
            finally:
                encoder.stdin.close()
            if encoder.wait():
                raise RuntimeError(f'{name}: encoding failed')
        manifest['clips'][name] = {'video': str(video.relative_to(out)), 'sha256': sha(video),
                                   'duration': 16, 'frames': 400, 'capture_seconds': elapsed}
        (out / 'sources.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('READY', out / 'sources.json', flush=True)


if __name__ == '__main__':
    main()
