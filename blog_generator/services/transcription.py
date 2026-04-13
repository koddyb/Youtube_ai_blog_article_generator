import glob as glob_module
import http.cookiejar
import logging
import os
import re
import subprocess
import tempfile

import requests

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
)

from .youtube import extract_video_id, get_cookies_path

logger = logging.getLogger(__name__)


def get_transcription(link: str) -> str | None:
    """Récupère la transcription avec stratégie multi-fallback.

    Stratégie : youtube-transcript-api → yt-dlp (meilleur anti-bot).
    """
    video_id = extract_video_id(link)
    if not video_id:
        return None

    logger.info(f"[Transcription] Essai youtube-transcript-api pour {video_id}")
    result = _get_transcription_api(video_id)
    if result:
        logger.info("[Transcription] Succès via youtube-transcript-api")
        return result

    logger.info(f"[Transcription] Fallback yt-dlp pour {video_id}")
    result = _get_transcription_ytdlp(video_id)
    if result:
        logger.info("[Transcription] Succès via yt-dlp")
        return result

    logger.warning(f"[Transcription] Échec total pour {video_id}")
    return None


def _get_transcription_api(video_id: str) -> str | None:
    """Récupère la transcription via youtube-transcript-api."""
    cookies_path = get_cookies_path()

    # v1.2.x : cookies via http_client (requests.Session)
    api_kwargs = {}
    if cookies_path:
        cj = http.cookiejar.MozillaCookieJar(cookies_path)
        try:
            cj.load(ignore_discard=True, ignore_expires=True)
            session = requests.Session()
            session.cookies = cj
            api_kwargs['http_client'] = session
        except Exception as e:
            logger.warning(f"[transcript-api] Impossible de charger les cookies: {e}")

    api = YouTubeTranscriptApi(**api_kwargs)

    try:
        data = api.fetch(video_id, languages=['fr', 'en'])
        return " ".join([s.text for s in data])
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        logger.warning(f"[transcript-api] Pas de transcript pour {video_id}: {e}")
    except Exception as e:
        logger.error(f"[transcript-api] Erreur fetch pour {video_id}: {type(e).__name__}: {e}")

    # Fallback : lister toutes les langues disponibles
    try:
        transcript_list = api.list(video_id)
        transcripts = list(transcript_list)
        if not transcripts:
            logger.warning(f"[transcript-api] Aucune langue disponible pour {video_id}")
            return None
        data = transcripts[0].fetch()
        return " ".join([s.text for s in data])
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        logger.warning(f"[transcript-api] Transcripts désactivés pour {video_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"[transcript-api] Erreur list/fallback pour {video_id}: {type(e).__name__}: {e}")
        return None


def _get_transcription_ytdlp(video_id: str) -> str | None:
    """Récupère la transcription via yt-dlp (meilleur contournement anti-bot)."""
    url = f"https://www.youtube.com/watch?v={video_id}"

    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            'yt-dlp',
            '--skip-download',
            '--write-subs',
            '--write-auto-subs',
            '--sub-langs', 'fr,en,fr.*,en.*',
            '--sub-format', 'vtt',
            '--no-warnings',
            '--no-check-formats',
            '--ignore-errors',
            '--ignore-no-formats-error',
            '-o', os.path.join(tmpdir, '%(id)s'),
        ]

        cookies_path = get_cookies_path()
        if cookies_path:
            cmd.extend(['--cookies', cookies_path])

        cmd.append(url)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                logger.info(f"yt-dlp returncode={result.returncode}, checking for subtitle files anyway")
                if result.stderr:
                    logger.info(f"yt-dlp stderr: {result.stderr[:500]}")
        except subprocess.TimeoutExpired:
            logger.warning("yt-dlp timeout")
            return None
        except FileNotFoundError:
            logger.error("yt-dlp not found in PATH")
            return None

        # Chercher les fichiers de sous-titres générés
        sub_files = glob_module.glob(os.path.join(tmpdir, '*.vtt'))
        if not sub_files:
            sub_files = glob_module.glob(os.path.join(tmpdir, '*.srt'))
        if not sub_files:
            logger.warning(f"yt-dlp n'a produit aucun fichier de sous-titres pour {video_id}")
            return None

        # Préférer fr > en > premier disponible
        chosen = sub_files[0]
        for sf in sub_files:
            if '.fr.' in sf:
                chosen = sf
                break
            elif '.en.' in sf:
                chosen = sf

        return _parse_vtt(chosen)


def _parse_vtt(filepath: str) -> str | None:
    """Parse un fichier VTT/SRT et retourne le texte brut sans doublons."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    text_lines = []
    seen = set()

    for line in lines:
        line = line.strip()
        if not line or line == 'WEBVTT' or '-->' in line or line.startswith('NOTE'):
            continue
        if re.match(r'^\d+$', line):
            continue
        clean = re.sub(r'<[^>]+>', '', line).strip()
        if clean and clean not in seen:
            seen.add(clean)
            text_lines.append(clean)

    return ' '.join(text_lines) if text_lines else None
