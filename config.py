"""Load configuration from environment variables."""
import os


def get_config():
    """Return all config values from environment.

    Tries .env file first via python-dotenv if available.
    Returns dict with all config keys.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    return {
        "github_token": os.getenv("GITHUB_TOKEN", ""),
        "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "qq_smtp_user": os.getenv("QQ_SMTP_USER", ""),
        "qq_smtp_pass": os.getenv("QQ_SMTP_PASS", ""),
    }
