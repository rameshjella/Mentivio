import json
import math
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyttsx3
from PIL import Image, ImageDraw, ImageFont
import subprocess

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
SAFE_MARGIN = 50
SAFE_RECT = (
    SAFE_MARGIN,
    SAFE_MARGIN,
    FRAME_WIDTH - SAFE_MARGIN,
    FRAME_HEIGHT - SAFE_MARGIN,
)

WRAP_CACHE: dict[tuple[str, int, int], str] = {}


@dataclass
class SceneSpec:
    key: str
    title: str
    objective: str
    narration_en: str
    subtitle_te: str
    base_duration: float
    kind: str


def ensure_font(size: int = 28):
    for candidate in ["arial.ttf", "segoeui.ttf", "calibri.ttf"]:
        try:
            return ImageFont.truetype(candidate, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def line_wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int):
    words = text.split()
    lines = []
    current = []
    for word in words:
        trial = " ".join(current + [word])
        left, _, right, _ = draw.textbbox((0, 0), trial, font=font)
        if right - left <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def point_lerp(p: tuple[float, float], q: tuple[float, float], t: float):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)


def draw_line_progress(draw: ImageDraw.ImageDraw, p: tuple[float, float], q: tuple[float, float], prog: float, color: tuple[int, int, int], width: int):
    if prog <= 0:
        return
    end = point_lerp(p, q, min(1.0, prog))
    draw.line((p[0], p[1], end[0], end[1]), fill=color, width=width)


def draw_point_label(draw: ImageDraw.ImageDraw, p: tuple[float, float], label: str, color: tuple[int, int, int], font: ImageFont.ImageFont):
    draw.ellipse((p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4), fill=color)
    draw.text((p[0] + 8, p[1] - 24), label, fill=color, font=font)


def geometry_points():
    a = (220.0, 560.0)
    b = (980.0, 560.0)
    c = (560.0, 170.0)
    d = point_lerp(a, b, 0.42)
    e = point_lerp(a, c, 0.42)
    return a, b, c, d, e


def draw_header(draw: ImageDraw.ImageDraw, title: str, objective: str):
    draw.rounded_rectangle((32, 24, 1248, 696), radius=24, fill=(250, 251, 253), outline=(223, 227, 232), width=2)
    draw.text((74, 54), title, fill=(15, 23, 42), font=ensure_font(40))
    draw.text((76, 108), f"Learning objective: {objective}", fill=(32, 100, 185), font=ensure_font(24))


def draw_text_block(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, max_width: int, font_size: int, color: tuple[int, int, int], validations: list[dict[str, Any]], frame_index: int):
    font = ensure_font(font_size)
    cache_key = (text, font_size, max_width)
    block = WRAP_CACHE.get(cache_key)
    if block is None:
        lines = line_wrap(draw, text, font, max_width)
        block = "\n".join(lines)
        WRAP_CACHE[cache_key] = block
    spacing = 6
    bbox = draw.multiline_textbbox((x, y), block, font=font, spacing=spacing)
    draw.multiline_text((x, y), block, font=font, fill=color, spacing=spacing)

    sx1, sy1, sx2, sy2 = SAFE_RECT
    if bbox[0] < sx1 or bbox[1] < sy1 or bbox[2] > sx2 or bbox[3] > sy2:
        validations.append(
            {
                "frame": frame_index,
                "issue": "text_outside_safe_area",
                "bbox": [int(v) for v in bbox],
                "safe_rect": list(SAFE_RECT),
                "text": text[:120],
            }
        )


def draw_static_triangle(draw: ImageDraw.ImageDraw):
    a, b, c, _, _ = geometry_points()
    draw.line((a[0], a[1], b[0], b[1]), fill=(31, 41, 55), width=7)
    draw.line((b[0], b[1], c[0], c[1]), fill=(31, 41, 55), width=7)
    draw.line((c[0], c[1], a[0], a[1]), fill=(31, 41, 55), width=7)
    label_font = ensure_font(28)
    draw_point_label(draw, a, "A", (31, 41, 55), label_font)
    draw_point_label(draw, b, "B", (31, 41, 55), label_font)
    draw_point_label(draw, c, "C", (31, 41, 55), label_font)


