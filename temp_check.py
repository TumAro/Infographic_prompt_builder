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
