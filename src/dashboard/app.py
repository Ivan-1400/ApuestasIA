"""Dashboard Streamlit: parleys más probables y estadísticas más probables por partido
(MLB / fútbol), según el modelo. Ejecutar con:
    streamlit run src/dashboard/app.py
"""
from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

# Necesario para poder importar `src.*` al correr este archivo directamente con streamlit.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import yaml

from src.data.football_client import FootballClientError
from src.models.parlay import (
    best_pick_for_mlb,
    best_pick_for_soccer,
    check_pick_hit,
    most_likely_parlays,
    parlay_status,
)
from src.pipeline import build_mlb_predictions, build_soccer_predictions, get_track_record

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "leagues.yaml"

BAR_COLORS = ["#2b6cb0", "#a0aec0", "#e2b93b"]  # local, visitante, empate (fútbol)
AVATAR_COLORS = ["#2b6cb0", "#c0392b", "#27ae60", "#8e44ad", "#d68910", "#16a085", "#2c3e50", "#b83280"]

CUSTOM_CSS = """
<style>
/* Tarjeta de partido — targetea los st.container(key="card_...") */
div[class*="st-key-card_"] {
    border-radius: 16px !important;
    border: 1px solid rgba(128, 128, 128, 0.25) !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.10) !important;
    padding: 1.1rem 1.3rem !important;
    margin-bottom: 1.2rem !important;
}
div[class*="st-key-parlay_"] {
    border-radius: 12px !important;
    border: 1px solid rgba(128, 128, 128, 0.2) !important;
    padding: 0.75rem 1rem !important;
    margin-bottom: 0.7rem !important;
}
.ai-sport-tag {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: #718096;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
}
.ai-team-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    margin-bottom: 0.3rem;
}
.ai-team {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.35rem;
    flex: 1;
    min-width: 0;
}
.ai-avatar {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 700;
    font-size: 0.85rem;
    flex-shrink: 0;
    overflow: hidden;
}
.ai-avatar img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    padding: 4px;
    box-sizing: border-box;
}
.ai-avatar-fallback {
    display: none;
    width: 100%;
    height: 100%;
    align-items: center;
    justify-content: center;
}
.ai-team-name {
    font-weight: 700;
    font-size: 0.92rem;
    text-align: center;
    line-height: 1.2;
}
.ai-team-pct {
    font-size: 1.35rem;
    font-weight: 800;
    line-height: 1.1;
}
.ai-vs {
    font-size: 0.72rem;
    font-weight: 700;
    color: #a0aec0;
    background: rgba(160, 174, 192, 0.18);
    border-radius: 999px;
    padding: 0.2rem 0.65rem;
    flex-shrink: 0;
}
.ai-prob-bar {
    display: flex;
    height: 10px;
    border-radius: 6px;
    overflow: hidden;
    margin: 0.7rem 0 0.3rem 0;
    background: #eee;
}
.ai-prob-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    opacity: 0.75;
    margin-bottom: 0.6rem;
}
.ai-favorite-box {
    background: rgba(43, 108, 176, 0.08);
    border: 1px solid rgba(43, 108, 176, 0.35);
    border-radius: 10px;
    padding: 0.7rem 1rem;
    margin: 0.6rem 0;
}
.ai-favorite-box .ai-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    color: #2b6cb0;
    text-transform: uppercase;
}
.ai-favorite-box .ai-team-highlight {
    font-size: 1.1rem;
    font-weight: 700;
    margin: 0.15rem 0;
}
.ai-stat-list { margin: 0.4rem 0; }
.ai-stat-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 0.4rem 0;
    border-bottom: 1px solid rgba(128, 128, 128, 0.15);
    font-size: 0.9rem;
}
.ai-stat-row:last-child { border-bottom: none; }
.ai-stat-row .ai-stat-value { font-weight: 700; }
.ai-value-badge {
    display: inline-block;
    border-radius: 999px;
    padding: 0.2rem 0.75rem;
    font-weight: 700;
    font-size: 0.8rem;
    margin: 0.15rem 0.4rem 0.15rem 0;
}
.ai-value-positive { background: rgba(56, 161, 105, 0.18); color: #276749; }
.ai-value-negative { background: rgba(160, 174, 192, 0.25); color: #4a5568; }
.ai-result-hit { background: rgba(56, 161, 105, 0.18); color: #276749; }
.ai-result-miss { background: rgba(197, 48, 48, 0.15); color: #9b2c2c; }
.ai-callout {
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin: 0.6rem 0;
    font-size: 0.9rem;
    line-height: 1.45;
}
.ai-callout-positive { background: rgba(56, 161, 105, 0.10); border: 1px solid rgba(56, 161, 105, 0.3); }
.ai-callout-neutral { background: rgba(160, 174, 192, 0.12); border: 1px solid rgba(160, 174, 192, 0.35); }
.ai-callout-info { background: rgba(43, 108, 176, 0.10); border: 1px solid rgba(43, 108, 176, 0.3); }
.ai-callout-title { font-weight: 700; margin-bottom: 0.2rem; }
</style>
"""


