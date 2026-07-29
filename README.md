# QALab

Набор клиентов и pytest-инструментов для тестирования REST API, Airflow,
OpenShift, внешних систем данных и S3-совместимых объектных хранилищ.

## Установка

```bash
python -m pip install -r requirements.txt
```

Переменные можно хранить в `.env` в корне проекта. Общий
`utils.environment.ConfigEnv` загружает этот файл без перезаписи уже
экспортированных переменных окружения. Конфигурации клиентов собираются в
pytest-фикстурах, а сами клиенты окружение не читают.

## Переменные окружения

### Автозапуск и AI-анализ ошибок

В проект установлен `pytest-triage`. Каждый запуск формирует атомарный
машиночитаемый отчёт `reports/triage.json`; секреты в traceback и логах
редактируются в режиме `strict`. AI-анализ включается средой автозапуска через
стандартную переменную pytest:

```bash
export PYTEST_ADDOPTS="--ai-triage=on --ai-provider=openai"
export OPENAI_API_KEY="..."
pytest
```

Таким образом локальный `pytest` не делает неожиданных сетевых вызовов, а
планировщик или CI включает выбранный provider без изменения тестового кода.
`PYTEST_ADDOPTS` должен быть экспортирован до старта pytest: значение из `.env`
будет загружено `ConfigEnv` уже после разбора аргументов и потому для этой
переменной не подходит. Ключ выбранного provider можно хранить в `.env`.
Для provider нужно установить соответствующий extra:

```bash
python -m pip install "pytest-triage[openai]==0.1.2"
# или pytest-triage[anthropic] / pytest-triage[gigachat]
```

| Provider | Переменные окружения |
| --- | --- |
| OpenAI или OpenAI-compatible | `OPENAI_API_KEY`; опционально `OPENAI_MODEL`, `OPENAI_BASE_URL`, `OPENAI_ORG_ID` |
| Anthropic | `ANTHROPIC_API_KEY` или `ANTHROPIC_AUTH_TOKEN`; опционально `ANTHROPIC_MODEL`, `ANTHROPIC_BASE_URL` |
| GigaChat | `GIGACHAT_CREDENTIALS` или `GIGACHAT_ACCESS_TOKEN`; опционально `GIGACHAT_SCOPE`, `GIGACHAT_MODEL`, `GIGACHAT_CA_BUNDLE_FILE` |

`pytest-triage 0.1.x` не агрегирует падения xdist-workers. Автозапуск, который
должен выполнить итоговый AI-анализ, следует запускать без `-n/--numprocesses`.
Файл `reports/triage.json` является главным артефактом для следующего шага
pipeline и содержит точные pytest-селекторы для перезапуска падений.

### HTTP API, Web UI и Airflow

| Переменная | Обязательность | Назначение |
| --- | --- | --- |
| `API_BASE_URL` | Обязательна для API/Web UI fixtures, если не передан `--base_url` | Хост тестируемого API без схемы, например `jsonplaceholder.typicode.com`. Используется фикстурами `AsyncAPIClient`, `AirflowClient` и Web UI. |

`APIConfig`, `WebUIConfig`, `AsyncAPIClient` и `AirflowClient` при создании
напрямую не читают окружение: protocol, port, TLS, заголовки и аутентификация
передаются через конфигурацию и аргументы конструктора.

### Kerberos для health-check клиента

| Переменная | Обязательность | Назначение |
| --- | --- | --- |
| `KRB_PRINCIPAL` | Опциональна | Kerberos principal. Если задан, session-fixture выполняет `kinit`. |
| `KRB_PASSWORD` | Обязательна только вместе с `KRB_PRINCIPAL` | Пароль principal, передаваемый `kinit` через stdin. |

Для `TrinoConfig`, `ClickHouseConfig`, `SparkConfig` и `GreenPlumConfig`
обязательных переменных окружения нет: адреса, учётные данные и TLS-настройки
передаются в соответствующий dataclass. Kerberos-переменные нужны только для
конфигураций с `kerberos=True`.

### OpenShift / Kubernetes API

