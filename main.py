import os
import logging
from configs.config import ENV_PATH
from dotenv import load_dotenv


def main(request):
    event = request.headers.get('X-GitHub-Event', None)
    action = request.json.get('action', None)
    
    load_dotenv(ENV_PATH)

    # 设置初始化变量
    github_token = os.environ.get("GITHUB_TOKEN", "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")
    jira_token = os.environ.get("JIRA_TOKEN", "MTc1MzkxNDQzNDM1OmIrUkY7t1ywEYNYg+YO8UiYB66j")
    jira_root_url = os.environ.get("JIRA_ROOT_URL", "https://ix.jira.automotive.cloud/")
    github_username = os.environ.get("GITHUB_USERNAME", "uih50651")
    ai_token = os.environ.get("AI_API_KEY", "OujZtHKBv4PHXtfqQveh2S_gO8bvsUl8nosh5WK1-H8")
    ai_url = os.environ.get("AI_BASE_URL", "https://contivity.aws3116.ec1.aws.automotive.cloud:446/")
    ai_model_name = os.environ.get("AI_MODEL_NAME", "VIO:Gemini 2.5 Pro")
    local_ai_api_key = os.environ.get("LOCAL_AI_API_KEY", "")
    local_ai_base_url = os.environ.get("LOCAL_AI_BASE_URL", "http://10.214.142.119:8666/v1")
    local_ai_model_name = os.environ.get("LOCAL_AI_MODEL_NAME", "deepseek-reasoner")
    db_sheet_name = os.environ.get("SQL_TABLE", "model_pullrequest")
    db_config = {
        'database': os.environ.get("SQL_DBNAME", "ai_ops_db"),
        'user': os.environ.get("SQL_USER", "ai_ops"),
        'password': os.environ.get("SQL_PASSWORD", "Conti12345!"),
        'host': os.environ.get("SQL_HOST", "10.214.149.31"),
        'port': os.environ.get("SQL_PORT", "5432"),
    }
    logger = logging.getLogger(__name__)
    logger.info("------------------Initialize RevBot------------------")

    # Log parameters
    logger.info(f"GITHUB_TOKEN={'***' if github_token else ''}")
    logger.info(f"JIRA_TOKEN={'***' if jira_token else ''}")
    logger.info(f"JIRA_ROOT_URL={jira_root_url}")
    logger.info(f"GITHUB_USERNAME={github_username}")
    logger.info(f"AI_API_KEY={'***' if ai_token else ''}")
    logger.info(f"AI_BASE_URL={ai_url}")
    logger.info(f"AI_MODEL_NAME={ai_model_name}")
    logger.info(f"LOCAL_AI_API_KEY={'***' if local_ai_api_key else ''}")
    logger.info(f"LOCAL_AI_BASE_URL={local_ai_base_url}")
    logger.info(f"LOCAL_AI_MODEL_NAME={local_ai_model_name}")
    logger.info(f"SQL_DBNAME={db_config['database']}")
    logger.info(f"SQL_USER={db_config['user']}")
    logger.info(f"SQL_PASSWORD={'***' if db_config['password'] else ''}")
    logger.info(f"SQL_HOST={db_config['host']}")
    logger.info(f"SQL_PORT={db_config['port']}")
    logger.info(f"SQL_TABLE={db_sheet_name}")

    project = request.json.get('repository', {}).get("owner", {}).get("login", "")

    if project == 'chy-e0x-25-zcu':
        from src.chery_zcu_revbot import CheryZCU as AICodeReviewOrchestrator

    elif project == 'gee-crx-24-zcu':
        from src.geely_zcu_revbot import GeelyZCU as AICodeReviewOrchestrator

    else:
        from src.RevBot import AICodeReviewOrchestrator

    logger.info(f"PR_URL={request.json.get('pull_request', {}).get('html_url', '')}, EVENT={event}, ACTION={action}")

    revbot = AICodeReviewOrchestrator(
        github_token=github_token,
        jira_token=jira_token,
        jira_root_url=jira_root_url,
        github_username=github_username,
        ai_token=ai_token,
        ai_url=ai_url,
        ai_model_name=ai_model_name,
        local_ai_api_key=local_ai_api_key,
        local_ai_base_url=local_ai_base_url,
        local_ai_model_name=local_ai_model_name,
        db_sheet_name=db_sheet_name,
        db_config=db_config,
        request=request
    )
    revbot.main()
    return "OK", 200
