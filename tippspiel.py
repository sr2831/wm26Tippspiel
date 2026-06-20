import requests

# 1. Eure Tippspiel-Runden-Zuweisung (inkl. gängiger Namensvarianten der API)
TEAMS = {
    "Stephan": [
        "Iran", "Paraguay", "Germany", "Deutschland", "Sweden", "Schweden", "Algeria", "Algerien",
        "Uruguay", "Spain", "Spanien", "Ghana", "Portugal"
    ],
    "Matthias": [
        "South Africa", "Südafrika", "Korea Republic", "South Korea", "Südkorea", "Canada", "Kanada",
        "Scotland", "Schottland", "Brazil", "Brasilien", "Australia", "Australien", "Japan",
        "Netherlands", "Niederlande", "Belgium", "Belgien", "Norway", "Norwegen", "Austria", "Österreich"
    ],
    "Achim": [
        "Mexico", "Mexiko", "Switzerland", "Schweiz", "Ivory Coast", "Elfenbeinküste", "Cote d'Ivoire",
        "Argentina", "Argentinien", "Colombia", "Kolumbien", "England"
    ],
    "Boernie": [
        "Czech Republic", "Czechia", "Tschechien", "Bosnia and Herzegovina", "Bosnia-Herzegovina", "Bosnien", "Morocco", "Marokko",
        "Turkey", "Türkiye", "Türkei", "USA", "United States", "Ecuador", "Tunisia", "Tunesien", "Senegal", "Croatia", "Kroatien"
    ]
}

# API-URLs für die Ergebnisse und Tabellenstände der WM 2026
URL_GAMES = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=20260611-20260719&limit=100"
URL_STANDINGS = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings"

def fetch_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Fehler beim Abrufen der Daten ({url}): {e}")
        return None

def calculate_scores(events):
    player_results = {player: {"points": 0, "details": [], "bonus_teams": []} for player in TEAMS}
    seen_matches = set()

    if not events:
        return player_results

    for event in events:
        match_id = event.get('id')
        if match_id in seen_matches:
            continue

        status = event.get('status', {}).get('type', {}).get('name', '')

        # Jedes beendete Spiel im WM-Zeitraum auswerten
        if status == "STATUS_FULL_TIME":
            competitions = event.get('competitions', [{}])[0]
            competitors = competitions.get('competitors', [])

            if len(competitors) < 2:
                continue

            team1_name = competitors[0].get('team', {}).get('name')
            team1_score = int(competitors[0].get('score', 0))

            team2_name = competitors[1].get('team', {}).get('name')
            team2_score = int(competitors[1].get('score', 0))

            seen_matches.add(match_id)

            # Gewinner-Logik
            if team1_score > team2_score:
                winner, loser = team1_name, team2_name
                draw = False
            elif team2_score > team1_score:
                winner, loser = team2_name, team1_name
                draw = False
            else:
                winner, loser = None, None
                draw = True

            # Punkte zuordnen (3 für Sieg, 1 für Unentschieden)
            for player, countries in TEAMS.items():
                if draw:
                    if team1_name in countries:
                        player_results[player]["points"] += 1
                        player_results[player]["details"].append(f"1 P. | {team1_name} ({team1_score}:{team2_score} vs. {team2_name})")
                    if team2_name in countries:
                        player_results[player]["points"] += 1
                        player_results[player]["details"].append(f"1 P. | {team2_name} ({team2_score}:{team1_score} vs. {team1_name})")
                else:
                    if winner in countries:
                        player_results[player]["points"] += 3
                        player_results[player]["details"].append(f"3 P. | {winner} (Sieg {team1_score if winner==team1_name else team2_score}:{team2_score if winner==team1_name else team1_score} vs. {loser})")
                    if loser in countries:
                        player_results[player]["details"].append(f"0 P. | {loser} (Niederlage gegen {winner})")

    return player_results

def apply_bonus_points(player_results, standings_data):
    if not standings_data or 'children' not in standings_data:
        return player_results

    # Wir gehen durch jede Gruppe (A, B, C...)
    for group in standings_data['children']:
        standings = group.get('standings', {})
        entries = standings.get('entries', [])

        # Eine Gruppe gilt erst als beendet, wenn JEDES Team darin 3 Spiele absolviert hat
        group_finished = True
        for entry in entries:
            stats = entry.get('stats', [])
            games_played = 0
            for stat in stats:
                if stat.get('name') == 'gamesPlayed':
                    games_played = int(stat.get('value', 0))

            if games_played < 3:
                group_finished = False
                break

        # Die Bonuspunkte werden NUR vergeben, wenn die Gruppe mathematisch fertig gespielt wurde
        if group_finished and len(entries) >= 2:
            # Die ersten beiden Plätze (Index 0 und 1) erreichen sicher das Sechzehntelfinale
            for i, entry in enumerate(entries[:2]):
                team_name = entry.get('team', {}).get('name')

                # Prüfen, wer der Besitzer des Teams ist
                for player, countries in TEAMS.items():
                    if team_name in countries:
                        player_results[player]["points"] += 1
                        player_results[player]["bonus_teams"].append(team_name)

    return player_results

def display_scoreboard(player_results):
    print("=" * 65)
    print("🏆 AKTUELLER STAND EURER WM-TIPPRUNDE (SICHERE BONUSWERTUNG) 🏆")
    print("=" * 65)

    # Sortieren nach Punkten absteigend
    ranked_players = sorted(player_results.items(), key=lambda x: x[1]["points"], reverse=True)

    for rank, (player, data) in enumerate(ranked_players, 1):
        print(f"\n{rank}. {player.upper()}: {data['points']} Punkte")
        print("-" * 45)

        # Ausgeben der normalen Spielergebnisse
        if data["details"]:
            for detail in sorted(list(set(data["details"]))):
                print(f"  -> {detail}")

        # Ausgeben der Bonuspunkte (nur wenn Gruppen beendet sind)
        if data["bonus_teams"]:
            print(f"  🌟 BONUS (+1 P. für Erreichen der nächsten Runde):")
            for b_team in sorted(list(set(data['bonus_teams']))):
                print(f"     [X] {b_team}")
        else:
            print("  -> Noch keine fixen Bonus-Qualifikationen in beendeten Gruppen.")

    print("=" * 65)

if __name__ == "__main__":
    print("Rufe aktuelle WM-Spieldaten ab...")
    games_json = fetch_data(URL_GAMES)
    events = games_json.get('events', []) if games_json else []

    print("Rufe aktuelle Tabellenstände ab...")
    standings_json = fetch_data(URL_STANDINGS)

    # Punkte berechnen & Bonus addieren
    results = calculate_scores(events)
    results = apply_bonus_points(results, standings_json)

    # Rangliste anzeigen
    display_scoreboard(results)