def team_initials(name: str) -> str:
    words = re.findall(r"[A-Za-zÀ-ÿ]+", name)
    if len(words) >= 2:
        return (words[0][0] + words[-1][0]).upper()
    return name[:2].upper()


def team_color(name: str) -> str:
    return AVATAR_COLORS[hash(name) % len(AVATAR_COLORS)]


def render_sport_tag(label: str) -> str:
    return f'<div class="ai-sport-tag">{label}</div>'


def render_team_row(
    home_team: str,
    away_team: str,
    home_logo: str | None,
    away_logo: str | None,
    home_pct: float,
    away_pct: float,
) -> str:
    def avatar(name: str, logo_url: str | None, pct: float) -> str:
        initials_span = f'<span class="ai-avatar-fallback">{team_initials(name)}</span>'
        if logo_url:
            img = (
                f'<img src="{logo_url}" alt="{name}" '
                "onerror=\"this.style.display='none'; this.nextElementSibling.style.display='flex';\" />"
            )
            content = img + initials_span
        else:
            content = f'<span class="ai-avatar-fallback" style="display:flex;">{team_initials(name)}</span>'
        color = team_color(name)
        return (
            f'<div class="ai-team"><div class="ai-avatar" style="background:{color};">'
            f'{content}</div><div class="ai-team-name">{name}</div>'
            f'<div class="ai-team-pct" style="color:{color};">{pct:.1%}</div></div>'
        )

    return (
        f'<div class="ai-team-row">{avatar(away_team, away_logo, away_pct)}<div class="ai-vs">VS</div>'
        f"{avatar(home_team, home_logo, home_pct)}</div>"
    )


def render_prob_bar(entries: list[tuple[str, float]]) -> str:
    segments = "".join(
        f'<div style="width:{pct * 100:.1f}%; background:{BAR_COLORS[i % len(BAR_COLORS)]};"></div>'
        for i, (_, pct) in enumerate(entries)
    )
    labels = "".join(f"<span>{label} {pct:.1%}</span>" for label, pct in entries)
    return f'<div class="ai-prob-bar">{segments}</div><div class="ai-prob-labels">{labels}</div>'


def render_favorite_box(entries: list[tuple[str, float]]) -> str:
    favorite_label, favorite_pct = max(entries, key=lambda e: e[1])
    detail = " · ".join(f"{label} {pct:.1%}" for label, pct in entries)
    return (
        '<div class="ai-favorite-box">'
        '<div class="ai-label">Quién tiene más probabilidad</div>'
        f'<div class="ai-team-highlight">{favorite_label}</div>'
        f"<div>{detail}</div>"
        "</div>"
    )


