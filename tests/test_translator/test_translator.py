import unittest
from typing import List
import os
from app.core.translator import Translator, TranslationPreferences


class TestTranslator(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test case"""
        self.translator = Translator()
        self.test_preferences = TranslationPreferences(
            source_lang='en',
            target_lang='zh',
            formality_level='正式',
            domain='技术',
            terminology_mapping={
                'API': '应用程序接口',
                'HTTP': '无'
            }
        )

    def test_basic_translation(self):
        """Test basic translation functionality"""
        text = "It's meant to take you from zero all the way through to how LLMs are trained and why they work so impressively well."
        result = self.translator.translate(text, self.test_preferences)

        # 基本属性验证
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

        # 验证翻译结果 - 应该包含常见的中文翻译用语
        # expected_translations = ['你好', '世界']  # 可能的翻译结果
        # self.assertTrue(any(expected in result for expected in expected_translations),
        #                 f"Translation result '{result}' does not contain expected Chinese text")

        # 打印实际翻译结果以便检查
        print(f"\nInput: {text}")
        print(f"Translation: {result}")

    def test_batch_translation(self):
        """Test batch translation functionality"""
        texts = [
            "First paragraph",
            "Second paragraph",
            "Third paragraph"
        ]
        results = self.translator.batch_translate(texts, self.test_preferences)
        self.assertEqual(len(results), len(texts))
        for result in results:
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

    def test_stream_translation(self):
        """Test streaming translation functionality"""
        text = "This is a test for streaming translation."
        chunks = []

        def chunk_handler(chunk: str):
            print(f"Received chunk: {chunk}")  # 方便调试
            chunks.append(chunk)

        # 进行流式翻译
        result = self.translator.translate(
            text=text,
            preferences=self.test_preferences,
            chunk_callback=chunk_handler
        )

        # 验证
        self.assertGreater(len(chunks), 0, "Should receive at least one chunk")
        self.assertEqual(result, ''.join(chunks), "Full result should match joined chunks")

        # 验证翻译结果包含预期的中文内容
        expected_words = ['这', '是', '测试']  # 预期在结果中出现的中文词
        self.assertTrue(
            any(word in result for word in expected_words),
            f"Translation '{result}' should contain some expected Chinese words"
        )

    def test_technical_translation(self):
        """Test translation with technical terms"""
        text = "The HTTP API endpoint needs to be configured."
        result = self.translator.translate(text, self.test_preferences)
        self.assertIsNotNone(result)
        # 验证术语映射是否正确应用
        self.assertIn('应用程序接口', result)
        self.assertIn('HTTP', result)  # 因为在术语映射中标记为"无"

    def test_invalid_api_key(self):
        """Test translation with invalid API key"""
        # 临时保存原始API key
        original_key = os.getenv('DASHSCOPE_API_KEY')
        os.environ['DASHSCOPE_API_KEY'] = 'invalid_key'

        translator = Translator()
        with self.assertRaises(Exception):
            translator.translate("Test text")

        # 恢复原始API key
        if original_key:
            os.environ['DASHSCOPE_API_KEY'] = original_key

    def test_empty_text(self):
        """Test translation with empty text"""
        text = ""
        result = self.translator.translate(text, self.test_preferences)
        self.assertEqual(result, "")


if __name__ == '__main__':
    unittest.main()