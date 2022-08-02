from pathlib import Path
import sqlite3
import datetime
import glob
import appdirs
import os

def find_anki_db():
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

path = find_anki_db()
if not path:
    print("No Anki collection found")
    exit(1)

con = sqlite3.connect("file:"+path+"?immutable=1", uri=True)

def timestamp(dt):
    return int(dt.timestamp()*1000)

def dt(timestamp):
    return datetime.datetime.fromtimestamp(timestamp/1000)

def section(name):
    print("\n" + name)
    print("="*len(name))
    print()

def scalar(query, arguments=()):
    return con.execute(query, arguments).fetchone()[0]

achievements = []
next_achievements = []
def achievement_ladder(name, value, steps):
    for step in steps:
        if value >= step:
            achievements.append(name.format(step))
        else:
            next_achievements.append(name.format(step) + " (currently {})".format(value))
            break

now = datetime.datetime.now()
last_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

section("Totals")
cards = scalar("select count() from cards")
print("You have %d cards." % cards)
reviews = scalar("select count() from revlog")
first_review = scalar("select min(id) from revlog")
days_since_first_review = (now - dt(first_review)).days
reviews_per_day = reviews / days_since_first_review
print("You did %d reviews since %s (that's %.2f reviews per day)." % (reviews, dt(first_review).strftime("%Y-%m-%d"), reviews_per_day))
achievement_ladder("{} reviews in total", reviews, [10, 50, 100, 1000, 5000, 10000, 50000, 100000])
seconds_spent = scalar("select sum(time)/1000 from revlog")
minutes_spent = int(seconds_spent / 60)
hours_spent = int(minutes_spent / 60)
days_spent = int(hours_spent / 24)
if days_spent > 1:
    print("You spent %d days reviewing cards." % days_spent)
elif hours_spent > 1:
    print("You spent %d hours reviewing cards." % hours_spent)
else:
    print("You spent %d minutes reviewing cards." % minutes_spent)
print("(That's %.2f minutes per day)." % (minutes_spent / days_since_first_review))
achievement_ladder("{} minutes spent reviewing cards", minutes_spent, [10, 30])
achievement_ladder("{} hours spent reviewing cards", hours_spent, [1, 3, 10])
achievement_ladder("{} days spent reviewing cards", days_spent, [1, 3, 7, 14, 30])

section("Reviews")
streak = 0
current_streak = 0
max_streak = 0
current = True
for days_ago in range(365*10):
    from_time = last_midnight - datetime.timedelta(days=days_ago)
    to_time = last_midnight - datetime.timedelta(days=days_ago-1)

    count = scalar("select count() from revlog where id > ? and id < ?",
            (timestamp(from_time), timestamp(to_time)))
    if days_ago <= 14:
        print("On %s, you did %d reviews" % (from_time.strftime("%Y-%m-%d"), count))
    if count > 0:
        streak += 1
    else:
        if current:
            current_streak = streak
            current = False
        max_streak = max(streak, max_streak)
        streak = 0
print("\nYou are on a %d-day streak!" % current_streak)
achievement_ladder("{}-day current streak", current_streak, [3, 7, 14, 30, 50, 75, 125, 180, 250, 365])
print("Your best streak was a %d-day streak!" % max_streak)
achievement_ladder("{}-day maximum streak", max_streak, [3, 7, 14, 30, 50, 75, 125, 180, 250, 365])

section("Creations")
for months_ago in range(1,12):
    from_time = last_midnight - datetime.timedelta(days=30*months_ago)
    to_time = last_midnight - datetime.timedelta(days=30*(months_ago-1))

    created = scalar("select count() from cards where id > ? and id < ?",
            (timestamp(from_time), timestamp(to_time)))

    print("Between %s and %s, you created %d cards" % (from_time.strftime("%Y-%m-%d"), to_time.strftime("%Y-%m-%d"), created))

section("Your achievements")
for achievement in achievements:
    print(achievement)

section("Upcoming achievements")
for achievement in next_achievements:
    print(achievement)

con.close()
