import daily_report

l=daily_report.find_git_repos("/home/james/code_src")
for i in  l:
    print(f"{i}")