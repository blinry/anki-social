from anki.collection import Collection
import datetime
import glob
import appdirs

path = glob.glob(appdirs.user_config_dir(appname="anki") + "/**/collection.anki2")

if len(path) == 0:
    print("No Anki collection found")
    exit(1)

col = Collection(path[0])

def timestamp(dt):
    return int(dt.timestamp()*1000)

def dt(timestamp):
    return datetime.datetime.fromtimestamp(timestamp/1000)

def section(name):
    print("\n" + name)
    print("="*len(name))
    print()

now = datetime.datetime.now()
last_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

section("Totals")
cards = col.db.scalar("select count() from cards")
print("You have %d cards." % cards)
reviews = col.db.scalar("select count() from revlog")
first_review = col.db.scalar("select min(id) from revlog")
days_since_first_review = (now - dt(first_review)).days
reviews_per_day = reviews / days_since_first_review
print("You did %d reviews since %s (that's %.2f reviews per day)." % (reviews, dt(first_review).strftime("%Y-%m-%d"), reviews_per_day))

section("Reviews")
streak = 0
for days_ago in range(14):
    from_time = last_midnight - datetime.timedelta(days=days_ago)
    to_time = last_midnight - datetime.timedelta(days=days_ago-1)

    count = col.db.scalar("select count() from revlog where id > ? and id < ?",
            timestamp(from_time), timestamp(to_time))
    print("On %s, you did %d reviews" % (from_time.strftime("%Y-%m-%d"), count))
    if count > 0:
        streak += 1
    else:
        streak = 0
print("\nYou are on a %d-day streak!" % streak)

section("Creations")
for months_ago in range(1,12):
    from_time = last_midnight - datetime.timedelta(days=30*months_ago)
    to_time = last_midnight - datetime.timedelta(days=30*(months_ago-1))

    created = col.db.scalar("select count() from cards where id > ? and id < ?",
            timestamp(from_time), timestamp(to_time))

    print("Between %s and %s, you created %d cards" % (from_time.strftime("%Y-%m-%d"), to_time.strftime("%Y-%m-%d"), created))

col.close()
