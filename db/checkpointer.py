from config import settings


class CheckPointer:

    def __init__(self):
        self.database_url = (
            f"postgresql://"
            f"{settings.POSTGRES_USER}:"
            f"{settings.POSTGRES_PASSWORD}@"
            f"{settings.POSTGRES_HOST}:"
            f"{settings.POSTGRES_PORT}/"
            f"{settings.POSTGRES_DB}"
        )