| Переменная | Обязательность | Назначение |
| --- | --- | --- |
| `OPENSHIFT_NAMESPACE` | Обязательна для fixture `openshift_config` | Project/namespace, в котором клиент выполняет pod-операции. |
| `OPENSHIFT_AUTH_MODE` | Опциональна, по умолчанию `auto` | Способ загрузки credentials: `auto`, `in_cluster` или `kubeconfig`. |
| `OPENSHIFT_KUBECONFIG` | Опциональна | Явный путь к kubeconfig для этого клиента. |
| `KUBECONFIG` | Опциональна | Стандартная переменная Kubernetes SDK. Используется, если `OPENSHIFT_KUBECONFIG` не задана. |
| `OPENSHIFT_CONTEXT` | Опциональна | Контекст kubeconfig. Без неё используется `current-context`. |
| `OPENSHIFT_VERIFY_SSL` | Опциональна | Переопределяет проверку TLS из kubeconfig/in-cluster конфигурации. |
| `OPENSHIFT_CA_CERT` | Опциональна | Путь к CA certificate. Несовместима с `OPENSHIFT_VERIFY_SSL=false`. |
| `OPENSHIFT_CONNECT_TIMEOUT` | Опциональна, по умолчанию `5` | Таймаут подключения к Kubernetes API в секундах. |
| `OPENSHIFT_READ_TIMEOUT` | Опциональна, по умолчанию `30` | Таймаут чтения одного ответа Kubernetes API. |
| `OPENSHIFT_WAIT_TIMEOUT` | Опциональна, по умолчанию `300` | Общий timeout polling-операций. |
| `OPENSHIFT_POLL_INTERVAL` | Опциональна, по умолчанию `2` | Интервал polling в секундах. |
| `OPENSHIFT_LOG_LIMIT_BYTES` | Опциональна, по умолчанию `1000000` | Максимальный объём ответа при чтении pod logs. |
| `OPENSHIFT_EXEC_TIMEOUT` | Опциональна, по умолчанию `60` | Максимальное время выполнения одной команды внутри контейнера. |
| `OPENSHIFT_EXEC_OUTPUT_LIMIT_BYTES` | Опциональна, по умолчанию `1000000` | Общий лимит `stdout` и `stderr` одной команды в памяти pytest-worker. |

В режиме `auto` явно заданный kubeconfig/context имеет приоритет; без него
клиент сначала пробует service account внутри pod, затем стандартный
kubeconfig. Клиент использует официальный пакет `kubernetes`, не вызывает
`oc`/`kubectl` и не изменяет kubeconfig. Для сценария рестарта service account
или пользователь должен иметь права `get`, `list`, `delete` на `pods`, `get`
на `pods/log` и `create` на `pods/exec`.

### S3

| Переменная | Обязательность | Назначение |
| --- | --- | --- |
| `S3_BUCKET_NAME` | Обязательна для fixture `s3_config` | Bucket, с которым работает клиент. |
| `S3_ENDPOINT_URL` | Опциональна | URL S3-совместимого сервиса, например `http://localhost:9000`. Для AWS S3 не задаётся. |
| `AWS_REGION` | Опциональна | Регион AWS. Имеет приоритет над `AWS_DEFAULT_REGION`. |
| `AWS_DEFAULT_REGION` | Опциональна | Регион AWS, если `AWS_REGION` не задана. |
| `AWS_ACCESS_KEY_ID` | Зависит от способа аутентификации | Access key. Должна задаваться вместе с `AWS_SECRET_ACCESS_KEY`, если не используется profile/IAM role. |
| `AWS_SECRET_ACCESS_KEY` | Зависит от способа аутентификации | Secret key. Должна задаваться вместе с `AWS_ACCESS_KEY_ID`. |
| `AWS_SESSION_TOKEN` | Опциональна | Временный session token; требует обе переменные ключей. |
| `AWS_PROFILE` | Опциональна | Имя профиля из AWS credentials/config. |
| `S3_VERIFY_SSL` | Опциональна, по умолчанию `true` | Проверка TLS. Поддерживаются значения общего `ConfigEnv`: `true/false`, `1/0`, `yes/no`, `on/off`, `y/n`, `t/f`. |
| `AWS_CA_BUNDLE` | Опциональна | Путь к CA bundle для приватного центра сертификации; обрабатывается boto3/botocore. При её использовании оставьте `S3_VERIFY_SSL` незаданной. |
| `S3_ADDRESSING_STYLE` | Опциональна, по умолчанию `auto` | Стиль адресации: `auto`, `path` или `virtual`. Для некоторых MinIO-инсталляций нужен `path`. |
| `S3_CONNECT_TIMEOUT` | Опциональна, по умолчанию `5` | Таймаут установки соединения в секундах. |
| `S3_READ_TIMEOUT` | Опциональна, по умолчанию `30` | Таймаут чтения ответа в секундах. |
| `S3_MAX_ATTEMPTS` | Опциональна, по умолчанию `3` | Общее число попыток, включая первоначальный запрос. |

