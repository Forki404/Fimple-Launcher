<p align="center">
  <img src="icon.png" width="170" alt="Fimple Launcher">
</p>

<h1 align="center">Fimple Launcher</h1>

<p align="center">
  <b>Современный лаунчер Minecraft Java Edition</b><br>
  Тёмный интерфейс, инстансы, менеджер Java, моды с Modrinth и автообновление.
</p>

<p align="center">
  <a href="https://github.com/Forki404/Fimple-Launcher/releases/latest">
    <img src="https://img.shields.io/badge/%E2%AC%87_%D0%A1%D0%BA%D0%B0%D1%87%D0%B0%D1%82%D1%8C_%D0%BF%D0%BE%D1%81%D0%BB%D0%B5%D0%B4%D0%BD%D0%B8%D0%B9_%D1%80%D0%B5%D0%BB%D0%B8%D0%B7-3b82f6?style=for-the-badge&logo=github&logoColor=white" alt="Скачать последний релиз">
  </a>
  <a href="https://github.com/Forki404/Fimple-Launcher/releases">
    <img src="https://img.shields.io/github/v/release/Forki404/Fimple-Launcher?style=for-the-badge&label=release&color=3b82f6" alt="Latest release">
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/PySide6-6.6%2B-41CD52?style=flat-square&logo=qt&logoColor=white" alt="PySide6 6.6+">
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?style=flat-square&logo=windows&logoColor=white" alt="Windows 10/11">
  <img src="https://img.shields.io/badge/Minecraft-Java_Edition-62B47A?style=flat-square&logo=minecraft&logoColor=white" alt="Minecraft Java Edition">
</p>

> [!CAUTION]
> **Внимание:** Этот репозиторий может быть временным и в дальнейшем может измениться или быть перенесён!

**Fimple Launcher** — это лаунчер для **Minecraft Java Edition**, написанный на **Python** с интерфейсом на **PySide6 (Qt 6)**. Он объединяет установку версий и загрузчиков, управление Java, моды с Modrinth, несколько игровых инстансов и автоматические обновления в одном приложении.

> [!TIP]
> Лаунчер портативный: все данные хранятся в папке `Minecraft` рядом с exe, а обновление не удаляет ваши миры, моды и настройки.

---

## ✨ Возможности

| Возможность | Описание |
| :--- | :--- |
| 🎮 **Инстансы** | Отдельные сборки Minecraft со своими модами, мирами, настройками, Java и статистикой. |
| 🧱 **Загрузчики** | Установка Vanilla, Forge, Fabric и NeoForge прямо из лаунчера. |
| 🧩 **Моды** | Поиск и установка модов через Modrinth, привязка модов к выбранному инстансу. |
| ☕ **Менеджер Java** | Поиск установленных Java, скачивание Temurin JDK 8/17/21/25 и автоматический подбор версии под Minecraft. |
| 👤 **Аккаунты** | Оффлайн-ники и вход через Ely.by. Пароль Ely.by не сохраняется на диске. |
| 🔄 **Автообновление** | Проверка релизов на GitHub, скачивание с прогрессом и обновление с сохранением папки `Minecraft`. |
| 🎨 **Интерфейс** | Тёмная тема, акцентные цвета, анимации, уведомления и переключение RU/EN. |
| 📊 **Статистика** | Время в игре, количество запусков и последняя активность по каждому инстансу. |
| 🪵 **Логи** | Журнал лаунчера и вывод игры в одном разделе. |
| ⚙️ **Настройки** | Оперативная память, JVM-аргументы, размер окна, язык, акцентный цвет и пути. |

> [!NOTE]
> Quilt и OptiFine уже отображаются в интерфейсе, но их установка пока отключена.

---

## 🚀 Скачать

