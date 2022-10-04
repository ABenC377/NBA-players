from turtle import home
import requests
from datetime import date, datetime, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time
import csv
import os
from pathlib import Path
    


def main():
    # Check local database (if there is one) and get the list of games already saved
    games_saved = set()
    
    # If there is not the desired directory, then make it.
    os.makedirs('../../NBA data', exist_ok=True)

    if Path('../../NBA data/data.csv').exists():
        with open('../../NBA data/data.csv', 'r') as existing_data_file:
            existing_game_data = csv.DictReader(existing_data_file)
            for row in existing_game_data:
                games_saved.add(row['game_link'])
    
    

        

    


    number_of_previous_days = int(input("How many days of games would you like to get the data for?\n"))

    # first we get the data we want from the NBA website - I STILL NEED TO IMPLEMENT THE DAYS BIT OF IT
    games_saved = get_data(number_of_previous_days, games_saved)

    # Update the games_saved info in the database

    print('all finished')

class Game_Data:
    def __init__(self, date, away_team, home_team, game_link, away_scores, home_scores, plays):
        self.date = date
        self.away_team = away_team
        self.home_team = home_team
        self.game_link = game_link
        self.away_scores = away_scores
        self.home_scores = home_scores
        self.plays = plays

class Box_Score:
    def __init__(self, game_link, player_name, home, played, started, seconds, FGM, FGA, TPM, TPA, FTM, FTA, ORB, DRB, assists, steals, blocks, TO, PF, plus_minus):
        self.game_link = game_link
        self.player_name = player_name
        self.home = home
        self.played = played
        self.started = started
        self.seconds = seconds
        self.FGM = FGM
        self.FGA = FGA
        self.TPM = TPM
        self.TPA = TPA
        self.FTM = FTM
        self.FTA = FTA
        self.ORB = ORB
        self.DRB = DRB
        self.assists = assists
        self.steals = steals
        self.block = blocks
        self.TO = TO
        self.PF = PF
        self.plus_minus = plus_minus

class Play:
    def __init__(self, game_ID, quarter, seconds, away_score, home_score, player1_ID, player2_ID, home, shot=False, made=False, attempted_points=0, substitution=False, ORB=False, DRB=False, steal=False, foul=False, shot_type="", block=False):
        self.game_ID = game_ID
        self.quarter = quarter
        self.seconds = seconds
        self.away_score = away_score
        self.home_score = home_score
        self.player1_ID = player1_ID
        self.player2_ID = player2_ID
        self.home = home
        self.shot = shot
        self.made = made
        self.attempted_points = attempted_points
        self.substitution = substitution
        self.ORB = ORB
        self.DRB = DRB
        self.steal = steal
        self.foul = foul
        self.shot_type = shot_type
        self.block = block

def get_data(number_of_previous_days, games_already_saved):
    # make sure that the correct data type is passed into the get_data() function
    if type(number_of_previous_days) is not int:
        print('non-integer passed into get_data() function')
        return []
    if number_of_previous_days <= 0:
        print('invalid number passed into get_data() function')
        return []

    prefix = 'https://www.nba.com/games?date='

    # this goes back over a number of days to get the HTTP links for the games that happened on those days.  
    for n in range(number_of_previous_days, 0, -1):
        
        # Get the date in the format used by the NBA website
        nth_date = date.today() + timedelta(days = -n)
        nth_date_string = nth_date.strftime("%Y-%m-%d")
        #nth_date_string = "2022-02-08"

        # now we make a request for the webpage summarising the games on thaat date
        nth_day_webpage_response = requests.get(prefix + nth_date_string, timeout=1)
        if nth_day_webpage_response.status_code == None:
            continue
        
        # we do some BS to get the links to the pages for the individual game
        nth_day_webpage = nth_day_webpage_response.content
        nth_day_html = BeautifulSoup(nth_day_webpage, "html.parser")
        nth_day_games_links = nth_day_html.select("a")
        # the only way I could think to do this with BS is to get all the links, and then filter out the ones that are not for game pages
        
        for game in nth_day_games_links:
            if game["href"][0:5] == "/game" and len(game["href"]) == 27:
                link = "https://www.nba.com" + game["href"]
                # now we save the link to the game_links list
                if link not in games_already_saved:
                    games_already_saved.add(link)
                    game_obj = get_game_data(link, nth_date_string)
                    save_game_data(game_obj)

    return games_already_saved

def get_game_data(link, date_string):
    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)

    driver.get(link + "/box-score")

    away_team = ""
    home_team = ""

    headers = driver.find_elements(By.TAG_NAME, "h1")
    for h in headers:
            spans = h.find_elements(By.TAG_NAME, "span")
            for s in spans:
                if away_team == "":
                    away_team = s.text
                else:
                    home_team = s.text
    
    boxes = driver.find_elements(By.TAG_NAME, "table")
    
    away_scores_string = ""
    home_scores_string = ""
    for b in boxes:
        if away_scores_string == "":
            away_scores_string = b.text
        else:
            home_scores_string = b.text

    away_starters, away_boxscores = get_boxscores(link, away_scores_string, False)
    home_starters, home_boxscores = get_boxscores(link, home_scores_string, True)

    starters = list()
    for starter in away_starters:
        starters.append(starter)
    for starter in home_starters:
        starters.append(starter)

    # Then we save all the plays
    driver.get(link + "/play-by-play?period=All")
    play_elements = driver.find_elements(By.TAG_NAME, "article")
    plays_raw = []
    for p in play_elements:
        plays_raw.append(p.text)
    plays = get_plays(link, plays_raw, starters)

    game_obj = Game_Data(date=date_string, home_team=home_team, away_team=away_team, game_link=link, away_scores=away_boxscores, home_scores=home_boxscores, plays=plays)

    # Now we have all of the info for each of the games, we can close the driver
    driver.quit()

    return game_obj

