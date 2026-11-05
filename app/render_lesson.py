import argparse
import json

from app.lesson_engine import render_lesson


def main():
    parser = argparse.ArgumentParser(description="Render Mentivio BPT lesson locally.")
    parser.add_argument("--language", default="English", choices=["English", "Telugu"])
    parser.add_argument("--subtitle-language", default="English", choices=["English", "Telugu"])
    parser.add_argument("--fps", type=int, default=24)
    args = parser.parse_args()

    result = render_lesson(language=args.language, subtitle_language=args.subtitle_language, fps=args.fps)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

