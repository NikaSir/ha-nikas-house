from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .render import RenderError

HOUSE_RENDERER = "house_home_v1"
MAX_COLUMNS = 2


def _layout_engine_sha256(base_engine_sha256: str) -> str:
    layer_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return hashlib.sha256(f"{base_engine_sha256}:{layer_sha}".encode("utf-8")).hexdigest()


def _entity_map(semantic_view: Mapping[str, Any]) -> dict[str, str]:
    modules = semantic_view.get("modules")
    if not isinstance(modules, list) or len(modules) != 1:
        raise RenderError("house_home_v1 requires exactly one module")
    roles = modules[0].get("roles")
    if not isinstance(roles, list):
        raise RenderError("house_home_v1 semantic roles missing")
    result: dict[str, str] = {}
    for role in roles:
        name = role.get("role")
        entity_id = role.get("entity_id")
        if not isinstance(name, str) or not isinstance(entity_id, str):
            raise RenderError("house_home_v1 role/entity missing")
        result[name] = entity_id
    return result


def _members(entities: Mapping[str, str], prefix: str) -> list[str]:
    return [entities[key] for key in sorted(entities) if key.startswith(prefix)]


def _required(entities: Mapping[str, str], *names: str) -> None:
    missing = [name for name in names if name not in entities]
    if missing:
        raise RenderError("house_home_v1 missing roles: " + ", ".join(missing))


def _nav(manifest: Mapping[str, Any], key: str) -> str:
    navigation = manifest.get("spec", {}).get("navigation")
    if not isinstance(navigation, dict):
        raise RenderError("house_home_v1 requires spec.navigation")
    target = navigation.get(key)
    if not isinstance(target, str) or not target.startswith("/"):
        raise RenderError(f"house_home_v1 navigation target {key!r} missing")
    return target


def _literal(values: list[str]) -> str:
    return json.dumps(values, ensure_ascii=False)


def _heading(text: str, icon: str | None = None, *, title: bool = True) -> dict[str, Any]:
    card: dict[str, Any] = {
        "type": "heading",
        "heading": text,
        "heading_style": "title" if title else "subtitle",
    }
    if icon:
        card["icon"] = icon
    return card


def _chip(content: str, icon: str, icon_color: str, target: str, *, entity: str | None = None) -> dict[str, Any]:
    card: dict[str, Any] = {
        "type": "template",
        "content": content,
        "icon": icon,
        "icon_color": icon_color,
        "tap_action": {"action": "navigate", "navigation_path": target},
    }
    if entity:
        card["entity"] = entity
        card["hold_action"] = {"action": "more-info"}
    return card


def _nav_card(primary: str, secondary: str, icon: str, target: str, *, columns: int = 6, icon_color: str | None = None) -> dict[str, Any]:
    card: dict[str, Any] = {
        "type": "custom:mushroom-template-card",
        "primary": primary,
        "secondary": secondary,
        "icon": icon,
        "tap_action": {"action": "navigate", "navigation_path": target},
        "grid_options": {"columns": columns},
    }
    if icon_color:
        card["icon_color"] = icon_color
    return card


def _more_info_card(entity: str, primary: str, secondary: str, icon: str, icon_color: str, *, columns: int = 6, multiline: bool = False) -> dict[str, Any]:
    card: dict[str, Any] = {
        "type": "custom:mushroom-template-card",
        "entity": entity,
        "primary": primary,
        "secondary": secondary,
        "icon": icon,
        "icon_color": icon_color,
        "tap_action": {"action": "more-info"},
        "hold_action": {"action": "more-info"},
        "grid_options": {"columns": columns},
    }
    if multiline:
        card["multiline_secondary"] = True
    return card


