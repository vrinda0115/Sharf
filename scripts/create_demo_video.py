"""Create a two-minute SHARF prototype demo video.

The video is generated from validated app data so the demonstration can be
recreated without manual screen recording tools.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
APP_DATA = ROOT / "UI" / "prototype" / "data" / "app_data.js"
OUTPUT_DIR = ROOT / "videos"
FRAME_DIR = OUTPUT_DIR / "demo_frames"
OUTPUT_FILE = OUTPUT_DIR / "sharf_prototype_demo.mp4"

WIDTH = 1280
HEIGHT = 720
FPS = 24
SECONDS_PER_SLIDE = 10


def load_data() -> dict:
    text = APP_DATA.read_text(encoding="utf-8")
    json_text = text.removeprefix("window.SHARF_APP_DATA = ").rstrip().rstrip(";")
    return json.loads(json_text)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


TITLE = font(42, True)
SUBTITLE = font(24)
BODY = font(22)
SMALL = font(18)
LABEL = font(16, True)


def draw_text_box(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fill: str, size: int = 22) -> None:
    x, y = xy
    line = ""
    selected_font = font(size)
    max_width = 540
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=selected_font) <= max_width:
            line = trial
        else:
            draw.text((x, y), line, fill=fill, font=selected_font)
            y += size + 8
            line = word
    if line:
        draw.text((x, y), line, fill=fill, font=selected_font)


def card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str, value: str, accent: str) -> None:
    draw.rounded_rectangle(box, radius=8, fill="#ffffff", outline="#d9ded9", width=2)
    x1, y1, _, _ = box
    draw.text((x1 + 24, y1 + 22), title.upper(), fill="#68736f", font=LABEL)
    draw.text((x1 + 24, y1 + 58), value, fill=accent, font=TITLE)


def shell(title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#f4f6f3")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 250, HEIGHT), fill="#16221e")
    draw.rounded_rectangle((28, 32, 76, 80), radius=8, fill="#f0b95f")
    draw.text((45, 38), "S", fill="#16221e", font=TITLE)
    draw.text((92, 34), "SHARF", fill="#ffffff", font=font(26, True))
    draw.text((92, 66), "Founder cockpit", fill="#b9c5bf", font=SMALL)
    draw.rounded_rectangle((24, 132, 226, 178), radius=8, fill="#24342f")
    draw.text((44, 144), "Portfolio", fill="#ffffff", font=BODY)
    draw.text((44, 204), "Startup cockpit", fill="#dbe6df", font=BODY)
    draw.rounded_rectangle((24, 580, 226, 676), radius=8, outline="#3a4d45", width=2)
    draw.text((42, 600), "DATA VALIDATION", fill="#b9c5bf", font=LABEL)
    draw.text((42, 628), "17/17 checks passed", fill="#ffffff", font=BODY)
    draw.text((292, 40), title, fill="#19201d", font=TITLE)
    draw_text_box(draw, (294, 96), subtitle, "#43504b", 22)
    return image, draw


def risk_color(tier: str) -> str:
    return {"Critical": "#b93f35", "Watch": "#b77718", "Stable": "#25745c"}.get(tier, "#277c86")


def draw_portfolio_table(draw: ImageDraw.ImageDraw, companies: list[dict], top: int = 322) -> None:
    headers = ["Startup", "Stage", "Score", "Runway", "6-mo cashout", "Focus"]
    xs = [294, 548, 690, 800, 930, 1080]
    draw.rounded_rectangle((280, top - 48, 1238, 682), radius=8, fill="#ffffff", outline="#d9ded9", width=2)
    draw.text((304, top - 26), "Portfolio triage table", fill="#19201d", font=font(24, True))
    for x, header in zip(xs, headers):
        draw.text((x, top + 20), header.upper(), fill="#68736f", font=LABEL)
    y = top + 58
    for company in companies[:6]:
        draw.line((294, y - 12, 1220, y - 12), fill="#d9ded9", width=1)
        draw.text((xs[0], y), company["startup_name"], fill="#19201d", font=SMALL)
        draw.text((xs[1], y), company["stage"], fill="#19201d", font=SMALL)
        draw.text((xs[2], y), str(company["sharf_score"]), fill=risk_color(company["risk_tier"]), font=font(20, True))
        draw.text((xs[3], y), f"{company['runway_months']} mo.", fill="#19201d", font=SMALL)
        draw.text((xs[4], y), f"{company['forecast']['probability_cashout_6mo'] * 100:.1f}%", fill="#19201d", font=SMALL)
        draw.text((xs[5], y), company["remediation_priority"], fill="#19201d", font=SMALL)
        y += 52


def draw_trend(draw: ImageDraw.ImageDraw, company: dict) -> None:
    box = (282, 316, 820, 650)
    draw.rounded_rectangle(box, radius=8, fill="#ffffff", outline="#d9ded9", width=2)
    draw.text((306, 338), "Score and runway history", fill="#19201d", font=font(24, True))
    left, top, right, bottom = 322, 400, 790, 610
    for index in range(5):
        y = top + index * ((bottom - top) // 4)
        draw.line((left, y, right, y), fill="#d9ded9", width=1)
    history = company["history"]
    runway_max = max(36, *(point["runway_months"] for point in history))

    def points(values: list[float], max_value: float) -> list[tuple[float, float]]:
        result = []
        for idx, value in enumerate(values):
            x = left + idx * ((right - left) / (len(values) - 1))
            y = bottom - (value / max_value) * (bottom - top)
            result.append((x, y))
        return result

    draw.line(points([point["sharf_score"] for point in history], 100), fill="#25745c", width=4)
    draw.line(points([point["runway_months"] for point in history], runway_max), fill="#277c86", width=4)
    draw.text((322, 624), history[0]["month"][:7], fill="#68736f", font=SMALL)
    draw.text((724, 624), history[-1]["month"][:7], fill="#68736f", font=SMALL)


def slide_images(data: dict) -> list[Image.Image]:
    companies = data["companies"]
    priority = companies[0]
    stable = next(company for company in reversed(companies) if company["risk_tier"] == "Stable")
    slides = []

    image, draw = shell(
        "SHARF application prototype",
        "A two-screen founder dashboard built on validated synthetic startup-month data and Monte Carlo risk forecasts.",
    )
    card(draw, (292, 220, 520, 340), "Startups", str(data["meta"]["startup_count"]), "#25745c")
    card(draw, (548, 220, 776, 340), "Months", str(data["meta"]["observation_months"]), "#277c86")
    card(draw, (804, 220, 1032, 340), "Validation", "17/17", "#25745c")
    card(draw, (292, 380, 520, 500), "Forecast", "6 mo.", "#b77718")
    draw_text_box(draw, (548, 392), "The app turns score, runway, churn, CAC payback, sentiment, team capacity, and governance into founder-ready decisions.", "#19201d", 26)
    slides.append(image)

    image, draw = shell(
        "Screen 1: Portfolio overview",
        "The first screen gives a fast operating review across all 18 startups.",
    )
    card(draw, (292, 180, 520, 300), "Average score", str(data["portfolio"]["average_sharf_score"]), "#25745c")
    card(draw, (548, 180, 776, 300), "Average runway", f"{data['portfolio']['average_runway_months']} mo.", "#277c86")
    card(draw, (804, 180, 1032, 300), "Priority reviews", str(data["portfolio"]["high_risk_count"]), "#b93f35")
    draw_portfolio_table(draw, companies)
    slides.append(image)

    image, draw = shell(
        "Validated data is visible in the product",
        "The sidebar surfaces the validation result directly so users know the prototype is connected to checked data.",
    )
    draw.rounded_rectangle((292, 210, 620, 420), radius=8, fill="#ffffff", outline="#d9ded9", width=2)
    draw.text((320, 245), "Validation summary", fill="#19201d", font=font(28, True))
    draw.text((320, 300), "17/17 checks passed", fill="#25745c", font=font(34, True))
    draw_text_box(draw, (320, 360), "Schema, uniqueness, missingness, ranges, formulas, referential integrity, and Monte Carlo outputs all passed.", "#43504b", 22)
    draw.rounded_rectangle((680, 210, 1160, 420), radius=8, fill="#ffffff", outline="#d9ded9", width=2)
    draw.text((710, 245), "Sources", fill="#19201d", font=font(28, True))
    for index, source in enumerate(data["meta"]["generated_from"], start=1):
        draw.text((710, 290 + index * 34), source, fill="#43504b", font=SMALL)
    slides.append(image)

    image, draw = shell(
        "Portfolio triage supports fast filtering",
        "Risk tier filters let a founder or advisor move from a full portfolio to urgent companies.",
    )
    draw.rounded_rectangle((292, 190, 450, 238), radius=8, fill="#ffffff", outline="#d9ded9", width=2)
    draw.text((330, 202), "All", fill="#19201d", font=BODY)
    draw.rounded_rectangle((468, 190, 650, 238), radius=8, fill="#ffe6e3", outline="#b93f35", width=2)
    draw.text((505, 202), "Critical", fill="#b93f35", font=BODY)
    draw_portfolio_table(draw, [company for company in companies if company["risk_tier"] == "Critical"])
    slides.append(image)

    image, draw = shell(
        "Priority review card",
        "The portfolio screen also names the most urgent company and the reason for attention.",
    )
    draw.rounded_rectangle((292, 200, 1040, 510), radius=8, fill="#ffffff", outline="#d9ded9", width=2)
    draw.text((326, 238), priority["startup_name"], fill="#19201d", font=font(36, True))
    draw.text((326, 292), f"{priority['stage']} | {priority['industry']} | {priority['region']}", fill="#68736f", font=BODY)
    draw.text((326, 350), f"{priority['risk_tier']} risk", fill=risk_color(priority["risk_tier"]), font=font(34, True))
    draw_text_box(draw, (326, 410), f"{priority['burn_recommendation']}. {priority['fundraising_readiness']}. Focus area: {priority['remediation_priority']}.", "#19201d", 24)
    slides.append(image)

    image, draw = shell(
        "Screen 2: Startup cockpit",
        "Selecting a startup opens a focused operating view with current score, runway, forecast risk, and decision recommendations.",
    )
    draw.rounded_rectangle((292, 180, 1138, 286), radius=8, fill="#eef6f4", outline="#d9ded9", width=2)
    draw.text((320, 206), priority["startup_name"], fill="#19201d", font=font(34, True))
    draw.text((320, 252), f"{priority['stage']} | {priority['industry']} | {priority['region']}", fill="#43504b", font=BODY)
    card(draw, (292, 330, 520, 450), "Current score", str(priority["sharf_score"]), "#b93f35")
    card(draw, (548, 330, 776, 450), "Runway", f"{priority['runway_months']} mo.", "#b77718")
    card(draw, (804, 330, 1032, 450), "6-mo score", str(priority["forecast"]["expected_score_6mo"]), "#b93f35")
    card(draw, (292, 490, 520, 610), "Runway risk", f"{priority['forecast']['probability_runway_under_6mo'] * 100:.1f}%", "#b93f35")
    slides.append(image)

    image, draw = shell(
        "Trend chart explains the current call",
        "The cockpit keeps twelve months of score and runway history beside the recommendation.",
    )
    draw_trend(draw, priority)
    draw.rounded_rectangle((858, 316, 1194, 650), radius=8, fill="#ffffff", outline="#d9ded9", width=2)
    draw.text((884, 344), "Decision queue", fill="#19201d", font=font(26, True))
    draw_text_box(draw, (884, 398), f"Burn: {priority['burn_recommendation']}", "#19201d", 22)
    draw_text_box(draw, (884, 478), f"Fundraising: {priority['fundraising_readiness']}", "#19201d", 22)
    draw_text_box(draw, (884, 558), f"Forecast: {priority['forecast']['risk_label']}", "#19201d", 22)
    slides.append(image)

    image, draw = shell(
        "Forecast output is decision-oriented",
        "The app uses the Monte Carlo summary as probabilities, not false certainty.",
    )
    card(draw, (292, 210, 560, 340), "Cashout probability", f"{priority['forecast']['probability_cashout_6mo'] * 100:.1f}%", "#b93f35")
    card(draw, (592, 210, 860, 340), "Critical risk", f"{priority['forecast']['probability_critical_risk_6mo'] * 100:.1f}%", "#b93f35")
    card(draw, (892, 210, 1160, 340), "Simulations", f"{priority['forecast']['simulation_count']:,}", "#277c86")
    draw_text_box(draw, (294, 410), "This supports practical founder questions: hold spend, reduce burn, prepare outreach, or prioritize a remediation area before fundraising.", "#19201d", 28)
    slides.append(image)

    image, draw = shell(
        "A stable company still gets context",
        "The same cockpit can compare a healthier company without changing the workflow.",
    )
    draw.rounded_rectangle((292, 198, 1140, 304), radius=8, fill="#eef6f4", outline="#d9ded9", width=2)
    draw.text((320, 224), stable["startup_name"], fill="#19201d", font=font(34, True))
    draw.text((320, 268), f"{stable['stage']} | {stable['industry']} | {stable['region']}", fill="#43504b", font=BODY)
    card(draw, (292, 350, 520, 470), "Current score", str(stable["sharf_score"]), "#25745c")
    card(draw, (548, 350, 776, 470), "Runway", f"{stable['runway_months']} mo.", "#25745c")
    card(draw, (804, 350, 1032, 470), "Cashout", f"{stable['forecast']['probability_cashout_6mo'] * 100:.1f}%", "#25745c")
    draw_text_box(draw, (294, 540), f"Recommended action: {stable['burn_recommendation']}. {stable['fundraising_readiness']}.", "#19201d", 24)
    slides.append(image)

    image, draw = shell(
        "Prototype implementation",
        "The submission includes the app code, the data transform, validated source data, and this generated demonstration video.",
    )
    files = [
        "UI/prototype/index.html",
        "UI/prototype/app.js",
        "UI/prototype/styles.css",
        "scripts/prepare_app_data.py",
        "scripts/create_demo_video.py",
        "data/final/*",
    ]
    for index, item in enumerate(files):
        draw.rounded_rectangle((302, 178 + index * 68, 1030, 226 + index * 68), radius=8, fill="#ffffff", outline="#d9ded9", width=2)
        draw.text((330, 188 + index * 68), item, fill="#19201d", font=BODY)
    slides.append(image)

    image, draw = shell(
        "Demo path for reviewers",
        "Open the prototype, scan portfolio health, filter risk tiers, pick a startup, and review score/runway trend plus recommended action.",
    )
    steps = [
        "1. Open UI/prototype/index.html",
        "2. Confirm validation badge: All checks passed",
        "3. Review portfolio metrics and triage table",
        "4. Select a company to open Startup cockpit",
        "5. Use forecast probabilities to decide the next operating move",
    ]
    for index, step in enumerate(steps):
        draw.text((310, 200 + index * 72), step, fill="#19201d", font=font(28, True))
    slides.append(image)

    image, draw = shell(
        "First prototype delivered",
        "The app is intentionally small: two screens, validated data, and founder-facing decisions. It is ready for feedback and iteration.",
    )
    draw_text_box(draw, (312, 260), "Next natural additions would be editable assumptions, saved action logs, and a richer simulation-path explorer.", "#19201d", 30)
    slides.append(image)

    return slides


def write_frames(slides: list[Image.Image]) -> None:
    if FRAME_DIR.exists():
        shutil.rmtree(FRAME_DIR)
    FRAME_DIR.mkdir(parents=True)
    frame_number = 0
    frames_per_slide = FPS * SECONDS_PER_SLIDE
    for slide in slides:
        for _ in range(frames_per_slide):
            slide.save(FRAME_DIR / f"frame_{frame_number:05d}.png")
            frame_number += 1


def encode_video() -> None:
    command = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        str(FRAME_DIR / "frame_%05d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(OUTPUT_FILE),
    ]
    subprocess.run(command, check=True)


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    slides = slide_images(load_data())
    write_frames(slides)
    encode_video()
    shutil.rmtree(FRAME_DIR)
    print(f"Wrote {OUTPUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