Готовые сборки публикуются на странице **[GitHub Releases](https://github.com/Forki404/Fimple-Launcher/releases)**.

1. Скачайте `Fimple Launcher <XX.XX.XX>.zip` из последнего релиза.
2. Распакуйте архив в любую папку — установка не требуется.
3. Запустите `Fimple Launcher.exe`.
4. При первом запуске лаунчер проверит обновления и наличие подходящей Java.

<p align="center">
  <a href="https://github.com/Forki404/Fimple-Launcher/releases/latest">
    <b>⬇️ Перейти к последнему релизу</b>
  </a>
</p>

Внутри релизного архива:

```text
Fimple Launcher 13.1.1.zip
├── Fimple Launcher.exe
├── icon.ico
├── version.json
└── Minecraft/
    └── authlib-injector-1.2.7.jar
```

---

## 🖥️ Запуск из исходников

### Требования

- **Python 3.10+**
- **pip**
- Интернет для установки зависимостей и загрузки игры, модов и Java
- Windows 10/11 для готовых сборок; из исходников лаунчер запускается и на других ОС с Python и PySide6

### Установка

```bash
git clone https://github.com/Forki404/Fimple-Launcher.git
cd Fimple-Launcher
python -m venv .venv
```

Активируйте виртуальное окружение:

```bash
# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

Установите зависимости и запустите лаунчер:

```bash
python -m pip install -r requirements.txt
python main.py
```

### Флаги запуска

| Флаг | Что делает |
| :--- | :--- |
| `--no-splash` | Сразу открывает главное окно без проверки обновлений и Java |
| `--no-update` | Отключает проверку обновлений |
| `--no-java` | Не предлагает скачать Java |

---

## 🔨 Сборка релиза

Перед сборкой установите зависимости:

```bash
python -m pip install -r requirements.txt
```

Затем запустите:

```bash
python build.py
```

Скрипт:

- спросит версию проекта (по умолчанию возьмёт её из `version.json`);
- соберёт `Fimple Launcher.exe` с иконкой `icon.ico`;
- добавит `version.json`, `icon.ico` и `Minecraft/authlib-injector-1.2.7.jar`;
- упакует всё в `Fimple Launcher <XX.XX.XX>.zip`;
- обновит версию в `version.json`.

Для сборки папкой вместо одного exe:

```bash
python build.py --onedir
```

Если PyInstaller не установлен, `build.py` установит его автоматически. Готовый архив находится в корне проекта, exe — в папке `dist`.

Чтобы выпустить обновление, создайте GitHub Release с тегом вида `v13.1.1` и прикрепите к нему полученный zip.

---

## 🧰 Технологии

| Компонент | Что используется |
| :--- | :--- |
| Язык | Python 3.10+ |
| Интерфейс | PySide6 / Qt 6, кастомный QSS и иконки на QPainter |
| Запуск игры | minecraft-launcher-lib |
| Сеть | requests, GitHub API, Modrinth API v2, Adoptium API, Ely.by |
| Система | psutil для определения объёма памяти |
| Сборка | PyInstaller |

---

## 📁 Структура проекта

```text
main.py                    точка входа, проверка зависимостей и запуск GUI
build.py                   сборка exe и релизного zip
launcher/
  app.py                   инициализация QApplication
  bootstrap.py             экран загрузки: обновления → Java → GUI
  config.py                настройки, переводы, системная память
  paths.py                 пути для исходников и собранной версии
  updater.py               проверка и установка обновлений с GitHub
  java.py                  поиск, проверка и скачивание Java
  instances.py             инстансы, установка версий, запуск игры
  accounts.py              оффлайн-аккаунты и Ely.by
  modrinth.py              клиент Modrinth API
  workers.py               фоновые задачи с прогрессом
  appicon.py               иконка приложения
  ui/
    theme.py               палитра и QSS
    icons.py               векторные иконки
    widgets.py             карточки, кнопки, тосты, бейджи
    dialogs.py             выбор версий, установка, вход Ely.by
    main_window.py         главное окно, сайдбар, горячие клавиши
    pages/                 home, instances, mods, java, logs, settings
assets/README.md           как заменить иконку лаунчера
```

---

## 💾 Где хранятся данные

Всё находится рядом с exe, в папке `Minecraft/`:

```text
Minecraft/
  settings.json
  versions.json
  playtime.json
  authlib-injector-1.2.7.jar
  versions/                    версии Minecraft и загрузчиков
  assets/                      ресурсы игры
  libraries/                   библиотеки
  instances/<id>/              инстансы: моды, миры, конфиги
    mods/
    saves/
    config/
  runtime/java/jdk-NN/         скачанные JDK
  logs/                        логи лаунчера и игры
  cache/
  temp/
```

`versions/`, `assets/` и `libraries/` могут пересоздаваться при обновлении. Папка `instances/` с вашими мирами и модами не затрагивается.

---

## ☕ Какая Java нужна

| Minecraft | Java |
| :--- | :--- |
| 1.21 и новее | **25** (подойдёт и 21) |
| 1.20.5 – 1.20.6 | **21** |
| 1.17 – 1.20.4 | **21** |
| 1.16.5 и старше | **8** |

Лаунчер умеет находить уже установленную Java, скачивать подходящую версию Temurin в `Minecraft/runtime/java` и назначать отдельную Java каждому инстансу.

---

## ⌨️ Горячие клавиши

| Клавиши | Действие |
| :--- | :--- |
| `Ctrl+1` | Главная |
| `Ctrl+2` | Инстансы |
| `Ctrl+3` | Моды |
| `Ctrl+4` | Java |
| `Ctrl+5` | Логи |
| `Ctrl+6` | Настройки |
| `Ctrl+L` | Запустить игру |
| `Ctrl+R` | Обновить списки |
| `Ctrl+Q` | Выход |

---

## 🔄 Автообновление

При запуске лаунчер обращается к [GitHub Releases](https://github.com/Forki404/Fimple-Launcher/releases/latest), сравнивает последнюю версию с `version.json` рядом с exe и, если доступно обновление, показывает размер и список изменений. По кнопке архив скачивается с прогрессом, распаковывается, старые файлы заменяются, а папка `Minecraft` сохраняется.

Для приватного репозитория можно задать переменную окружения `GITHUB_TOKEN` или `GH_TOKEN`.

---

## 🎨 Своя иконка

Положите `icon.ico` рядом с exe — он станет иконкой окна, панели задач и самого приложения. Если файла нет, лаунчер нарисует иконку сам. Подробности — в [`assets/README.md`](assets/README.md).

---

## 🩺 Если что-то не работает

- Проверьте, что установлена подходящая версия Java (см. таблицу выше).
- Загляните в логи: `Minecraft/logs/`.
- Проверьте, что пути к игре и Java указаны в настройках.
- Если проблема повторяется, создайте issue: [GitHub Issues](https://github.com/Forki404/Fimple-Launcher/issues).

---

<p align="center">
  <sub>Fimple Launcher не связан с Mojang Studios или Microsoft. Minecraft — торговая марка Mojang Studios.</sub><br>
  <sub>Сделано с ❤️ для Minecraft Java Edition</sub>
</p>