def _house_now(entities: Mapping[str, str], manifest: Mapping[str, Any]) -> dict[str, Any]:
    safety = _members(entities, "safety_")
    openings = _members(entities, "opening_")
    motion = _members(entities, "motion_")
    lights = _members(entities, "light_")
    climate = _members(entities, "climate_")
    cameras = _members(entities, "camera_")
    weather = entities["weather"]

    safety_list = _literal(safety)
    opening_list = _literal(openings)
    motion_list = _literal(motion)
    light_list = _literal(lights)
    climate_list = _literal(climate)
    camera_list = _literal(cameras)

    chips_top = {
        "type": "custom:mushroom-chips-card",
        "alignment": "center",
        "grid_options": {"columns": "full"},
        "chips": [
            _chip(
                "{% set op=label_devices('В эксплуатации') %}{% set svc=label_devices('На обслуживании') %}{% set rep=label_devices('Требует замены') %}{% set es=" + safety_list + " %}{% set ns=namespace(n=0,bad=0) %}{% for e in es %}{% set d=device_id(e) %}{% if d and (d in op or d in svc or d in rep) %}{% if d in svc or d in rep %}{% set ns.bad=ns.bad+1 %}{% endif %}{% if is_state(e,'on') %}{% set ns.n=ns.n+1 %}{% elif states(e) in ['unknown','unavailable'] %}{% set ns.bad=ns.bad+1 %}{% endif %}{% endif %}{% endfor %}{% if ns.n>0 %}Безопасность — тревога {{ ns.n }}{% elif ns.bad>0 %}Безопасность — внимание{% else %}Безопасность — в норме{% endif %}",
                "mdi:shield-home",
                "{% set op=label_devices('В эксплуатации') %}{% set svc=label_devices('На обслуживании') %}{% set rep=label_devices('Требует замены') %}{% set es=" + safety_list + " %}{% set ns=namespace(n=0,bad=0) %}{% for e in es %}{% set d=device_id(e) %}{% if d and (d in op or d in svc or d in rep) %}{% if d in svc or d in rep %}{% set ns.bad=ns.bad+1 %}{% endif %}{% if is_state(e,'on') %}{% set ns.n=ns.n+1 %}{% elif states(e) in ['unknown','unavailable'] %}{% set ns.bad=ns.bad+1 %}{% endif %}{% endif %}{% endfor %}{% if ns.n>0 %}red{% elif ns.bad>0 %}orange{% else %}green{% endif %}",
                _nav(manifest, "safety"),
            ),
            _chip(
                "{% set op=label_devices('В эксплуатации') %}{% set es=" + opening_list + " %}{% set ns=namespace(n=0,total=0,bad=0) %}{% for e in es %}{% set d=device_id(e) %}{% if d and d in op %}{% set ns.total=ns.total+1 %}{% if is_state(e,'on') %}{% set ns.n=ns.n+1 %}{% elif states(e) in ['unknown','unavailable'] %}{% set ns.bad=ns.bad+1 %}{% endif %}{% endif %}{% endfor %}Открыто {{ ns.n }}",
                "mdi:door-open",
                "{% set op=label_devices('В эксплуатации') %}{% set es=" + opening_list + " %}{% set ns=namespace(n=0,total=0,bad=0) %}{% for e in es %}{% set d=device_id(e) %}{% if d and d in op %}{% set ns.total=ns.total+1 %}{% if is_state(e,'on') %}{% set ns.n=ns.n+1 %}{% elif states(e) in ['unknown','unavailable'] %}{% set ns.bad=ns.bad+1 %}{% endif %}{% endif %}{% endfor %}{% if ns.n>0 %}yellow{% elif ns.bad>0 %}orange{% elif ns.total>0 %}green{% else %}grey{% endif %}",
                _nav(manifest, "open"),
            ),
        ],
    }

    chips_activity = {
        "type": "custom:mushroom-chips-card",
        "alignment": "center",
        "grid_options": {"columns": "full"},
        "chips": [
            _chip(
                "{% set op=label_devices('В эксплуатации') %}{% set es=" + motion_list + " %}{% set ns=namespace(n=0,bad=0) %}{% for e in es %}{% set d=device_id(e) %}{% if d and d in op %}{% if is_state(e,'on') %}{% set ns.n=ns.n+1 %}{% elif states(e) in ['unknown','unavailable'] %}{% set ns.bad=ns.bad+1 %}{% endif %}{% endif %}{% endfor %}Движение {{ ns.n }}",
                "mdi:motion-sensor",
                "{% set op=label_devices('В эксплуатации') %}{% set es=" + motion_list + " %}{% set ns=namespace(n=0,bad=0) %}{% for e in es %}{% set d=device_id(e) %}{% if d and d in op %}{% if is_state(e,'on') %}{% set ns.n=ns.n+1 %}{% elif states(e) in ['unknown','unavailable'] %}{% set ns.bad=ns.bad+1 %}{% endif %}{% endif %}{% endfor %}{% if ns.bad>0 %}orange{% elif ns.n>0 %}yellow{% else %}green{% endif %}",
                _nav(manifest, "activity"),
            ),
            _chip(
                "{% set op=label_devices('В эксплуатации') %}{% set es=" + light_list + " %}{% set ns=namespace(n=0,bad=0) %}{% for e in es %}{% set d=device_id(e) %}{% if d and d in op %}{% if is_state(e,'on') %}{% set ns.n=ns.n+1 %}{% elif states(e) in ['unknown','unavailable'] %}{% set ns.bad=ns.bad+1 %}{% endif %}{% endif %}{% endfor %}Свет {{ ns.n }}",
                "mdi:lightbulb-group",
                "{% set op=label_devices('В эксплуатации') %}{% set es=" + light_list + " %}{% set ns=namespace(n=0,bad=0) %}{% for e in es %}{% set d=device_id(e) %}{% if d and d in op %}{% if is_state(e,'on') %}{% set ns.n=ns.n+1 %}{% elif states(e) in ['unknown','unavailable'] %}{% set ns.bad=ns.bad+1 %}{% endif %}{% endif %}{% endfor %}{% if ns.bad>0 %}orange{% elif ns.n>0 %}yellow{% else %}green{% endif %}",
                _nav(manifest, "lights"),
            ),
            _chip(
                "{% set op=label_devices('В эксплуатации') %}{% set es=" + climate_list + " %}{% set ns=namespace(n=0,bad=0) %}{% for e in es %}{% set d=device_id(e) %}{% if d and d in op %}{% if state_attr(e,'hvac_action') in ['heating','cooling'] %}{% set ns.n=ns.n+1 %}{% endif %}{% if states(e) in ['unknown','unavailable'] %}{% set ns.bad=ns.bad+1 %}{% endif %}{% endif %}{% endfor %}Климат {{ ns.n }}",
                "mdi:thermostat",
                "{% set op=label_devices('В эксплуатации') %}{% set es=" + climate_list + " %}{% set ns=namespace(n=0,bad=0) %}{% for e in es %}{% set d=device_id(e) %}{% if d and d in op %}{% if state_attr(e,'hvac_action') in ['heating','cooling'] %}{% set ns.n=ns.n+1 %}{% endif %}{% if states(e) in ['unknown','unavailable'] %}{% set ns.bad=ns.bad+1 %}{% endif %}{% endif %}{% endfor %}{% if ns.bad>0 %}orange{% elif ns.n>0 %}yellow{% else %}green{% endif %}",
                _nav(manifest, "climate"),
            ),
        ],
    }

    chips_context = {
        "type": "custom:mushroom-chips-card",
        "alignment": "center",
        "grid_options": {"columns": "full"},
        "chips": [
            _chip(
                "{% set op=label_devices('В эксплуатации') %}{% set es=" + camera_list + " %}{% set ns=namespace(ok=0,total=0) %}{% for e in es %}{% set d=device_id(e) %}{% if d and d in op %}{% set ns.total=ns.total+1 %}{% if states(e) not in ['unknown','unavailable'] %}{% set ns.ok=ns.ok+1 %}{% endif %}{% endif %}{% endfor %}Камеры {{ ns.ok }}/{{ ns.total }}",
                "mdi:cctv",
                "{% set op=label_devices('В эксплуатации') %}{% set es=" + camera_list + " %}{% set ns=namespace(ok=0,total=0) %}{% for e in es %}{% set d=device_id(e) %}{% if d and d in op %}{% set ns.total=ns.total+1 %}{% if states(e) not in ['unknown','unavailable'] %}{% set ns.ok=ns.ok+1 %}{% endif %}{% endif %}{% endfor %}{% if ns.total==0 %}grey{% elif ns.ok==ns.total %}green{% elif ns.ok>0 %}orange{% else %}red{% endif %}",
                _nav(manifest, "cameras"),
            ),
            _chip(
                "{% set s=states('" + weather + "') %}{% set m={'sunny':'Ясно','clear-night':'Ясно','partlycloudy':'Переменная облачность','cloudy':'Облачно','rainy':'Дождь','pouring':'Ливень','snowy':'Снег','fog':'Туман','windy':'Ветрено','lightning':'Гроза','lightning-rainy':'Гроза с дождём'} %}{% set t=state_attr('" + weather + "','temperature') %}{% if s in ['unknown','unavailable'] %}Погода — нет данных{% elif t is number %}{{ t|round(1) }}° · {{ m.get(s,s) }}{% else %}{{ m.get(s,s) }}{% endif %}",
                "mdi:weather-partly-cloudy",
                "{% if states('" + weather + "') in ['unknown','unavailable'] %}grey{% else %}blue{% endif %}",
                _nav(manifest, "weather"),
                entity=weather,
            ),
        ],
    }

    main = entities["heating_main"]
    reserve = entities["heating_reserve"]
    main_temp = entities.get("heating_main_temp")
    reserve_temp = entities.get("heating_reserve_temp")
    heating_secondary = "{% if is_state('" + main + "','on') %}Основной котёл" + ("{% if is_number(states('" + main_temp + "')) %} · {{ states('" + main_temp + "')|float|round(1) }} °C{% endif %}" if main_temp else "") + "{% elif is_state('" + reserve + "','on') %}Резервный котёл" + ("{% if is_number(states('" + reserve_temp + "')) %} · {{ states('" + reserve_temp + "')|float|round(1) }} °C{% endif %}" if reserve_temp else "") + "{% elif states('" + main + "') in ['unknown','unavailable'] and states('" + reserve + "') in ['unknown','unavailable'] %}Нет данных{% else %}Котлы не активны{% endif %}"

    alarm_683 = entities["car_683_alarm"]
    alarm_130 = entities["car_130_alarm"]
    internet = entities["internet"]
    nav_cards = [
        _nav_card("Помещения", "2 этажа · 18 помещений", "mdi:floor-plan", _nav(manifest, "rooms"), icon_color="blue"),
        _nav_card("Семья", "Люди и присутствие", "mdi:account-group", _nav(manifest, "family"), icon_color="blue"),
        _nav_card("Отопление", heating_secondary, "mdi:radiator", _nav(manifest, "heating"), icon_color="{% if is_state('" + main + "','on') or is_state('" + reserve + "','on') %}orange{% else %}grey{% endif %}"),
        _nav_card("Автомобили", "{% set es=['" + alarm_683 + "','" + alarm_130 + "'] %}{% set ns=namespace(alarm=0,bad=0) %}{% for e in es %}{% if is_state(e,'on') %}{% set ns.alarm=ns.alarm+1 %}{% elif states(e) in ['unknown','unavailable'] %}{% set ns.bad=ns.bad+1 %}{% endif %}{% endfor %}{% if ns.bad==2 %}Нет данных{% elif ns.alarm>0 %}Тревога {{ ns.alarm }}{% else %}Тревог нет{% endif %}", "mdi:car-multiple", _nav(manifest, "cars"), icon_color="{% if is_state('" + alarm_683 + "','on') or is_state('" + alarm_130 + "','on') %}red{% elif states('" + alarm_683 + "') in ['unknown','unavailable'] and states('" + alarm_130 + "') in ['unknown','unavailable'] %}grey{% else %}green{% endif %}"),
        _nav_card("Инфраструктура", "{% if is_state('" + internet + "','on') %}Интернет доступен{% elif is_state('" + internet + "','off') %}Нет доступа в интернет{% else %}Нет данных{% endif %}", "mdi:server-network", _nav(manifest, "infrastructure"), icon_color="{% if is_state('" + internet + "','on') %}green{% elif is_state('" + internet + "','off') %}red{% else %}grey{% endif %}"),
        _nav_card("Действия", "Быстрые команды", "mdi:gesture-tap-button", _nav(manifest, "actions"), icon_color="blue"),
    ]

    return {"type": "grid", "cards": [_heading("Дом сейчас", "mdi:home-heart"), chips_top, chips_activity, chips_context, *nav_cards]}