PANORAMA_CONTENT = {
    "coincide": (
        "🎯",
        "PANORAMA · OPORTUNIDAD FUERTE",
        "ai-callout-positive",
        "El sistema coincide con {provider}. Acá pisa firme.",
    ),
    "mas_confiado": (
        "📈",
        "PANORAMA · MODELO MÁS CONFIADO",
        "ai-callout-info",
        "El modelo le da más probabilidad que {provider} a este resultado.",
    ),
    "menos_confiado": (
        "⚠️",
        "PANORAMA · MODELO MÁS CAUTELOSO",
        "ai-callout-neutral",
        "El modelo le da menos probabilidad que {provider} a este resultado.",
    ),
}


def render_panorama(result: dict) -> str | None:
    """Compara la pick del modelo contra la cuota real de mercado (DraftKings vía ESPN) y
    devuelve el callout 'Panorama' — o None si todavía no hay cuota publicada para comparar."""
    comparison = result.get("market_comparison")
    if not comparison:
        return None
    icon, title, cls, template = PANORAMA_CONTENT[comparison]
    provider = result.get("market_provider") or "el mercado"
    return (
        f'<div class="ai-callout {cls}">'
        f'<div class="ai-callout-title">{icon} {title}</div>'
        f"{template.format(provider=provider)}</div>"
    )


def render_stat_list(rows: list[tuple[str, str]]) -> str:
    rows_html = "".join(
        f'<div class="ai-stat-row"><span>{label}</span><span class="ai-stat-value">{value}</span></div>'
        for label, value in rows
    )
    return f'<div class="ai-stat-list">{rows_html}</div>'


def render_result_badge(hit: bool, outcome_label: str) -> str:
    cls = "ai-result-hit" if hit else "ai-result-miss"
    icon = "✅" if hit else "❌"
    verdict = "Acertó" if hit else "No acertó"
    return f'<span class="ai-value-badge {cls}">{icon} {verdict} — predijo: {outcome_label}</span>'


PARLAY_STATUS_BADGE = {
    "ganado": '<span class="ai-value-badge ai-result-hit">🏆 GANADO</span>',
    "perdido": '<span class="ai-value-badge ai-result-miss">💔 PERDIDO</span>',
    "en_curso": '<span class="ai-value-badge ai-value-negative">⏳ EN CURSO</span>',
}


def render_track_record(sport: str) -> None:
    """Resumen histórico de todas las picks guardadas hasta ahora para este deporte, para
    poder medir con el tiempo si el modelo acierta más de lo que dice el puro azar."""
    record = get_track_record(sport)
    if record["total"] == 0:
        return

    st.subheader("📊 Historial de aciertos")
    decided = record["hits"] + record["misses"]
    if decided:
        badge_cls = "ai-result-hit" if record["hit_rate"] >= 0.5 else "ai-result-miss"
        st.markdown(
            f'<span class="ai-value-badge {badge_cls}">{record["hit_rate"]:.1%} de acierto</span>',
            unsafe_allow_html=True,
        )
        caption = f"{record['hits']} acertadas de {decided} ya jugadas"
        if record["pending"]:
            caption += f" · {record['pending']} pendientes"
        st.caption(caption)
    else:
        st.caption(f"{record['pending']} predicciones guardadas — todavía ninguna terminó de jugarse.")

    with st.expander("Ver historial completo"):
        for row in record["rows"]:
            if row["hit"] is None:
                st.write(f"⏳ **{row['outcome_label']}** ({row['match_label']}) — pendiente")
            else:
                icon = "✅" if row["hit"] else "❌"
                st.write(
                    f"{icon} **{row['outcome_label']}** ({row['match_label']}) — "
                    f"{row['home_score']}-{row['away_score']}"
                )


