from app.core.translator import Translator, TranslationPreferences
from app.parsers.docx_parser import DocParser, DocParserConfig


def main():
    # 初始化翻译器
    translator = Translator()

    # 设置翻译偏好
    preferences = TranslationPreferences(
        source_lang='en',
        target_lang='zh',
        formality_level='正式',
        domain='技术',
        keep_original_terms=True,
        translate_by_paragraph=True
    )

    # 设置文档解析器配置
    config = DocParserConfig(
        skip_headers=True,
        skip_footers=True,
        skip_tables=False,
    )

    # 初始化文档解析器
    doc_parser = DocParser(translator, config)

    # 执行文档翻译
    try:
        doc_parser.translate_document(doc_path=r'E:\Documents\DocDemo\sample-files.com-formatted-report.docx', preferences=preferences)
        print("文档翻译完成！")
    except Exception as e:
        print(f"翻译过程中发生错误: {str(e)}")


if __name__ == "__main__":
    main()