def _active_events(entities: Mapping[str, str], manifest: Mapping[str, Any]) -> dict[str, Any]:
    openings = _members(entities, "opening_")
    safety = _members(entities, "safety_")
    power = [entities["power_a"], entities["power_b"], entities["power_c"]]
    alarm_683 = entities["car_683_alarm"]
    alarm_130 = entities["car_130_alarm"]
    water = entities["water_drinking"]
    internet = entities["internet"]
    irrigation = entities.get("irrigation_now")

    cards: list[dict[str, Any]] = [_heading("Активные события", "mdi:alert-circle-outline")]
    if irrigation:
        cards.append({
            "type": "conditional",
            "conditions": [{"condition": "state", "entity": irrigation, "state_not": "idle"}],
            "card": {
                "type": "custom:mushroom-template-card",
                "entity": irrigation,
                "primary": "{% set s=states(entity) %}{% set z=state_attr(entity,'active_zone')|int(0) %}{% if s=='watering' %}Автополив · Зона {{ z }}{% elif s=='waiting' %}Автополив · ожидание зоны{% elif s in ['offline','unknown','unavailable'] %}Автополив · нет связи{% else %}Автополив · {{ s }}{% endif %}",
                "secondary": "{% set s=states(entity) %}{% set r=state_attr(entity,'remaining_min')|int(0) %}{% if s=='watering' %}Осталось {{ r }} мин{% elif s=='waiting' %}Есть очередь зон{% else %}Требуется проверка состояния{% endif %}",
                "icon": "mdi:sprinkler-variant",
                "icon_color": "{% if states(entity)=='watering' %}blue{% elif states(entity)=='waiting' %}orange{% else %}red{% endif %}",
                "tap_action": {"action": "navigate", "navigation_path": _nav(manifest, "irrigation")},
                "hold_action": {"action": "more-info"},
                "grid_options": {"columns": 12},
            },
        })

    cards.append({
        "type": "custom:auto-entities",
        "show_empty": False,
        "card": {"type": "grid", "square": False, "columns": 1},
        "card_param": "cards",
        "filter": {
            "template": (
                "{% set op=label_devices('В эксплуатации') %}{% set ns=namespace(cards=[],w=0,d=0,out=0) %}"
                "{% set es=" + _literal(openings) + " %}{% for e in es %}{% set x=device_id(e) %}{% if x and x in op and is_state(e,'on') %}{% if 'sensor_wo_' in e %}{% set ns.w=ns.w+1 %}{% else %}{% set ns.d=ns.d+1 %}{% endif %}{% endif %}{% endfor %}"
                "{% if ns.w+ns.d>0 %}{% set ns.cards=ns.cards+[{'type':'custom:mushroom-template-card','primary':'Открыто ' ~ (ns.w+ns.d),'secondary':'Окна ' ~ ns.w ~ ' · двери/ворота ' ~ ns.d,'icon':'mdi:door-open','icon_color':'yellow','tap_action':{'action':'navigate','navigation_path':'" + _nav(manifest, "safety") + "'},'grid_options':{'columns':12}}] %}{% endif %}"
                "{% set hs=" + _literal(safety) + " %}{% for e in hs %}{% set x=device_id(e) %}{% if x and x in op and is_state(e,'on') %}{% set ns.cards=ns.cards+[{'type':'custom:mushroom-template-card','entity':e,'primary':state_attr(e,'friendly_name') or e,'secondary':'Тревога безопасности','icon':'mdi:alert-circle','icon_color':'red','tap_action':{'action':'more-info'},'hold_action':{'action':'more-info'},'grid_options':{'columns':12}}] %}{% endif %}{% endfor %}"
                "{% set p=states('" + water + "') %}{% if is_number(p) %}{% if p|float==0 %}{% set ns.cards=ns.cards+[{'type':'custom:mushroom-template-card','entity':'" + water + "','primary':'Питьевая вода — нет давления','secondary':'0 бар','icon':'mdi:water-alert','icon_color':'red','tap_action':{'action':'navigate','navigation_path':'" + _nav(manifest, "water") + "'},'hold_action':{'action':'more-info'},'grid_options':{'columns':12}}] %}{% elif p|float<2.4 or p|float>3.6 %}{% set ns.cards=ns.cards+[{'type':'custom:mushroom-template-card','entity':'" + water + "','primary':'Питьевая вода — отклонение','secondary':p ~ ' бар','icon':'mdi:water-alert-outline','icon_color':'orange','tap_action':{'action':'navigate','navigation_path':'" + _nav(manifest, "water") + "'},'hold_action':{'action':'more-info'},'grid_options':{'columns':12}}] %}{% endif %}{% endif %}"
                "{% set pe=namespace(v=[],bad=0) %}{% for e in " + _literal(power) + " %}{% if is_number(states(e)) %}{% set pe.v=pe.v+[states(e)|float] %}{% else %}{% set pe.bad=pe.bad+1 %}{% endif %}{% endfor %}{% if pe.bad==0 and pe.v|count==3 %}{% if (pe.v|min)<125 or (pe.v|max)>275 %}{% set ns.cards=ns.cards+[{'type':'custom:mushroom-template-card','primary':'Электросеть дома — авария','secondary':'Вне рабочего диапазона стабилизаторов','icon':'mdi:home-lightning-bolt','icon_color':'red','tap_action':{'action':'navigate','navigation_path':'" + _nav(manifest, "electricity") + "'},'grid_options':{'columns':12}}] %}{% elif (pe.v|min)<150 or (pe.v|max)>265 %}{% set ns.cards=ns.cards+[{'type':'custom:mushroom-template-card','primary':'Электросеть дома — рабочий предел','secondary':'Проверить входное напряжение','icon':'mdi:home-lightning-bolt-outline','icon_color':'orange','tap_action':{'action':'navigate','navigation_path':'" + _nav(manifest, "electricity") + "'},'grid_options':{'columns':12}}] %}{% endif %}{% endif %}"
                "{% for e,n in [('" + alarm_683 + "','683-й — тревога'),('" + alarm_130 + "','130-й — тревога')] %}{% if is_state(e,'on') %}{% set ns.cards=ns.cards+[{'type':'custom:mushroom-template-card','entity':e,'primary':n,'secondary':'Сигнализация','icon':'mdi:car-emergency','icon_color':'red','tap_action':{'action':'more-info'},'hold_action':{'action':'more-info'},'grid_options':{'columns':12}}] %}{% endif %}{% endfor %}"
                "{% if is_state('" + internet + "','off') %}{% set ns.cards=ns.cards+[{'type':'custom:mushroom-template-card','entity':'" + internet + "','primary':'Интернет — нет связи','secondary':'Проверить подключение','icon':'mdi:wan-off','icon_color':'red','tap_action':{'action':'navigate','navigation_path':'" + _nav(manifest, "network") + "'},'hold_action':{'action':'more-info'},'grid_options':{'columns':12}}] %}{% endif %}{{ ns.cards }}"
            )
        },
        "grid_options": {"columns": "full"},
    })

    cards.append({
        "type": "custom:auto-entities",
        "show_empty": False,
        "card": {"type": "vertical-stack"},
        "card_param": "cards",
        "filter": {
            "template": "{% set s=label_devices('На обслуживании')|count %}{% set r=label_devices('Требует замены')|count %}{% if s+r>0 %}{{ [{'type':'custom:mushroom-template-card','primary':'Оборудование требует внимания','secondary':('На обслуживании ' ~ s ~ ' · замена ' ~ r),'icon':'mdi:tools','icon_color':('orange' if r>0 else 'yellow'),'badge_icon':'mdi:chevron-right','badge_color':'grey','tap_action':{'action':'navigate','navigation_path':'" + _nav(manifest, "equipment") + "'}}] }}{% else %}{{ [] }}{% endif %}"
        },
        "grid_options": {"columns": "full"},
    })

    # UPS events are deliberately summary-only here. Detailed telemetry belongs to the UPS panel.
    for prefix, title in (("ups_internet_", "UPS Интернет"), ("ups_boiler_", "UPS Котёл")):
        stale = entities.get(prefix + "stale")
        on_battery = entities.get(prefix + "on_battery")
        cloud = entities.get(prefix + "cloud")
        if not stale or not on_battery or not cloud:
            continue
        cards.append({
            "type": "custom:auto-entities",
            "show_empty": False,
            "card": {"type": "vertical-stack"},
            "card_param": "cards",
            "filter": {
                "template": "{% set stale=states('" + stale + "') %}{% set batt=states('" + on_battery + "') %}{% set cloud=states('" + cloud + "') %}{% if stale!='off' or cloud!='on' or batt=='on' %}{% set p='" + title + " — ' ~ ('Работа от АКБ' if batt=='on' else 'Нет актуальных данных') %}{{ [{'type':'custom:mushroom-template-card','primary':p,'secondary':('Проверить источник данных' if batt!='on' else 'Резервное питание активно'),'icon':('mdi:battery-alert-variant-outline' if batt=='on' else 'mdi:cloud-alert-outline'),'icon_color':'orange','tap_action':{'action':'navigate','navigation_path':'" + _nav(manifest, "infrastructure") + "'}}] }}{% else %}{{ [] }}{% endif %}"
            },
            "grid_options": {"columns": "full"},
        })

    return {"type": "grid", "cards": cards}


