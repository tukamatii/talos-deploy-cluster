# USAGE: python3 ./ci/collectcontent.py roles/postgres_s1_postgres_cluster_setup/ output.txt

import os
import sys

# Расширения, которые считаем текстовыми
TEXT_EXTENSIONS = {
    '.txt', '.md', '.py', '.json', '.csv', '.log',
    '.html', '.htm', '.css', '.js', '.xml', '.yaml', '.yml',
    '.ini', '.cfg', '.conf', '.sh', '.bat', '.pl', '.rb', '.go'
}

def is_text_file(filename):
    """Проверяет, является ли файл текстовым по расширению."""
    _, ext = os.path.splitext(filename)
    return ext.lower() in TEXT_EXTENSIONS

def collect_text_files(root_dir, output_file):
    """Собирает содержимое всех текстовых файлов в указанной директории и записывает в output_file."""
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for filename in filenames:
                if is_text_file(filename):
                    filepath = os.path.join(dirpath, filename)
                    relative_path = os.path.relpath(filepath, root_dir)

                    out_f.write(f"=== Файл: {relative_path} ===\n")
                    out_f.write("=" * 50 + "\n")

                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            out_f.write(content)
                    except Exception as e:
                        out_f.write(f"[Ошибка чтения файла: {e}]\n")

                    out_f.write("\n\n" + "="*50 + "\n\n")

    print(f"✅ Сбор завершён. Результат записан в: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python collect_text_files.py <директория> <выходной_файл>")
        print("Пример: python collect_text_files.py ./my_project output.txt")
        sys.exit(1)

    root_directory = sys.argv[1]
    output_filename = sys.argv[2]

    if not os.path.exists(root_directory):
        print(f"❌ Директория не найдена: {root_directory}")
        sys.exit(1)

    collect_text_files(root_directory, output_filename)