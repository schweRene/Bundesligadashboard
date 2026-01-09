import sqlite3
import pandas as pd

def get_table_data():
    conn = sqlite3.connect("bundesliga.db")
    query = """
    SELECT heim, gast, tore_heim, tore_gast
    FROM spiele
    WHERE saison = '2025/26' AND tore_heim IS NOT NULL
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    stats = {}
    for _, row in df.iterrows():
        h, g = row['heim'], row['gast']
        th, tg = int(row['tore_heim']), int(row['tore_gast'])
        
        for team in [h, g]:
            if team not in stats:
                stats[team] = {'Spiele': 0, 'S': 0, 'U': 0, 'N': 0, 'Tore': 0, 'Gegentore': 0, 'Punkte': 0}

        stats[h]['Spiele'] += 1; stats[g]['Spiele'] += 1
        stats[h]['Tore'] += th; stats[h]['Gegentore'] += tg
        stats[g]['Tore'] += tg; stats[g]['Gegentore'] += th

        if th > tg:
            stats[h]['S'] += 1; stats[h]['Punkte'] += 3
            stats[g]['N'] += 1
        elif th < tg:
            stats[g]['S'] += 1; stats[g]['Punkte'] += 3
            stats[h]['N'] += 1
        else:
            stats[h]['U'] += 1; stats[h]['Punkte'] += 1
            stats[g]['U'] += 1; stats[g]['Punkte'] += 1

    table = pd.DataFrame.from_dict(stats, orient='index')
    table['Diff'] = table['Tore'] - table['Gegentore']
    table = table.sort_values(by=['Punkte', 'Diff', 'Tore'], ascending=False)    
    table.index.name = 'Verein'
    table = table.reset_index()
    table.insert(0, 'Platz', range(1, len(table) + 1))
    return table

def save_table_to_txt():
    table = get_table_data()
    output = f"\n--- 📄 TABELLE BUNDESLIGA 2025/26 ---\n\n"
    output += table.to_string(index=False)
    with open("aktuelle_tabelle.txt", "w", encoding="utf-8") as f:
        f.write(output)
    print("✅ Tabelle in 'aktuelle_tabelle.txt' gespeichert.")
    
def show_table():
    print(get_table_data().to_string())

if __name__ == "__main__":
    show_table()
    save_table_to_txt()