def _resources(entities: Mapping[str, str], manifest: Mapping[str, Any]) -> dict[str, Any]:
    power = [entities["power_a"], entities["power_b"], entities["power_c"]]
    water = entities["water_drinking"]
    internet = entities["internet"]
    power_list = _literal(power)
    return {
        "type": "grid",
        "cards": [
            _heading("Ресурсы", "mdi:home-lightning-bolt-outline"),
            _nav_card("Электросеть дома", "{% set es=" + power_list + " %}{% set ns=namespace(vals=[],bad=0) %}{% for e in es %}{% if is_number(states(e)) %}{% set ns.vals=ns.vals+[states(e)|float] %}{% else %}{% set ns.bad=ns.bad+1 %}{% endif %}{% endfor %}{% if ns.bad>0 %}Нет данных{% elif (ns.vals|min)<125 or (ns.vals|max)>275 %}Авария{% elif (ns.vals|min)<150 or (ns.vals|max)>265 %}Рабочий предел{% else %}В норме{% endif %}", "mdi:home-lightning-bolt", _nav(manifest, "electricity"), icon_color="{% set es=" + power_list + " %}{% set ns=namespace(vals=[],bad=0) %}{% for e in es %}{% if is_number(states(e)) %}{% set ns.vals=ns.vals+[states(e)|float] %}{% else %}{% set ns.bad=ns.bad+1 %}{% endif %}{% endfor %}{% if ns.bad>0 %}grey{% elif (ns.vals|min)<125 or (ns.vals|max)>275 %}red{% elif (ns.vals|min)<150 or (ns.vals|max)>265 %}orange{% else %}green{% endif %}"),
            _more_info_card(water, "Питьевая вода", "{% set p=states(entity) %}{% if not is_number(p) %}Нет данных{% elif p|float==0 %}Нет давления{% elif p|float>=2.4 and p|float<=3.6 %}{{ p }} бар{% else %}{{ p }} бар · отклонение{% endif %}", "mdi:water", "{% set p=states(entity) %}{% if not is_number(p) %}grey{% elif p|float==0 %}red{% elif p|float>=2.4 and p|float<=3.6 %}green{% else %}orange{% endif %}"),
            _nav_card("Интернет", "{% if is_state('" + internet + "','on') %}Доступен{% elif is_state('" + internet + "','off') %}Нет связи{% else %}Нет данных{% endif %}", "mdi:wan", _nav(manifest, "network"), columns=12, icon_color="{% if is_state('" + internet + "','on') %}green{% elif is_state('" + internet + "','off') %}red{% else %}grey{% endif %}"),
        ],
    }


