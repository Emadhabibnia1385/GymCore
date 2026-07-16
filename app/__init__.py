"""GymCore — fitness coach management platform.

Clean architecture layers:
    models   -> SQLAlchemy ORM entities (persistence)
    services -> business logic (the only place rules live)
    api      -> REST API (/api/v1) for web, bots and future mobile app
    web      -> server-rendered Persian admin panel + client dashboard
    bots     -> Telegram & Bale bots sharing one platform-agnostic core
"""

__version__ = "1.0.0"
