import sqlite3
conn = sqlite3.connect("db.sqlite3")
cur = conn.cursor()

# Add bloom_level column if it doesn't exist
cur.execute("PRAGMA table_info(material_question)")
cols = [row[1] for row in cur.fetchall()]
print("Current columns:", cols)

if 'bloom_level' not in cols:
    cur.execute("""
        ALTER TABLE material_question
        ADD COLUMN bloom_level integer NULL
    """)
    print("Added bloom_level column")
else:
    print("bloom_level column already exists")

# Register migration in django_migrations table
cur.execute("SELECT name FROM django_migrations WHERE name='0017_question_bloom_level_question_completar_blank'")
if not cur.fetchone():
    import datetime
    cur.execute(
        "INSERT INTO django_migrations (app, name, applied) VALUES (?, ?, ?)",
        ('material', '0017_question_bloom_level_question_completar_blank', datetime.datetime.now().isoformat())
    )
    print("Registered migration 0017 in django_migrations")
else:
    print("Migration 0017 already registered")

conn.commit()
conn.close()
print("Done.")