def _heating(entities: Mapping[str, str], manifest: Mapping[str, Any]) -> dict[str, Any]:
    cards: list[dict[str, Any]] = [_heading("Отопление и ГВС", "mdi:heating-coil")]
    for role, name, icon in (
        ("heating_radiators", "Радиаторы", "mdi:radiator"),
        ("heating_floor", "Тёплый пол", "mdi:heating-coil"),
        ("heating_circulation", "Циркуляция ГВС", "mdi:pump"),
    ):
        cards.append({
            "type": "tile",
            "entity": entities[role],
            "name": name,
            "tap_action": {"action": "more-info"},
            "hold_action": {"action": "more-info"},
            "icon_hold_action": {"action": "more-info"},
            "grid_options": {"columns": 6},
            "icon": icon,
        })
    cards.append({
        "type": "tile",
        "entity": entities["heating_dhw"],
        "name": "ГВС",
        "icon": "mdi:thermometer",
        "tap_action": {"action": "more-info"},
        "hold_action": {"action": "more-info"},
        "icon_hold_action": {"action": "more-info"},
        "grid_options": {"columns": 6},
    })
    for role, name in (("heating_main", "Основной котёл"), ("heating_reserve", "Резервный котёл")):
        entity = entities[role]
        cards.append(_more_info_card(entity, name, "{% if is_state(entity,'on') %}Обогрев{% elif is_state(entity,'off') %}Простой{% else %}Нет данных{% endif %}", "mdi:fire", "{% if is_state(entity,'on') %}red{% elif is_state(entity,'off') %}grey{% else %}orange{% endif %}"))
    cards.append(_nav_card("Подробнее", "Отопление и ГВС", "mdi:arrow-right-circle-outline", _nav(manifest, "heating"), columns=12))
    return {"type": "grid", "cards": cards}


