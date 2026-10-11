#!/usr/bin/env python3
"""Rebuild THE SIGNAL from current Astra artwork; no emulator or paid services.

The edit combines promotional motion design and native gameplay. Inspired by
SuperRugbyV/tools/teaser's frame-exact FFmpeg/Pillow pipeline and source manifest.
"""
import argparse
import hashlib
import json
import math
import subprocess
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
W, H = 960, 540
INK = (5, 7, 17)
CYAN = (127, 211, 212)
WHITE = (231, 230, 219)
AMBER = (214, 145, 110)


def run(args):
    subprocess.run([str(x) for x in args], check=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=32)
def font(size, bold=False):
    name = 'SpaceMono-Bold.ttf' if bold else 'SpaceMono-Regular.ttf'
    return ImageFont.truetype(str(HERE / 'fonts' / name), size)


def smooth(x):
    x = min(1, max(0, x))
    return x * x * (3 - 2 * x)


def centered(draw, text, y, size=24, color=WHITE, bold=False):
    face = font(size, bold)
    while draw.textbbox((0, 0), text, font=face)[2] > W - 100:
        size -= 1
        face = font(size, bold)
    draw.text((W // 2, y), text, font=face, fill=color, anchor='mt')


def cover(image, zoom=1, focus=(.5, .5)):
    scale = max(W / image.width, H / image.height) * zoom
    image = image.resize((math.ceil(image.width * scale), math.ceil(image.height * scale)), Image.Resampling.NEAREST)
    x = int((image.width - W) * focus[0])
    y = int((image.height - H) * focus[1])
    return image.crop((x, y, x + W, y + H))


class Renderer:
    def __init__(self, config, root, footage=None):
        self.config = config
        self.footage = footage
        self.clips = {}
        self.assets = {key: Image.open(root / path).convert('RGB') for key, path in config['assets'].items()}
        rng = np.random.default_rng(config['seed'])
        self.stars = rng.random((100, 4))
        # A faint optical falloff and scan lines, kept constant across frames.
        yy, xx = np.mgrid[:H, :W]
        radius = ((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2
        alpha = np.minimum(170, radius * 220).astype('uint8')
        alpha[::3] = np.minimum(200, alpha[::3].astype('uint16') + 16)
        self.glass = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        self.glass.putalpha(Image.fromarray(alpha))

    def gameplay(self, shot, local):
        key = (shot['clip'], shot['in'], shot['seconds'])
        if key not in self.clips:
            path = self.footage[shot['clip']]
            raw = subprocess.check_output([
                'ffmpeg', '-v', 'error', '-ss', str(shot['in']), '-i', str(path),
                '-t', str(shot['seconds']), '-vf', f'fps={self.config["fps"]},scale=320:256:flags=neighbor',
                '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
            count = shot['seconds'] * self.config['fps']
            if len(raw) != count * 320 * 256 * 3:
                raise ValueError(f'Gameplay clip too short: {key}')
            self.clips[key] = raw
        size = 320 * 256 * 3
        frame = min(int(local * self.config['fps']), shot['seconds'] * self.config['fps'] - 1)
        return Image.frombytes('RGB', (320, 256), self.clips[key][frame*size:(frame+1)*size])

    def frame(self, shot, local, absolute, index):
        duration = shot['seconds']
        u = local / duration
        drift = smooth(u)
        mode = shot['mode']
        image = Image.new('RGB', (W, H), INK)
        source = self.assets.get(shot.get('asset'))
        if mode == 'gameplay':
            game = self.gameplay(shot, local)
            zoom_start, zoom_end = shot.get('zoom', [1, 1])
            zoom = zoom_start + (zoom_end - zoom_start) * drift
            focus_x, focus_y = shot.get('focus', [.5, .5])
            crop_w, crop_h = game.width / zoom, game.height / zoom
            left, top = (game.width - crop_w) * focus_x, (game.height - crop_h) * focus_y
            game = game.resize((640, 512), Image.Resampling.NEAREST,
                               box=(left, top, left + crop_w, top + crop_h))
            image.paste(game, (160, 14))
            draw = ImageDraw.Draw(image)
            draw.text((24, 197), 'A500', font=font(18, True), fill=WHITE)
            draw.text((24, 229), 'GAMEPLAY', font=font(10), fill=CYAN)
            draw.text((24, 252), 'NORMAL SPEED', font=font(9), fill=CYAN)
            draw.line((24, 289, 92, 289), fill=AMBER)
            draw.text((824, 221), shot['clip'].upper(), font=font(10), fill=CYAN)
            draw.text((824, 246), 'SIGNAL ACTIVE', font=font(9), fill=AMBER)
            fade = smooth(local / .35) * smooth((duration - local) / .35)
            return ImageEnhance.Brightness(image).enhance(fade)
        elif mode in ('void', 'pan', 'title'):
            image = cover(source, 1.12 + .14 * drift, (.3 + .4 * u, .5))
            image = ImageEnhance.Brightness(image).enhance(.38 if mode != 'pan' else .85)
        elif mode == 'portrait':
            image = cover(source, 1.01 + .16 * drift, (.35 + .3 * u, .48))
        elif mode == 'detail':
            image = cover(source, 1.8 + .4 * drift, (.88 - .12 * u, .38))
        elif mode == 'eye':
            # Isolate the pilot's face: an editorial crop, not a replacement asset.
            image = cover(source.crop((12, 38, 50, 80)), 1 + .16 * drift, (.5, .42))
            image = ImageEnhance.Brightness(image).enhance(.6)
        elif mode == 'mirror':
            entity = source.crop((source.width * 2 // 5, 0, source.width, source.height))
            plane = cover(entity, 1.05 + .22 * math.sin(u * math.pi), (.5, .5))
            half = plane.crop((int(110 + 70 * drift), 0, int(590 + 70 * drift), H))
            image.paste(half, (0, 0))
            image.paste(ImageOps.mirror(half), (W // 2, 0))
            image = ImageEnhance.Brightness(image).enhance(.65)

        draw = ImageDraw.Draw(image)
        if mode in ('signal', 'void', 'pan', 'title'):
            for sx, sy, speed, brightness in self.stars:
                x = int((sx * W - absolute * (2 + 9 * speed)) % W)
                y = int(sy * H)
                value = int((55 + 100 * brightness) * (.7 + .3 * math.sin(absolute + sx * 8)))
                draw.point((x, y), fill=(value, value, min(255, value + 25)))
        if mode == 'signal':
            # An asymmetric, slowly turning receiver ring with a breathing waveform.
            cx, cy = W // 2, 245
            for r in (76, 107, 146):
                angle = (absolute * (3 if r == 107 else -2) + r) % 360
                draw.arc((cx-r, cy-r, cx+r, cy+r), angle, angle + 247, fill=(25, 55, 67), width=1)
            points = []
            for x in range(280, 681, 2):
                envelope = math.exp(-((x - 480) / 94) ** 2)
                v = math.sin(x * .08 + absolute * 2.5) * math.sin(x * .019 - absolute)
                points.append((x, cy + int(28 * envelope * v)))
            draw.line(points, fill=CYAN, width=1)
            draw.line((470, cy, 490, cy), fill=WHITE)
            draw.line((480, cy-10, 480, cy+10), fill=WHITE)
        if mode in ('detail', 'mirror'):
            # Deliberate, brief horizontal tape slips; never full-frame flashing.
            phase = int(local * 25)
            if phase % 109 in (18, 19, 20):
                y = 110 + (phase * 13) % 270
                strip = image.crop((0, y, W, y + 11))
                image.paste(strip, (8 if index % 2 else -8, y))

        if mode != 'gameplay':
            image = Image.alpha_composite(image.convert('RGBA'), self.glass).convert('RGB')
        # Letterbox and instrument typography are deliberately separate from game art.
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, W, 57), fill=INK)
        draw.rectangle((0, H - 65, W, H), fill=INK)
        draw.line((38, 56, 922, 56), fill=(28, 44, 53))
        header = 'A500 / NATIVE GAMEPLAY CAPTURE' if mode == 'gameplay' else 'A / L     DEEP SPACE RECEIVER'
        draw.text((39, 24), header, font=font(10), fill=CYAN)
        draw.text((920, 24), f'{index + 1:02d}     /     {int(absolute):03d}:00', font=font(10), fill=CYAN, anchor='rt')
        if shot.get('sub') and mode != 'title':
            draw.text((39, 499), shot['sub'], font=font(10), fill=CYAN)
        draw.text((920, 499), 'TRANSMISSION FILM', font=font(9), fill=(90, 105, 122), anchor='rt')

        overlay = Image.new('RGBA', (W, H))
        textdraw = ImageDraw.Draw(overlay)
        text = shot.get('text', '')
        if mode == 'title':
            textdraw.rectangle((0, 57, W, 475), fill=(5, 7, 17, 65))
            centered(textdraw, 'A S T R A', 167, 78, WHITE, True)
            centered(textdraw, shot['sub'], 281, 22, CYAN)
            textdraw.line((405, 337, 555, 337), fill=AMBER, width=1)
            centered(textdraw, 'A side-scrolling shooter for Amiga OCS/ECS', 364, 13, WHITE)
            centered(textdraw, 'KEEP ONE LIGHT ALIVE.', 413, 12, AMBER)
            centered(textdraw, 'github.com/youenchene/astra-last-light', 500, 10, CYAN)
        elif text:
            y = 352 if mode == 'signal' else 386
            if mode != 'signal':
                for line in range(310, 476):
                    textdraw.line((0, line, W, line), fill=(3, 5, 13, int(210 * (line-310)/166)))
            centered(textdraw, text, y, 25, WHITE, mode == 'signal')
        alpha = smooth((local - .7) / 1.3) * smooth((duration - local - .25) / .7)
        overlay.putalpha(overlay.getchannel('A').point(lambda x: int(x * alpha)))
        image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
        # Film fades are editorial; no claims about the game's frame rate.
        fade = smooth(local / (.95 if mode in ('signal', 'title') else .55))
        fade *= smooth((duration - local) / .65)
        return ImageEnhance.Brightness(image).enhance(fade)


def soundtrack(config, path):
    """Seeded stereo score: detuned drones, reversed bells, pulse and radio dust."""
    rate = 48000
    duration = sum(s['seconds'] for s in config['shots'])
    samples = round(duration * rate)
    audio = np.zeros((samples, 2), dtype=np.float32)
    rng = np.random.default_rng(config['seed'])
    for second in range(math.ceil(duration)):
        start = second * rate
        stop = min(samples, start + rate)
        t = np.arange(start, stop, dtype=np.float64) / rate
        rise = np.clip((t - duration * .24) / (duration * .53), 0, 1)
        fade = np.minimum(np.clip(t / 6, 0, 1), np.clip((duration - t) / 2, 0, 1))
        # Intentional near-silence before the final title reveal.
        hollow = np.where((t >= duration - 23) & (t < duration - 20), .08, 1)
        for channel in range(2):
            phase = channel * .6
            drone = (.11 * np.sin(2*np.pi*41.2*t + .3*np.sin(t*.19))
                     + .048 * np.sin(2*np.pi*(61.735 + .08*channel)*t)
                     + .029 * np.sin(2*np.pi*82.4*t + phase)
                     + .016 * np.sin(2*np.pi*(123.47 + .13*channel)*t))
            breath = .66 + .24 * np.sin(t * .47 + phase)
            high = .014 * rise * np.sin(2*np.pi*174.61*t + 2*np.sin(t*.3 + phase))
            # Uneven 5-beat pulse creates tension without a conventional dance beat.
            beat = np.mod(t, 2.5)
            pulse = .1 * rise * np.exp(-beat*9) * np.sin(2*np.pi*55*t)
            hiss = rng.normal(0, .002, len(t)) * (.4 + rise)
            audio[start:stop, channel] = (drone*breath + high + pulse + hiss) * fade * hollow

    def bell(at, frequency, length, gain, reverse=False, pan=.5):
        n = round(length * rate)
        t = np.arange(n) / rate
        envelope = np.exp(-t * 1.1) * np.minimum(1, t * 30)
        tone = (np.sin(2*np.pi*frequency*t) + .36*np.sin(2*np.pi*frequency*2.013*t)
                + .16*np.sin(2*np.pi*frequency*3.97*t)) * envelope * gain
        if reverse:
            tone = tone[::-1]
        i = round(at * rate)
        n = min(n, samples-i)
        audio[i:i+n, 0] += tone[:n] * math.sqrt(1-pan)
        audio[i:i+n, 1] += tone[:n] * math.sqrt(pan)

    cursor = 0
    for index, shot in enumerate(config['shots']):
        frequency = [164.81, 174.61, 246.94, 233.08][index % 4]
        if cursor > 3:
            bell(cursor - 3, frequency, 3, .13, reverse=True, pan=.25 if index % 2 else .75)
        bell(cursor + 1, frequency / 2, 5, .17, pan=.7 if index % 2 else .3)
        cursor += shot['seconds']
    # Three unanswered notes, then their altered reply.
    for at, frequency in [(3, 659.25), (5.2, 622.25), (8, 493.88), (duration-3, 659.25), (duration-1.9, 622.25)]:
        bell(at, frequency, 1.8, .065)
    audio = np.tanh(audio * 1.3)
    audio[-rate:] *= np.linspace(1, 0, rate)[:, None]
    pcm = (audio * 27000).astype('<i2')
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm.tobytes())
    return {'sample_rate': rate, 'samples': samples, 'peak_dbfs': float(20*np.log10(np.max(np.abs(pcm.astype(float)))/32768))}


def git_info(root):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
    return {'commit': git('rev-parse', 'HEAD'), 'working_tree': git('status', '--short')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--edit', type=Path, default=HERE / 'edit.json')
    parser.add_argument('--source-root', type=Path, default=ROOT, help='Astra checkout whose current assets should be used')
    parser.add_argument('--out', type=Path, default=ROOT / '.tmp' / 'astra-trailer-90s')
    parser.add_argument('--footage', type=Path, default=ROOT / '.tmp/astra-gameplay/sources.json')
    parser.add_argument('--preview', action='store_true', help='Render storyboard only')
    args = parser.parse_args()
    config = json.loads(args.edit.read_text())
    score_path = args.edit.parent / config['score']
    score = json.loads(score_path.read_text())
    duration = sum(s['seconds'] for s in config['shots'])
    if duration != config['duration']:
        raise ValueError(f'The trailer must be exactly {config["duration"]} seconds, got {duration}')
    if sum(cue['seconds'] for cue in score['shots']) < duration:
        raise ValueError('Locked score must cover the full picture duration')
    fps = config['fps']
    for shot in config['shots']:
        if shot['seconds'] <= 0 or shot['seconds'] * fps != int(shot['seconds'] * fps):
            raise ValueError('Shot durations must be positive whole frame counts')
    args.out.mkdir(parents=True, exist_ok=True)
    capture = json.loads(args.footage.read_text())
    footage = {key: args.footage.parent / value['video'] for key, value in capture['clips'].items()}
    for key, path in footage.items():
        if digest(path) != capture['clips'][key]['sha256']:
            raise ValueError(f'Gameplay source hash mismatch: {path}')
    renderer = Renderer(config, args.source_root, footage)
    sheet = Image.new('RGB', (320 * 4, 202 * math.ceil(len(config['shots']) / 4)), INK)
    cursor = 0
    timeline = []
    for i, shot in enumerate(config['shots']):
        image = renderer.frame(shot, shot['seconds'] * .55, cursor + shot['seconds'] * .55, i)
        x, y = (i % 4) * 320, (i // 4) * 202
        sheet.paste(image.resize((320, 180), Image.Resampling.LANCZOS), (x, y))
        ImageDraw.Draw(sheet).text((x+8, y+184), f'{cursor//60:02d}:{cursor%60:02d} / {shot["mode"]}', font=font(10), fill=CYAN)
        timeline.append({**shot, 'start': cursor, 'start_frame': cursor * fps, 'frames': shot['seconds'] * fps})
        cursor += shot['seconds']
    sheet.save(args.out / 'storyboard.jpg', quality=92)
    if args.preview:
        print(args.out / 'storyboard.jpg')
        return
    audio_path = args.out / 'signal-score.wav'
    audio_info = soundtrack(score, audio_path)
    audio_info.update(mode='continuous original score; gameplay audio excluded',
                      excerpt_start=0, excerpt_seconds=duration, final_fade_seconds=1,
                      score_sha256=digest(score_path), wav_sha256=digest(audio_path))
    silent = args.out / 'picture.mp4'
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pixel_format', 'rgb24',
               '-video_size', f'{W}x{H}', '-framerate', str(fps), '-i', '-', '-an',
               '-vf', f'scale={config["width"]}:{config["height"]}:flags=neighbor,setsar=1',
               '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
               '-threads', '4', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', str(silent)]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
        try:
            for i, shot in enumerate(timeline):
                print(f'{i+1:02d}/{len(timeline)} {shot["start"]:03d}s {shot["mode"]}', flush=True)
                for frame in range(shot['frames']):
                    local = frame / fps
                    image = renderer.frame(shot, local, shot['start'] + local, i)
                    encoder.stdin.write(image.tobytes())
        finally:
            encoder.stdin.close()
        if encoder.wait() != 0:
            raise RuntimeError('FFmpeg picture encoding failed')
    final = args.out / f'Astra-The-Signal-{duration}s.mp4'
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', silent, '-i', audio_path,
         '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-af',
         f'loudnorm=I=-18:TP=-2:LRA=11,afade=t=out:st={duration-1}:d=1', '-c:a', 'aac', '-b:a', '192k',
         '-ar', '48000', '-t', str(duration), '-movflags', '+faststart', '-metadata', 'title=ASTRA: LAST LIGHT — THE SIGNAL',
         '-metadata', 'comment=Animated artwork and normal-speed A500 gameplay with editorial zooms; continuous original score, no gameplay audio.', final])
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-show_streams',
                                               '-show_format', '-of', 'json', str(final)], text=True))
    video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    if int(video['nb_read_frames']) != duration * fps or abs(float(probe['format']['duration']) - duration) > .05:
        raise RuntimeError('Export failed frame-count/duration verification')
    if (video['width'], video['height']) != (config['width'], config['height']) or audio['channels'] != 2:
        raise RuntimeError('Export failed geometry/stereo verification')
    sources = {key: {'path': path, 'sha256': digest(args.source_root / path)} for key, path in config['assets'].items()}
    manifest = {'title': config['title'], 'kind': 'animated artwork and normal-speed native A500 gameplay',
                'gameplay': capture, 'gameplay_seconds': sum(s['seconds'] for s in timeline if s['mode'] == 'gameplay'),
                'duration': duration, 'fps': fps, 'source': git_info(args.source_root), 'assets': sources,
                'renderer_sha256': digest(Path(__file__)), 'edit_sha256': digest(args.edit),
                'fonts': {p.name: digest(p) for p in (HERE / 'fonts').glob('*.ttf')},
                'ffmpeg': subprocess.check_output(['ffmpeg', '-version'], text=True).splitlines()[0],
                'audio': audio_info, 'shots': timeline, 'export_sha256': digest(final), 'probe': probe}
    (args.out / 'edit-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'READY: {final} / {duration}s / {duration*fps} frames', flush=True)


if __name__ == '__main__':
    main()
