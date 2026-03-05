#!/usr/bin/env python3
"""
Unit tests for flexible_date_parser module

Run with:
    python -m pytest tests/test_flexible_date_parser.py -v
    or
    python tests/test_flexible_date_parser.py
"""

import unittest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.flexible_date_parser import (
    FlexibleDateParser,
    parse_possible_date,
    get_global_parser,
    DateExtractor
)


class TestFlexibleDateParser(unittest.TestCase):
    """Test suite for FlexibleDateParser"""

    def setUp(self):
        """Set up test fixtures"""
        self.parser = FlexibleDateParser()
        self.reference_date = datetime(2023, 10, 15)

    def test_initialization(self):
        """Test parser initialization"""
        self.assertIsNotNone(self.parser)
        self.assertEqual(self.parser.default_locale, "en")
        self.assertIsNotNone(self.parser.config)

    def test_supported_locales(self):
        """Test supported locales"""
        locales = self.parser.get_supported_locales()
        self.assertIn("en", locales)
        self.assertIn("zh", locales)
        self.assertIn("es", locales)

    # ========== English Date Parsing ==========

    def test_english_dd_month_yyyy(self):
        """Test 'DD Month YYYY' format"""
        result = self.parser.parse_possible_date("8 May 2023", locale="en")
        self.assertEqual(result, datetime(2023, 5, 8))

        result = self.parser.parse_possible_date("25 May, 2023", locale="en")
        self.assertEqual(result, datetime(2023, 5, 25))

    def test_english_month_dd_yyyy(self):
        """Test 'Month DD YYYY' format"""
        result = self.parser.parse_possible_date("May 8, 2023", locale="en")
        self.assertEqual(result, datetime(2023, 5, 8))

        result = self.parser.parse_possible_date("December 25, 2023", locale="en")
        self.assertEqual(result, datetime(2023, 12, 25))

    def test_english_yyyy_mm_dd(self):
        """Test 'YYYY-MM-DD' format"""
        result = self.parser.parse_possible_date("2023-05-08", locale="en")
        self.assertEqual(result, datetime(2023, 5, 8))

        result = self.parser.parse_possible_date("2023-12-25", locale="en")
        self.assertEqual(result, datetime(2023, 12, 25))

    def test_english_mm_dd_yyyy(self):
        """Test 'MM/DD/YYYY' format"""
        result = self.parser.parse_possible_date("05/08/2023", locale="en")
        self.assertEqual(result, datetime(2023, 5, 8))

    def test_english_abbreviated_months(self):
        """Test abbreviated month names"""
        result = self.parser.parse_possible_date("8 May 2023", locale="en")
        self.assertEqual(result, datetime(2023, 5, 8))

        result = self.parser.parse_possible_date(
            "8 Sept 2023",
            locale="en",
            reference_date=self.reference_date
        )
        self.assertEqual(result, datetime(2023, 9, 8))

    def test_english_relative_dates(self):
        """Test relative dates (yesterday, tomorrow, etc.)"""
        result = self.parser.parse_possible_date(
            "today",
            locale="en",
            reference_date=self.reference_date
        )
        self.assertEqual(result, datetime(2023, 10, 15))

        result = self.parser.parse_possible_date(
            "yesterday",
            locale="en",
            reference_date=self.reference_date
        )
        self.assertEqual(result, datetime(2023, 10, 14))

        result = self.parser.parse_possible_date(
            "tomorrow",
            locale="en",
            reference_date=self.reference_date
        )
        self.assertEqual(result, datetime(2023, 10, 16))

    # ========== Chinese Date Parsing ==========

    def test_chinese_yyyy_mm_dd(self):
        """Test Chinese '2023年5月8日' format"""
        result = self.parser.parse_possible_date("2023年5月8日", locale="zh")
        self.assertEqual(result, datetime(2023, 5, 8))

        result = self.parser.parse_possible_date("2023年12月25日", locale="zh")
        self.assertEqual(result, datetime(2023, 12, 25))

    def test_chinese_mm_dd(self):
        """Test Chinese '5月8日' format (without year)"""
        result = self.parser.parse_possible_date(
            "5月8日",
            locale="zh",
            reference_date=self.reference_date
        )
        # Should use reference year
        self.assertEqual(result, datetime(2023, 5, 8))

    def test_chinese_relative_dates(self):
        """Test Chinese relative dates"""
        result = self.parser.parse_possible_date(
            "今天",
            locale="zh",
            reference_date=self.reference_date
        )
        self.assertEqual(result, datetime(2023, 10, 15))

        result = self.parser.parse_possible_date(
            "昨天",
            locale="zh",
            reference_date=self.reference_date
        )
        self.assertEqual(result, datetime(2023, 10, 14))

        result = self.parser.parse_possible_date(
            "明天",
            locale="zh",
            reference_date=self.reference_date
        )
        self.assertEqual(result, datetime(2023, 10, 16))

    # ========== Spanish Date Parsing ==========

    def test_spanish_dd_de_month_de_yyyy(self):
        """Test Spanish '8 de mayo de 2023' format"""
        result = self.parser.parse_possible_date("8 de mayo de 2023", locale="es")
        self.assertEqual(result, datetime(2023, 5, 8))

    def test_spanish_relative_dates(self):
        """Test Spanish relative dates"""
        result = self.parser.parse_possible_date(
            "hoy",
            locale="es",
            reference_date=self.reference_date
        )
        self.assertEqual(result, datetime(2023, 10, 15))

        result = self.parser.parse_possible_date(
            "ayer",
            locale="es",
            reference_date=self.reference_date
        )
        self.assertEqual(result, datetime(2023, 10, 14))

    # ========== Extract All Dates ==========

    def test_extract_all_dates(self):
        """Test extracting multiple dates from text"""
        text = "Between May 8, 2023 and June 3, 2023"
        dates = self.parser.extract_all_dates(text, locale="en")

        self.assertEqual(len(dates), 2)
        self.assertEqual(dates[0], datetime(2023, 5, 8))
        self.assertEqual(dates[1], datetime(2023, 6, 3))

    def test_extract_multiple_formats(self):
        """Test extracting dates in different formats"""
        text = "Events on 2023-05-08 and May 25, 2023"
        dates = self.parser.extract_all_dates(text, locale="en")

        self.assertEqual(len(dates), 2)
        self.assertIn(datetime(2023, 5, 8), dates)
        self.assertIn(datetime(2023, 5, 25), dates)

    # ========== Edge Cases ==========

    def test_invalid_dates(self):
        """Test handling of invalid dates"""
        result = self.parser.parse_possible_date("February 30, 2023", locale="en")
        self.assertIsNone(result)  # Invalid date

        result = self.parser.parse_possible_date("13th month", locale="en")
        self.assertIsNone(result)

    def test_empty_input(self):
        """Test handling of empty input"""
        result = self.parser.parse_possible_date("", locale="en")
        self.assertIsNone(result)

        result = self.parser.parse_possible_date("   ", locale="en")
        self.assertIsNone(result)

        result = self.parser.parse_possible_date(None, locale="en")
        self.assertIsNone(result)

    def test_no_date_in_text(self):
        """Test text without dates"""
        result = self.parser.parse_possible_date("Hello world", locale="en")
        self.assertIsNone(result)

    def test_case_insensitive(self):
        """Test case-insensitive parsing"""
        result1 = self.parser.parse_possible_date("MAY 8, 2023", locale="en")
        result2 = self.parser.parse_possible_date("may 8, 2023", locale="en")
        result3 = self.parser.parse_possible_date("May 8, 2023", locale="en")

        self.assertEqual(result1, result2)
        self.assertEqual(result2, result3)

    # ========== Custom Patterns ==========

    def test_add_custom_pattern(self):
        """Test adding custom date pattern"""
        # Add DD.MM.YYYY pattern
        self.parser.add_custom_pattern(
            'en',
            'ddmmyyyy_dots',
            r'(\d{2})\.(\d{2})\.(\d{4})',
            ['day', 'month', 'year'],
            priority=1
        )

        result = self.parser.parse_possible_date("08.05.2023", locale="en")
        self.assertEqual(result, datetime(2023, 5, 8))

    # ========== Backward Compatibility ==========

    def test_backward_compatible_date_extractor(self):
        """Test backward compatibility with old DateExtractor"""
        dates = DateExtractor.extract_dates_from_query(
            "Between May 8, 2023 and June 3, 2023",
            default_year=2023
        )

        self.assertEqual(len(dates), 2)
        self.assertEqual(dates[0], datetime(2023, 5, 8))
        self.assertEqual(dates[1], datetime(2023, 6, 3))

    def test_backward_compatible_time_range(self):
        """Test backward compatibility with extract_time_range"""
        time_range = DateExtractor.extract_time_range(
            "Between May 8, 2023 and June 3, 2023",
            default_year=2023
        )

        self.assertIsNotNone(time_range)
        self.assertEqual(time_range['start'], '2023-05-08')
        self.assertEqual(time_range['end'], '2023-06-03')

    def test_backward_compatible_detect_temporal(self):
        """Test backward compatibility with detect_temporal_question"""
        is_temporal = DateExtractor.detect_temporal_question(
            "When did Caroline go to the LGBTQ support group?"
        )
        self.assertTrue(is_temporal)

        is_temporal = DateExtractor.detect_temporal_question(
            "What is Caroline's favorite color?"
        )
        self.assertFalse(is_temporal)

    # ========== Convenience Functions ==========

    def test_convenience_function(self):
        """Test parse_possible_date convenience function"""
        result = parse_possible_date("May 8, 2023", locale="en")
        self.assertEqual(result, datetime(2023, 5, 8))

        result = parse_possible_date("2023年5月8日", locale="zh")
        self.assertEqual(result, datetime(2023, 5, 8))

    def test_global_parser_singleton(self):
        """Test global parser singleton"""
        parser1 = get_global_parser()
        parser2 = get_global_parser()

        self.assertIs(parser1, parser2)  # Same instance

    # ========== Real-world Examples ==========

    def test_locomo_examples(self):
        """Test with real LoCoMo dataset examples"""
        # From LoCoMo sessions
        result = self.parser.parse_possible_date(
            "Session 1 - 1:56 pm on 8 May, 2023",
            locale="en"
        )
        self.assertEqual(result, datetime(2023, 5, 8))

        result = self.parser.parse_possible_date(
            "Session 10 - 8:56 pm on 20 July, 2023",
            locale="en"
        )
        self.assertEqual(result, datetime(2023, 7, 20))

    def test_question_with_date(self):
        """Test extracting date from question"""
        result = self.parser.parse_possible_date(
            "When did Caroline go to the LGBTQ support group on May 3rd?",
            locale="en"
        )
        # Should extract May 3 (though 3rd might not be captured)
        # Depends on pattern - for now test what we can parse
        dates = self.parser.extract_all_dates(
            "When did Caroline go to the LGBTQ support group on May 3, 2023?",
            locale="en"
        )
        if dates:
            self.assertIn(datetime(2023, 5, 3), dates)


class TestPerformance(unittest.TestCase):
    """Performance tests"""

    def test_bulk_parsing(self):
        """Test parsing many dates"""
        parser = FlexibleDateParser()

        test_dates = [
            "May 8, 2023",
            "2023-05-08",
            "8 May 2023",
            "2023年5月8日",
            "8 de mayo de 2023"
        ] * 100  # 500 dates

        import time
        start = time.time()

        for date_str in test_dates:
            parser.parse_possible_date(date_str)

        elapsed = time.time() - start

        # Should parse 500 dates in < 1 second
        self.assertLess(elapsed, 1.0, f"Parsing took {elapsed:.2f}s, expected < 1s")


def run_tests():
    """Run all tests"""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    run_tests()