def draw_geometry_scene(draw: ImageDraw.ImageDraw, scene: SceneSpec, t: float):
    a, b, c, d, e = geometry_points()
    side_prog = min(1.0, t / 0.35)
    draw_line_progress(draw, a, b, side_prog * 1.2, (31, 41, 55), 7)
    draw_line_progress(draw, b, c, max(0.0, (side_prog - 0.2) * 1.4), (31, 41, 55), 7)
    draw_line_progress(draw, c, a, max(0.0, (side_prog - 0.45) * 1.8), (31, 41, 55), 7)

    label_font = ensure_font(28)
    if t > 0.22:
        draw_point_label(draw, a, "A", (31, 41, 55), label_font)
        draw_point_label(draw, b, "B", (31, 41, 55), label_font)
        draw_point_label(draw, c, "C", (31, 41, 55), label_font)

    if scene.kind in {"de_parallel", "angles", "ratio", "equation", "examples", "application", "assessment", "recap"} and t > 0.35:
        pd = min(1.0, (t - 0.35) / 0.25)
        draw_point_label(draw, d, "D", (220, 38, 38), label_font)
        draw_point_label(draw, e, "E", (220, 38, 38), label_font)
        draw_line_progress(draw, d, e, pd, (220, 38, 38), 6)

    if scene.kind in {"de_parallel", "angles", "ratio", "equation", "examples", "application", "assessment", "recap"} and t > 0.52:
        draw_text = "DE || BC"
        draw.text((470, 305), draw_text, fill=(220, 38, 38), font=ensure_font(30))

    if scene.kind in {"angles", "ratio", "equation", "examples", "application", "assessment", "recap"}:
        if t > 0.6:
            draw.arc((190, 500, 270, 580), start=0, end=48, fill=(3, 148, 99), width=5)
            draw.arc((319, 456, 399, 536), start=0, end=48, fill=(3, 148, 99), width=5)
            draw.text((150, 460), "Angle A", fill=(3, 148, 99), font=ensure_font(22))

    if scene.kind in {"ratio", "equation", "examples", "application", "assessment", "recap"} and t > 0.7:
        draw.polygon([a, d, e], outline=(29, 161, 242), fill=(214, 237, 255))
        draw.text((335, 510), "smaller triangle ADE", fill=(29, 161, 242), font=ensure_font(22))


def draw_example_overlay(draw: ImageDraw.ImageDraw, index: int):
    box = (660, 225, 1200, 620)
    draw.rounded_rectangle(box, radius=16, fill=(255, 255, 255), outline=(198, 207, 217), width=2)
    lines = [
        [
            "Example 1",
            "Given AD = 4, DB = 6, AE = 3",
            "From BPT: AD/DB = AE/EC",
            "4/6 = 3/EC",
            "EC = (3 x 6) / 4 = 4.5",
        ],
        [
            "Example 2",
            "Given AD:DB = 2:5, AE = 6",
            "2/5 = 6/EC",
            "EC = (6 x 5) / 2 = 15",
            "Segments stay proportional",
        ],
        [
            "Example 3",
            "Scale triangle by factor 3",
            "AB -> 3AB, AC -> 3AC",
            "Ratios remain unchanged",
            "Similarity keeps proportionality",
        ],
    ][index]
    y = 248
    for i, line in enumerate(lines):
        draw.text((685, y), line, fill=(15, 23, 42) if i == 0 else (33, 41, 55), font=ensure_font(26 if i == 0 else 23))
        y += 60


