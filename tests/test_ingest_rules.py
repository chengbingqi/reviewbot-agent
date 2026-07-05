from ingest_rules import parse_rule_file


def test_parse_rule_file_splits_second_level_headings(tmp_path):
    path = tmp_path / "rules.md"
    path.write_text("# Rules\n\n## Rule A\n\nBody A\n\n## Rule B\n\nBody B", encoding="utf-8")
    rules = parse_rule_file(path)
    assert [rule.title for rule in rules] == ["Rule A", "Rule B"]
    assert all(rule.content for rule in rules)
