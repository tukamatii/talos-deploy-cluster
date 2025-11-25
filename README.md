## Talos Kubernetes Cluster Deployment Role (Production-Grade Documentation)

### 1. Введение

Ansible-роль `talos_deploy_cluster` автоматизирует развертывание production-ready кластера Kubernetes на базе [Talos Linux](https://www.talos.dev/). Роль выполняет:  
✅ Создание ВМ в VMware vCenter с embedded конфигурацией Talos через vApp properties  
✅ Настройку controlplane/worker/infra нод  
✅ Автоматическую инициализацию кластера (включая bootstrap etcd)  
✅ Применение аддонов для расширения функциональности (CNI, CSI, CPI и др.)  
✅ Интеграцию с enterprise-инфраструктурой (CA-сертификаты, DNS, NTP)

**Ключевые преимущества:**

- **Immutable infrastructure:** Полная идемпотентность через declarative конфигурацию Talos.
- **Zero-touch bootstrap:** Автоматическая инициализация кластера без ручного вмешательства.
- **Addons as Code:** Гибкое управление расширениями через Git-репозитории.
- **Enterprise-ready:** Поддержка корпоративных CA, VLAN, шаблонов ВМ vCenter.

---

### 2. Требования

#### 2.1. Предварительные условия

| Компонент              | Версия/Требование   | Примечание                                                    |
| ---------------------- | ------------------- | ------------------------------------------------------------- |
| Ansible Control Node   | >= 2.12             | Python >= 3.8                                                 |
| VMware vCenter         | 7.0+                | API-доступ для пользователя `svc-ansible-vcenter`             |
| Talos Template         | talos_01 (пример)   | Шаблон ВМ с предустановленным Talos Linux (без конфигурации)  |
| Сетевая инфраструктура | Настроенная vSwitch | Сеть для нод (pg-vlan61-Baran в примере)                      |
| Git Access             | SSH-ключ в CI/CD    | Для клонирования репозиториев с аддонами (gitlab.okbtsp.corp) |

#### 2.2. Зависимости Ansible Collections

```bash
ansible-galaxy collection install vmware.vmware_rest community.vmware kubernetes.core
```

---

### 3. Переменные

#### 3.1. Обязательные переменные

| Имя переменной                | Описание                                      | Пример значения                                |
| ----------------------------- | --------------------------------------------- | ---------------------------------------------- |
| `talos_controlplane_endpoint` | Адрес API-сервера Kubernetes (с портом 6443)  | `https://talos-cluster-test.okbtsp.corp:6443`  |
| `talos_controlplane_dns`      | DNS-имя controlplane для SAN-сертификатов     | `talos-cluster-test.okbtsp.corp`               |
| `s1_vcenter_parent_folder`    | Путь к папке в vCenter (начиная с Datacenter) | `rp-INFRA/rp-OIT-for-Employee/rp-a.baran/TEST` |
| `s1_vm_network_name`          | Имя порт-группы vSphere для подключения нод   | `pg-vlan61-Baran`                              |
| `s1_vms_template`             | Имя шаблона ВМ в vCenter                      | `talos_01`                                     |
| `talos_node_type`             | Тип ноды (`controlplane`, `worker`, `infra`)  | `controlplane` (настраивается на уровне хоста) |

#### 3.2. Критически важные опциональные переменные

| Имя переменной                       | Значение по умолчанию                       | Описание                                              |
| ------------------------------------ | ------------------------------------------- | ----------------------------------------------------- |
| `talos_cluster_name`                 | `talos-cluster`                             | Имя кластера в Talos config                           |
| `talos_additional_cert_sans`         | `[]`                                        | Дополнительные SAN для TLS-сертификатов (IP/DNS)      |
| `s1_vms_disk`                        | `[ { datastore: "default", size_gb: 20 } ]` | Список дисков для ВМ (поддержка нескольких дисков)    |
| `talos_cp_machine_additional_config` | `{}`                                        | Доп. настройки для controlplane (пример: NTP-серверы) |
| `talos_wk_machine_additional_config` | `{}`                                        | Доп. настройки для worker/infra нод                   |

#### 3.3. Переменные vCenter (групповые)

| Имя переменной          | Обязательная | Пример значения                     |
| ----------------------- | ------------ | ----------------------------------- |
| `s1_vcenter_hostname`   | Да           | `vcenter-01.infra.corp`             |
| `s1_vcenter_username`   | Да           | `svc-ansible-vcenter`               |
| `s1_vcenter_password`   | Да           | `!vault ...` (хранить в Vault!)     |
| `s1_vcenter_datacenter` | Нет          | `Datacenter`                        |
| `s1_vms_hardware`       | Нет          | `{ memory_mb: 16384, num_cpus: 8 }` |

> **Важно:** Пароли и секреты **обязательно** шифруются через `ansible-vault`.

---

### 4. Примеры использования

#### 4.1. Инвентарь (группа `talos-cluster-test`)

```yaml
# inventory/talos.yml
talos-cluster-test:
  hosts:
    talos-test-01:
      s1_ip_addr: "10.10.61.61/24"
      talos_node_type: controlplane
    talos-test-21:
      talos_node_type: worker
  vars:
    s1_vcenter_parent_folder: "rp-INFRA/rp-OIT-for-Employee/rp-a.baran/TEST"
    s1_vm_network_name: pg-vlan61-Baran
    s1_vms_template: "talos_01"
    s1_vms_disk:
      - datastore: "stvm-vSanDadastore-Backup"
        size_gb: 30
    s1_vms_hardware:
      memory_mb: 16384
      num_cpus: 8
```

#### 4.2. Групповые переменные

```yaml
# group_vars/talos-cluster-test/talos.yml
talos_controlplane_endpoint: "https://talos-cluster-test.okbtsp.corp:6443"
talos_controlplane_dns: "talos-cluster-test.okbtsp.corp"
talos_cluster_name: talos-cluster-test
talos_additional_cert_sans:
  - "10.10.61.49"
```

```yaml
# group_vars/talos-cluster-test/talos-addons.yml
talos_addons_repositories:
  - url: ssh://git@gitlab.okbtsp.corp:2222/oit/k8s/talos-cilium.git
    k8s_manifests_dir: manifests-to-apply
  - url: ssh://git@gitlab.okbtsp.corp:2222/oit/k8s/talos-vmware-csi.git
    k8s_manifests_dir: manifests-to-apply
```

#### 4.3. Плейбук

```yaml
# playbooks/talos-deploy-cluster.yml
- hosts: talos-cluster-test
  connection: local
  gather_facts: false
  any_errors_fatal: true
  roles:
    - role: talos_deploy_cluster
      vars:
        talos_addons_clone: true # true = клонировать репозитории аддонов
```

**Запуск:**

```bash
ansible-playbook playbooks/talos-deploy-cluster.yml \
  -i inventory/talos.yml \
  --vault-password-file ~/.vault_pass
```

---

### 5. Логика работы с аддонами

Аддоны — это компоненты, расширяющие функционал кластера (CNI, CSI, мониторинг и т.д.). Роль управляет ими через GitOps-подход.

#### 5.1. Структура репозитория аддона

```
talos-cilium/
├── manifests-to-apply/    # Директория с Kubernetes-манифестами (обязательно)
│   ├── cilium.yaml
│   └── crds.yaml
├── ansible/
│   ├── pre_tasks.yml      # Задачи до применения манифестов (опционально)
│   ├── wait_tasks.yml     # Проверки после применения (опционально)
│   └── test-cluster.yml   # Переменные для конкретного кластера (опционально)
└── README.md
```

#### 5.2. Алгоритм применения аддонов

1. **Клонирование репозиториев**:

   - Репозитории клонируются в `/root/talos-addons` на control ноде.
   - Управление через `talos_addons_clone: true/false` (полезно для отладки).

2. **Подготовка манифестов**:

   - Все `.yaml`/`.yml` файлы из `k8s_manifests_dir` рендерятся как Jinja2-шаблоны.
   - Результат сохраняется в `/root/talos-addons/rendered_k8s/<repo_name>/`.

3. **Применение манифестов**:

   - Файлы применяются в алфавитном порядке с задержкой 30 сек между ними (для корректной инициализации зависимостей).
   - Используется `kubernetes.core.k8s` модуль с локальным kubeconfig.

4. **Пост-задачи**:
   - Выполняются задачи из `ansible/wait_tasks.yml` для проверки readiness аддона (пример: ожидание запуска Cilium pods).

#### 5.3. Особенности

- **Idempotency**: Повторный запуск не вызывает ошибок (Kubernetes-манифесты идемпотентны).
- **Изоляция**: Каждый аддон обрабатывается в изолированной директории.
- **Отладка**:
  - Все рендеренные манифесты сохраняются в `/root/talos-addons/rendered_k8s/`.
  - При `talos_addons_clone: false` используются существующие файлы (удобно для тестирования).

---

### 6. Безопасность

- **Секреты**: Все sensitive-данные (пароли vCenter, TLS-ключи) должны храниться в `ansible-vault`.
- **Talos API**: Доступ защищен mTLS. Kubeconfig генерируется только для controlplane endpoint.
- **CA-сертификаты**:
  - Корпоративные CA автоматически добавляются в ноды через `files/trustedcerts.yaml`.
  - Пример CA должен быть заменен на актуальный сертификат вашей инфраструктуры.

---

### 7. Troubleshooting

| Проблема                       | Решение                                                                    |
| ------------------------------ | -------------------------------------------------------------------------- |
| ВМ не появляются в vCenter     | Проверить права `svc-ansible-vcenter`, шаблон `talos_01`, путь к папке     |
| Talos нода не инициализируется | Проверить логи через `talosctl logs -n <IP>`                               |
| Аддоны не применяются          | Убедиться, что репозитории доступны по SSH, проверить рендеринг шаблонов   |
| Проблемы с etcd bootstrap      | Убедиться, что первый controlplane хост указан верно в `groups[target][0]` |

**Ключевые команды для отладки:**

```bash
# Проверить состояние Talos нод
talosctl health -n 10.10.61.61 --talosconfig /root/.talos/talos-cluster-test.yaml

# Просмотреть логи etcd
talosctl logs etcd -n 10.10.61.61 --talosconfig /root/.talos/talos-cluster-test.yaml

# Проверить примененные аддоны
kubectl get pods -n kube-system --kubeconfig /root/.kube/talos-cluster-test.yaml
```