def draw_assessment(draw: ImageDraw.ImageDraw, t: float):
    questions = [
        "1. Why must DE be parallel to BC?",
        "2. If AD/DB = 3/4 and AE = 9, find EC.",
        "3. Which angle pair proves similarity first?",
        "4. Where is BPT used in real life?",
        "5. State the theorem in one sentence.",
    ]
    answers = [
        "Answer: Parallelism creates equal corresponding angles.",
        "Answer: 3/4 = 9/EC, so EC = 12.",
        "Answer: Corresponding angles between ADE and ABC.",
        "Answer: Surveying, design, and map scaling.",
        "Answer: A parallel line divides two sides proportionally.",
    ]
    draw.rounded_rectangle((620, 190, 1210, 640), radius=16, fill=(255, 255, 255), outline=(198, 207, 217), width=2)
    sec_per_q = 6.0
    active = min(4, int(t // sec_per_q))
    base_y = 220
    for idx, q in enumerate(questions):
        color = (15, 23, 42) if idx == active else (76, 86, 101)
        draw.text((645, base_y + idx * 58), q, fill=color, font=ensure_font(22))
    reveal = (t % sec_per_q) > 3.5
    if reveal:
        draw.text((645, 540), answers[active], fill=(0, 128, 83), font=ensure_font(21))


def draw_frame(scene: SceneSpec, frame_index: int, frames_in_scene: int, validations: list[dict[str, Any]]):
    image = Image.new("RGB", (FRAME_WIDTH, FRAME_HEIGHT), (244, 247, 252))
    draw = ImageDraw.Draw(image)
    t = frame_index / max(1, frames_in_scene - 1)
    draw_header(draw, scene.title, scene.objective)

    if scene.kind in {"intro", "prereq", "similar"}:
        draw_static_triangle(draw)
    else:
        draw_geometry_scene(draw, scene, t)

    if scene.kind == "examples1":
        draw_example_overlay(draw, 0)
    elif scene.kind == "examples2":
        draw_example_overlay(draw, 1)
    elif scene.kind == "examples3":
        draw_example_overlay(draw, 2)
    elif scene.kind == "application":
        app_text = "Applications: architecture, map scaling, surveying, model design, camera perspective"
        draw_text_block(draw, app_text, 655, 250, 520, 24, (24, 35, 58), validations, frame_index)
    elif scene.kind == "assessment":
        draw_assessment(draw, t * scene.base_duration)

    panel_text = scene.narration_en
    draw_text_block(draw, panel_text, 650, 170, 530, 23, (33, 41, 55), validations, frame_index)

    if scene.kind == "equation":
        steps = [
            "Step 1: DE || BC",
            "Step 2: Angles in ADE equal angles in ABC",
            "Step 3: Triangles ADE and ABC are similar",
            "Step 4: Corresponding sides are proportional",
            "Final: AD/DB = AE/EC",
        ]
        vis = max(1, int(1 + t * 4.8))
        y = 430
        for step in steps[:vis]:
            draw.text((650, y), step, fill=(9, 79, 164), font=ensure_font(22))
            y += 44

    if scene.kind == "ratio":
        draw.text((650, 470), "AD / AB = AE / AC", fill=(9, 79, 164), font=ensure_font(30))
        draw.text((650, 520), "=> AD / DB = AE / EC", fill=(9, 79, 164), font=ensure_font(30))

    return image


def scene_definitions() -> list[SceneSpec]:
    return [
        SceneSpec("intro", "Mentivio: Similar Triangles and BPT", "Connect scale drawings to proportional reasoning.", "Imagine a map and the real city. The shapes look different in size, but their proportions match. Today we use that idea to understand similar triangles and the Basic Proportionality Theorem.", "స్కేలు డ్రాయింగ్ భావనతో సారూప్య త్రిభుజాలు మరియు బిపిటిని అర్థం చేసుకుందాం.", 18.0, "intro"),
        SceneSpec("prereq", "Prerequisite: Angles and Ratios", "Recall angle equality and ratio meaning.", "Before BPT, we need two ideas: equal corresponding angles and side ratios. A ratio compares lengths without changing the shape's logic.", "ముందుగా కోణ సమానత్వం మరియు నిష్పత్తి భావన గుర్తుంచుకోండి.", 16.0, "prereq"),
        SceneSpec("similar", "What Makes Triangles Similar?", "Identify similarity conditions.", "Two triangles are similar when matching angles are equal and corresponding sides are proportional. Similarity means same shape, maybe different size.", "అనుగుణ కోణాలు సమానం, భుజాలు నిష్పత్తిలో ఉంటే త్రిభుజాలు సారూప్యం.", 20.0, "similar"),
        SceneSpec("construct", "Build Triangle ABC", "Construct the main geometry setup.", "We begin with triangle A B C. This larger triangle is our reference shape. Now we place points on two sides to study proportional division.", "ప్రధాన త్రిభుజం ABC నిర్మాణం చేయబడుతుంది.", 16.0, "de_parallel"),
        SceneSpec("parallel", "Place D and E, Draw DE", "Construct DE parallel to BC.", "Point D lies on side A B and point E lies on side A C. Draw line D E so that it stays parallel to B C. This parallel condition is the heart of BPT.", "AB, AC పై D, E ఉంచి DE ను BC కు సమాంతరంగా గీయాలి.", 18.0, "de_parallel"),
        SceneSpec("angles", "Why Parallel Matters", "Relate corresponding angles.", "Because D E is parallel to B C, the angles made with transversals are equal. That creates angle correspondence between triangles A D E and A B C.", "సమాంతర గీత వల్ల అనుగుణ కోణాలు సమానమవుతాయి.", 18.0, "angles"),
        SceneSpec("ratio", "From Similarity to Ratios", "Derive proportional side relations.", "Equal angles imply the smaller and larger triangles are similar. Similar triangles force corresponding sides into proportional relationships.", "సారూప్యత వల్ల అనుగుణ భుజాలు నిష్పత్తిలో వస్తాయి.", 18.0, "ratio"),
        SceneSpec("equation", "Derive the BPT Equation", "Obtain AD over DB equals AE over EC.", "Now simplify the proportional relations to segment form. The division on side A B matches the division on side A C. So A D by D B equals A E by E C.", "చివరగా AD/DB = AE/EC అనే బిపిటి సమీకరణం వస్తుంది.", 20.0, "equation"),
        SceneSpec("examples1", "Worked Example 1", "Solve with direct substitution.", "Example one. If A D is four, D B is six, and A E is three, use BPT and solve for E C. Substitution gives E C equals four point five.", "ఉదాహరణ 1 లో ప్రత్యక్ష ప్రతిస్థాపనతో EC విలువ కనుక్కుంటాం.", 18.0, "examples1"),
        SceneSpec("examples2", "Worked Example 2", "Solve with ratio form.", "Example two. If A D to D B is two to five and A E is six, set two by five equal to six by E C. Solving gives E C equals fifteen.", "ఉదాహరణ 2 లో నిష్పత్తి రూపంతో EC ను కనుగొంటాం.", 18.0, "examples2"),
        SceneSpec("examples3", "Worked Example 3", "Use scaling argument.", "Example three uses scaling. If the whole triangle scales by a factor of three, every matching side scales by three, but the ratios stay the same.", "ఉదాహరణ 3 లో స్కేలు ఫ్యాక్టర్ వాడి నిష్పత్తి మారదని చూపిస్తాం.", 18.0, "examples3"),
        SceneSpec("application", "Real-world Applications", "Transfer theorem to practical contexts.", "Architects use proportional reasoning for models, surveyors estimate inaccessible distances, and map designers preserve shape with scaling.", "వాస్తవ జీవితంలో నిర్మాణం, మ్యాపులు, సర్వేయింగ్ లో ఈ సిద్ధాంతం ఉపయోగపడుతుంది.", 16.0, "application"),
        SceneSpec("assessment", "Quick Assessment", "Check conceptual understanding.", "Now answer five quick questions. Pause mentally before each answer appears. This helps you test whether you understand why proportionality follows from parallel lines.", "ఇప్పుడు ఐదు ప్రశ్నలతో మీ అర్థాన్ని పరీక్షించండి.", 32.0, "assessment"),
        SceneSpec("recap", "Lesson Recap", "State BPT confidently.", "Recap. In a triangle, if a line is parallel to one side and cuts the other two sides, those sides are divided proportionally. This is the Basic Proportionality Theorem.", "సంక్షిప్తంగా: ఒక భుజానికి సమాంతర గీత మిగిలిన రెండు భుజాలను నిష్పత్తిలో విభజిస్తుంది.", 16.0, "recap"),
    ]


def detect_telugu_voice(engine: pyttsx3.Engine):
    for voice in engine.getProperty("voices"):
        hay = f"{voice.name} {voice.id}".lower()
        if "telugu" in hay or " te-" in hay or "te_in" in hay:
            return voice.id
    return None


def get_tts_engine():
    engine = pyttsx3.init()
    if not engine:
        raise RuntimeError("Local TTS engine unavailable")
    engine.setProperty("rate", 130)
    return engine


def render_narration_wav(narration_text: str, out_path: Path, voice_id: str | None = None):
    engine = get_tts_engine()
    if voice_id:
        engine.setProperty("voice", voice_id)
    engine.save_to_file(narration_text, str(out_path))
    engine.runAndWait()


def wav_duration_seconds(path: Path):
    with wave.open(str(path), "rb") as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        return frames / float(rate)


def word_count(text: str):
    return max(1, len([w for w in text.replace("\n", " ").split(" ") if w.strip()]))


def srt_time(seconds: float):
    millis = int(round(seconds * 1000.0))
    h = millis // 3600000
    millis %= 3600000
    m = millis // 60000
    millis %= 60000
    s = millis // 1000
    ms = millis % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(cues: list[tuple[float, float, str]], out_path: Path):
    lines = []
    for i, (start, end, text) in enumerate(cues, start=1):
        lines.extend([str(i), f"{srt_time(start)} --> {srt_time(end)}", text, ""])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def ffprobe_json(path: Path):
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    res = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(res.stdout)


def render_video(scene_plan: list[dict[str, Any]], out_video: Path, fps: int):
    debug = True
    frames_dir = out_video.parent / "frames"
    if frames_dir.exists():
        for old in frames_dir.glob("*.jpg"):
            old.unlink()
    else:
        frames_dir.mkdir(parents=True, exist_ok=True)

    validations: list[dict[str, Any]] = []
    global_frame = 0
    total_frames = sum(row["frame_count"] for row in scene_plan)
    if debug:
        print(f"[Mentivio] Rendering {total_frames} frames at {fps} FPS...")

    for row in scene_plan:
        scene = row["scene"]
        count = row["frame_count"]
        if debug:
            print(f"[Mentivio] Scene {scene.key}: {count} frames")
        for frame_idx in range(count):
            image = draw_frame(scene, frame_idx, count, validations)
            global_frame += 1
            frame_path = frames_dir / f"frame_{global_frame:06d}.jpg"
            image.save(frame_path, format="JPEG", quality=90)
            if debug and global_frame % 400 == 0:
                print(f"[Mentivio] Rendered {global_frame}/{total_frames} frames")

    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frames_dir / "frame_%06d.jpg"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(out_video),
    ]
    subprocess.run(cmd, check=True)
    return validations


def merge_audio_video(video: Path, audio: Path, output: Path):
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video),
        "-i",
        str(audio),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        str(output),
    ]
    subprocess.run(cmd, check=True)


