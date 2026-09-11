from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration settings for the application."""

    # Add your configuration fields here
    OPENAI_BASE_URL:str
    OPENAI_API_KEY:str  
    MODEL_NAME :str
    TEMPRATURE:float    

    # =========================================================
    # Tavily
    # =========================================================

    TAVILY_API_KEY:str
    TAVILY_MCP_URL :str


    # ========================================================
    # AviationStack
    # ========================================================

    AVIATION_STACK_API_KEY:str

    # Development:
    AVIATION_MCP_TRANSPORT:str

    # =========================================================
    # Weather
    # =========================================================

    OPENWEATHER_API_KEY:str

    # Development:
    WEATHER_MCP_TRANSPORT:str


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()