def get_boxscores(link, boxscore_string, home):
    starting_players = list()

    boxscores = list()

    # Then, we want to seperate out all of the individual rows of the box_score
    # The rows are separated by new lines
    team_rows = boxscore_string.split('\n')

    # the first row is always the header of the columns, and so we can ignore
    # After that, the name and starting position of each player are on seperate lines to that player's box score
    # Therefore, we will get the starters' info first (as they have three lines each), and then the bench's info.
    for i in range(1, 16, 3):

        # First info is player_name.  We will need to turn this into a player_ID by consulting the players table
        player_name = team_rows[i]
        # We also append the player id to the list of starting players so that we can later pass this into the play-by-play database
        starting_players.append(player_name)

        # Now we can seperate out the individual box scores (they are seperated by spaces) and assign them to variables
        player_box_scores = team_rows[i + 2].split()

        minutes = player_box_scores[0]
        seconds = get_seconds_from_minutes(minutes)
        FGM = player_box_scores[1]
        FGA = player_box_scores[2]
        TPM = player_box_scores[4]
        TPA = player_box_scores[5]
        FTM = player_box_scores[7]
        FTA = player_box_scores[8]
        ORB = player_box_scores[10]
        DRB = player_box_scores[11]
        assists = player_box_scores[13]
        steals = player_box_scores[14]
        blocks = player_box_scores[15]
        TO = player_box_scores[16]
        PF = player_box_scores[17]
        plus_minus = player_box_scores[19]
        box_score = Box_Score(game_link=link, player_name=player_name, home=home, played=True, started=True, seconds=seconds, FGM=FGM, FGA=FGA, TPM=TPM, TPA=TPA, FTM=FTM, FTA=FTA, ORB=ORB, DRB=DRB, assists=assists, steals=steals, blocks=blocks, TO=TO, PF=PF, plus_minus=plus_minus)

        boxscores.append(box_score)

    for i in range(17, len(team_rows), 2):
        player_name = team_rows[i]

        # We need to have a look in the boxscore to find out if the non-starting palyers actually Played
        # Therefore, we save the box score string for the player, and check if the first three characters are DNP
        box_string = team_rows[i + 1]

        if box_string[0:2] == "DNP" or box_string[0:2] == "DND":
            box_score = Box_Score(game_link=link, player_name=player_name, home=home, played=False, started=False, seconds=0, FGM=0, FGA=0, TPM=0, TPA=0, FTM=0, FTA=0, ORB=0, DRB=0, assists=0, steals=0, blocks=0, TO=0, PF=0, plus_minus=0)   
            
            boxscores.append(box_score)

        else:
            minutes = player_box_scores[0]
            seconds = get_seconds_from_minutes(minutes)
            FGM = player_box_scores[1]
            FGA = player_box_scores[2]
            TPM = player_box_scores[4]
            TPA = player_box_scores[5]
            FTM = player_box_scores[7]
            FTA = player_box_scores[8]
            ORB = player_box_scores[10]
            DRB = player_box_scores[11]
            assists = player_box_scores[13]
            steals = player_box_scores[14]
            blocks = player_box_scores[15]
            TO = player_box_scores[16]
            PF = player_box_scores[17]
            plus_minus = player_box_scores[19]
            box_score = Box_Score(game_link=link, player_name=player_name, home=home, played=True, started=True, seconds=seconds, FGM=FGM, FGA=FGA, TPM=TPM, TPA=TPA, FTM=FTM, FTA=FTA, ORB=ORB, DRB=DRB, assists=assists, steals=steals, blocks=blocks, TO=TO, PF=PF, plus_minus=plus_minus)   
            
            boxscores.append(box_score)
        
        return starting_players, boxscores

def get_seconds_from_minutes(minutes):
    if len(minutes) < 2:
        return 0
    if minutes[1] == ":":
        mins = int(minutes[0])
        secs = int(minutes[2:])
        total = (mins * 60) + secs
        return total
    elif minutes[2] == ":":
        mins = int(minutes[:2])
        secs = int(minutes[3:])
        total = (mins * 60) + secs
        return total
    elif minutes[1] == ".":
        return int(minutes[0])
    elif minutes[2] == ".":
        return int(minutes[:2])
    else:
        return 0

def get_plays(game_link, plays, starters):
    play_objects = list()
    
    period = 1
    last_seconds = 720
    away_players = starters[:5]
    home_players = starters[5:]

    for play in plays:
        information_pieces = play.split('\n')
        
        if len(information_pieces) == 0:
            continue
            
        minutes_string = information_pieces[0]
        seconds = get_seconds_from_minutes(minutes_string)
        if (seconds > last_seconds):
            period += 1
        last_seconds = seconds

    return plays


def save_game_data(game_object):
    ____

if __name__ == '__main__':
    main()