def render_parlays(picks: list) -> None:
    """Muestra los parleys (combinadas) con mayor probabilidad de ganar, armados con la pick
    más segura de cada partido — con las stats que sustentan cada pata (carreras/goles
    esperados, pitchers) y, si el partido ya terminó, el resultado real y si ganó o perdió,
    tanto por pata como el parley completo. Requiere al menos 2 partidos para combinar."""
    if len(picks) < 2:
        return

    st.subheader("🎟️ Parleys más probables de ganar")
    st.caption(
        "Combina la opción más probable de cada partido (asumiendo que los partidos son "
        "independientes entre sí — una simplificación, no una garantía)."
    )
    for i, parlay in enumerate(most_likely_parlays(picks, min_legs=2, max_legs=4, top_n=5)):
        status = parlay_status(parlay["legs"])
        with st.container(border=True, key=f"parlay_{i}"):
            st.markdown(
                f'<span class="ai-value-badge ai-value-positive">'
                f'{parlay["num_legs"]} patas — {parlay["combined_probability"]:.1%} de ganar todo</span>'
                f"{PARLAY_STATUS_BADGE[status]}",
                unsafe_allow_html=True,
            )
            for leg in parlay["legs"]:
                leg_line = f"**{leg.outcome_label}** ({leg.match_label})"
                if leg.detail:
                    leg_line += f"  \n{leg.detail}"
                if leg.is_final and leg.home_score is not None:
                    hit = check_pick_hit(leg, leg.home_score, leg.away_score)
                    icon = "✅" if hit else "❌"
                    leg_line += f"  \n{icon} Resultado: {leg.home_score}-{leg.away_score}"
                st.write(leg_line)


st.set_page_config(page_title="ApuestasIA", layout="centered")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
st.title("ApuestasIA — pronósticos de fútbol y MLB")
st.caption(
    "Estadísticas más probables según un modelo de Poisson (fútbol) / carreras + Pythagorean-log5 "
    "(MLB). Son datos de referencia para armar tu propia apuesta en la casa que prefieras."
)

with open(CONFIG_PATH, encoding="utf-8") as f:
    config = yaml.safe_load(f)

sport = st.sidebar.radio("Deporte", ["MLB", "Fútbol"])
date = st.sidebar.date_input("Fecha", datetime.date.today())
date_str = date.isoformat()


if sport == "MLB":
    if not config["mlb"]["enabled"]:
        st.warning("MLB está deshabilitado en config/leagues.yaml")
    else:
        with st.spinner("Cargando partidos y calculando predicciones de MLB..."):
            try:
                predictions = build_mlb_predictions(date_str)
            except Exception as exc:  # red / API caídos, etc.
                st.error(f"Error al traer datos de MLB: {exc}")
                predictions = []

        if not predictions:
            st.info("No hay partidos de MLB para esa fecha.")

        render_track_record("mlb")
        render_parlays([best_pick_for_mlb(p) for p in predictions])

        for p in predictions:
            with st.container(border=True, key=f"card_{p['fixture_id'].replace(':', '_')}"):
                st.markdown(render_sport_tag("MLB"), unsafe_allow_html=True)
                st.markdown(
                    render_team_row(
                        p["home_team"],
                        p["away_team"],
                        p["home_team_logo"],
                        p["away_team_logo"],
                        p["p_home_win"],
                        p["p_away_win"],
                    ),
                    unsafe_allow_html=True,
                )

                entries = [(p["home_team"], p["p_home_win"]), (p["away_team"], p["p_away_win"])]
                st.markdown(render_prob_bar(entries), unsafe_allow_html=True)
                st.markdown(render_favorite_box(entries), unsafe_allow_html=True)

                panorama = render_panorama(p)
                if panorama:
                    st.markdown(panorama, unsafe_allow_html=True)

                stat_rows = [
                    (f"Carreras esperadas — {p['home_team']}", f"{p['home_runs_xg']:.2f}"),
                    (f"Carreras esperadas — {p['away_team']}", f"{p['away_runs_xg']:.2f}"),
                    ("Total esperado", f"{p['total_runs_xg']:.2f} carreras"),
                    (f"Más de {p['line']} carreras", "Sí, probable" if p["p_over"] > 0.5 else "No, improbable"),
                ]
                if p["home_pitcher_name"] or p["away_pitcher_name"]:
                    home_p = p["home_pitcher_name"] or "sin anunciar"
                    home_era = f"ERA {p['home_pitcher_era']:.2f}" if p["home_pitcher_era"] is not None else "sin ERA"
                    away_p = p["away_pitcher_name"] or "sin anunciar"
                    away_era = f"ERA {p['away_pitcher_era']:.2f}" if p["away_pitcher_era"] is not None else "sin ERA"
                    stat_rows.append(("Pitchers abridores", f"{away_p} ({away_era}) vs {home_p} ({home_era})"))
                if p["is_final"] and p["home_score"] is not None:
                    stat_rows.append(
                        ("Resultado final", f"{p['away_team']} {p['away_score']} - {p['home_score']} {p['home_team']}")
                    )
                st.markdown(render_stat_list(stat_rows), unsafe_allow_html=True)

                if p["is_final"] and p["home_score"] is not None:
                    pick = best_pick_for_mlb(p)
                    hit = check_pick_hit(pick, p["home_score"], p["away_score"])
                    st.markdown(render_result_badge(hit, pick.outcome_label), unsafe_allow_html=True)

