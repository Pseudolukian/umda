# Обработка YML-файлов (class YMLHandler)

В директории с исходниками документации могут находится различные `yml`-файлы. Некоторые из них являются обязательными для работы UMDA, например: `media.yml`. При запуске UMDA впервую очередь стартует class `YMLHandler`, который сначала читает корневой `yml` -- `umda.yml`, а затем другие `yml`-файлы в корневом каталоге документации, указанные в `umda.yml`.

class `YMLHandler` подгатавливает набор диктов для работы других хэндлеров.

Структура `umda.yml`:

```yml
routers:
  media: media.yml
  aliases: aliases.yml 
```

class `YMLHandler` создаёт следующие дикты:

- `media_list` = { media.yml structure }
- `aliases_list` = { aliases.yml structure }


Использует библиотеки:
- pyyml
- Pathlib
