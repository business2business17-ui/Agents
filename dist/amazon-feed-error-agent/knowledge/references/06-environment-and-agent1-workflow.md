# Локальные папки, PowerShell, GitHub, Agent 1 workflow

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 21. Рабочая среда: локальные папки, PowerShell и GitHub

Агент должен уметь работать с локально предоставленной пользователем структурой папок.

Пользователь может передать:

- одну локальную папку;
- несколько папок;
- папку с Amazon Feed;
- папку с результатом `Agent 1`;
- папку с дополнительными источниками данных;
- локальный clone / checkout GitHub repository.

Типовой набор входов:

```text
/workdir/
  amazon-feed/
    feed.xlsm

  agent-1-output/
    prepared_data.xlsx
    prepared_data.csv
    prepared_data.json
    notes.md

  repository/
    ...
```

## PowerShell mode

Если рабочая среда Windows / PowerShell, агент должен:

1. работать только внутри указанной пользователем локальной директории;
2. не выполнять destructive operations без необходимости;
3. не удалять исходные файлы;
4. не переименовывать исходный Amazon Feed;
5. сохранять новые версии отдельно;
6. использовать абсолютные или явно разрешенные относительные пути;
7. перед изменением файла создавать отдельную рабочую копию;
8. логировать путь входного и выходного файла;
9. не выполнять неизвестные `.ps1`, `.bat`, `.cmd`, `.exe` из локальной папки без явной необходимости и проверки;
10. не запускать macros/VBA из XLSM для анализа данных.

Пример логики именования:

```text
feed_original.xlsm
feed_working_v1.xlsm
feed_corrected_v1.xlsm
feed_corrected_v2.xlsm
```

Исходный файл всегда остается неизменным.

## 22. GitHub / Browser mode

Если пользователь предоставляет GitHub repository или подключенный repository:

Агент может использовать его для:

- чтения методики;
- чтения mapping-файлов;
- чтения lookup tables;
- чтения схем;
- чтения предыдущих verified fixes;
- чтения документации проекта;
- сравнения версий;
- использования approved reference data.

## Правила GitHub

1. GitHub рассматривается как источник данных и версионируемая база знаний.
2. Не изменяй repository без отдельного запроса пользователя.
3. Не push / commit / merge без явного разрешения.
4. Если repository содержит правила заполнения Feed, сопоставляй их с текущим Amazon template.
5. При конфликте:
   - текущий Amazon template;
   - Data Definitions;
   - Valid Values;
   - актуальная документация Amazon
   имеют приоритет над устаревшей логикой repository.
6. Фиксируй, какая версия/commit/reference использовалась для анализа, если эта информация доступна.

## 23. Agent 1 → Feed Agent workflow

Пользователь может передать:

1. `Amazon Feed (.xlsm)`;
2. файл из `Agent 1`, в котором уже собраны все данные, готовые к заполнению.

Agent 1 output считается **источником подготовленных значений**, но не абсолютной истиной.

Перед переносом каждого значения:

1. сопоставь товар;
2. сопоставь SKU/EAN/GTIN/ASIN, если доступны;
3. сопоставь целевой Amazon attribute;
4. проверь Data Definitions;
5. проверь Valid Values / dropdown;
6. проверь тип данных;
7. проверь marketplace;
8. проверь row/product mapping;
9. только после этого предложи запись в Feed.

Если значение Agent 1 конфликтует с Amazon template:

`Amazon template rules > Agent 1 prepared value`

и конфликт должен быть показан пользователю.
