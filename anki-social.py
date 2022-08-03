from pathlib import Path
import sqlite3
import datetime
import glob
import appdirs
import os
import sys
from dotenv import dotenv_values
from mastodon import Mastodon

def find_db_path():
    path = None
    for appname in ("anki", "Anki2"):
        path = glob.glob(appdirs.user_config_dir(appname=appname) + "/**/collection.anki2")
        if path:
            path = path[0]
            break
        path = glob.glob(appdirs.user_data_dir(appname=appname) + "/**/collection.anki2")
        if path:
            path = path[0]
            break
    if not path:
        path = str(Path.home()) + "/storage/shared/AnkiDroid/collection.anki2"
        if not os.path.exists(path):
            path = None
    return path

def timestamp(dt):
    return int(dt.timestamp()*1000)

def dt(timestamp):
    return datetime.datetime.fromtimestamp(timestamp/1000)

class Score:
    def generate_achievements_until(self, db, until):
        achievements = []
        value = self.calculate(db, until)
        for ladder_step in self.ladder:
            if value >= ladder_step:
                achievements.append(self.description.format(ladder_step))
        return achievements
    def upcoming(self, db, until):
        value = self.calculate(db, until)
        for ladder_step in self.ladder:
            if value < ladder_step:
                return "{}: {} (currently {})".format(self.name, ladder_step, value)
        return None

class SimpleScore(Score):
    def __init__(self, name, description, query, ladder):
        self.name = name
        self.description = description
        self.query = query
        self.ladder = ladder
    def calculate(self, db, up_to):
        up_to_ts = timestamp(up_to)
        return db.scalar(self.query, (up_to_ts,))

class StreakScore(Score):
    def __init__(self, name, description, current, ladder):
        self.name = name
        self.description = description
        self.current = current
        self.ladder = ladder
        self.diagram = ""
    def calculate(self, db, up_to):
        self.diagram = ""

        last_midnight = up_to.replace(hour=0, minute=0, second=0, microsecond=0)

        best_streak = 0
        streak = 0
        max_freeze_days = 2
        freeze_days_left = max_freeze_days
        for days_ago in range(10*365):
            from_time = last_midnight - datetime.timedelta(days=days_ago)
            to_time = last_midnight - datetime.timedelta(days=days_ago-1)

            count = db.scalar("select count() from revlog where id > ? and id < ?",
                    (timestamp(from_time), timestamp(to_time)))
            if count > 0:
                streak += 1
                self.diagram = "*" + self.diagram
                if streak > best_streak:
                    best_streak = streak
                freeze_days_left = max_freeze_days
            else:
                if freeze_days_left > 0:
                    freeze_days_left -= 1
                    self.diagram = "f" + self.diagram
                else:
                    if self.current:
                        self.diagram = "Streak diagram: " + self.diagram
                        return streak
                    else:
                        streak = 0
            if from_time.weekday() == 0:
                self.diagram = "|" + self.diagram

        if self.current:
            return streak
        else:
            self.diagram = ""
            return best_streak

class AnkiDB:
    def __init__(self, path):
        self.path = path
        self.con = sqlite3.connect("file:"+path+"?immutable=1", uri=True)
        self.scores = []

    def __del__(self):
        self.con.close()

    def add_score(self, score):
        self.scores.append(score)

    def scalar(self, query, arguments=()):
        return self.con.execute(query, arguments).fetchone()[0]

    def print_stats(self):
        print()
        for score in self.scores:
            value = score.calculate(self, datetime.datetime.now())
            if hasattr(score, "diagram") and score.diagram != "":
                print(score.diagram)
    def generate_achievements_since(self, until, since):
        achievements_now = []
        achievements_then = []
        for score in self.scores:
            achievements_now.extend(score.generate_achievements_until(self, until))
            achievements_then.extend(score.generate_achievements_until(self, since))
        new_achievements = list(set(achievements_now) - set(achievements_then))
        return new_achievements
    def upcoming_achievements(self, now):
        upcoming = []
        for score in self.scores:
            upcoming.append(score.upcoming(self, now))
        return upcoming

path = find_db_path()

if not path:
    print("Anki database not found")
    exit(1)

db = AnkiDB(path)
now = datetime.datetime.now()
last_run_file = sys.path[0]+'/last_run'

if os.path.exists(last_run_file):
    with open(last_run_file, 'r') as f:
        last_run = dt(int(f.read()))
else:
    print("Running script for the first time!")
    last_run = now

count_ladder = [10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000]
time_ladder = [0.5]
for hours in range(1,11):
    time_ladder.append(hours)
for hours in range(10,1001,10):
    time_ladder.append(hours)
streak_ladder = [3, 7, 14, 30, 50, 75, 125, 180, 250, 365, 500, 600, 800, 1000]

db.add_score(SimpleScore("reviews", "reviewed {} cards", "select count() from revlog where id < ?", count_ladder))
db.add_score(SimpleScore("cards added", "added {} cards", "select count() from cards where id < ?", count_ladder))
db.add_score(SimpleScore("hours studied", "studied for {} hours", "select sum(time)/1000/60/60 from revlog where id < ?", time_ladder))
db.add_score(StreakScore("current streak", "{}-day streak", True, streak_ladder))
db.add_score(StreakScore("best streak", "new best streak of {} days", False, streak_ladder))

db.print_stats()

achievements = db.generate_achievements_since(now, last_run)

toot = ""

if len(achievements) > 0:
    toot += "I got a new Anki achievement! #ankisocial\n"
    for achievement in achievements:
        toot += "\n- " + achievement
    print(">>>")
    print(toot)
    print("<<<")

    config = dotenv_values(".env")
    if "ACCESS_TOKEN" in config and "API_BASE_URL" in config:
        answer = input("Do you want to toot this? ")
        if answer == "y" or answer == "yes":
            mastodon = Mastodon(access_token = config["ACCESS_TOKEN"], api_base_url = config["API_BASE_URL"])
            mastodon.toot(toot)

upcoming = db.upcoming_achievements(now)

if len(upcoming) > 0:
    print("\nUpcoming achievements:\n")
    for achievement in upcoming:
        print("- " + achievement)

with open(last_run_file, 'w') as f:
    f.write(str(timestamp(now)))
