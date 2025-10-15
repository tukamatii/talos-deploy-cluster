# 🚀 Ansible Роль: `talos-deploy-vm`

Эта роль автоматизирует **полный жизненный цикл развертывания кластера Talos Linux в VMware vSphere**, включая создание виртуальных машин (как control plane, так и worker), инициализацию etcd, применение доверенных корневых сертификатов и генерацию клиентских конфигураций (`talosconfig` и `kubeconfig`).

---

## 📋 Требования

- **Ansible ≥ 2.10**
- **Коллекции:**
  - `community.vmware`
  - `vmware.vmware_rest`
- **Утилиты на контроллере:**
  - Доступ к интернету для скачивания `talosctl` (или локальный бинарник)
- **vSphere/vCenter:**
  - Шаблон VM с предустановленным Talos OS
  - Права на создание VM, управление папками и питанием
- **Секреты:**
  - Сгенерированные через `talosctl gen secrets` и `talosctl gen config`
  - Зашифрованы с помощью **Ansible Vault**

---

## 🧩 Основные возможности

✅ Поддержка **многонодовых кластеров** с разделением на **control plane** и **worker**  
✅ Автоматическая установка `talosctl` нужной версии  
✅ Динамическая генерация конфигурации Talos через Jinja2 (`controlplane.yaml.j2` / `worker.yaml.j2`)  
✅ Применение **доверенных корневых сертификатов** после первого старта  
✅ Инициализация etcd **только один раз** (идемпотентность)  
✅ Генерация `talosconfig` с endpoint’ами **только для control plane узлов**  
✅ Полная поддержка **Ansible Vault** для хранения секретов  
✅ Создание изолированной папки в vCenter под кластер

---

## 🛠️ Использование

### 1. Инвентарь с типами узлов

```yaml
# inventory/talos-cluster-test.yml
talos-cluster-test:
  hosts:
    cp-01:
      s1_ip_addr: "10.10.1.11/24"
      talos_node_type: controlplane
    cp-02:
      s1_ip_addr: "10.10.1.12/24"
      talos_node_type: controlplane
    wk-01:
      s1_ip_addr: "10.10.1.21/24"
      talos_node_type: worker
```

> ⚠️ Переменная `talos_node_type` обязательна и определяет, какой шаблон (`controlplane.yaml.j2` или `worker.yaml.j2`) будет использован.

### 2. Групповые переменные

```yaml
# group_vars/talos-cluster-test/talos.yml
target: "talos-cluster-test"
talos_cluster_name: "talos-cluster-test"
talos_interface_vip: "10.10.1.10"
talos_controlplane_endpoint: "https://10.10.1.10:6443"

talos_cp_machine_additional_config:
  registries:
    mirrors:
      docker.io:
        endpoints: ["https://daocloud.io"]

talos_cluster_network:
  cni: { name: none }
  podSubnets: ["10.224.0.0/13"]
  serviceSubnets: ["10.240.0.0/13"]

# Настройки vCenter
s1_vcenter_parent_folder: "/VMs/Talos"
s1_vms_template: "talos-1.11-template"
s1_vm_network_name: "vlan100"
s1_vms_hardware:
  memory_mb: 8192
  num_cpus: 4
```

### 3. Секреты (в Vault)

```yaml
# group_vars/talos-cluster-test/secrets.yml (зашифрован)
talos_secrets: { ... } # из `talosctl gen secrets`
talos_client: { ... } # из `talosctl gen config`
s1_vcenter_username: "user@vsphere.local"
s1_vcenter_password: "supersecret"
```

Зашифруйте:

```bash
ansible-vault encrypt group_vars/talos-cluster-test/secrets.yml
```

### 4. Запуск

```yaml
# playbook.yml
- name: Deploy Talos Cluster in vSphere
  hosts: "{{ target }}"
  gather_facts: false
  roles:
    - talos-deploy-vm
```

Запуск:

```bash
ansible-playbook playbook.yml -e target=talos-cluster-test --ask-vault-pass
```

---

## ⚙️ Ключевые переменные

### vSphere / VM

| Переменная           | Обязательная  | Описание                                                 |
| -------------------- | ------------- | -------------------------------------------------------- |
| `target`             | ✅            | Имя группы хостов (используется для папки и имен файлов) |
| `s1_vms_template`    | ✅            | Имя шаблона Talos в vCenter                              |
| `s1_vm_network_name` | ✅            | Имя сети vSphere                                         |
| `s1_ip_addr`         | ✅ (на хосте) | IP с маской, например `10.10.1.11/24`                    |
| `talos_node_type`    | ✅ (на хосте) | `controlplane` или `worker`                              |

### Talos

| Переменная                           | Описание                                                              |
| ------------------------------------ | --------------------------------------------------------------------- |
| `talos_cp_machine_additional_config` | Доп. настройки **только для control plane** (registries, time и т.д.) |
| `talos_wk_machine_additional_config` | Доп. настройки **для worker** (если нужны)                            |
| `talos_cp_cluster_additional_config` | Inline-манифесты (например, Cilium) — применяются на control plane    |
| `talos_cluster_network`              | Подсети pod/service, CNI                                              |

### Пути и утилиты

| Переменная            | Значение по умолчанию |
| --------------------- | --------------------- |
| `talosctl_version`    | `1.11.2`              |
| `talos_config_folder` | `~/.talos/`           |
| `kube_config_folder`  | `~/.kube/`            |

---

## 🔐 Файл доверенных сертификатов

Роль применяет файл `files/trustedcerts.yaml` (в формате `TrustedRootsConfig`) к каждой ноде после создания:

```yaml
# files/trustedcerts.yaml
apiVersion: v1alpha1
kind: TrustedRootsConfig
name: my-enterprise-ca
certificates: |
  -----BEGIN CERTIFICATE-----
  MIIF... (ваш корневой CA)
  -----END CERTIFICATE-----
```

> Этот шаг выполняется **до** инициализации etcd и позволяет Talos доверять внутренним репозиториям .

---

## 📁 Структура роли

```
talos-deploy-vm/
├── defaults/main.yml          # Настройки vSphere по умолчанию
├── tasks/
│   ├── main.yml               # Основной workflow
│   ├── install_talosctl.yml   # Установка talosctl
│   ├── vm.yml                 # Создание и настройка VM
│   ├── reset_vapp.yml         # Перезагрузка VM (если выключена)
│   └── init_talos.yml         # Bootstrap, kubeconfig, trusted roots
├── templates/
│   ├── controlplane.yaml.j2
│   ├── worker.yaml.j2
│   └── talosconfig.j2
├── files/
│   └── trustedcerts.yaml      # Доверенный CA
└── README.md
```

---

## 💡 Примечания

- Роль **идемпотентна**: повторный запуск не пересоздаст etcd или VM.
- `talosconfig` содержит endpoint’ы **только control plane узлов**, что соответствует best practices.
- Поддерживается **гибкая настройка сети**, времени, реестров и других параметров через `*_additional_config`.
- Все операции с Talos (`bootstrap`, `kubeconfig`, `patch`) выполняются **локально** через `delegate_to: localhost`.