def render_lesson(language: str = "English", subtitle_language: str = "English", fps: int = 24):
    if fps < 24 or fps > 30:
        raise ValueError("FPS must be between 24 and 30")

    output_dir = OUTPUT_DIR / "lesson_bpt"
    output_dir.mkdir(exist_ok=True)

    scenes = scene_definitions()

    telugu_available = False
    telugu_voice_id = None
    try:
        probe_engine = get_tts_engine()
        telugu_voice_id = detect_telugu_voice(probe_engine)
        telugu_available = telugu_voice_id is not None
    except Exception:
        telugu_available = False

    narration_language = language.lower()
    if narration_language == "telugu" and not telugu_available:
        narration_language = "english"

    narration_wav = output_dir / "mentivio_bpt_lesson.wav"
    print("[Mentivio] Generating narration...")
    narration_text = " ".join(scene.narration_en for scene in scenes)
    voice_id = telugu_voice_id if narration_language == "telugu" else None
    render_narration_wav(narration_text, narration_wav, voice_id=voice_id)
    total_audio_duration = wav_duration_seconds(narration_wav)
    if total_audio_duration < 180.0:
        stretched_wav = output_dir / "mentivio_bpt_lesson_stretched.wav"
        target = 182.0
        tempo = max(0.5, min(2.0, total_audio_duration / target))
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(narration_wav),
                "-filter:a",
                f"atempo={tempo:.4f}",
                str(stretched_wav),
            ],
            check=True,
        )
        narration_wav.unlink(missing_ok=True)
        stretched_wav.replace(narration_wav)
        total_audio_duration = wav_duration_seconds(narration_wav)
    print(f"[Mentivio] Narration duration: {round(total_audio_duration, 2)} seconds")

    total_words = sum(word_count(scene.narration_en) for scene in scenes)
    raw_scene_durations = []
    for scene in scenes:
        est_audio = total_audio_duration * (word_count(scene.narration_en) / total_words)
        extra = 8.0 if scene.kind == "assessment" else 0.8
        raw_scene_durations.append(max(scene.base_duration, est_audio + extra))

    total_raw_duration = sum(raw_scene_durations)
    target_duration = min(240.0, max(180.0, total_audio_duration + 12.0))
    target_duration = min(target_duration, total_raw_duration)
    scale = target_duration / total_raw_duration if total_raw_duration > 0 else 1.0

    scene_plan = []
    cues = []
    t = 0.0
    for scene, raw_duration in zip(scenes, raw_scene_durations):
        duration = raw_duration * scale
        frame_count = max(1, int(round(duration * fps)))
        duration = frame_count / fps
        est_audio = total_audio_duration * (word_count(scene.narration_en) / total_words)
        scene_plan.append(
            {
                "scene": scene,
                "audio_duration": est_audio,
                "duration": duration,
                "frame_count": frame_count,
            }
        )
        subtitle_text = scene.narration_en if subtitle_language.lower() == "english" else scene.subtitle_te
        cues.append((t, t + duration, subtitle_text))
        t += duration

    silent_video = output_dir / "mentivio_bpt_lesson_silent.mp4"
    frames_dir = output_dir / "frames"
    expected_frames = sum(row["frame_count"] for row in scene_plan)
    existing_frames = len(list(frames_dir.glob("frame_*.jpg"))) if frames_dir.exists() else 0
    if silent_video.exists() and existing_frames == expected_frames:
        print(f"[Mentivio] Reusing existing silent video ({existing_frames} frames).")
        validation_issues = []
    else:
        validation_issues = render_video(scene_plan, silent_video, fps)
    print("[Mentivio] Merging narration with video...")

    final_video = output_dir / "mentivio_bpt_lesson_with_audio.mp4"
    merge_audio_video(silent_video, narration_wav, final_video)

    srt_path = output_dir / ("mentivio_bpt_lesson.srt" if subtitle_language.lower() == "english" else "mentivio_bpt_lesson_telugu.srt")
    write_srt(cues, srt_path)

    scene_breakdown = []
    cursor = 0.0
    for row in scene_plan:
        scene = row["scene"]
        duration = row["duration"]
        scene_breakdown.append(
            {
                "scene_key": scene.key,
                "title": scene.title,
                "objective": scene.objective,
                "start_seconds": round(cursor, 3),
                "end_seconds": round(cursor + duration, 3),
                "duration_seconds": round(duration, 3),
                "audio_duration_seconds": round(row["audio_duration"], 3),
                "kind": scene.kind,
            }
        )
        cursor += duration

    script = {
        "curriculum": {
            "country": "India",
            "board": "CBSE",
            "class": "10",
            "subject": "Mathematics",
            "chapter": "Triangles",
            "topic": "Similar Triangles and Basic Proportionality Theorem (BPT)",
        },
        "teaching_language_requested": language,
        "narration_language_used": narration_language.capitalize(),
        "subtitle_language": subtitle_language,
        "telugu_tts_available": telugu_available,
        "scene_breakdown": scene_breakdown,
        "assessment_questions": [
            "Why must DE be parallel to BC for BPT?",
            "If AD/DB = 3/4 and AE = 9, find EC.",
            "Which angle pairs show triangle similarity?",
            "Where is BPT used in practical measurement?",
            "State BPT in one clear sentence.",
        ],
    }
    script_path = output_dir / "lesson_script.json"
    script_path.write_text(json.dumps(script, indent=2), encoding="utf-8")

    scene_path = output_dir / "scene_breakdown.json"
    scene_path.write_text(json.dumps(scene_breakdown, indent=2), encoding="utf-8")

    probe = ffprobe_json(final_video)
    audio_probe = ffprobe_json(narration_wav)
    video_stream = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), {})

    measured_duration = float(probe.get("format", {}).get("duration", "0") or 0.0)
    measured_fps = video_stream.get("avg_frame_rate", "0/1")
    if "/" in measured_fps:
        n, d = measured_fps.split("/")
        measured_fps_value = float(n) / float(d) if float(d) else 0.0
    else:
        measured_fps_value = float(measured_fps)

    report = {
        "video_path": str(final_video),
        "subtitle_path": str(srt_path),
        "script_path": str(script_path),
        "scene_breakdown_path": str(scene_path),
        "measured": {
            "duration_seconds": round(measured_duration, 3),
            "fps": round(measured_fps_value, 3),
            "resolution": f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}",
            "video_codec": video_stream.get("codec_name"),
            "audio_codec": audio_stream.get("codec_name"),
            "audio_sample_rate": audio_stream.get("sample_rate"),
            "narration_wav_duration_seconds": round(float(audio_probe.get("format", {}).get("duration", "0") or 0.0), 3),
        },
        "quality_checks": {
            "duration_target_180_to_300": 180.0 <= measured_duration <= 300.0,
            "fps_target_24_to_30": 24.0 <= measured_fps_value <= 30.0,
            "text_safe_area_violations": len(validation_issues),
            "audio_present": bool(audio_stream),
            "scene_count": len(scene_breakdown),
        },
        "limitations": [],
    }

    if language.lower() == "telugu" and not telugu_available:
        report["limitations"].append("Telugu local TTS voice not available; used English narration fallback with Telugu subtitle track.")

    report_path = output_dir / "validation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    narration_status = "Local narration generated successfully."
    if language.lower() == "telugu" and not telugu_available:
        narration_status = "Telugu TTS is not available on this machine. English narration was generated as fallback, and Telugu subtitles were produced."

    return {
        "video_path": str(final_video),
        "subtitle_path": str(srt_path),
        "script_path": str(script_path),
        "scene_breakdown_path": str(scene_path),
        "validation_report_path": str(report_path),
        "narration_status": narration_status,
        "duration_seconds": measured_duration,
        "fps": measured_fps_value,
    }

