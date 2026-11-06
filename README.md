# Mentivio

Understand visually. Learn in any language.

This project renders a local educational video for:
- Board: CBSE
- Class: 10
- Subject: Mathematics
- Chapter: Triangles
- Topic: Similar Triangles and Basic Proportionality Theorem (BPT)

## Local requirements

- Python 3.12+
- FFmpeg and FFprobe in PATH
- Windows local speech voices (for offline TTS fallback)

## Install

```powershell
cd C:\SourceCode\Mentivio
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run the local desktop app

```powershell
cd C:\SourceCode\Mentivio
.\.venv\Scripts\python.exe -m app.mentivio_app
```

## Render from CLI (quick verification)

```powershell
cd C:\SourceCode\Mentivio
.\.venv\Scripts\python.exe -m app.render_lesson --language English --subtitle-language English --fps 24
```

## Outputs

The renderer writes artifacts to `output/lesson_bpt/`:
- `mentivio_bpt_lesson_with_audio.mp4`
- `mentivio_bpt_lesson.srt` or `mentivio_bpt_lesson_telugu.srt`
- `lesson_script.json`
- `scene_breakdown.json`
- `validation_report.json`

## Notes

- Telugu narration uses a genuine local Telugu voice only if present.
- If Telugu voice is not installed, narration falls back to English and this is explicitly reported in `validation_report.json`.
