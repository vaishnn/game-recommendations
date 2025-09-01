import requests
from bs4 import BeautifulSoup
import polars as pl
import time
import datetime

def scrape_steam_charts():
    timeCounter = datetime.datetime.now()
    base_url = "https://steamcharts.com/top/p.{}"
    page_number = 1
    all_games_data = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    while True:
        url = base_url.format(page_number)
        time_elapsed = datetime.datetime.now() - timeCounter
        print(f"requesting page number {page_number}, time elapsed: {time_elapsed}")

        try:
            response = requests.get(url, headers = headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            games_table = soup.find('table', id = 'top-games')
            if not games_table:
                print("No more tables end of the scrape")
                break
            rows = games_table.find('tbody').find_all('tr') #type: ignore

            if not rows or len(rows) == 0:
                print("No more rows end of the scrape")
                break

            for row in rows:
                cols = row.find_all('td') #type: ignore

                if len(cols) <6:
                    continue

                name_cell = cols[1].find('a') #type: ignore
                if not name_cell:
                    continue

                name = name_cell.text.strip() #type: ignore
                peak = cols[4].text.strip()
                hours_played_all_time = cols[5].text.strip()
                all_games_data.append({
                    'Game': name,
                    'Peak': peak,
                    'Hours Played All Time': hours_played_all_time
                })
            page_number += 1
            time.sleep(0.2)

        except requests.exceptions.RequestException as e:
            print(f"An error occurred during the request: {e}")
            break
        except Exception as e:
            print(f"An error occurred during parsing: {e}")
            break

    if not all_games_data:
        return None

    df = pl.DataFrame(all_games_data)
    return df

if __name__ == "__main__":

    df = scrape_steam_charts()
    if df is not None:
        print("Scraped")
        print(df.shape)

        try:
            df.write_csv("steam_charts.csv")
        except Exception as e:
            print(f"Some error occurred: {e}")