def _cars(entities: Mapping[str, str], manifest: Mapping[str, Any]) -> dict[str, Any]:
    a683, f683 = entities["car_683_alarm"], entities["car_683_fuel"]
    a130, f130 = entities["car_130_alarm"], entities["car_130_fuel"]
    cards: list[dict[str, Any]] = [_heading("Автомобили", "mdi:garage-variant")]
    cards.append(_more_info_card(a683, "683-й — сигнализация", "{% if is_state(entity,'on') %}Тревога{% elif is_state(entity,'off') %}ОК{% else %}Нет данных{% endif %}", "{% if is_state(entity,'on') %}mdi:shield-alert{% elif is_state(entity,'off') %}mdi:shield-check{% else %}mdi:shield-off-outline{% endif %}", "{% if is_state(entity,'on') %}red{% elif is_state(entity,'off') %}green{% else %}grey{% endif %}"))
    cards.append(_more_info_card(f683, "683-й — топливо", "{% set raw=states(entity) %}{% if not is_number(raw) %}Нет данных{% else %}{% set pct=[raw|float*75/23,100]|min %}{% set liters=72*pct/100 %}{{ liters|round(1)|string|replace('.',',') }} л · {{ pct|round(0)|int }}%{% endif %}", "mdi:gas-station", "blue"))
    cards.append(_more_info_card(a130, "130-й — сигнализация", "{% if is_state(entity,'on') %}Тревога{% elif is_state(entity,'off') %}ОК{% else %}Нет данных{% endif %}", "{% if is_state(entity,'on') %}mdi:shield-alert{% elif is_state(entity,'off') %}mdi:shield-check{% else %}mdi:shield-off-outline{% endif %}", "{% if is_state(entity,'on') %}red{% elif is_state(entity,'off') %}green{% else %}grey{% endif %}"))
    cards.append(_more_info_card(f130, "130-й — топливо", "{% set raw=states(entity) %}{% if not is_number(raw) %}Нет данных{% else %}{% set pct=[raw|float*100/57,100]|min %}{% set liters=72*pct/100 %}{{ liters|round(1)|string|replace('.',',') }} л · {{ pct|round(0)|int }}%{% endif %}", "mdi:gas-station", "blue"))
    cards.append(_nav_card("Подробнее", "Автомобили", "mdi:arrow-right-circle-outline", _nav(manifest, "cars"), columns=12))
    return {"type": "grid", "cards": cards}


