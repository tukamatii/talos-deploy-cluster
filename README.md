Разумеется\! Вот готовый README на русском языке для вашей Ansible роли, основанный на предоставленных файлах.

# 🚀 Ansible Роль: `talos-deploy-vm`

Эта Ansible роль предназначена для **автоматизированного развертывания виртуальных машин Talos Linux Control Plane в среде VMware vSphere (с использованием vCenter)**, инициализации кластера и генерации необходимых конфигурационных файлов (`talosconfig` и `kubeconfig`).

## 📋 Требования

- **Ansible:** Версия 2.10 или выше.
- **Коллекции Ansible:**
  - `community.vmware`
  - `vmware.vmware_rest`
- **Утилиты на машине-контроллере (localhost):**
  - **`talosctl`**: для инициализации кластера и получения `kubeconfig`. Роль сама скачивает и устанавливает его по умолчанию в `/usr/local/bin/`.
- **vCenter/vSphere:** Доступные учетные данные и настроенный шаблон VM с Talos.
- **Секреты:** Необходимые секреты кластера и клиента, сгенерированные `talosctl gen secrets` и `talosctl gen config`.

---

## 🛠️ Как использовать

### 1\. Подготовка Инвентаря

В вашем инвентаре определите группу (например, `talos-cluster-test`), которая будет соответствовать полю **`target`** в роли, и укажите уникальные переменные для каждого хоста.

**Пример `inventory.yml`:**

```yaml
talos-cluster-test:
  hosts:
    talos-test-01:
      s1_ip_addr: "10.10.1.1/24" # IP-адрес для VM
    talos-test-02:
      s1_ip_addr: "10.10.1.2/24"
    talos-test-03:
      s1_ip_addr: "10.10.1.3/24"
```

### 2\. Определение Переменных Группы

Определите переменные для группы хостов. Их можно разместить в файле `group_vars/<имя_группы>.yml`.

**Пример `group_vars/talos-cluster-test.yml` (Не-секреты):**

```yaml
# --- Основные настройки кластера ---
target: "talos-cluster-test" # Имя группы используется для создания папки в vCenter и имени конфигов
talos_cluster_name: "talos-cluster-test"
talos_interface_vip: "10.10.1.5"
talos_controlplane_endpoint: "https://10.10.1.5:6443"

# --- Настройки для vCenter ---
# ... (Переменные vCenter см. в разделе Defaults) ...

# --- Дополнительные настройки Talos Cluster (опционально) ---
talos_machine_additional_config:
  registries:
    mirrors:
      docker.io:
        endpoints:
          - https://daocloud.io
  time:
    disabled: false
    servers:
      - 8.8.8.8
      - 8.8.4.4

talos_cluster_network:
  cni:
    name: none
  podSubnets:
    - 10.224.0.0/13
  serviceSubnets:
    - 10.240.0.0/13
# ... (и другие talos_cluster_additional_config)
```

### 3\. Обработка Секретов (Vault)

**Секреты должны быть зашифрованы с помощью Ansible Vault.** В них входят:

1.  **Секреты кластера (`talos_secrets`):** Данные из `secrets.yaml`, полученные после `talosctl gen secrets`.
2.  **Сертификаты клиента (`talos_client`):** Данные из `talosconfig`, полученные после `talosctl gen config`.
3.  **Учетные данные vCenter (`s1_vcenter_password`, `s1_vcenter_username`):** В примере пароль находится в `defaults/main.yml` и зашифрован.

**Пример файла с секретами перед шифрованием (например, `group_vars/talos-cluster-test_secrets.yml`):**

```yaml
# Файл: cluster_secrets.yml (для шифрования)
# --- Секреты кластера (talosctl gen secrets) ---
talos_secrets:
  cluster:
    id: "..."
    secret: "..."
  # ... остальные поля из secrets.yaml
  certs:
    etcd:
      crt: "..."
      key: "..."
    # ... остальные certs

# --- Секреты для talosconfig (talosctl gen config) ---
talos_client:
  crt: "..."
  key: "..."
```

**После создания файла зашифруйте его:**

```bash
ansible-vault encrypt group_vars/talos-cluster-test_secrets.yml
```

### 4\. Запуск Роли

Используйте роль в вашем плейбуке, применив ее к вашей целевой группе:

```yaml
---
- name: Deploy Talos Cluster
  hosts: "{{target}}"
  gather_facts: false
  roles:
    - talos-deploy-vm
```

---

## ⚙️ Переменные Роли

Переменные делятся на три категории: **vCenter/VM-Specific**, **Talos Cluster Configuration** и **Talosctl/Kubeconfig Paths**.

### 1\. Переменные для vCenter/VM (Defaults)

Эти переменные обычно устанавливаются в `defaults/main.yml` или переопределяются в `group_vars` или `host_vars`.

