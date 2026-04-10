## MDHandler

Класс `MDHandle` обходит все `.md`-файлы из `doc_input`, обрабатывает вставки изображений и сохраняет результат в `doc_output` с сохранением структуры папок. Оригинальные файлы не изменяются.

### Что обрабатывается

#### 1. PSD-вставки

```markdown
![base_layer;Focuses=[A];Frames=[B,C]]({{ media.screenshots.diagram }})
![Default;Crops=[Canvas]]({{ media.screenshots.diagram }})
```

- `{{ media.screenshots.diagram }}` — переменная, разрешается через `UMDAData` из yml-роутеров
- `base_layer` — верхнеуровневая группа в PSD
- `Focuses`, `Frames`, `Crops` — списки слоёв для наложения (кавычки вокруг имён игнорируются)
- Вызывается `PSDHandler.render(PSDConfig(...))`, результат `.webp` сохраняется в `image_storage_output`
- Ссылка в MD подменяется на абсолютный путь до `.webp`

Правила:
- Сначала базовый слой, затем Focuses, затем Frames
- `Crops` используется только без Focuses/Frames — обрезает итог по маске слоя

#### 2. Локальные изображения

```markdown
![alt](./img/file.png)
```

- Поддерживаются: `png`, `jpg`, `jpeg`, `gif`, `webp`, `svg`
- Файл копируется в `image_storage_output` с сохранением пути относительно `doc_input`
- Ссылка подменяется на абсолютный путь до скопированного файла

### Копирование yml-файлов

В `umda.yml` секция `config.doc_ymls` задаёт список yml-файлов, которые нужно скопировать в `doc_output`:

```yaml
config:
  doc_ymls:
    - toc.yaml
    - vars.yaml
```

Остальные yml не копируются.

### Конфигурация (umda.yml)

```yaml
config:
  doc_input: /path/to/source/docs
  doc_output: /path/to/output
  image_storage_output: /path/to/images
  doc_ymls:
    - toc.yaml
    - vars.yaml
routers:
  media: media.yml
  aliases: aliases.yml
```

### Запуск

```bash
umda /path/to/docs   # указать путь к доке
umda .               # из папки с докой
```

`umda` — обёртка, запускает `main.py` через venv `/root/umda/.umda`.
