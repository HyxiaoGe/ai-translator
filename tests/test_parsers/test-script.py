from app.core.translator import Translator
from app.parsers.docx_parser import DocParser


def main():
    # 初始化翻译器
    translator = Translator()

    # 初始化文档解析器
    doc_parser = DocParser(translator)

    # 执行文档翻译
    try:
        doc_parser.translate_document(doc_path=r'E:\Documents\DocDemo\sample-files.com-formatted-report.docx')
        print("文档翻译完成！")
    except Exception as e:
        print(f"翻译过程中发生错误: {str(e)}")


if __name__ == "__main__":
    main()
