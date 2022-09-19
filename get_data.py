import requests
from datetime import date, datetime, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time
import mysql.connector
from mysql.connector import Error

mySQL_username = 'root'
mySQL_password = 'Dexter123£'
mySQL_host_name = '127.0.0.0'
mySQL_database_name = 'NbaData'

def main():
    # first we get the data we want from the NBA website - I STILL NEED TO IMPLEMENT THE DAYS BIT OF IT
    games_data = get_data(days)
    for game in games_data:
        #then we add the data to our database
        add_game_to_database(game["date"], game["home"], game["away"])
        starters_info = add_boxscore_to_database(game["date"], game["home_scores"], game["away_scores"])
        add_plays_to_database(game["date"], game["home"], game["away"], starters_info)
    print('all finished')



def get_data(days):
    #make sure that the correct data type is passed into the get_data() function
    if type(days) is not int:
        print('non-integer passed into get_data() function')
        return []
    if days <= 0:
        print('invalid number passed into get_data() function')
        return []

    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    prefix = 'https://www.nba.com/games?date='

    #this variable will save the links for each of the games in the date range that we are looking at
    game_links = []

    #this goes back over a number of days to get the HTTP links for the games that happened on those days.  currently, it is hard coded for one day (i.e., yesterday)
    for n in range(1):
        #these lines just get the date in the format used by the NBA website
        nth_date = date.today() + timedelta(-1 + n)
        date_string = nth_date.strftime("%Y-%m-%d")
        #now we make a request for the webpage summarising the games on thaat date
        nth_day_webpage_response = requests.get(prefix + date_string)
        #we do some BS to get the links to the pages for the individual gamse
        nth_day_webpage = nth_day_webpage_response.content
        nth_day_html = BeautifulSoup(nth_day_webpage, "html.parser")
        nth_day_games_links = nth_day_html.select("a")
        #the only way I could think to do this with BS is to get all the links, and then filter out the ones that are not for game pages
        for game in nth_day_games_links:
            if game["href"][0:5] == "/game" and len(game["href"]) == 27:
                link = "https://www.nba.com" + game["href"]
                #now we save the link to the game_links list
                if [link, date_string] not in game_links:
                    game_links.append([link, date_string])

    #now we make a list of all the games that we are looking at.  Currently empty
    games = []

    #we iterate through the links, and for each one get the box score, and the play-by-play.
    #had to use Selenium for this one, as the info was loaded through JS and not in the HTML
    for game in game_links:
        driver.get(game[0] + "/box-score")
        headers = driver.find_elements(By.TAG_NAME, "h1")
        #all of the info for each game is going to be saved in a dictionary to make it easier to access each specific bit of info later
        the_game = {
            "date": game[1]
        }
        for h in headers:
            spans = h.find_elements(By.TAG_NAME, "span")
            for s in spans:
                if "away" not in the_game:
                    the_game["away"] = s.text
                else:
                    the_game["home"] = s.text
        boxes = driver.find_elements(By.TAG_NAME, "table")
        for b in boxes:
            if "away_scores" not in the_game:
                the_game["away_scores"] = b.text
            else:
                the_game["home_scores"] = b.text


        driver.get(game[0] + "/play-by-play?period=All")
        play_elements = driver.find_elements(By.TAG_NAME, "article")
        plays = []
        for p in play_elements:
            plays.append(p.text)
        the_game["plays"] = plays

        if the_game not in games:
            games.append(the_game)
    #Now we have all of the info for each of the games, we can close the driver
    driver.quit()

    return games



def add_game_to_database(date, home_team, away_team):
    try:
        connection = mysql.connector.connect(host=mySQL_host_name,
                                         database=mySQL_database_name,
                                         user=mySQL_username,
                                         password=mySQL_password)
        query_string = "INSERT INTO games (date, AwayTeam, HomeTeam) VALUES ({Date}, {Away_team}, {Home_team});".format(Date = date, Away_team = away_team, Home_team = home_team)

        cursor = connection.cursor()
        cursor.execute(query_string)
        connection.commit()

    except Error as e:
        print("Error while connecting to MySQL", e)
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


