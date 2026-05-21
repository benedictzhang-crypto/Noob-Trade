from pathlib import Path

from app import app
from models.auth import AssistantIntentFeedback


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "assistant_nlu" / "data" / "generated_feedback.yml"


def _escape_example(text):
    return str(text or "").replace("\n", " ").strip()


def export_feedback():
    grouped = {}
    with app.app_context():
        rows = (
            AssistantIntentFeedback.query
            .order_by(AssistantIntentFeedback.created_at.asc())
            .all()
        )

        for row in rows:
            intent = row.corrected_intent or row.predicted_intent
            transcript = _escape_example(row.transcript)
            if not intent or intent == "unknown" or not transcript:
                continue
            grouped.setdefault(intent, [])
            if transcript not in grouped[intent]:
                grouped[intent].append(transcript)

    lines = [
        'version: "3.1"',
        "",
    ]
    if not grouped:
        lines.append("nlu: []")
    else:
        lines.append("nlu:")
        for intent in sorted(grouped):
            lines.append(f"  - intent: {intent}")
            lines.append("    examples: |")
            for example in grouped[intent]:
                lines.append(f"      - {example}")
            lines.append("")

    OUTPUT_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return OUTPUT_PATH


if __name__ == "__main__":
    output_path = export_feedback()
    print(f"Exported assistant feedback to {output_path}")
