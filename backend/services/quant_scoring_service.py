from statistics import mean


class QuantScoringService:
    """Quant weighting and penalty model used by the Trade page."""

    PUBLIC_EQUAL9_PROFILE = "public_equal9"

    INDICATOR_ALIASES = {
        "PBV": "OBV",
    }

    FULL_SCORE_BY_INDICATOR = {
        "MA": 3,
        "EMA": 3,
        "MACD": 30,
        "BOLL": 30,
        "RSI": 15,
        "VOL": 15,
        "KDJ": 9,
        "OI": 9,
        "OBV": 9,
    }

    WEIGHT_BY_INDICATOR = {
        "MA": 1,
        "EMA": 1,
        "MACD": 10,
        "BOLL": 10,
        "RSI": 5,
        "VOL": 5,
        "KDJ": 3,
        "OI": 3,
        "OBV": 3,
    }

    PUBLIC_EQUAL9_INDICATOR_WEIGHTS = {
        "MA": 1.0,
        "EMA": 1.0,
        "MACD": 1.0,
        "BOLL": 1.0,
        "RSI": 1.0,
        "VOL": 1.0,
        "KDJ": 1.0,
        "OI": 1.0,
        "OBV": 1.0,
    }

    FULL_WEIGHT_SUM = sum(WEIGHT_BY_INDICATOR.values())
    MIN_ADAPTIVE_PENALTY = 0.72
    SOFT_SIMILARITY_WINDOWS = {
        "MA": 8,
        "EMA": 8,
        "MACD": 18,
        "BOLL": 16,
        "RSI": 12,
        "VOL": 12,
        "KDJ": 12,
        "OI": 12,
        "OBV": 12,
    }
    RELATIVE_BASELINE_FLOORS = {
        "MA": 1.0,
        "EMA": 1.0,
        "MACD": 0.5,
        "BOLL": 0.1,
        "VOL": 1.0,
        "OI": 1.0,
        "OBV": 1000.0,
    }

    def normalize_indicator_name(self, indicator_name):
        upper_name = str(indicator_name).upper()
        return self.INDICATOR_ALIASES.get(upper_name, upper_name)

    def normalize_indicator_names(self, indicators):
        return [self.normalize_indicator_name(indicator) for indicator in indicators]

    def calc_indicator_score(self, indicator_name, sim_pct):
        indicator_name = self.normalize_indicator_name(indicator_name)

        if indicator_name in ("MA", "EMA"):
            if sim_pct <= 1:
                return 3
            if sim_pct <= 3:
                return 2
            if sim_pct <= 5:
                return 1
            return 0

        if indicator_name in ("MACD", "BOLL"):
            if sim_pct <= 1:
                return 30
            if sim_pct <= 3:
                return 20
            if sim_pct <= 5:
                return 10
            return 0

        if indicator_name in ("RSI", "VOL"):
            if sim_pct <= 1:
                return 15
            if sim_pct <= 3:
                return 10
            if sim_pct <= 5:
                return 5
            return 0

        if indicator_name in ("KDJ", "OI", "OBV"):
            if sim_pct <= 1:
                return 9
            if sim_pct <= 3:
                return 6
            if sim_pct <= 5:
                return 3
            return 0

        return 0

    def get_full_score(self, indicator_name):
        return self.FULL_SCORE_BY_INDICATOR.get(self.normalize_indicator_name(indicator_name), 0)

    def get_weight(self, indicator_name):
        return self.WEIGHT_BY_INDICATOR.get(self.normalize_indicator_name(indicator_name), 0)

    def is_public_equal9_profile(self, scoring_profile):
        return str(scoring_profile or "").strip().lower() == self.PUBLIC_EQUAL9_PROFILE

    def weights_for_profile(self, scoring_profile=None):
        if self.is_public_equal9_profile(scoring_profile):
            return dict(self.PUBLIC_EQUAL9_INDICATOR_WEIGHTS)
        return None

    def full_weight_sum_for_profile(self, scoring_profile=None, indicator_weights=None):
        profile_weights = self.weights_for_profile(scoring_profile)
        if profile_weights is not None:
            return sum(profile_weights.values())
        normalized_weights = self._normalize_indicator_weights(indicator_weights)
        if normalized_weights is not None:
            return sum(normalized_weights.values())
        return self.FULL_WEIGHT_SUM

    def selection_weight_for_profile(self, selected_indicators, scoring_profile=None, indicator_weights=None):
        profile_weights = self.weights_for_profile(scoring_profile)
        normalized_weights = profile_weights if profile_weights is not None else self._normalize_indicator_weights(indicator_weights)
        if normalized_weights is not None:
            return sum(
                normalized_weights.get(indicator_name, 0.0)
                for indicator_name in self.normalize_indicator_names(selected_indicators)
            )
        return sum(
            self.get_weight(indicator_name)
            for indicator_name in self.normalize_indicator_names(selected_indicators)
        )

    def score_match(
        self,
        current_window,
        candidate_window,
        indicators,
        include_breakdown=True,
        indicator_weights=None,
        indicator_fit_weight=None,
        path_weight=None,
        scoring_profile=None,
    ):
        selected_indicators = self.normalize_indicator_names(indicators)
        if self.is_public_equal9_profile(scoring_profile):
            indicator_weights = self.PUBLIC_EQUAL9_INDICATOR_WEIGHTS
            indicator_fit_weight = 1.0
            path_weight = 0.0
        custom_weights = self._normalize_indicator_weights(indicator_weights)
        current_snapshot = self._indicator_snapshot(current_window)
        candidate_snapshot = self._indicator_snapshot(candidate_window)

        total_score = 0
        total_full = 0
        total_weight = 0
        total_soft_similarity = 0.0
        breakdown = [] if include_breakdown else None

        for indicator_name in selected_indicators:
            current_value = current_snapshot.get(indicator_name)
            candidate_value = candidate_snapshot.get(indicator_name)
            sim_pct = self._similarity_percent(indicator_name, current_value, candidate_value)
            full_score = self.get_full_score(indicator_name)
            weight = self._resolve_indicator_weight(indicator_name, custom_weights)
            score = self.calc_indicator_score(indicator_name, sim_pct)
            soft_similarity = self._soft_similarity_score(indicator_name, sim_pct)

            total_score += score
            total_full += full_score
            total_weight += weight
            total_soft_similarity += soft_similarity * weight

            if include_breakdown:
                breakdown.append(
                    {
                        "indicator": indicator_name,
                        "currentValue": self._round_number(current_value),
                        "historicalValue": self._round_number(candidate_value),
                        "gapPercent": round(sim_pct, 4),
                        "score": score,
                        "maxScore": full_score,
                        "weight": weight,
                        "softSimilarity": round(soft_similarity * 100, 2),
                    }
                )

        fit_ratio = (total_score / total_full) if total_full else 0.0
        indicator_fit_ratio = (total_soft_similarity / total_weight) if total_weight else 0.0
        path_similarity = self._price_path_similarity(
            current_window.feature_vector if current_window else {},
            candidate_window.feature_vector if candidate_window else {},
        )
        display_fit_ratio = self._combine_display_fit(
            indicator_fit_ratio,
            path_similarity,
            indicator_fit_weight=indicator_fit_weight,
            path_weight=path_weight,
        )
        full_weight_sum = self._full_weight_sum(custom_weights)
        weight_ratio = (total_weight / full_weight_sum) if full_weight_sum else 0.0
        weight_penalty = self._adaptive_weight_penalty(weight_ratio)

        return {
            "total_score": total_score,
            "max_score": total_full,
            "fit_ratio": round(fit_ratio, 6),
            "hard_score_percent": round(fit_ratio * 100, 4),
            "indicator_fit_ratio": round(indicator_fit_ratio, 6),
            "path_similarity": round(path_similarity, 6),
            "display_fit_ratio": round(display_fit_ratio, 6),
            "score_percent": round(display_fit_ratio * 100, 4),
            "selected_score_percent": round(display_fit_ratio * 100, 4),
            "full_scale_max_score": sum(self.FULL_SCORE_BY_INDICATOR.values()),
            "weight_ratio": round(weight_ratio, 6),
            "weight_penalty": round(weight_penalty, 6),
            "breakdown": breakdown or [],
            "is_bullish": bool(candidate_window.return_pct is not None and float(candidate_window.return_pct) > 0),
        }

    def _normalize_indicator_weights(self, indicator_weights):
        if not isinstance(indicator_weights, dict):
            return None

        normalized_weights = {}
        for indicator_name, raw_weight in indicator_weights.items():
            normalized_name = self.normalize_indicator_name(indicator_name)
            try:
                weight = float(raw_weight)
            except Exception:
                continue
            if weight <= 0:
                continue
            normalized_weights[normalized_name] = weight

        return normalized_weights or None

    def _resolve_indicator_weight(self, indicator_name, indicator_weights):
        indicator_name = self.normalize_indicator_name(indicator_name)
        if indicator_weights is not None:
            return indicator_weights.get(indicator_name, 0.0)
        return self.get_weight(indicator_name)

    def _full_weight_sum(self, indicator_weights):
        if indicator_weights is not None:
            return sum(indicator_weights.values())
        return self.FULL_WEIGHT_SUM

    def summarize_probability(self, selected_indicators, scored_matches):
        usable_matches = [
            match
            for match in scored_matches
            if match["score"].get("future_return_5d") is not None
        ]

        if not usable_matches or not selected_indicators:
            return {
                "probability_percent": 0.0,
                "fit_ratio": 0.0,
                "base_prob": 0.0,
                "weight_penalty": 0.0,
                "signal": "NEUTRAL SIGNAL",
                "average_return": None,
                "average_drawdown": None,
                "historical_confidence": 0.0,
            }

        sample_count = len(usable_matches)
        historical_up_count = sum(
            1 for match in usable_matches
            if match["score"]["future_return_5d"] > 0
        )
        base_prob = historical_up_count / sample_count if sample_count else 0.0
        fit_ratio = mean(
            max(0.0, min(1.0, (match["score"].get("score_percent", 0) or 0) / 100))
            for match in usable_matches
        )
        _, _, total_weight = self._calculate_selection_totals(
            selected_indicators,
            self._aggregate_similarity_dict(selected_indicators, usable_matches),
        )
        weight_ratio = (total_weight / self.FULL_WEIGHT_SUM) if self.FULL_WEIGHT_SUM else 0.0
        weight_penalty = self._adaptive_weight_penalty(weight_ratio)
        confidence_multiplier = 0.6 + (0.4 * fit_ratio)
        penalty_multiplier = 0.75 + (0.25 * weight_penalty)
        final_prob = max(0.0, min(1.0, base_prob * confidence_multiplier * penalty_multiplier))

        average_return = mean(
            match["score"]["future_return_5d"]
            for match in usable_matches
        )
        average_drawdown = mean(
            match.get("maxDrawdown", 0) or 0
            for match in usable_matches
        )

        if final_prob >= 0.6:
            signal = "BULLISH SIGNAL"
        elif final_prob <= 0.4:
            signal = "BEARISH SIGNAL"
        else:
            signal = "NEUTRAL SIGNAL"

        return {
            "probability_percent": round(final_prob * 100, 2),
            "fit_ratio": round(fit_ratio, 4),
            "base_prob": round(base_prob, 4),
            "weight_penalty": round(weight_penalty, 4),
            "signal": signal,
            "average_return": round(average_return, 4) if average_return is not None else None,
            "average_drawdown": round(average_drawdown, 4) if average_drawdown is not None else None,
            "historical_confidence": round(fit_ratio, 2),
        }

    def _calculate_selection_totals(self, selected_indicators, similarity_dict):
        total_score = 0
        total_full = 0
        total_weight = 0

        for indicator_name in self.normalize_indicator_names(selected_indicators):
            sim_pct = similarity_dict.get(indicator_name, 999)
            total_score += self.calc_indicator_score(indicator_name, sim_pct)
            total_full += self.get_full_score(indicator_name)
            total_weight += self.get_weight(indicator_name)

        return total_score, total_full, total_weight

    def _aggregate_similarity_dict(self, selected_indicators, scored_matches):
        selected_lookup = set(self.normalize_indicator_names(selected_indicators))
        similarity_dict = {}

        for indicator_name in selected_lookup:
            gaps = []

            for match in scored_matches:
                for row in match["score"].get("breakdown", []):
                    if row.get("indicator") == indicator_name and row.get("gapPercent") is not None:
                        gaps.append(float(row["gapPercent"]))

            similarity_dict[indicator_name] = round(mean(gaps), 4) if gaps else 999

        return similarity_dict

    def _indicator_snapshot(self, window_record):
        feature_vector = window_record.feature_vector or {}
        indicators = feature_vector.get("indicators", {})

        return {
            "MA": indicators.get("ma"),
            "EMA": indicators.get("ema"),
            "MACD": indicators.get("macd"),
            "BOLL": indicators.get("boll_bandwidth"),
            "RSI": indicators.get("rsi"),
            "VOL": indicators.get("volume_ratio"),
            "KDJ": indicators.get("kdj_average"),
            "OI": indicators.get("oi"),
            "OBV": indicators.get("obv"),
        }

    def _similarity_percent(self, indicator_name, current_value, candidate_value):
        if current_value is None or candidate_value is None:
            return 999.0

        indicator_name = self.normalize_indicator_name(indicator_name)
        current_value = float(current_value)
        candidate_value = float(candidate_value)

        if indicator_name in ("RSI", "KDJ"):
            return abs(current_value - candidate_value)

        baseline = max(
            abs(current_value),
            abs(candidate_value),
            self.RELATIVE_BASELINE_FLOORS.get(indicator_name, 1e-9),
        )
        return abs(current_value - candidate_value) / baseline * 100

    def _round_number(self, value):
        if value is None:
            return None

        return round(float(value), 6)

    def _adaptive_weight_penalty(self, weight_ratio):
        """
        Keep indicator weighting meaningful without crushing probability for
        lightweight selections. High-weight bundles stay close to 1.0, while
        low-weight bundles are softened into a ~70% penalty band instead of
        collapsing into single digits.
        """
        if weight_ratio <= 0:
            return 0.0

        smoothed_penalty = self.MIN_ADAPTIVE_PENALTY + (1 - self.MIN_ADAPTIVE_PENALTY) * (weight_ratio ** 0.5)
        return min(1.0, round(smoothed_penalty, 6))

    def _soft_similarity_score(self, indicator_name, sim_pct):
        indicator_name = self.normalize_indicator_name(indicator_name)
        soft_window = self.SOFT_SIMILARITY_WINDOWS.get(indicator_name, 15)
        similarity = 1 / (1 + (max(sim_pct, 0) / soft_window))
        return max(0.0, min(1.0, similarity))

    def _price_path_similarity(self, current_feature_vector, candidate_feature_vector):
        current_path = (current_feature_vector or {}).get("normalized_close_path") or []
        candidate_path = (candidate_feature_vector or {}).get("normalized_close_path") or []

        if not current_path or not candidate_path:
            return 0.0

        compare_length = min(len(current_path), len(candidate_path))
        if compare_length == 0:
            return 0.0

        paired_diffs = [
            abs(float(current_path[index]) - float(candidate_path[index]))
            for index in range(compare_length)
        ]
        mean_abs_diff = mean(paired_diffs) if paired_diffs else 999.0
        similarity = 1 / (1 + (mean_abs_diff / 6))
        return max(0.0, min(1.0, similarity))

    def _combine_display_fit(self, indicator_fit_ratio, path_similarity, indicator_fit_weight=None, path_weight=None):
        try:
            indicator_weight = float(indicator_fit_weight)
        except Exception:
            indicator_weight = 0.75
        try:
            path_component_weight = float(path_weight)
        except Exception:
            path_component_weight = 0.25

        if indicator_weight < 0:
            indicator_weight = 0.0
        if path_component_weight < 0:
            path_component_weight = 0.0

        total_weight = indicator_weight + path_component_weight
        if total_weight <= 0:
            indicator_weight = 0.75
            path_component_weight = 0.25
            total_weight = 1.0

        indicator_share = indicator_weight / total_weight
        path_share = path_component_weight / total_weight
        return max(0.0, min(1.0, (indicator_fit_ratio * indicator_share) + (path_similarity * path_share)))
