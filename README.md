# NikaS House

Автономная интеграция основной эксплуатационной панели Home Assistant NikaS «Дом».

Первый выпуск является точным техническим выделением действующей панели из
`NikaSir/ha-contract-generated-ui` версии `0.38.2`, коммит
`f5bff8145eef20475cf3e3f9f470e94d564b72fc`. Дизайн, состав сущностей,
логика состояний и утверждённая компоновка не перерабатываются.

## Версии и маршрут

| Компонент | Значение |
| --- | --- |
| Домен | `nikas_house` |
| Интеграция | `NikaS House` `0.1.0` |
| Интерфейс | `UI v1.0.0` |
| Новый маршрут | `/dashboard-house-v13/home` |
| Сохранённый действующий маршрут | `/dashboard-house-v12/home` |
| Публикация | ветка `main`, без GitHub Releases |

Интеграция регистрирует только `dashboard-house-v13`. Если этот путь уже занят,
она не удаляет и не заменяет владельца маршрута. Старые YAML-панели и интеграция
`contract_generated_ui` не изменяются.

## Границы проекта

Репозиторий содержит только House-контракт, House-манифест, интеграцию
`custom_components/nikas_house`, автономный frontend, локальный WebP-ассет,
схемы, проверки и документацию. Реализации панелей «Помещения», «Действия»,
«Инфраструктура», «Доступ» и оборудования сюда не входят.

Проверенные внешние переходы:

| Карточка | Маршрут |
| --- | --- |
| Дом | `/dashboard-house-v13/home` |
| Помещения | `/dashboard-rooms-v11/rooms` |
| Действия | `/dashboard-actions/home` |
| Инфра | `/dashboard-infrastructure/overview` |
| Электросеть | `/dashboard-lider` |
| Интернет | `/dashboard-keenetic` |
| Отопление | `/dashboard-zont` |
| Ворота и точки доступа | `/dashboard-access-v1/home` |

Остальные действующие ссылки перенесены без изменения. В частности, вода пока
ведёт в `/dashboard-infrastructure/overview`; отдельный путь не придуман.

## Автономность и приватный инвентарь

JavaScript, Python-модули и изображения загружаются только из
`custom_components/nikas_house`. Статические URL начинаются с
`/nikas_house/frontend/`, а web components, bootstrap-ключ и ключ масштаба имеют
собственные имена, поэтому версии v12 и v13 могут работать одновременно.

Реальные `entity_id` не публикуются. При первом запуске, только если
`/config/nikas_house/inventory/` пуст, интеграция находит существующий проверенный
House-инвентарь в `/config/contract_generated_ui/inventory/`, выбирает из него
только полный набор `house.home.*` со статусом `verified` и атомарно копирует в
собственный каталог. Исходный файл не изменяется, посторонние привязки не
переносятся, существующий целевой инвентарь никогда не перезаписывается. После
этого панель строится только из `/config/nikas_house`.

## Установка тестовой ветки

До принятия PR каталог `custom_components/nikas_house` можно скопировать из
ветки проверки в `/config/custom_components/nikas_house`. Затем требуется полная
перезагрузка Home Assistant и добавление интеграции **NikaS House** через UI.
Проверочный адрес: `/dashboard-house-v13/home`.

`/dashboard-house-v12/home`, старые YAML-маршруты и исходный репозиторий должны
оставаться установленными на всём этапе приёмки.

## Локальная проверка

```bash
python -m pip install -e '.[test]'
./scripts/build_frontend_bundles.sh
python -m generator validate .
python scripts/check_nikas_ui_standard.py
python -m pytest -q
python -m compileall -q generator custom_components/nikas_house tests
node --check custom_components/nikas_house/frontend/nikas-house-hero.js
node --input-type=module --check < custom_components/nikas_house/frontend/nikas-house-overview.js
node --check custom_components/nikas_house/frontend/nikas-ui.js
node --check custom_components/nikas_house/frontend/dist/nikas-house-overview.js
```

Pull request дополнительно запускает Hassfest, HACS validation, проверку
детерминированной сборки и smoke-тесты холодной регистрации frontend.