boto3 продолжает использовать стандартную цепочку провайдеров AWS. Поэтому
статические ключи не нужны при работе через `AWS_PROFILE`, IAM role или другой
поддерживаемый boto3 источник credentials.

Пример `.env` для локального MinIO:

```dotenv
API_BASE_URL=jsonplaceholder.typicode.com

S3_BUCKET_NAME=qa-artifacts
S3_ENDPOINT_URL=http://localhost:9000
AWS_ACCESS_KEY_ID=minio
AWS_SECRET_ACCESS_KEY=change-me
AWS_DEFAULT_REGION=us-east-1
S3_VERIFY_SSL=false
S3_ADDRESSING_STYLE=path
```

## S3-клиент

```python
from src.s3 import S3Client, S3Config

config = S3Config(
    bucket_name="qa-artifacts",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minio",
    aws_secret_access_key="change-me",
)

with S3Client(config) as client:
    uploaded = client.upload_bytes(
        data=b"report",
        object_key="runs/42/report.txt",
        content_type="text/plain",
        metadata={"qa-run-id": "42"},
    )
    stored = client.head_object(
        object_key="runs/42/report.txt",
        version_id=uploaded.version_id,
    )
    assert stored.metadata["qa-run-id"] == "42"

    payload = client.download_bytes(
        object_key="runs/42/report.txt",
        version_id=stored.version_id,
        max_size=1024,
    )
    keys = client.list_keys(prefix="runs/42/")
    url = client.generate_presigned_url(
        object_key="runs/42/report.txt",
        expires_in=900,
    )
```

`object_key` — полное имя объекта внутри bucket. Например, у объекта
`runs/42/report.txt` часть `runs/42/` является prefix, а `report.txt` — именем.
В boto3 upload/download это единое поле `Key`; отдельный параметр `Prefix`
используется только при list-операциях.

`head_object()` возвращает типизированные метаданные, необходимые
интеграционным тестам: размер, `ETag`, `VersionId`, `ContentType`,
пользовательскую metadata, checksum, время изменения и request ID.
`upload_bytes()` и `delete_object()` также возвращают типизированные результаты.
Параметр `max_size` у `download_bytes()` ограничивает потребление памяти
pytest-worker. Для больших объектов следует использовать `download_file()`;
через его `extra_args` можно передать, например, `VersionId`.

В корневом `conftest.py` уже есть function-scoped fixture `s3_client` с таким
lifecycle; неизменяемый `s3_config` имеет session scope:

```python
def test_report_is_uploaded(s3_client):
    assert s3_client.object_exists(object_key="runs/42/report.txt")
```

Для fixture другого scope используется тот же контекстный менеджер:

```python
import pytest

from src.s3 import S3Client


@pytest.fixture
def isolated_s3_client(s3_config):
    with S3Client(s3_config) as client:
        yield client
```

`close()` идемпотентен. Клиент закрывает только boto3-транспорт, созданный своей
фабрикой; внедрённый через `service=` fake или общий транспорт остаётся во
владении вызывающего кода. После выхода из контекста объект `S3Client` больше не
принимает операции.

Контекстный менеджер не удаляет объекты. Уникальные имена DAG, учёт созданных
ключей и политика cleanup относятся к pytest-фикстурам конкретного сценария.
Для versioned bucket fixture может передать сохранённый `VersionId` в
`delete_object()`, чтобы удалить именно созданную тестом версию.

`S3Client` принимает внедряемые `S3Service` или `S3ServiceFactory`, поэтому
unit-тесты могут подменять boto3 без сети и реального bucket. Ошибки и логи
имеют стабильные поля `operation`, `target`, `cause_type`, `error_code`,
`http_status` и `request_id`: `pytest-triage` получает диагностический контекст
без payload, credentials и presigned URL.

## OpenShift-клиент

```python
from src.openshift import OpenShiftClient, OpenShiftConfig

config = OpenShiftConfig(
    namespace="airflow",
    auth_mode="kubeconfig",
    kubeconfig_path="/path/to/kubeconfig",
    context="qa",
)

name_pattern = "airflow-webserver-*"

with OpenShiftClient(config) as client:
    webserver = client.find_pod(name_pattern)

    restarted = client.restart_pod_by_pattern(
        name_pattern,
    )

    assert restarted.replacement.ready
    assert restarted.replacement.uid != restarted.previous.uid
```