def _access(entities: Mapping[str, str]) -> dict[str, Any]:
    items = [
        (entities["access_entrance"], "Дверь Входная", "door"),
        (entities["access_tambour"], "Дверь в Тамбур", "door"),
        (entities["access_garage"], "Дверь в Гараж", "door"),
        (entities["access_sectional"], "Ворота секционные", "garage"),
        (entities["access_veranda"], "Дверь на Веранду", "door"),
        (entities["access_garden"], "Дверь в сад", "door"),
    ]
    rendered = repr(items)
    template = "{% set op=label_devices('В эксплуатации') %}{% set items=" + rendered + " %}{% set ns=namespace(cards=[]) %}{% for e,n,k in items %}{% set d=device_id(e) %}{% if d and d in op %}{% set s=states(e) %}{% set secondary=('Открыто' if s=='on' else 'Закрыто' if s=='off' else 'Открывается' if s=='opening' else 'Закрывается' if s=='closing' else 'Нет данных' if s in ['unknown','unavailable'] else 'Неизвестное состояние') %}{% set color=('yellow' if s=='on' else 'grey' if s=='off' else 'blue' if s in ['opening','closing'] else 'red') %}{% set icon=('mdi:garage-open' if k=='garage' and s=='on' else 'mdi:garage' if k=='garage' and s=='off' else 'mdi:garage-alert' if k=='garage' else 'mdi:door-open' if s=='on' else 'mdi:door-closed' if s=='off' else 'mdi:door-alert') %}{% set ns.cards=ns.cards+[{'type':'custom:mushroom-template-card','entity':e,'primary':n,'secondary':secondary,'icon':icon,'icon_color':color,'grid_options':{'columns':6},'tap_action':{'action':'more-info'},'hold_action':{'action':'more-info'}}] %}{% endif %}{% endfor %}{{ ns.cards }}"
    return {
        "type": "grid",
        "cards": [
            _heading("Ключевые точки доступа", "mdi:door"),
            {
                "type": "custom:auto-entities",
                "show_empty": False,
                "card": {"type": "grid", "square": False, "columns": 2},
                "card_param": "cards",
                "filter": {"template": template},
                "grid_options": {"columns": "full"},
            },
        ],
    }


