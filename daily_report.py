import os
import subprocess
from datetime import datetime
import requests
from pathlib import Path
from dotenv import load_dotenv
import json
from openai import OpenAI
# 加载.env文件
load_dotenv()

def get_git_user():
    """获取当前git配置的用户名"""
    try:
        name = subprocess.check_output(['git', 'config', 'user.name']).decode().strip()
        email = subprocess.check_output(['git', 'config', 'user.email']).decode().strip()
        return f"{name} <{email}>"
    except subprocess.CalledProcessError:
        return None

def find_git_repos(base_dir):
    """查找指定目录下的所有git仓库，包括子仓库"""
    git_repos = []
    for root, dirs, files in os.walk(base_dir):
        # 检查是否是标准git仓库（有.git目录）
        if '.git' in dirs:
            git_repos.append(root)
            dirs.remove('.git')  # 不递归进入.git目录
        # 检查是否是git子模块（有.git文件）
        elif '.git' in files:
            # 确认这是一个git子模块文件而不是其他同名文件
            git_file_path = os.path.join(root, '.git')
            try:
                with open(git_file_path, 'r') as f:
                    content = f.read().strip()
                    # 子模块的.git文件通常包含"gitdir:"前缀
                    if content.startswith('gitdir:'):
                        git_repos.append(root)
            except (IOError, UnicodeDecodeError):
                # 如果不是文本文件或无法读取，则跳过
                pass
    return git_repos

def get_today_commits(repo_path, git_user):
    """获取指定git仓库中当前用户今天的提交记录，包含所有分支"""
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        log = subprocess.check_output(
            ['git', '-C', repo_path, 'log', '--all',
             '--since', f'{today} 00:00:00',
             '--until', f'{today} 23:59:59',
             '--author', git_user,
             '--pretty=format:%s'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return log.split('\n') if log else []
    except subprocess.CalledProcessError:
        return []

def generate_daily_report(commits):
    """调用deepseek API生成日报"""
    api_key = os.getenv('DEEPSEEK_API_KEY')
    api_url = os.getenv('DEEPSEEK_API_URL')
    
    if not api_key:
        raise ValueError("请在.env文件中设置DEEPSEEK_API_KEY")
    if not api_url:
        raise ValueError("请在.env文件中设置DEEPSEEK_API_URL")
    client = OpenAI(
    api_key=api_key,
    base_url=api_url,
)
    
    
    data = {
        'commits': commits,
        'date': datetime.now().strftime('%Y-%m-%d')
    }
    
    system_prompt = """
用户提交一些仓库中的git提交日志，请为它们生成一份工作日报，说明今天做了什么。

示例 MARKDOWN 输出:

- 今今日工作完成情况: 
1. 修复了浏览器xxx的bug
2. 优化了xxx
3. 完成了xxx功能
4. ...
- 明日工作计划:
1. 修复xxx的bug
2. 优化xxx
3. 完成xxx功能
4. ...
"""

    user_prompt = json.dumps(data)

    messages = [{"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}]

    response = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    response_format={
        'type': 'text'
    }
)

    return response.choices[0].message.content
    # if response.status_code == 200:
    #     return response.json().get('summary', '')
    # else:
    #     raise Exception(f"Deepseek API error: {response.status_code} - {response.text}")

def main():
    base_dir = os.getenv('WORK_REPORT_DIR')
    if not base_dir:
        raise ValueError("请在.env文件中设置WORK_REPORT_DIR")
    
    git_user = get_git_user()
    if not git_user:
        print("Git user not configured")
        return
    
    all_commits = []
    for repo in find_git_repos(base_dir):
        commits = get_today_commits(repo, git_user)
        print(f"Found {len(commits)} commits in {repo}")
        all_commits.extend([f"repo:{repo}: commit:{commit}" for commit in commits])
    
    if not all_commits:
        print("No commits found for today")
        return
    
    try:
        print(f"Generating daily report for commits {len(all_commits)}")
        report = generate_daily_report(all_commits)
        print(report)
        with open('report.md', 'w') as f:
            f.write(report)
    except Exception as e:
        print(f"Error generating report: {str(e)}")

if __name__ == '__main__':
    main()