import asyncio
from app.core.translator import Translator, TranslationPreferences
from app.parsers.docx_parser import DocParser


async def main():
    # 初始化翻译器
    translator = Translator()

    # 创建翻译偏好设置
    preferences = TranslationPreferences(
        source_lang='en',
        target_lang='zh',
        formality_level='正式',
        domain='技术',
        terminology_mapping={}  # 如果没有特定术语映射，提供空字典
    )

    # 初始化文档解析器
    doc_parser = DocParser(translator)

    # 执行文档翻译
    try:
        await doc_parser.translate_document(
            doc_source=r'E:\IDM\Documents\sample-files.com-formatted-report.docx',
            filename='sample-files.com-formatted-report.docx',
            preferences=preferences,  # 传入翻译偏好设置
            output_path=r'E:\IDM\Documents\sample-files.com-formatted-report-2.docx',
        )
        print("文档翻译完成！")
    except Exception as e:
        print(f"翻译过程中发生错误: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
