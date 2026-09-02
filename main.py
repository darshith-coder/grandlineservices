import os
import staypresent

# Creates a web service for Render to check
staypresent.web.json({"status": "running"})

# This wraps your bot, restarting it if it crashes
staypresent.run(
    "bot.py",
    port=int(os.getenv("PORT", 8080)),
    restart_on_crash=True,
    max_restarts=5,
    restart_delay=2.0
)
