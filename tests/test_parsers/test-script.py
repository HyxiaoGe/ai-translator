import asyncio
from app.core.translator import Translator, TranslationPreferences
from app.parsers.docx_parser import DocParser
import time


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
            doc_source=r'E:\IDM\Documents\demo.docx',
            filename='demo.docx',
            preferences=preferences,  # 传入翻译偏好设置
            output_path=r'E:\IDM\Documents\demo_3.docx',
        )
        print("文档翻译完成！")
    except Exception as e:
        print(f"翻译过程中发生错误: {str(e)}")

async def test_rate_limit():
    translator = Translator()
    text = "Hello World"
    
    # 创建70个并发请求
    tasks = []
    for i in range(70):
        tasks.append(translator.translate(text))
    
    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    
    # 统计成功和失败的请求
    success = sum(1 for r in results if not isinstance(r, Exception))
    failures = sum(1 for r in results if isinstance(r, Exception))
    
    print(f"总耗时: {end_time - start_time:.2f}秒")
    print(f"成功请求: {success}")
    print(f"失败请求: {failures}")


if __name__ == "__main__":
    asyncio.run(main())
