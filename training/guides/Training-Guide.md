# Training a Model Using LLaMA-Factory

This guide walks you through the steps to fine-tune a model using the `llamafactory-cli train` command. Each parameter is explained in a simple and generic way, so you can adapt it to your specific needs.

## Prerequisites

Before you start, ensure you have the following:
- A Hugging Face account. Sign up at [Hugging Face](https://huggingface.co/) if you don’t have one.
- Python 3.8 or higher installed.
- Tmux installed (optional but recommended for running long commands).
- Sufficient GPU resources for training.

### Log in to Hugging Face CLI
To authenticate with Hugging Face, use the following command and provide your access token:
```bash
huggingface-cli login
```
You can find your access token in your Hugging Face account settings.

## Steps to Set Up and Train the Model

### 1. Clone the Repository
First, clone the repository and install dependencies:
```bash
# Clone the repository
git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git
cd LLaMA-Factory

# Install dependencies
pip install -e ".[torch,metrics]"
```

### 2. Add Dataset Information
Edit the `data/dataset_info.json` file to include your dataset information. For example:
```json
"your_dataset": {
  "hf_hub_url": "your_huggingface_repo",
  "columns": {
    "prompt": "input",
    "response": "output",
    "system": "system"
  }
}
```
Replace `your_dataset`, `your_huggingface_repo`, `input`, `output` and `system` with your dataset name, Hugging Face repository, and column names respectively.
In our case we use the column names `question` and `answer`, so a sataset section will look like the example below:

```json
"mpc_training": {
  "hf_hub_url": "oodeh/mpc_training",
  "columns": {
    "prompt": "question",
    "response": "answer",
    "system": "system"
  }
}
```

### 3. Run Training Command
Use the following command to train the model:
```bash
llamafactory-cli train \
    --stage <stage> \
    --do_train <True/False> \
    --model_name_or_path <model_name> \
    --preprocessing_num_workers <num_workers> \
    --finetuning_type <finetuning_method> \
    --template <template_name> \
    --flash_attn <True/False/auto> \
    --dataset_dir <dataset_directory> \
    --dataset <dataset_name> \
    --cutoff_len <max_token_length> \
    --learning_rate <learning_rate> \
    --num_train_epochs <epochs> \
    --max_samples <max_samples> \
    --per_device_train_batch_size <batch_size> \
    --gradient_accumulation_steps <accumulation_steps> \
    --lr_scheduler_type <scheduler_type> \
    --max_grad_norm <gradient_clipping> \
    --logging_steps <steps> \
    --save_steps <steps> \
    --warmup_steps <steps> \
    --packing <True/False> \
    --report_to <report_type> \
    --output_dir <output_directory> \
    --bf16 <True/False> \
    --plot_loss <True/False> \
    --ddp_timeout <timeout> \
    --optim <optimizer> \
    --lora_rank <rank> \
    --lora_alpha <alpha> \
    --lora_dropout <dropout_rate> \
    --lora_target <target_layers> \
    --disable_gradient_checkpointing <True/False>
```

## Explanation of Parameters

### General Settings
- **`--stage`**: Specifies the training stage (e.g., `sft`, `rlhf`).
- **`--do_train`**: Whether to perform training (`True` or `False`).
- **`--model_name_or_path`**: Path or name of the pre-trained model to fine-tune.

### Preprocessing and Dataset
- **`--preprocessing_num_workers`**: Number of workers for data preprocessing.
- **`--dataset_dir`**: Directory containing the dataset.
- **`--dataset`**: Name of the dataset to use for training.
- **`--cutoff_len`**: Maximum token length for input sequences.

### Training Settings
- **`--learning_rate`**: Learning rate for the optimizer.
- **`--num_train_epochs`**: Number of epochs to train the model.
- **`--max_samples`**: Maximum number of samples to use from the dataset.
- **`--per_device_train_batch_size`**: Batch size for training on each device.
- **`--gradient_accumulation_steps`**: Number of steps to accumulate gradients before updating.
- **`--lr_scheduler_type`**: Learning rate scheduler (e.g., `linear`, `cosine`).
- **`--max_grad_norm`**: Maximum gradient norm for clipping.

### Logging and Checkpoints
- **`--logging_steps`**: Number of steps between logging progress.
- **`--save_steps`**: Number of steps between saving checkpoints.
- **`--warmup_steps`**: Number of warmup steps for the learning rate scheduler.
- **`--report_to`**: Where to log training results (e.g., `none`, `wandb`).
- **`--output_dir`**: Directory to save the trained model.

### Optimization and Performance
- **`--bf16`**: Whether to use 16-bit precision for faster training (`True` or `False`).
- **`--plot_loss`**: Whether to plot the training loss (`True` or `False`).
- **`--ddp_timeout`**: Timeout for distributed training.
- **`--optim`**: Optimizer to use (e.g., `adamw_torch`).

### LoRA Fine-Tuning
- **`--finetuning_type`**: Fine-tuning method (e.g., `lora`).
- **`--lora_rank`**: Rank of the LoRA matrix.
- **`--lora_alpha`**: Scaling factor for LoRA.
- **`--lora_dropout`**: Dropout rate for LoRA layers.
- **`--lora_target`**: Layers to apply LoRA.

### Advanced Settings
- **`--flash_attn`**: Whether to use flash attention for faster training (`True`, `False`, or `auto`).
- **`--packing`**: Whether to pack sequences to improve efficiency (`True` or `False`).
- **`--disable_gradient_checkpointing`**: Disable gradient checkpointing to reduce memory usage (`True` or `False`).

## Example Command
Here’s an example of how the command might look:
```bash
llamafactory-cli train \
    --stage sft \
    --do_train True \
    --model_name_or_path your_model_name \
    --preprocessing_num_workers 8 \
    --finetuning_type lora \
    --template llama3 \
    --flash_attn auto \
    --dataset_dir data \
    --dataset your_dataset \
    --cutoff_len 512 \
    --learning_rate 5e-05 \
    --num_train_epochs 3 \
    --max_samples 100000 \
    --per_device_train_batch_size 4 \
    --gradient_accumulation_steps 8 \
    --lr_scheduler_type cosine \
    --max_grad_norm 1.0 \
    --logging_steps 10 \
    --save_steps 50 \
    --warmup_steps 100 \
    --packing False \
    --report_to none \
    --output_dir output/trained_model \
    --bf16 True \
    --plot_loss True \
    --ddp_timeout 180000 \
    --optim adamw_torch \
    --lora_rank 16 \
    --lora_alpha 16 \
    --lora_dropout 0.1 \
    --lora_target all \
    --disable_gradient_checkpointing False
```

NOTE: it's possible to run the command with a yaml file instead of running the long command, in that case the user needs to fill a yaml file with all relevant fields and run the command

```
llamafactory-cli train <arguments file path>
```
for examples please refer to this [link](https://github.com/hiyouga/LLaMA-Factory/tree/main/examples)

## LLM Training framework and overview session
[Session video](https://drive.google.com/file/d/16FSwz422uMIGqbDvpIL7XWKjPoirT2wN/view)
