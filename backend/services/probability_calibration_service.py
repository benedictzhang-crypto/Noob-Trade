from statistics import mean


def build_probability_calibration_summary(matches, sample_limit=20):
    scores = []
    for match in matches or []:
        try:
            score = float(match.get("matchScore", 0) or 0)
        except (TypeError, ValueError):
            continue
        if score > 0:
            scores.append(max(0.0, min(score, 100.0)))

    selected_scores = sorted(scores, reverse=True)[:max(1, int(sample_limit or 20))]
    if not selected_scores:
        return None

    top_ten_scores = selected_scores[:10]
    return {
        "method": "similarity_weighted_v1",
        "sampleSize": len(selected_scores),
        "top1Similarity": round(selected_scores[0], 2),
        "top10AverageSimilarity": round(mean(top_ten_scores), 2),
    }