else:
    leagues = config["soccer"]["leagues"]
    league_names = [entry["name"] for entry in leagues]
    selected_name = st.sidebar.selectbox("Liga", league_names)
    league_cfg = next(entry for entry in leagues if entry["name"] == selected_name)
    season = config.get("season", datetime.date.today().year)

    source = league_cfg.get("source", "football_data")
    if source == "espn":
        st.sidebar.caption(
            "⚠️ Esta liga usa una fuente no oficial (API interna de ESPN) — puede fallar sin aviso."
        )

    with st.spinner(f"Cargando partidos y calculando predicciones de {selected_name}..."):
        try:
            predictions = build_soccer_predictions(
                league_cfg["code"], league_cfg["name"], season, date_str, source=source
            )
        except FootballClientError as exc:
            st.error(str(exc))
            predictions = []
        except Exception as exc:
            st.error(f"Error al traer datos de {selected_name}: {exc}")
            predictions = []

    if not predictions:
        st.info("No hay partidos para esa fecha/liga.")

    render_track_record("soccer")
    render_parlays([best_pick_for_soccer(p) for p in predictions])

    for p in predictions:
        with st.container(border=True, key=f"card_{p['fixture_id'].replace(':', '_')}"):
            st.markdown(render_sport_tag(selected_name), unsafe_allow_html=True)
            st.markdown(
                render_team_row(
                    p["home_team"],
                    p["away_team"],
                    p["home_team_logo"],
                    p["away_team_logo"],
                    p["p_home_win"],
                    p["p_away_win"],
                ),
                unsafe_allow_html=True,
            )

            entries = [
                (p["home_team"], p["p_home_win"]),
                ("Empate", p["p_draw"]),
                (p["away_team"], p["p_away_win"]),
            ]
            st.markdown(render_prob_bar(entries), unsafe_allow_html=True)
            st.markdown(render_favorite_box(entries), unsafe_allow_html=True)

            panorama = render_panorama(p)
            if panorama:
                st.markdown(panorama, unsafe_allow_html=True)

            stat_rows = [
                (f"Goles esperados — {p['home_team']}", f"{p['home_xg']:.2f}"),
                (f"Goles esperados — {p['away_team']}", f"{p['away_xg']:.2f}"),
                (
                    "Marcador más probable",
                    f"{p['most_likely_score'][0]}-{p['most_likely_score'][1]} ({p['most_likely_score_prob']:.1%})",
                ),
                ("Over 2.5 goles", f"{p['p_over_2_5']:.1%}"),
                ("Ambos anotan", f"{p['p_btts']:.1%}"),
            ]
            if p["is_final"] and p["home_score"] is not None:
                stat_rows.append(
                    ("Resultado final", f"{p['home_team']} {p['home_score']} - {p['away_score']} {p['away_team']}")
                )
            st.markdown(render_stat_list(stat_rows), unsafe_allow_html=True)

            if p["is_final"] and p["home_score"] is not None:
                pick = best_pick_for_soccer(p)
                hit = check_pick_hit(pick, p["home_score"], p["away_score"])
                st.markdown(render_result_badge(hit, pick.outcome_label), unsafe_allow_html=True)