| Переменная                      | Где указать           | Стандартное значение                        | Описание                                                                               |
| :------------------------------ | :-------------------- | :------------------------------------------ | :------------------------------------------------------------------------------------- |
| **`s1_vcenter_hostname`**       | Defaults/Group Vars   | `"vcenter.mydomain.com"`                    | Имя хоста vCenter.                                                                     |
| **`s1_vcenter_username`**       | Group Vars/Vault      | `"myuser"`                                  | Имя пользователя vCenter.                                                              |
| **`s1_vcenter_password`**       | Vault                 | **Зашифровано**                             | Пароль пользователя vCenter (должен быть в Vault).                                     |
| **`s1_vcenter_datacenter`**     | Defaults/Group Vars   | `"Datacenter"`                              | Имя датацентра.                                                                        |
| **`s1_vcenter_validate_certs`** | Defaults/Group Vars   | `true`                                      | Проверка сертификатов vCenter.                                                         |
| **`s1_vcenter_parent_folder`**  | Group Vars            | **Нет**                                     | Родительская папка для создания VM-группы (например, `/VMs/Talos`).                    |
| **`s1_vms_cluster`**            | Defaults/Group Vars   | `"Cluster"`                     | Имя кластера vSphere для размещения VM.                                                |
| **`s1_vms_resource_pool`**      | Defaults/Group Vars   | `"rp-vms"`                              | Имя пула ресурсов.                                                                     |
| **`s1_vms_state`**              | Defaults/Group Vars   | `"present"`                                 | Желаемое состояние VM (`present` - создать).                                           |
| **`s1_vms_template`**           | Group Vars            | **Нет**                                     | **Обязательно.** Имя шаблона VM (с установленным Talos OS).                            |
| **`s1_vms_hardware`**           | Defaults/Group Vars   | `(8GB RAM, 4 vCPU)`                         | Параметры железа VM.                                                                   |
| **`s1_vm_network_config`**      | Defaults/Group Vars   | `(vmxnet3, dhcp, name: s1_vm_network_name)` | Конфигурация сетевых адаптеров VM.                                                     |
| **`s1_vm_network_name`**        | Group Vars            | **Нет**                                     | **Обязательно.** Имя vCenter-сети для подключения VM.                                  |
| **`s1_ip_addr`**                | Host Vars             | **Нет**                                     | **Обязательно для хоста.** IP-адрес с маской (`10.10.1.6/24`).                       |
| **`target`**                    | Group Vars/Extra Vars | **Нет**                                     | **Обязательно.** Имя группы хостов (используется для папки в vCenter и имен конфигов). |

### 2\. Переменные конфигурации Talos Cluster (Group Vars)

| Переменная                            | Где указать              | Стандартное значение                   | Описание                                                        |
| :------------------------------------ | :----------------------- | :------------------------------------- | :-------------------------------------------------------------- |
| **`talos_cluster_name`**              | Group Vars               | `"talos-cluster-test"`                 | Имя кластера (используется для имени контекста).                |
| **`talos_interface_vip`**             | Group Vars               | `"10.10.1.5"`                          | Виртуальный IP-адрес для Control Plane.                         |
| **`talos_controlplane_endpoint`**     | Group Vars               | `"https://10.10.1.5:6443"`             | API-эндпоинт кластера.                                          |
| **`talos_secrets`**                   | Vault (Секреты)          | **Зашифровано**                        | Секреты кластера, сгенерированные `talosctl gen secrets`.       |
| **`talos_client`**                    | Vault (Секреты)          | **Зашифровано**                        | Секреты клиента, извлеченные из `talosctl gen config`.          |
| **`talos_machine_additional_config`** | Group Vars (Опционально) | `(Пример: registries, time servers)`   | Дополнительные настройки секции `machine` в конфигурации Talos. |
| **`talos_cluster_network`**           | Group Vars               | `(Пример: podSubnets, serviceSubnets)` | Сетевые настройки кластера (CNI, подсети).                      |
| **`talos_cluster_additional_config`** | Group Vars (Опционально) | `(Пример: inlineManifests для Cilium)` | Дополнительные настройки секции `cluster` в конфигурации Talos. |

### 3\. Переменные Talosctl и пути к конфигам

| Переменная                | Где указать | Стандартное значение        | Описание                                      |
| :------------------------ | :---------- | :-------------------------- | :-------------------------------------------- |
| **`talosctl_version`**    | Defaults    | `"1.11.2"`                  | Версия `talosctl` для скачивания.             |
| **`talosctl_url`**        | Defaults    | _Сформированный URL_        | URL для скачивания бинарника `talosctl`.      |
| **`talosctl_dest`**       | Defaults    | `"/usr/local/bin/talosctl"` | Путь для сохранения `talosctl`.               |
| **`talos_config_folder`** | Defaults    | `~/.talos/`                 | Локальная папка для сохранения `talosconfig`. |
| **`kube_config_folder`**  | Defaults    | `~/.kube/`                  | Локальная папка для сохранения `kubeconfig`.  |
