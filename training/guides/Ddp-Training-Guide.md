# README: Running LLM Finetuning in DDP Mode

This guide explains how to run **finetuning** for an LLM model in **Distributed Data Parallel (DDP)** mode with 8 nodes. It also includes setting up **WireGuard VPN** to ensure secure communication between nodes and step-by-step instructions for environment setup, dataset configuration, and model training.

## Table of Contents

1. **Prerequisites**
2. **Environment Setup**
3. **WireGuard VPN Setup**
4. **Dataset Configuration**
5. **Understanding the Training Command**
6. **Running the Training**
7. **Example Configurations**
8. **Troubleshooting**

---

## 1. Prerequisites

Before proceeding, ensure you have:

- **x nodes** (where x > 1)(servers or VMs) with GPUs and PyTorch installed.
- **WireGuard** installed for secure communication between nodes.
- Python 3.11 and necessary libraries installed.
- Internet access for downloading model checkpoints and packages.
- Basic understanding of SSH and Linux commands.

---

## 2. Environment Setup

Before configuring WireGuard and training the model, set up your Python environment and install required dependencies.

### Step 1: Create and Activate a Virtual Environment

On **each node**, run the following commands:

```bash
python -m venv myenv
source ./myenv/bin/activate
```

### Step 2: Upgrade Pip

```bash
pip install --upgrade pip
```

### Step 3: Clone LLaMA-Factory Repository and Install Dependencies

```bash
git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git
cd LLaMA-Factory
pip install -e ".[torch,metrics]"
pip install wheel
pip install flash-attn
```

### Step 4: Authenticate with Hugging Face

```bash
huggingface-cli login --token hf_xxxxx # with your own token
```

---

## 3. WireGuard VPN Setup

To ensure secure communication between nodes, configure **WireGuard** VPN.

### Install WireGuard on Each Node

```bash
sudo dnf install -y wireguard-tools
```

### Generate Keys

On **each node**, generate the WireGuard private and public keys:

```bash
wg genkey | tee wg_private.key | wg pubkey > wg_public.key
```

- `wg_private.key` is the **private key**.
- `wg_public.key` is the **public key**.

### Configuration File

On each node, create a WireGuard configuration file (`wg0.conf`) in the `/etc/wireguard/` directory.

#### Example Configuration for Node 1 (MASTER NODE)

**File:** `/etc/wireguard/wg0.conf`

```ini
[Interface]
PrivateKey = cM9k9qPZsilyGIEZaQ2QyMjAHpuqxT9CSlMTVwdqV2o=
Address = 10.0.100.1/24
ListenPort = 58895

[Peer]
PublicKey = MVZj7koElYLPeybOevsaP0ELI+CiCwrarHaa3kNgU1U=
AllowedIPs = 10.0.100.2/32
Endpoint = 3.18.238.55:58895
PersistentKeepalive = 25
```

Repeat this process for all 8 nodes, changing `PrivateKey`, `Address`, and peer configurations accordingly.

### Start WireGuard

```bash
sudo wg-quick up wg0
```

Verify it is running:

```bash
sudo wg show
```

---

## 4. Dataset Configuration

Modify the dataset file `data/dataset.json` in the **LLaMA-Factory** directory.

### Add the following dataset entry for your sepecific dataset details:

```json
"ecogotest": {
    "hf_hub_url": "oodeh/eco-gotest-TAG",
    "columns": {
      "prompt": "input_text",
      "response": "output_text",
      "system": "system"
    }
  }
```

This ensures the correct dataset is loaded during training.

---

## 5. Understanding the Training Command

The training command uses **torchrun** in DDP mode to distribute training across nodes.

### Training Command

```bash
NCCL_DEBUG=INFO NCCL_SOCKET_IFNAME=wg0 FORCE_TORCHRUN=1 \
NNODES=8 NODE_RANK=7 MASTER_ADDR=10.0.100.1 MASTER_PORT=58895 \
llamafactory-cli train     \
--stage sft     \
--do_train True     \
--model_name_or_path meta-llama/Llama-3.2-3B-Instruct     \
--preprocessing_num_workers 16     \
--finetuning_type lora     \
--template llama3     \
--flash_attn fa2     \
--dataset_dir data     \
--dataset ecogotest    \
--cutoff_len 8192     \
--learning_rate 5e-05     \
--num_train_epochs 25.0     \
--max_samples 100000     \
--per_device_train_batch_size 1     \
--gradient_accumulation_steps 32     \
--lr_scheduler_type cosine     \
--max_grad_norm 1.0     \
--logging_steps 5     \
--save_steps 126     \
--warmup_steps 0     \
--packing False     \
--report_to none     \
--output_dir saves/Llama-3.2-3B-Instruct/lora/train_2025-01-29    \
--bf16 True     \
--plot_loss True     \
--trust_remote_code True     \
--ddp_timeout 180000000     \
--optim adamw_torch     \
--lora_rank 16     \
--lora_alpha 16     \
--lora_dropout 0.1     \
--lora_target all \
--disable_gradient_checkpointing
```

---

## 7. Troubleshooting

- **WireGuard Connection Issues:**

   ```bash
   sudo wg show
   sudo wg-quick down wg0 && sudo wg-quick up wg0
   ```

- **NCCL Communication Issues:**

   ```bash
   ping 10.0.100.x
   ```

- **DDP Timeout Issues:**

   ```bash
   Increase --ddp_timeout value
   ```

---

## Conclusion

This guide ensures you can configure and finetune an LLM model in DDP mode securely and efficiently. If any issues arise, refer to the troubleshooting section or recheck your configuration.