Точное имя pod не является переменной окружения. `find_pod()` получает список
pod только из `OPENSHIFT_NAMESPACE` и применяет к имени case-sensitive glob:
`*`, `?` и диапазоны `[...]`. Поэтому паттерн `airflow-webserver-*` продолжает
работать после смены генерируемого суффикса. Поиск выполняется на стороне
клиента, так как Kubernetes field selector не поддерживает glob по имени.

`find_pod()` выбирает ровно один `Ready` pod. При нуле или нескольких
совпадениях он выбрасывает `OpenShiftPodSelectionError` и не выбирает случайный
экземпляр. `find_pods()` возвращает все совпадения, если множественный результат
нужен самому тесту. Когда у workload есть стабильные labels, паттерн лучше
дополнительно сузить серверным selector:

```python
webserver = openshift_client.find_pod(
    "airflow-webserver-*",
    label_selector="app.kubernetes.io/component=webserver",
)
```

Для частых команд внутри Airflow webserver в корневой `conftest.py` добавлена
третья fixture. Она хранит паттерн и container name, а не текущее имя pod:

```python
@pytest.fixture
def web_server(openshift_client):
    return openshift_client.container(
        "airflow-webserver-*",
        container_name="webserver",
    )
```

Перед каждой операцией fixture заново находит единственный `Ready` pod.
Поэтому один объект `web_server` продолжает работать после рестарта и смены
суффикса:

```python
def test_dags_are_visible_in_webserver(web_server):
    version = web_server.exec(
        ("airflow", "version"),
        check=True,
    )
    assert version.stdout.strip()

    dags = web_server.sh(
        "find /opt/airflow/dags -maxdepth 1 -type f -name '*.py'",
        check=True,
        timeout=30,
    )
    assert "example_dag.py" in dags.stdout
```

`exec()` принимает argv-последовательность без shell-интерпретации. Для pipe,
redirect, `&&` и glob shell используется явный `sh()`. Оба метода возвращают
`CommandResult` с `stdout`, `stderr`, `exit_code`, `duration_seconds` и
фактическим именем pod. В container fixture `check=True` используется по
умолчанию: ненулевой exit code немедленно завершает тест
`OpenShiftCommandFailedError`. Для проверки негативного сценария передаётся
`check=False`. Exec не создаёт интерактивный TTY и не поддерживает stdin — это
намеренно детерминированный API для автоматизации.

`restart_pod()` предназначен для pod под управлением Deployment, StatefulSet
или другого контроллера. Неконтролируемый pod удалён не будет. Перед удалением
клиент запоминает UID всех pod, подходящих под selector, добавляет UID
precondition к DELETE и ждёт новый `Ready` pod. Поэтому гонка замены или
существующая соседняя реплика не может дать ложноположительный результат.
`restart_pod_by_pattern()` делает те же проверки и дополнительно принимает
замену только от того же controller UID, которому принадлежал удалённый pod.

Для диагностики доступен ограниченный хвост логов:

```python
logs = openshift_client.read_pod_logs(
    restarted.replacement.name,
    container="webserver",
    tail_lines=500,
)
```

События `openshift.client` пишутся в формате JSON Lines как в stdout, так и в
общий файл логов. Значения сохраняют исходные типы, что удобно для CI и
`pytest-triage`; содержимое pod logs, stdout/stderr команды, её аргументы,
kubeconfig и credentials автоматически в события не попадают:

```json
{"timestamp":"2026-07-29T10:15:30.123+00:00","level":"INFO","logger":"openshift.client","event":"openshift_pod_restarted","namespace":"airflow","previous_pod":"airflow-webserver-old","previous_uid":"uid-old","replacement_pod":"airflow-webserver-new","replacement_uid":"uid-new"}
```

В корневом `conftest.py` находятся session-scoped `openshift_config` и
function-scoped `openshift_client`. Клиент синхронный; его polling всегда
ограничен timeout. Kubernetes API и clock внедряются через узкие protocols,
поэтому unit-тесты не требуют кластера. Assertions, cleanup и проверка Airflow
DAG остаются ответственностью тестового сценария.

В асинхронном тесте с `AirflowClient` синхронный polling нельзя выполнять
непосредственно в event loop:

```python
import asyncio

restarted = await asyncio.to_thread(
    openshift_client.restart_pod_by_pattern,
    "airflow-webserver-*",
)
```
