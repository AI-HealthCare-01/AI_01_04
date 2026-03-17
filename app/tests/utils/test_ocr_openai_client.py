from app.integrations.ocr.openai_client import _merge_parser_hints


class TestMergeParserHints:
    def test_fills_empty_diagnosis_and_drugs_from_parser_hints(self):
        result = {
            "diagnosis_list": [],
            "drugs": [],
        }
        parser_hints = {
            "candidate_diagnosis_codes": ["I109", "E119"],
            "candidate_drugs": ["타이레놀정", "코푸시럽"],
        }

        merged = _merge_parser_hints(result, parser_hints)

        assert merged["diagnosis_list"] == ["I109", "E119"]
        assert merged["drugs"] == ["타이레놀정", "코푸시럽"]

    def test_keeps_ai_values_when_present(self):
        result = {
            "diagnosis_list": ["고혈압"],
            "drugs": ["아스피린"],
        }
        parser_hints = {
            "candidate_diagnosis_codes": ["I109"],
            "candidate_drugs": ["타이레놀정"],
        }

        merged = _merge_parser_hints(result, parser_hints)

        assert merged["diagnosis_list"] == ["고혈압"]
        assert merged["drugs"] == ["아스피린"]

    def test_dedupes_parser_values(self):
        result = {
            "diagnosis_list": [],
            "drugs": [],
        }
        parser_hints = {
            "candidate_diagnosis_codes": ["I109", "I109", "E119"],
            "candidate_drugs": ["타이레놀정", "타이레놀정", "코푸시럽"],
        }

        merged = _merge_parser_hints(result, parser_hints)

        assert merged["diagnosis_list"] == ["I109", "E119"]
        assert merged["drugs"] == ["타이레놀정", "코푸시럽"]
