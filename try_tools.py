from tools import completeness_report, skill_match, find_weak_bullets
text = open("sample_data/sample_resume.txt", encoding="utf-8").read()
print("Completeness score:", completeness_report(text)["score"])
print(skill_match(text, ["Python", "SQL", "Excel", "Power BI", "Git"]))
for bullet in find_weak_bullets(text):
    print("WEAK:", bullet)