# This function gets the player ID from SQL and takes the player that you're looking for's name as an argument
def get_player_ID(player_name):
    player_id;

    # Make a SQL query to find the player_id
    try:
        connection = mysql.connector.connect(host=mySQL_host_name,
                                         database=mySQL_database_name,
                                         user=mySQL_username,
                                         password=mySQL_password)
        player_Query = "IF EXISTS (SELECT playerID FROM NbaData.players WHERE playerName = {name}) BEGIN SELECT playerID FROM NbaData.players WHERE playerName = {name} END ELSE SELECT '';".format(name = player_name)
        cursor = connection.cursor()
        cursor.execute(game_Query)
        player_results = cursor.fetchall()
        # we should check that this actually returns an ID
        if len(player_results) == 0:
            player_id = "none"
        else:
            player_id = player_results[0]
    except mysql.connector.Error as e:
        print("Error reading data from MySQL table", e)
    finally:
        if connection.is_connected():
            connection.close()
            cursor.close()

    # If no ID was returned, then we need to add the player to the database
    if player_id == 'none':
        try:
            connection = mysql.connector.connect(host=mySQL_host_name,
                                             database=mySQL_database_name,
                                             user=mySQL_username,
                                             password=mySQL_password)
            add_player_query = "INSERT INTO players (playerName) VALUES ({player_Name});".format(player_Name = player_name)
            cursor = connection.cursor()
            cursor.execute(query_string)
            connection.commit()
        except Error as e:
            print("Error while connecting to MySQL", e)
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
        # Then we still need to get the ID of this newly added player
        # We can do this recursively
        return get_player_ID(player_name)

    else:
        return player_id



def add_row_to_boxscore_table(game_id, player_id, Home, played, started, minutes, fieldGoalsMade, foeldGoalsAttempted, threePointersMade, threePointersAttempted, freeThrowsMade, freeThrowsAttempted, offensiveRebounds, defensiveRebounds, rebounds, assists, steals, blocks, turnOvers, personalFouls, plusMinue):
    try:
        connection = mysql.connector.connect(host=mySQL_host_name,
                                         database=mySQL_database_name,
                                         user=mySQL_username,
                                         password=mySQL_password)
        add_player_query = "INSERT INTO boxScores (game_id, player_id, Home, played, started, minutes, fieldGoalsMade, foeldGoalsAttempted, threePointersMade, threePointersAttempted, freeThrowsMade, freeThrowsAttempted, offensiveRebounds, defensiveRebounds, rebounds, assists, steals, blocks, turnOvers, personalFouls, plusMinue) VALUES ({Game_id}, {Player_id}, {HOme}, {Played}, {Started}, {Minutes}, {FieldGoalsMade}, {FoeldGoalsAttempted}, {ThreePointersMade}, {ThreePointersAttempted}, {FreeThrowsMade}, {FreeThrowsAttempted}, {OffensiveRebounds}, {DefensiveRebounds}, {Rebounds}, {Assists}, {Steals}, {Blocks}, {TurnOvers}, {PersonalFouls}, {PlusMinue});".format(Game_id = game_id, Player_id = player_id, HOme = Home, Played = played, Started = started, Minutes = minutes, FieldGoalsMade = fieldGoalsMade, FoeldGoalsAttempts = foeldGoalsAttempted, ThreePointersMade = threePointersMade, ThreePointersAttempted = threePointersAttempted, FreeThrowsMade = freeThrowsMade, FreeThrowsAttempted = freeThrowsAttempted, OffensiveRebounds = offensiveRebounds, DefensiveRebounds = defensiveRebounds, Rebounds = rebounds, Assists = assists, Steals = steals, Blocks = blocks, TurnOvers = turnOvers, PersonalFouls = personalFouls, PlusMinue = plusMinue)
        cursor = connection.cursor()
        cursor.execute(query_string)
        connection.commit()
    except Error as e:
        print("Error while connecting to MySQL", e)
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()



def add_boxscores_to_database(date, home_box, away_box):
# This function adds all of the information for a game to the the boxscore executable_path
# This function returns a list of the starting players in this game

    # Firstly, we want to get the game id, so that we can add it to all of the boxscore entries for this game.
    game_id;
    try:
        connection = mysql.connector.connect(host=mySQL_host_name,
                                         database=mySQL_database_name,
                                         user=mySQL_username,
                                         password=mySQL_password)
        game_Query = "SELECT id FROM NbaData.games WHERE AwayTeam = {awayTeam} AND HomeTeam = {homeTeam} AND date;".format(awayTeam = away_team, homeTeam = home_team)
        cursor = connection.cursor()
        cursor.execute(game_Query)
        game_results = cursor.fetchall()
        game_id = game_results[0]
    except mysql.connector.Error as e:
        print("Error reading data from MySQL table", e)
    finally:
        if connection.is_connected():
            connection.close()
            cursor.close()

    away_players = add_team_boxscore_to_database(game_id, away_box, False)
    home_players = add_team_boxscore_to_database(game_id, home_box, True)

    return away_players + home_players


