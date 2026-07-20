# ApuestasIA

IA de pronósticos deportivos (fútbol + MLB) que calcula las estadísticas más probables de un partido — goles totales, goles por equipo, ganador — para usarlas como apoyo a la hora de apostar.

> Nombre de trabajo, pendiente de definir uno final.

## Alcance

- **Fútbol**: Premier League, La Liga, Serie A, Bundesliga, Champions League (configurable en `config/leagues.yaml`). Liga MX y MLS quedan configuradas pero sin fuente de datos gratis con temporada actual — ver más abajo.
- **MLB**: temporada regular completa.

## Fuentes de datos

- [MLB Stats API](https://statsapi.mlb.com) — oficial, gratuita, sin API key.
- [football-data.org](https://www.football-data.org) — tier gratis, cubre 12 competencias (incluidas las 5 de arriba) con partidos/resultados actuales (demorados unos minutos, no en vivo). Requiere API key propia en `.env` (ver `.env.example`). **No cubre Liga MX ni MLS.**
- Cuotas de casas de apuestas: carga manual en el dashboard por ahora (sin integración automática todavía — ver `src/odds/manual_odds.py`).

> Se evaluó [API-Football](https://www.api-football.com) primero, pero su tier gratis no da acceso a la temporada actual en ninguna liga (solo histórico 2022-2024) — confirmado el 2026-07-19 contra la API real.

## Modelos

- **Fútbol**: distribución de Poisson por equipo (fuerza de ataque/defensa local y visitante) para marcador más probable, goles totales (over/under) y probabilidades 1X2.
- **MLB**: modelo de carreras (Poisson) para el total, y Pythagorean win expectation / log5 para el moneyline.

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # completar FOOTBALL_DATA_API_KEY
```

## Uso

```bash
streamlit run src/dashboard/app.py
```

## Estructura

```
config/leagues.yaml       # ligas/temporadas a seguir
src/data/                 # clientes de datos (MLB, football-data.org) + cache SQLite
src/models/                # modelos de predicción (Poisson fútbol, modelo MLB)
src/odds/                  # entrada manual de cuotas + cálculo de valor (edge %)
src/pipeline.py            # orquesta fetch -> stats -> modelos -> predicciones
src/dashboard/app.py       # dashboard Streamlit
data/                       # cache local (SQLite), gitignored
```
