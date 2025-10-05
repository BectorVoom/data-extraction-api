# requirements: transformers datasets accelerate torch
# python 3.8+
from datasets import load_dataset
import torch
import torch.nn as nn
from transformers import (
    AutoTokenizer,
    AutoModel,            # ベースを読み込んで自前のヘッドを載せる例
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
)
import numpy as np
from typing import Optional, Dict

MODEL_ID = "tohoku-nlp/bybert-jp-100m"
NUM_LABELS = 2
MAX_LENGTH = 1024  # バイトトークンなので必要に応じて調整

# 1) まずは「簡単パス」を試す（うまくいくならこれでOK）
try:
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_ID,
        num_labels=NUM_LABELS,
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    print("AutoModelForSequenceClassification load OK")
except Exception as e:
    print("AutoModelForSequenceClassification failed:", e)
    model = None
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)

# 2) フォールバック：AutoModel を読み、簡単な分類ヘッドを自作するパス
if model is None:
    base = AutoModel.from_pretrained(MODEL_ID, trust_remote_code=True)
    class ByBertForSequenceClassification(nn.Module):
        def __init__(self, base_model, num_labels):
            super().__init__()
            self.base = base_model
            hidden_size = base_model.config.hidden_size
            self.classifier = nn.Sequential(
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(hidden_size, num_labels),
            )

        def mean_pooling(self, last_hidden_state, attention_mask):
            mask = attention_mask.unsqueeze(-1).to(last_hidden_state.dtype)
            summed = (last_hidden_state * mask).sum(1)
            counts = mask.sum(1).clamp(min=1e-9)
            return summed / counts

        def forward(self, input_ids=None, attention_mask=None, labels=None):
            outputs = self.base(input_ids=input_ids, attention_mask=attention_mask, return_dict=True)
            last_hidden = outputs.last_hidden_state  # (batch, seq_len, hidden)
            pooled = self.mean_pooling(last_hidden, attention_mask)
            logits = self.classifier(pooled)
            loss = None
            if labels is not None:
                if NUM_LABELS == 1:
                    loss_fct = nn.BCEWithLogitsLoss()
                    loss = loss_fct(logits.view(-1), labels.float().view(-1))
                else:
                    loss_fct = nn.CrossEntropyLoss()
                    loss = loss_fct(logits.view(-1, NUM_LABELS), labels.view(-1))
            return {"loss": loss, "logits": logits}

    model = ByBertForSequenceClassification(base, NUM_LABELS)

# 3) データ読み込み（例：Hugging Face datasets の csv を使う想定）
# replace with actual dataset
dataset = load_dataset("csv", data_files={"train": "train.csv", "validation": "valid.csv"})

def preprocess_fn(examples):
    # テキスト列名を 'text' 、ラベル列を 'label' と仮定
    enc = tokenizer(examples["text"], truncation=True, padding="max_length", max_length=MAX_LENGTH)
    enc["labels"] = examples["label"]
    return enc

tokenized = dataset.map(preprocess_fn, batched=True, remove_columns=dataset["train"].column_names)

# 4) Trainer 用の wrapper (model が nn.Module のときは HuggingFace のモデルラッパーが必要)
from transformers import DefaultDataCollator

data_collator = DefaultDataCollator(return_tensors="pt")

def compute_metrics(p):
    preds = p.predictions
    if isinstance(preds, tuple):
        preds = preds[0]
    pred_labels = np.argmax(preds, axis=1)
    acc = (pred_labels == p.label_ids).mean()
    return {"accuracy": acc}

training_args = TrainingArguments(
    output_dir="./bybert-classifier",
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    evaluation_strategy="epoch",
    num_train_epochs=3,
    logging_steps=100,
    save_total_limit=2,
    fp16=False,
)

# If model is a pure nn.Module, create a wrapper huggingface model or use custom Trainer subclass.
# Simpler: if AutoModelForSequenceClassification loaded successfully, use it directly with Trainer.
if isinstance(model, (torch.nn.Module,)) and hasattr(model, "base") and not hasattr(model, "config"):
    # Very simple approach: save & reload via from_pretrained not available — for production, wrap into PreTrainedModel.
    raise RuntimeError("Custom nn.Module wrapper required to use Trainer easily. Prefer AutoModelForSequenceClassification path.")
else:
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )
    trainer.train()
    trainer.save_model("./bybert-finetuned-classifier")
