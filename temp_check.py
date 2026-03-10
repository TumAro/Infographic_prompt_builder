import sys
sys.path.insert(0, r"c:\Users\wgcs\Desktop\Company Project\AI ML Pic Book 2")
import doc_parser
from pathlib import Path

base = Path(r"c:\Users\wgcs\Desktop\Company Project\AI ML Pic Book 2")
syllabus = doc_parser.parse_syllabus(base / "data/grade_7/Class_7.docx")

for mod_num in [5, 6]:
    mod_file = list((base / "data/grade_7").glob(f"Module_{mod_num}_*.docx"))[0]
    print(f"\n=== Module {mod_num}: {mod_file.name} ===")
    try:
        result = doc_parser.parse_module(mod_file, syllabus, mod_num)
        print(f"Found {len(result['topics'])} topics:")
        for t in result['topics']:
            print(f"  topic_num={t['topic_num']}: {t['name']} ({len(t['subtopics'])} subtopics)")
    except Exception as e:
        print(f"ERROR: {e}")

# Why the @output/grade_7/module_1/topic_2/gist.md and @output/grade_7/module_2/topic_1/gist.md look like Which is not according to @data/grade_7/Class_7.docx . Why this is happening?

# Also I think the doc_parser is not capturing all the subtopics in a topic. For example, the @output/grade_7/module_3/topic_2/gist.md , there are only 4 sub topic but the @data/grade_7/Class_7.docx module 3 topic 2 there are 8 sub topic. So investigate both the problem, garbage LLM outputs and the all subtopic are not captured and give the possible fixes.