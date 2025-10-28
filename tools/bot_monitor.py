import requests
import datetime
from datetime import timedelta
import os

from dotenv import load_dotenv

from src.modules import EmailSender
from configs.config import GITHUB_URL, LOG_PATH, PROJECT_MAPPING, ENV_PATH

class WatchDog:
    def __init__(
            self, 
            github_username: str, 
            github_password: str,
            smtp_server: str,
            smtp_port: int,
            smtp_username: str,
            smtp_password: str,
            sender_email: str,
            recipients_email,
            tolerance = 3
        ):

        self.session = requests.Session()

        if github_username and github_password:
            self.session.auth = (github_username, github_password)

        self.email_sender = EmailSender(
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            sender_email=sender_email,
            recipients_email=recipients_email
        )

        self.tolerance = tolerance

        self.headers = {
            "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
        }
      
    def _get_past_one_hour_utc(self):
        """
        Calculates the UTC timestamp for one hour ago in ISO 8601 format.
        """
        one_hour_ago_utc = datetime.datetime.now(datetime.timezone.utc) - timedelta(minutes=60)
        return one_hour_ago_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _event_filter(self, event):
        event_type = event.get('type')

        if event_type == 'PushEvent':
            response = requests.get(event.get('actor').get('url'), headers=self.headers)
            user_info = response.json()
            if user_info.get('type') != 'Bot':
                return False
        elif event_type == 'PullRequestEvent' and event.get('payload').get('action') == 'opened':
            return True
        elif event_type == 'IssueCommentEvent' and event.get('actor').get('login') != 'uih50651':
            comment = event.get('payload').get('comment').get('body')
            if 'AI' in comment or '@uih50651' in comment:
                return True
        return False
        
    def _get_pr_count(self):
        start_time = self._get_past_one_hour_utc()

        events_list = []

        results = {}

        for owner in PROJECT_MAPPING:
            for repo in PROJECT_MAPPING[owner]['Repo']:

                all_events = []
                page = 1

                while True:
                    url = f"{GITHUB_URL}/api/v3/repos/{owner}/{repo}/events?per_page=100&page={page}"
                    try:
                        response = self.session.get(url, headers=self.headers)
                        response.raise_for_status()
                        events = response.json()
                    except Exception as e:
                        raise Exception(f"Failed to fetch events: {str(e)}")

                    if not events:
                        break

                    filtered_events = []
                    for event in events:
                        created_at = event.get('created_at')
                        
                        if created_at > start_time:
                            if self._event_filter(event):
                                filtered_events.append(event)
                                events_list.append(event)
                        else:
                            break
                    
                    all_events.extend(filtered_events)

                    if len(filtered_events) < len(events):
                        break

                    page += 1

                
                results[f'{repo}'] = {
                        "updated_pr_count": len(all_events)
                    }
                
        total_pr_count = sum(stats.get("updated_pr_count") for stats in results.values()) # get total pr count

        return total_pr_count, events_list
    
    def _get_revbot_count(self):
        success_count = 0
        error_count = 0
        github_url_list = []

        for k, v in PROJECT_MAPPING.items():
            log_file = os.path.join(LOG_PATH, v["Project"], 'log/watch_dog.log')

            one_hour_ago = datetime.datetime.now() - timedelta(hours=1)

            try:
                with open(log_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        timestamp_str, status, _, github_url = line.split(" - ")
                        run_time = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                        if run_time >= one_hour_ago:
                            if status == "SUCCESS":
                                success_count += 1
                            elif status == "ERROR":
                                error_count += 1
                            
                            github_url_list.append(github_url)
                        
            except FileNotFoundError:
                print(f"日志文件 {log_file} 不存在。")
                return 0, 0

        return success_count, error_count, github_url_list

    def comparison(self):
        success_count, error_count, github_url_list = self._get_revbot_count()

        total_revbot_count = success_count + error_count

        total_pr_count, events_list = self._get_pr_count()

        difference = abs(total_revbot_count - total_pr_count)

        if difference > self.tolerance:
            message = (
                f"RevBot运行异常: 过去一小时 \n"
            )
        
            message = message + (
                f"  - RevBot 运行 {total_revbot_count} 次\n"
                f"  - GitHub PR共 {total_pr_count} 次"
            )

            self.email_sender.send_email(body=message)

def main():
    wd = WatchDog(
        github_username = os.getenv("GITHUB_USERNAME"),
        github_password = os.getenv("GITHUB_PASSWORD"),
        smtp_server = os.getenv("SMTP_SERVER"),
        smtp_port = os.getenv("SMTP_PORT"),
        smtp_username = os.getenv("SMTP_USERNAME"),
        smtp_password = os.getenv("SMTP_PASSWORD"),
        sender_email = os.getenv("SENDER_EMAIL"),
        recipients_email = ['jiachen.2.lu@aumovio.com', 'shutong.li@aumovio.com'],
        tolerance = 3
    )

    wd.comparison()


if __name__ == '__main__':
    load_dotenv(ENV_PATH)

    main()

# crontab -e
# 0 * * * * bash /mnt/SHARE/cict_proj/99_Tools/RevBotV2/bot_monitor.sh
