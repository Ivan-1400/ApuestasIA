"""Recolector diario: corre sin UI (pensado para un cron de GitHub Actions) para que las
predicciones y resultados se sigan guardando aunque nadie abra el dashboard ese día.

Por cada deporte, procesa HOY y AYER:
- HOY: guarda picks nuevas para los partidos del día (antes de que se jueguen).
- AYER: vuelve a traer esos partidos para actualizar el resultado final una vez que ya se
  jugaron — así `get_track_record()` los puede verificar sin depender de que alguien haya
  abierto el dashboard justo cuando terminó cada partido.
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from src.pipeline import build_mlb_predictions, build_soccer_predictions

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "leagues.yaml"


def collect() -> None:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    today = datetime.date.today()
    dates = [today.isoformat(), (today - datetime.timedelta(days=1)).isoformat()]

    if config["mlb"]["enabled"]:
        for date in dates:
            try:
                results = build_mlb_predictions(date)
                print(f"[MLB] {date}: {len(results)} partidos procesados")
            except Exception as exc:  # una liga/fecha con error no debe tumbar el resto
                print(f"[MLB] {date}: ERROR — {exc}")

    if config["soccer"]["enabled"]:
        for league in config["soccer"]["leagues"]:
            for date in dates:
                try:
                    results = build_soccer_predictions(
                        league["code"],
                        league["name"],
                        config.get("season", today.year),
                        date,
                        source=league.get("source", "football_data"),
                    )
                    print(f"[{league['name']}] {date}: {len(results)} partidos procesados")
                except Exception as exc:
                    print(f"[{league['name']}] {date}: ERROR — {exc}")


if __name__ == "__main__":
    collect()
