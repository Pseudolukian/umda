## PSDHandler

Класс `PSDHandler` рендерит слои из PSD-файла и сохраняет результат в WebP.

### Входная модель — `PSDConfig`

```python
class PSDConfig(BaseModel):
    psd_path: str        # путь к .psd файлу
    base_layer: str      # название верхнеуровневой группы
    Frames: list[str]    # слои из группы Frames (shape-слои, рамки)
    Focuses: list[str]   # слои из группы Focuses (pixel-слои, подсветка)
    Crops: list[str]     # слои из группы Crops (обрезка по маске)
```

### Структура PSD

Ожидаемая иерархия:

```
diagram.psd
└── Account/                  ← верхнеуровневая группа (base_layer)
    ├── Account               ← базовый pixel-слой (одноимённый с группой)
    ├── Focuses/
    │   └── Account           ← pixel-слой с opacity
    ├── Frames/
    │   ├── Account_btn       ← shape-слой (stroke/fill rectangle)
    │   └── Account_email     ← shape-слой
    └── Crops/
        └── Canvas            ← слой с mask_data — bbox для обрезки
```

### Порядок рендеринга

1. **Базовый слой** — читается через `topil()` (обходит проблему скрытых групп)
2. **Focuses** — pixel-слои, читаются через `topil()` с применением `opacity` слоя
3. **Frames** — shape-слои (rectangle), рендерятся вручную через `ImageDraw.rectangle()`;
   цвет stroke и fill берутся из `tagged_blocks[VECTOR_STROKE_DATA]` и `SOLID_COLOR_SHEET_SETTING`,
   координаты — из `tagged_blocks[VECTOR_ORIGINATION_DATA]`
4. **Crops** — после compositing canvas обрезается по `layer._record.mask_data` bbox

### Структура выходного пути

```
{image_storage_output}/{base_layer}/                        → только базовый слой
{image_storage_output}/{base_layer}/Focuses/{names}.webp    → с Focuses
{image_storage_output}/{base_layer}/Frames/{names}.webp     → с Frames
{image_storage_output}/{base_layer}/Crops/{names}.webp      → с Crops
{image_storage_output}/{base_layer}/Focuses_Frames/{names}.webp → комбинация
```

### Валидация

При неверном имени `base_layer` или слоя внутри группы бросается `ValueError` с подсказкой какие имена доступны.

### Методы

- `.render(config: PSDConfig) -> Path` — рендерит и сохраняет WebP, возвращает путь
- `.terminate()` — очищает кэш загруженных PSD из памяти
