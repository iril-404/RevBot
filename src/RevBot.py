import re
import json
from datetime import datetime, timedelta, timezone
import logging
import os
import openai
import httpx
import base64
import psycopg2
from psycopg2 import pool
import threading
from src.modules import setup_watchdog, AIPrReview
from configs.config import JIRA_URL, LOG_PATH, PROJECT_MAPPING
import requests

class AICodeReviewOrchestrator:
    def __init__(
        self,
        github_token="",
        jira_token="",
        jira_root_url=JIRA_URL,
        github_username="",
        ai_token="",
        ai_url="https://contivity.aws3116.ec1.aws.automotive.cloud:446",
        ai_model_name="VIO:Gemini 2.5 Pro",
        local_ai_api_key="",
        local_ai_base_url="http://10.214.142.119:8666/v1",
        local_ai_model_name="deepseek-reasoner",
        db_sheet_name="model_pullself.request",
        db_config=None,
        request=None
    ):
        self.github_token = github_token
        self.jira_token = jira_token
        self.jira_root_url = jira_root_url
        self.github_username = github_username
        self.ai_token = ai_token
        self.ai_url = ai_url
        self.ai_model_name = ai_model_name
        self.local_ai_api_key = local_ai_api_key
        self.local_ai_base_url = local_ai_base_url
        self.local_ai_model_name = local_ai_model_name
        self.db_sheet_name = db_sheet_name
        self.db_config = db_config
        self.request = request

        self.project = request.json.get('repository', {}).get("owner", {}).get("login", "")
        self.project_folder = PROJECT_MAPPING.get(self.project, {}).get("Project", "")
        self.repo_name = request.json.get('repository', {}).get("name", "")
        self.pr_number = request.json.get('pull_request', {}).get("number", 0)
        self.report_dir = os.path.join(LOG_PATH, self.project, "revbot_report")  # Directory to save review history
        if self.project_folder and self.repo_name and self.pr_number:
            self.setup_logging(self.report_dir, self.project_folder, self.repo_name, self.pr_number)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"AICodeReviewOrchestrator initialized for project: {self.project_folder}, repo: {self.repo_name}, PR: {self.pr_number}")

    # 日志配置：输出到文件，按日期分目录，文件名包含项目、仓库、PR号
    def setup_logging(self, report_dir, project, repo_name, pr_number):
        log_dir = os.path.join(report_dir, datetime.now().strftime('%Y%m'), datetime.now().strftime('%d'))
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{project}_{repo_name}_{pr_number}.log")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        logging.info(f"Logging setup complete. Log file: {log_file}")

    def _get_checklist_table(self):
        markdown_table = """
# 这是一个Checklist 的 demo 输出，用于测试RevBot在无法正确获得AI评估分数的情况下，返回的内容

# 请注意，这条评论应该仅仅出现在RevBot库中。

# 这是正常的特性，请不用担心。
"""

        return markdown_table

    def _get_prompt(self, ticket_detail, base_branch, repo, diff_content, language="zh"):
        if language == "zh":
            review_instruction = (
                "# 以下修改属于基于AI的代码自动审核项目，请根据 Jira 需求和对应的 Github Pull Request 变更进行代码审查，并评估合并风险。\n"
                "## 审查要求：\n"
                "1. 必须用中文回答。\n"
                "2. 对发现的问题可适当提供修改建议。\n"
                "3. 输出结果必须严格按照以下结构组织：\n"
                "   **1. 总体评价**：对整体代码质量、规范符合度、潜在风险进行综合评价。\n"
                "   **2. 逐一文件建议和分析**：按文件逐个分析变更内容，指出问题、规范违规情况及修改建议。\n"
                "   **3. 总结**：总结主要发现、风险等级及后续建议。\n"
                "   **4. 合并风险评估**：在最后一行只输出一个单词字符表示风险等级（low / medium / high），不要有解释或额外内容。\n"
            )

            merge_instruction = (
                "## 合并风险评估规则：\n"
                "- low：代码规范好，变更范围小，无明显风险。\n"
                "- medium：存在少量规范问题或潜在风险，但可以接受。\n"
                "- high：存在严重规范问题、潜在错误或设计缺陷，不建议直接合并。\n"
                "请根据你的整体分析，**在最终一行只输出一个单词字符作为合并风险结果（low / medium / high）**，不要输出多余内容或解释。"
            )

            question = (
                f"{review_instruction}\n"
                f"# 本次变更的 Jira 需求：\n{ticket_detail or '无'}\n\n"
                f"# 本次变更的目标分支：\n{base_branch}\n\n"
                f"# 仓库 {repo} 的 Pull Request 变更内容如下：\n{diff_content}\n\n"
                f"{merge_instruction}"
            )
        else:
            review_instruction = (
                "# The following changes are part of an AI-based code review project. Please conduct a code review based on the Jira requirements and the corresponding GitHub Pull Request changes, and assess the merge risk.\n"
                "## Review Requirements:\n"
                "1. Must respond in English.\n"
                "2. Provide modification suggestions for identified issues as appropriate.\n"
                "3. The output must be strictly organized according to the following structure:\n"
                "   **1. Overall Evaluation**: A comprehensive evaluation of overall code quality, compliance with standards, and potential risks.\n"
                "   **2. File-by-File Suggestions and Analysis**: Analyze the changes file by file, pointing out issues, standard violations, and modification suggestions.\n"
                "   **3. Summary**: Summarize the main findings, risk level, and follow-up recommendations.\n"
                "   **4. Merge Risk Assessment**: At the very end, output only a single word character indicating the risk level (low / medium / high), without explanations or additional content.\n"
            )

            merge_instruction = (
                "## Merge Risk Assessment Rules:\n"
                "- low: Good code standards, small change scope, no obvious risks.\n"
                "- medium: A few standard issues or potential risks exist but are acceptable.\n"
                "- high: Serious standard issues, potential errors, or design flaws exist; direct merging is not recommended.\n"
                "Based on your overall analysis, **output only a single word character as the final merge risk result (low / medium / high) in the last line**, without any extra content or explanations."
            )

            question = (
                f"{review_instruction}\n"
                f"# The Jira requirement for this change:\n{ticket_detail or 'None'}\n\n"
                f"# The target branch for this change:\n{base_branch}\n\n"
                f"# The Pull Request changes for repository {repo} are as follows:\n{diff_content}\n\n"
                f"{merge_instruction}"
            )

        return question

    def _get_failed_review_result(self, jira_link, pr_url):
        md_checklist = self._get_checklist_table()
        review_result = "*Due to multiple reasons, no code review from AI is available.*\n\n" + md_checklist

        self.logger.error("❌ AI code review failed with AI error")
        setup_watchdog(success=False, project=self.project, jira_link=jira_link, pr_url=pr_url)

        return review_result

    def _get_qtools_result_filter(self, changed_files, owner, repo):
        changed_files = ""
        owner = ""
        repo = ""
        return changed_files + owner + repo

    def ai_pr_review(self, git_diff_content="", db_payload={}, language="zh", jira_ticket_id="", jira_ticket_detail=""):
        repo_name = self.request.json.get("repository", {}).get("name", "")
        self.logger.info("Starting AI PR review process.")
        if not git_diff_content or not repo_name:
            self.logger.error("Failed to get PR diff content or repository name.")
            return "Failed to get PR diff content or repository name."
        base_ref = self.request.json.get('pull_request', {}).get('base', {}).get('ref', "")
        title = self.request.json.get('pull_request', {}).get('title', "")
        if not title:
            title = self.request.json.get('issue', {}).get('title', "")
            if not title:
                if language == "zh":
                    title = "无PR标题"
                else:
                    title = "No PR Title"
        
        # Qtools result filter
        pr_url = self.request.json.get('pull_request', {}).get('html_url', "")
        owner = self.request.json.get("repository", {}).get("owner", {}).get("login", "")
        changed_files = self.get_changes_list()
        db_payload["changed_files_list"] = changed_files
        self.logger.info(f"Changed files: {changed_files}")
        self.rule_descriptions = self._get_qtools_result_filter(changed_files, owner, repo_name)

        # Save Jira Thing to local
        pr_number = self.request.json.get('pull_request', {}).get("number", 0)
        self.logger.info(f"Saving PR history for PR number: {pr_number}")
        self.save_history(jira_ticket_id, jira_ticket_detail, owner, repo_name, pr_number, git_diff_content)

        # Get Prompt
        question = self._get_prompt(jira_ticket_detail, base_ref, repo_name, git_diff_content)
        self.logger.info("Prompt for AI review generated.")
        self.logger.info(f"AI Review Prompt: {question}")
        
        # Get Review from AI
        system_prompt = None
        review_result = self.ai_request(question=question, system_prompt=system_prompt, ai_model="VIO:Gemini 2.5 Pro")
        review_result = review_result.strip()
        jira_link = f"{self.jira_root_url}browse/{jira_ticket_id}" if jira_ticket_id else ""
        self.logger.info("AI review result received.")
        self.logger.info(f"AI Review Result: {review_result}")

        # VIO Switcher Adapter
        if not review_result:
            self.logger.warning("Get response from VIO and Local AI failed")
            review_result = self._get_failed_review_result(jira_link, pr_url)

        else:
            # Get Review Score from Review Result
            review_score = review_result.strip().splitlines()[-1].strip().lower()

            if review_score not in {"low", "medium", "high"}:
                db_payload["ai_risk_level"] = ""
                self.logger.warning(f"Unexpected merge risk value")
                print(review_result)
                review_score = review_result
                review_result = self._get_failed_review_result(jira_link, pr_url)

            else:
                db_payload["ai_risk_level"] = review_score
                review_score_ch = {
                    "low": "低",
                    "medium": "中等",
                    "high": "高"
                }[review_score]
                
                jira_summary = db_payload.get("jira_summary", "")
                if jira_summary:
                    pr_info_summary = f"本次PR基于Jira Ticket: **{jira_summary}**\n\n" + f"本次PR的Target Branch: **{base_ref}**\n\n" + f"本此AI代码审核结果为: 合并风险**{review_score_ch}**\n\n"

                    review_result = pr_info_summary + "---\n\n" + review_result
                else:
                    pr_info_summary = f"本次PR的Target Branch: **{base_ref}**\n\n" + f"本此AI代码审核结果为: 合并风险**{review_score_ch}**\n\n"

                    review_result = pr_info_summary + "---\n\n" + "*获取Jira Summary失败，请检查项目权限.*\n\n" + "*Review message from AI:*\n\n" + review_result

                self.logger.info("✅ AI code review completed successfully.")
                setup_watchdog(success=True, project=self.project, jira_link=jira_link, pr_url=pr_url)

                # DVAF-119 Reviwe评分 --> AI Post Check 
                score, reason = self._ai_post_check(
                    prompt=question, 
                    review_result=review_result, 
                    language='zh'
                )

                review_result = review_result + '\n---\n\n' + f'*AI Post Check*\nScore: {score}\nReason: {reason}'
        
        self.logger.info("------------------Terminate RevBot------------------")

        error_pattern = re.compile(r"^Error: data:|Error: Response generation timed out|^VIO API request exception:")
        if re.search(error_pattern, review_result):
            print(f"Error found in review result: {review_result}")
            if language == "zh":
                return "*Review message from AI:*\n\n非常抱歉，由于上下文（PR改动和评论）过多或者网络连接出错，我无法对这次改动进行审查。"
            else:
                return "*Review message from AI:*\n\nI'm sorry, but I cannot review this change due to excessive context (PR changes and comments) or network issues."
        else:
            review_result = "*Review message from AI:*\n\n" + review_result + "\n\n*Any question, you can ask me with 'AI' in your comment or @me.*"

        return review_result



    def _ai_post_check(self, prompt, review_result, language):
        self.logger.info("------------------Start AI Post Review------------------")

        ai = AIPrReview(
            vio_api_key = os.getenv("AI_API_KEY"), 
            vio_base_url = os.getenv("AI_BASE_URL"), 
            vio_model_name = 'VIO:GPT 5-chat',
            local_ai_api_key=os.environ.get("LOCAL_AI_API_KEY", ""), 
            local_ai_base_url=os.environ.get("LOCAL_AI_BASE_URL"), 
            local_ai_model_name=os.environ.get("LOCAL_AI_MODEL_NAME"), 
        )


        if language == "zh":
            question = (
                f"你是一个代码审核机器人，接下来我将提供一个输入给其他AI模型的Prompt：\n"
                f"{prompt}\n"
                f"以及其他AI返回的结果：\n"
                f"{review_result}\n"
                f"请评估该代码审核结果的准确性，指出是否存在明显错误。\n"
                f"请返回评分（0-100分）及简短理由。\n"
                f"请按以下格式返回：分数，理由。请不要添加其他内容。"
            )
        else:
            question = (
                f"You are a code review assistant. Below is a prompt provided to another AI model:\n"
                f"{prompt}\n"
                f"and the response received from the other AI:\n"
                f"{review_result}\n"
                f"Please assess the accuracy of the code review result and identify any obvious errors.\n"
                f"Return a score (0-100) along with a brief explanation.\n"
                f"Please respond in the following format: (score, explanation). Do not include anything else."
            )

        def parse_result(result):
            result = result.strip()
            
            if ',' in result:
                score, reason = result.split(',', 1)  # 分割一次，保证分数和原因分开
                score = int(score.strip())
                reason = reason.strip()
                
                return score, reason
            else:
                self.logger.error("Error: Invalid result format, no comma found.")
                self.logger.error("❌ AI Post Check failed!")
                return None, None

        max_retry = 2
        retry_count = 0 
        score, reason = None, None

        while retry_count <= max_retry:
            try:
                result = ai.chat(question=question)
                score, reason = parse_result(result)

                if 0 <= score <= 100 and isinstance(reason, str):
                    self.logger.error("✅ AI Post Check success!")
                    break

            except Exception as e:
                self.logger.error(f"Error encountered during AI post check: {str(e)}, retrying... ({retry_count + 1}/{MAX_RETRIES})")
                retry_count += 1  # 增加重试次数
                if retry_count > max_retry:
                    self.logger.error("Max retry attempts reached. Exiting.")
                    self.logger.error("❌ AI Post Check failed!")
                    break

        self.logger.info("------------------Terminate AI Post Review------------------")

        return score, reason

    def save_history(self, jira_ticket, ticket_detail, owner, repo, pr_number, diff_content):
        """
        Format historical changes for storage in vector database for RAG retrieval.
        Format: jira ticket requirement: ...\nuser's corresponding change: ...
        Directly write to self.report_dir/{owner}_{repo}/{pr_number_folder}/{pr_number}.txt
        pr_number_folder is the part of pr_number with the last two digits removed, pad with 0 if less than 100.
        On any error, exit the function directly.
        """
        try:
            subdir = datetime.now().strftime("%Y%m/%d")
            out_dir = os.path.join(self.report_dir, subdir)
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f"{owner}_{repo}_{pr_number}.txt")
            self.logger.info(f"Saving history to {out_path}")
            if ticket_detail:
                rag_text = (
                    "# 该次变更已合入主分支，以下为变更历史：\n\n"
                    f"# 该次代码提交关联的Jira ticket：{jira_ticket}\n\n"
                    f"# 该次代码提交的Jira需求：\n{ticket_detail}\n\n"
                    f"# 该次代码提交的PR Git Diff（以下仅列出仓库 {repo} 的变更内容）：\n{diff_content}"
                )
            else:
                rag_text = (
                    "# 该次变更已合入主分支，以下为变更历史：\n\n"
                    f"# 该次代码提交关联的Jira ticket：{jira_ticket}\n\n"
                    f"# 该次代码提交的PR Git Diff（以下仅列出仓库 {repo} 的变更内容）：\n{diff_content}"
                )
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(rag_text)
        except Exception as e:
            print(f"format_history_for_rag exception: {e}")
            return

    def get_code_owners(self, org_url=None, repo_url=None):
        base_ref = self.request.json.get('pull_request', {}).get('base', {}).get('ref', "")
        github_token = self.github_token
        if not github_token or not base_ref or not org_url or not repo_url:
            print("Missing github_token or base_ref or org_url or repo_url")
            return []
        # 获取 base branch 的 CODEOWNERS 文件
        headers = {"Authorization": f"token {github_token}"}
        codeowners_url = f"{repo_url}/contents/.github/CODEOWNERS?ref={base_ref}"
        try:
            resp = requests.get(codeowners_url, headers=headers, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch CODEOWNERS file: {e}")
            return []
        content = resp.json().get("content", "")
        decoded = base64.b64decode(content).decode("utf-8")
        org = None
        team = None
        for line in decoded.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            owner_str = parts[-1]
            if owner_str.startswith("@"):
                owner_str = owner_str[1:]
            if "/" in owner_str:
                org, team = owner_str.split("/", 1)
                break
        if not org or not team:
            print("No valid team owner found in CODEOWNERS file")
            return []
        # 自动获取参数
        team_url = f"{org_url}/teams/{team}/members"
        headers = {"Authorization": f"token {github_token}"}
        try:
            resp = requests.get(team_url, headers=headers, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch team members: {e}")
            return []
        members = resp.json()
        member_logins = [m.get("login", "") for m in members]
        return member_logins

    def check_review_approval_status(self, db_payload= {}, code_owners=None, repo_url=None):
        number = self.request.json.get('pull_request', {}).get("number", 0)
        github_token = self.github_token
        if not number or not code_owners or not repo_url:
            print("Missing pull self.request number or code_owners or repo_url")
            return

        # 获取所有 review 信息
        reviews_url = f"{repo_url}/pulls/{number}/reviews"
        headers = {"Authorization": f"token {github_token}"}
        try:
            resp = requests.get(reviews_url, headers=headers, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch reviews: {e}")
            return
        reviews = resp.json()

        approved_users = set()
        code_owner_approved = False
        for review in reviews:
            if review.get("state", "").lower() == "approved":
                user_login = review.get("user", {}).get("login", "")
                if user_login:
                    approved_users.add(user_login)
                    if user_login in code_owners:
                        code_owner_approved = True
        db_payload["review_code_owner_approved"] = code_owner_approved
        db_payload["review_satisfied"] = len(approved_users) >= 1

    def get_pr_diff(self, language="zh"):
        github_token = self.github_token
        repo_url = self.request.json.get("repository", {}).get("url", "")
        if not github_token or not repo_url:
            print("Missing github_token or repo_url")
            if language == "zh":
                return "缺少Github token或仓库链接，导致无法获取改动"
            else:
                return "Missing github_token or repo_url, unable to fetch changes"
        number = self.request.json.get('pull_request', {}).get("number", 0)
        if not number:
            # get from issue comment event
            number = self.request.json.get("issue", {}).get("number", 0)
            if not number:
                print("Missing pull self.request number")
                if language == "zh":
                    return "未获取到PR序号，导致无法获取改动"
                else:
                    return "Missing pull self.request number, unable to fetch changes"
        diff_url = f"{repo_url}/pulls/{number}.diff"
        headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3.diff"}
        try:
            resp = requests.get(diff_url, headers=headers, timeout=60)
            resp.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch PR diff: {e}")
            if language == "zh":
                return "该PR修改过多或者网络原因导致无法获取改动"
            else:
                return "The PR has too many changes or network issues prevent fetching changes"
        return resp.text

    def get_changes_list(self):
        github_token = self.github_token
        repo_url = self.request.json.get("repository", {}).get("url", "")
        if not github_token or not repo_url:
            print("Missing github_token or repo_url")
            return []
        number = self.request.json.get('pull_request', {}).get("number", 0)
        if not number:
            # get from issue comment event
            number = self.request.json.get("issue", {}).get("number", 0)
            if not number:
                print("Missing pull self.request number")
                return []
        files_url = f"{repo_url}/pulls/{number}/files"
        headers = {"Authorization": f"token {github_token}"}
        try:
            resp = requests.get(files_url, headers=headers, timeout=60)
            resp.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch PR changed files: {e}")
            return []
        files = resp.json()
        changed_files = [f.get("filename", "") for f in files]
        return changed_files

    def get_pr_number_from_commit(self):
        commit = self.request.json.get("commit", {}).get("sha", "")
        repo_url = self.request.json.get("repository", {}).get("url", "")
        pr_number = None
        github_token = self.github_token
        if not commit or not repo_url or not github_token:
            return None
        # repo_url: https://api.github.com/repos/owner/repo
        pulls_url = f"{repo_url}/commits/{commit}/pulls"
        headers = {
            "Accept": "application/vnd.github.groot-preview+json",
            "Authorization": f"token {github_token}"
        }
        try:
            resp = requests.get(pulls_url, headers=headers, timeout=30)
            resp.raise_for_status()
            pulls = resp.json()
            if pulls and isinstance(pulls, list):
                pr_number = pulls[0].get("number", None)
        except Exception as e:
            print(f"Failed to fetch PR from commit: {e}")
            pr_number = None
        return pr_number

    def get_jira_ticket_detail(self, jira_ticket_id, db_payload={}):
        url = f"{self.jira_root_url}rest/api/latest/issue/{jira_ticket_id}"
        headers = {
            "Authorization": f"Bearer {self.jira_token}",
            "Content-Type": "application/json"
        }
        try:
            resp = requests.get(url, headers=headers, timeout=60)
            resp.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch Jira ticket {jira_ticket_id}: {e}")
            return ""
        data = resp.json()
        fields = data.get('fields', {})
        summary = fields.get('summary', '')
        description = fields.get('description', '')
        details = []
        if summary:
            db_payload["jira_summary"] = summary
            details.append(f"Summary: {summary}")
        if description:
            db_payload["jira_description"] = description
            details.append(f"Description: {description}")
        jira_ticket_detail = "\n".join(details)
        db_payload["jira_issuetype"] = fields.get("issuetype", {}).get("name", "")
        db_payload["jira_fixversions"] = ",".join([v.get("name", "") for v in fields.get("fixVersions", [])]) if fields.get("fixVersions") else ""
        db_payload["jira_versions"] = ",".join([v.get("name", "") for v in fields.get("versions", [])]) if fields.get("versions") else ""
        db_payload["jira_components"] = ",".join([c.get("name", "") for c in fields.get("components", [])]) if fields.get("components") else ""
        db_payload["jira_labels"] = fields.get("labels", [])
        return jira_ticket_detail

    def ai_request(self, question="", system_prompt=None, ai_model="VIO:Gemini 2.5 Pro"):
        try:
            client = openai.OpenAI(
                api_key=self.ai_token,
                base_url=self.ai_url,
                http_client=httpx.Client(verify=False)
            )
        except Exception as e:
            return f"VIO API client initialization exception: {e}"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": question})
        response = client.chat.completions.create(
            model=ai_model,
            messages=messages
        )
        return response.choices[0].message.content

    def ai_pr_reply(self, user_name="", git_diff_content="", review_comments="", language="zh"): # TODO
        repo_name = self.request.json.get("repository", {}).get("name", "")
        if not git_diff_content or not repo_name or not user_name or not review_comments:
            return "Failed to get PR diff content or repository name or user name or user reply content or original review comments."
        title = self.request.json.get('issue', {}).get('title', "")
        if not title:
            title = self.request.json.get('pull_request', {}).get('title', "")
            if not title:
                if language == "zh":
                    title = "无PR标题"
                else:
                    title = "No PR Title"
        if len(git_diff_content) > 300000:
            git_diff_content = git_diff_content[:300000] + "\n...\n*The diff content is too long, has been truncated.*"
        # 优化后的AI提示词
        if language == "zh":
            question = f"""# 目标 (Goal)
用户{user_name}基于你的代码审查意见进行了回复，请你基于以下信息回答该用户，保持专业、客观、友好的语气和称谓。除非用户指出回复语言，否则使用中文回复。

# 该用户评论以及评论历史 (User Comment and History)
{review_comments}

# 上下文信息 (Contextual Information)
1. 当前时间日期为 {(datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')} Shanghai Time，当前为第 {(datetime.utcnow() + timedelta(hours=8)).isocalendar()[1]} 周。
2. **该PR的标题**
{title}
3.  **该PR的具体改动(Git Diff)，仅列出仓库 {repo_name} 的变更内容**:
{git_diff_content}
"""
        else:
            question = f"""# Goal
The user {user_name} has replied to your code review comments. Please respond to the user based on the information below, maintaining a professional, objective, and friendly tone and salutation. Unless the user specifies a reply language, respond in English.

# User Comment and History
{review_comments}

# Contextual Information
1. Current date and time: {(datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')} Shanghai Time, week {(datetime.utcnow() + timedelta(hours=8)).isocalendar()[1]}.
2. **PR Title**
{title}
3. **Specific changes (Git Diff), only for repository {repo_name}:**
{git_diff_content}
"""
        system_prompt = None
        review_result = self.ai_request(question=question, system_prompt=system_prompt, ai_model="VIO:Gemini 2.5 Pro")
        review_result = review_result.strip()
        error_pattern = re.compile(r"^Error: data:|Error: Response generation timed out|^VIO API self.request exception:")
        if re.search(error_pattern, review_result):
            print(f"Error found in review result: {review_result}")
            if language == "zh":
                return "非常抱歉，由于上下文（PR改动和评论）过多或者网络连接出错，我无法回复你的评论。"
            else:
                return "I'm sorry, but I cannot reply to your comment due to excessive context (PR changes and comments) or network issues."
        return review_result

    def create_ai_review_comment(self, review_result):
        repo_url = self.request.json.get("repository", {}).get("url", "")
        pr_number = self.request.json.get('pull_request', {}).get("number", 0)
        github_token = self.github_token
        if not repo_url or not pr_number or not github_token or not self.github_username:
            print("Missing repo_url, pr_number, or github_token or github_username")
            return False
        comments_url = f"{repo_url}/issues/{pr_number}/comments"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}"
        }
        try:
            resp = requests.get(comments_url, headers=headers, timeout=60)
            resp.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch PR comments: {e}")
            return False
        comments = resp.json()
        my_comment = None
        for c in comments:
            if c.get("user", {}).get("login", "").lower() == self.github_username.lower():
                my_comment = c
                break
        body = review_result
        if my_comment:
            comment_id = my_comment["id"]
            patch_url = f"{repo_url}/issues/comments/{comment_id}"
            patch_data = {"body": body}
            try:
                patch_resp = requests.patch(patch_url, json=patch_data, headers=headers, timeout=30)
                patch_resp.raise_for_status()
            except Exception as e:
                print(f"Failed to update AI review comment: {e}")
                return False
        else:
            data = {"body": body}
            try:
                post_resp = requests.post(comments_url, json=data, headers=headers, timeout=30)
                post_resp.raise_for_status()
            except Exception as e:
                print(f"Failed to create AI review comment: {e}")
                return False
        return True

    def create_ai_reply_comment(self, reply_result):
        repo_url = self.request.json.get("repository", {}).get("url", "")
        github_token = self.github_token
        if not repo_url or not github_token or not self.github_username:
            print("Missing repo_url, or github_token or github_username")
            return False
        pr_number = self.request.json.get("issue", {}).get("number", 0)
        if not pr_number:
            pr_number = self.request.json.get('pull_request', {}).get("number", 0)
            if not pr_number:
                print("Missing pull self.request number")
                return False
        comments_url = f"{repo_url}/issues/{pr_number}/comments"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}"
        }
        data = {"body": reply_result}
        try:
            post_resp = requests.post(comments_url, json=data, headers=headers, timeout=30)
            post_resp.raise_for_status()
            setup_watchdog(success=True, project=self.project, jira_link='', pr_url=comments_url)
        except Exception as e:
            print(f"Failed to create AI reply comment: {e}")
            setup_watchdog(success=False, project=self.project, jira_link='', pr_url=comments_url)
            return False
        return True

    def get_review_comments(self, language="zh"):
        repo_url = self.request.json.get("repository", {}).get("url", "")
        github_token = self.github_token
        if not repo_url or not github_token:
            print("Missing repo_url or github_token")
            return ""
        pr_number = self.request.json.get("issue", {}).get("number", 0)
        if not pr_number:
            pr_number = self.request.json.get('pull_request', {}).get("number", 0)
            if not pr_number:
                print("Missing pull self.request number")
                return ""
        comments_url = f"{repo_url}/issues/{pr_number}/comments"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}"
        }
        try:
            resp = requests.get(comments_url, headers=headers, timeout=60)
            resp.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch PR comments: {e}")
            return ""
        comments = resp.json()
        discussion_chain = []
        for c in comments:
            user_name = c.get("user", {}).get("login", "")
            if user_name.lower() == self.github_username.lower():
                if language == "zh":
                    user_name = "你(AI)"
                else:
                    user_name = "You (AI)"
            else:
                user_ldap_dn = c.get("user", {}).get("ldap_dn", "")
                if user_ldap_dn:
                    match = re.match(r"CN=([^\(]+)", user_ldap_dn)
                    if match:
                        user_name = match.group(1).strip()
            body = c.get("body", "")
            updated_at = c.get("updated_at", "")
            # 格式化最后更新时间（如有需要）
            try:
                dt = datetime.strptime(updated_at, "%Y-%m-%dT%H:%M:%SZ")
                updated_at_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                updated_at_str = updated_at
            if language == "zh":
                discussion_chain.append(f"{user_name}回复于[{updated_at_str}]:\n{body}\n")
            else:
                discussion_chain.append(f"{user_name} replied at [{updated_at_str}]:\n{body}\n")
        return "\n---\n" + "\n".join(discussion_chain)

    def write_to_db(self, db_payload):
        conn = None
        try:
            conn = self._db_pool.getconn()
            with conn.cursor() as cur:
                pk = db_payload.get('html_url')
                if not pk:
                    print("No primary key (html_url) in db_payload, skip DB update.")
                    return
                # 自动填充 last_edit 字段（带东八区时区信息，避免 Django warning）
                if pk and not db_payload.get('last_edit'):
                    db_payload['last_edit'] = datetime.now(timezone(timedelta(hours=8)))
                columns = []
                values = []
                for k, v in db_payload.items():
                    if v is not None and k != 'html_url':
                        # 如果是 dict 或 list，序列化为 JSON 字符串
                        if isinstance(v, (dict, list)):
                            v = json.dumps(v, ensure_ascii=False)
                        columns.append(k)
                        values.append(v)
                if not columns:
                    print("No fields to update in db_payload.")
                    return
                # 先尝试 UPDATE
                set_clause = ', '.join([f"{col} = %s" for col in columns])
                update_sql = f"UPDATE {self.db_sheet_name} SET {set_clause} WHERE html_url = %s"
                update_values = values + [pk]
                cur.execute(update_sql, update_values)
                if cur.rowcount == 0:
                    # 没有行被更新，执行 INSERT
                    insert_columns = ', '.join(['html_url'] + columns)
                    insert_placeholders = ', '.join(['%s'] * (len(columns) + 1))
                    insert_sql = f"INSERT INTO {self.db_sheet_name} ({insert_columns}) VALUES ({insert_placeholders})"
                    insert_values = [pk] + values
                    cur.execute(insert_sql, insert_values)
                conn.commit()
        except Exception as e:
            print(f"DB update/insert error: {e}")
            print(f"Payload keys/values: {[(k, v, len(str(v))) for k, v in db_payload.items()]}")
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def db_payload_install(self, db_payload):
        # 使用类属性直接配置数据库
        db_config = self.db_config

        # 初始化连接池
        if not hasattr(self, '_db_pool'):
            self._db_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                **db_config
            )

        # 并发写入优化：使用线程池
        threading.Thread(target=self.write_to_db, args=(db_payload,)).start()

    def main(self):
        db_payload = {}
        repo_url = self.request.json.get("repository", {}).get("url", "")
        org_url = self.request.json.get("organization", {}).get("url", "")
        event = self.request.headers.get('X-GitHub-Event', None)
        action = self.request.json.get('action', None)

        # 从请求中直接提取字段
        if event == "check_run":
            check_run = self.request.json.get("check_run", {})
            check_run_name = check_run.get("name", "")
            if check_run_name != "Jenkins":
                return 'OK', 200
            pull_requests = check_run.get('pull_requests', [])
            if not pull_requests:
                return 'OK', 200
            db_payload["html_url"] = pull_requests[0].get("url", "").replace("/api/v3/repos/", "/").replace("/pulls/", "/pull/")
            db_payload["check_run_status"] = check_run.get("status", "")
            db_payload["check_run_conclusion"] = check_run.get("conclusion", "")
            db_payload["check_run_started_at"] = check_run.get("started_at", "")
            db_payload["check_run_completed_at"] = check_run.get("completed_at", "")
            db_payload["check_run_details_url"] = check_run.get("details_url", "")
            check_run_output = check_run.get("output", {})
            db_payload["check_run_output_title"] = check_run_output.get("title", "")
            db_payload["check_run_output_summary"] = check_run_output.get("summary", "")
            db_payload["check_run_output_text"] = check_run_output.get("text", "")
            if check_run.get("started_at") and check_run.get("completed_at"):
                try:
                    start_dt = datetime.strptime(check_run.get("started_at"), "%Y-%m-%dT%H:%M:%SZ")
                    end_dt = datetime.strptime(check_run.get("completed_at"), "%Y-%m-%dT%H:%M:%SZ")
                    duration = int((end_dt - start_dt).total_seconds())
                    db_payload["check_run_duration"] = duration
                except Exception as e:
                    print(f"Error parsing check_run timestamps: {e}")
                    db_payload["check_run_duration"] = None
            check_suite = check_run.get("check_suite", {})
            db_payload["check_suite_status"] = check_suite.get("status", "")
            db_payload["check_suite_conclusion"] = check_suite.get("conclusion", "")
        elif event == "status":
            repository = self.request.json.get("repository", {})
            repository_html_url = repository.get("html_url", "")
            pr_number = self.get_pr_number_from_commit()
            if pr_number:
                db_payload["html_url"] = f"{repository_html_url}/pull/{str(pr_number)}"
                db_payload["status_state"] = self.request.json.get("state", "")
                db_payload["status_description"] = self.request.json.get("description", "")
                if db_payload["status_state"] == "pending" or db_payload["status_state"] == "in_progress":
                    db_payload["status_created_at"] = self.request.json.get("created_at", "")
                db_payload["status_updated_at"] = self.request.json.get("updated_at", "")
                if self.request.json.get("updated_at"):
                    try:
                        start_dt = None
                        # 检查并初始化数据库连接池
                        if not hasattr(self, '_db_pool'):
                            self._db_pool = psycopg2.pool.ThreadedConnectionPool(
                                minconn=1,
                                maxconn=10,
                                **self.db_config
                            )
                        conn = self._db_pool.getconn()
                        try:
                            with conn.cursor() as cur:
                                cur.execute(f"SELECT status_created_at FROM {self.db_sheet_name} WHERE html_url = %s", (db_payload["html_url"],))
                                result = cur.fetchone()
                                if result:
                                    start_dt = result[0]  # 通常为 datetime 类型
                        except Exception as e:
                            print(f"DB select error: {e}")
                            start_dt = None
                        finally:
                            self._db_pool.putconn(conn)
                        if start_dt:
                            end_dt = datetime.strptime(self.request.json.get("updated_at"), '%Y-%m-%dT%H:%M:%S%z')
                            duration = int((end_dt - start_dt).total_seconds())
                            db_payload["status_duration"] = duration
                    except Exception as e:
                        print(f"Error parsing status timestamps: {e}")
                        db_payload["status_duration"] = None
        elif event == "pull_request_review":
            review = self.request.json.get("review", {})
            db_payload["review_updated_at"] = review.get("submitted_at", "")
            db_payload["html_url"] = self.request.json.get("pull_request", {}).get("html_url", "")
        elif event == "pull_request":
            pull_request = self.request.json.get('pull_request', {})
            db_payload["html_url"] = pull_request.get("html_url", "")
            db_payload["number"] = pull_request.get("number", 0)
            db_payload["title"] = pull_request.get("title", "")
            db_payload["state"] = pull_request.get("state", "")
            db_payload["labels"] = pull_request.get("labels", [])
            db_payload["mergeable"] = pull_request.get("mergeable", "")
            auto_merge = pull_request.get("auto_merge", "")
            if auto_merge:
                if isinstance(auto_merge, dict):
                    db_payload["auto_merge"] = True if auto_merge.get("enabled_by") else False
                else:
                    db_payload["auto_merge"] = str(bool(auto_merge))
            db_payload["merged"] = pull_request.get("merged", False)
            db_payload["commits"] = pull_request.get("commits", 0)
            db_payload["comments"] = pull_request.get("comments", 0)
            db_payload["review_comments"] = pull_request.get("review_comments", 0)
            db_payload["additions"] = pull_request.get("additions", 0)
            db_payload["deletions"] = pull_request.get("deletions", 0)
            db_payload["changed_files"] = pull_request.get("changed_files", 0)
            db_payload["created_at"] = pull_request.get("created_at", "")
            db_payload["updated_at"] = pull_request.get("updated_at", "")
            db_payload["closed_at"] = pull_request.get("closed_at", "")
            db_payload["merged_at"] = pull_request.get("merged_at", "")
            if pull_request.get("created_at") and pull_request.get("closed_at"):
                try:
                    start_dt = datetime.strptime(pull_request.get("created_at"), "%Y-%m-%dT%H:%M:%SZ")
                    end_dt = datetime.strptime(pull_request.get("closed_at"), "%Y-%m-%dT%H:%M:%SZ")
                    duration = int((end_dt - start_dt).total_seconds())
                    db_payload["opened_duration"] = duration
                except Exception as e:
                    print(f"Error parsing pr timestamps: {e}")
                    db_payload["opened_duration"] = None
            db_payload["diff_url"] = pull_request.get("diff_url", "")
            db_payload["patch_url"] = pull_request.get("patch_url", "")
            db_payload["merge_commit_sha"] = pull_request.get("merge_commit_sha", "")
            repository = self.request.json.get('repository', {})
            db_payload["repository_name"] = repository.get("name", "")
            db_payload["repository_owner_login"] = repository.get("owner", {}).get("login", "")
            db_payload["repository_html_url"] = repository.get("html_url", "")
            head = pull_request.get('head', {})
            db_payload["head_ref"] = head.get('ref', "")
            db_payload["head_sha"] = head.get('sha', "")
            base = pull_request.get('base', {})
            db_payload["base_ref"] = base.get('ref', "")
            db_payload["base_sha"] = base.get('sha', "")
        elif event == "issue_comment":
            pass
        else:
            return 'OK', 200

        # 从请求中提取间接使用字段
        if event == "check_run":
            pass
        elif event == "status":
            pass
        elif event == "pull_request_review":
            if action in ['submitted', 'edited']:
                code_owners = self.get_code_owners(org_url=org_url, repo_url=repo_url)
                if code_owners:
                    self.check_review_approval_status(db_payload=db_payload, code_owners=code_owners, repo_url=repo_url)
        elif event == "pull_request":
            if action in ['opened', 'synchronize']:
                # 执行AI审查
                language = "zh"
                user_ldap_dn = self.request.json.get("pull_request", {}).get("user", {}).get("ldap_dn", "")
                if user_ldap_dn:
                    if ",OU=cn," in user_ldap_dn:
                        language = "zh"
                    else:
                        language = "en"
                git_diff_content = self.get_pr_diff(language=language)
                head_ref = self.request.json.get('pull_request', {}).get('head', {}).get('ref', "")
                match = re.match(r"feature/([^/]+)*", head_ref)
                jira_ticket_id = match.group(1) if match else head_ref
                if jira_ticket_id:
                    db_payload["jira_id"] = jira_ticket_id
                    db_payload["jira_link"] = f"{self.jira_root_url}browse/{jira_ticket_id}"
                    jira_ticket_detail = self.get_jira_ticket_detail(jira_ticket_id=jira_ticket_id, db_payload=db_payload)
                else:
                    if language == "zh":
                        jira_ticket_detail = "无相关Jira信息。"
                    else:
                        jira_ticket_detail = "No related Jira information."
                if git_diff_content:
                    review_result = self.ai_pr_review(git_diff_content=git_diff_content, db_payload=db_payload, language=language, jira_ticket_id=jira_ticket_id, jira_ticket_detail=jira_ticket_detail)
                    _ = self.create_ai_review_comment(review_result)
        elif event == "issue_comment":
            if action not in ['created', 'edited']:
                return 'OK', 200
            user_name = self.request.json.get("comment", {}).get("user", {}).get("login", "")
            if not user_name or user_name.lower() == self.github_username.lower():
                return 'OK', 200
            user_reply_content = self.request.json.get("comment", {}).get("body", "")
            if not user_reply_content or (not "AI" in user_reply_content and not "@uih50651" in user_reply_content): # TODO
                return 'OK', 200
            language = "zh"
            user_ldap_dn = self.request.json.get("comment", {}).get("user", {}).get("ldap_dn", "")
            if user_ldap_dn:
                match = re.match(r"CN=([^\(]+)", user_ldap_dn)
                if match:
                    user_name = match.group(1).strip()
                if ",OU=cn," in user_ldap_dn:
                    language = "zh"
                else:
                    language = "en"
            git_diff_content = self.get_pr_diff(language=language)
            review_comments = self.get_review_comments(language=language)
            reply_result = self.ai_pr_reply(user_name=user_name, git_diff_content=git_diff_content, review_comments=review_comments, language=language)
            _ = self.create_ai_reply_comment(reply_result)
            return 'OK', 200
        else:
            return 'OK', 200
        
        # 将 db_payload 存储到数据库
        self.db_payload_install(db_payload)
        return 'OK', 200