def add_team_boxscore_to_database(game_id, team_box, Home)
# This function adds the scores for an individual team to the boxscore database
# This function returns the staring players for said team

    starting_players = []

    # Then, we want to seperate out all of the individual rows of the box_score
    # The rows are separated by new lines
    team_rows = team_box.split('\n')

    # the first row is always the header of the columns, and so we can ignore
    # After that, the name and starting position of each player are on seperate lines to that player's box score
    # Therefore, we will get the starters' info first (as they have three lines each), and then the bench's info.
    for i in range(1, 17, 3):

        # First info is player_name.  We will need to turn this into a player_ID by consulting the players table
        player_name = team_rows[i]
        player_id = get_player_ID(player_name);

        # We also append the player id to the list of starting players so that we can later pass this into the play-by-play database
        starting_players.append(player_id);

        # The player's presence in this section of the box score already tells us that they played and started for the home team
        home = Home
        played = True
        started = True

        # Now we can seperate out the individual box scores (they are seperated by spaces) and assign them to variables
        player_box_scores = team_rows[i + 2].split()

        minutes = player_box_scores[0];
        fieldGoalsMade = player_box_scores[1];
        foeldGoalsAttempted = player_box_scores[2];
        threePointersMade = player_box_scores[4];
        threePointersAttempted = player_box_scores[5];
        freeThrowsMade = player_box_scores[7];
        freeThrowsAttempted = player_box_scores[8];
        offensiveRebounds = player_box_scores[10];
        defensiveRebounds = player_box_scores[11];
        rebounds = player_box_scores[12];
        assists = player_box_scores[13];
        steals = player_box_scores[14];
        blocks = player_box_scores[15];
        turnOvers = player_box_scores[16];
        personalFouls = player_box_scores[17];
        plusMinue = player_box_scores[19];
        add_row_to_boxscore_table(game_id, player_id, home, played, started, minutes, fieldGoalsMade, foeldGoalsAttempted, threePointersMade, threePointersAttempted, freeThrowsMade, freeThrowsAttempted, offensiveRebounds, defensiveRebounds, rebounds, assists, steals, blocks, turnOvers, personalFouls, plusMinue)

    for i in range(17, len(team_rows), 2):
        player_name = team_rows[i]
        player_id = get_player_ID(player_name);

        # The player's presence in this section of the box score already tells us that they played and started for the home team
        home = Home
        started = False

        # We need to have a look in the boxscore to find out if the non-starting palyers actually Played
        # Therefore, we save the box score string for the player, and check if the first three characters are DNP
        played;
        box_string = team_rows[i + 1]
        if box_string[0:2] == "DNP"
            played = False
            add_row_to_boxscore_table(game_id, player_id, home, played, started, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        else:
            played = True
            player_box_scores = home_rows[i + 1].split()
            minutes = player_box_scores[0];
            fieldGoalsMade = player_box_scores[1];
            foeldGoalsAttempted = player_box_scores[2];
            threePointersMade = player_box_scores[4];
            threePointersAttempted = player_box_scores[5];
            freeThrowsMade = player_box_scores[7];
            freeThrowsAttempted = player_box_scores[8];
            offensiveRebounds = player_box_scores[10];
            defensiveRebounds = player_box_scores[11];
            rebounds = player_box_scores[12];
            assists = player_box_scores[13];
            steals = player_box_scores[14];
            blocks = player_box_scores[15];
            turnOvers = player_box_scores[16];
            personalFouls = player_box_scores[17];
            plusMinue = player_box_scores[19];
            add_row_to_boxscore_table(game_id, player_id, Home, played, started, minutes, fieldGoalsMade, foeldGoalsAttempted, threePointersMade, threePointersAttempted, freeThrowsMade, freeThrowsAttempted, offensiveRebounds, defensiveRebounds, rebounds, assists, steals, blocks, turnOvers, personalFouls, plusMinue)
    return starting_players



def add_plays_to_database(date, home_team, away_team, plays, starters):
    # This function makes sense of the information from the play-by-play starting_players
    period = '1'
    last_minutes = datetime.strptime("12:00", "%M:%S")
    away_players = starters[:5]
    home_players = [5:]
    for play in plays:
        information_pieces = play.split('\n')
        if len(information_pieces == 0):
            pass
        else:
            minutes = datetime.strptime(information_pieces[0], "%M:%S")
            if (minutes > last_minutes):
                period = next_period(period)
            last_minutes = minutes
            minutes_string = minute.strftime("%M:%S")




def add_play_to_database(game_id, player_id, home, game_period, minutes, shot, free_throw, made, distance, type_of_shot, assist, rebound, offensive, home_time_out, away_time_out, jump_ball_win, jump_ball_loss, violation, violation_text, foul, turnover, steal, block, substitution, incoming_player)


def next_period(previous_period):
    if previous_period == '1':
        return '2'
    else if previous_period == '2':
        return '3'
    else if previous_period == '3':
        return '4'
    else:
        return 'OT'



if __name__ == '__main__':
    main()