def render_house_dashboard(
    dashboard: dict[str, Any],
    trace: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Transform one validated tiles_v1 manifest into the Home mobile preview."""
    views = dashboard.get("views")
    semantic_views = trace.get("semantics", {}).get("views")
    manifest_views = manifest.get("spec", {}).get("views")
    if not isinstance(views, list) or not isinstance(semantic_views, list) or not isinstance(manifest_views, list):
        raise RenderError("house_home_v1 view metadata missing")
    if len(views) != 1 or len(semantic_views) != 1 or len(manifest_views) != 1:
        raise RenderError("house_home_v1 preview requires exactly one view")
    if manifest_views[0].get("renderer") != HOUSE_RENDERER:
        raise RenderError("house_home_v1 renderer not selected")

    entities = _entity_map(semantic_views[0])
    _required(
        entities,
        "weather",
        "power_a", "power_b", "power_c",
        "water_drinking", "internet",
        "heating_radiators", "heating_floor", "heating_circulation", "heating_dhw",
        "heating_main", "heating_reserve",
        "car_683_alarm", "car_683_fuel", "car_130_alarm", "car_130_fuel",
        "access_entrance", "access_tambour", "access_garage", "access_sectional", "access_veranda", "access_garden",
    )
    for prefix in ("safety_", "opening_", "motion_", "light_", "climate_", "camera_"):
        if not _members(entities, prefix):
            raise RenderError(f"house_home_v1 requires at least one {prefix} role")

    source_view = views[0]
    result_view = {
        "type": "sections",
        "title": source_view.get("title", "Дом"),
        "path": source_view.get("path", "home"),
        "icon": "mdi:home",
        "max_columns": MAX_COLUMNS,
        "dense_section_placement": True,
        "sections": [
            {"type": "grid", "cards": [{**_heading(source_view.get("title", "Дом")), "grid_options": {"columns": "full"}}]},
            _house_now(entities, manifest),
            _active_events(entities, manifest),
            _resources(entities, manifest),
            _heating(entities, manifest),
            _cars(entities, manifest),
            _access(entities),
        ],
    }
    return {"views": [result_view]}


__all__ = ["HOUSE_RENDERER", "_layout_engine_sha256", "render_house_dashboard"]
