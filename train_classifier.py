from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import numpy as np

MODEL_NAME = "distilbert-base-uncased"

# Load your dataset
dataset = load_dataset("csv", data_files="data/training_dataset.csv")

# Split into train/test
dataset = dataset["train"].train_test_split(test_size=0.2, seed=42)

# Tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

def tokenize(batch):
    return tokenizer(batch["text"], truncation=True, padding="max_length", max_length=256)
dataset = dataset.map(tokenize, batched=True)

# Label encoding
labels = sorted(set(dataset["train"]["label"]))
label2id = {l: i for i, l in enumerate(labels)}
id2label = {i: l for l, i in label2id.items()}

def encode_labels(example):
    example["labels"] = label2id[example["label"]]
    return example

dataset = dataset.map(encode_labels)

# Model
model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=len(labels),
    id2label=id2label,
    label2id=label2id,
)

# Metrics
def compute_metrics(pred):
    preds = np.argmax(pred.predictions, axis=1)
    precision, recall, f1, _ = precision_recall_fscore_support(pred.label_ids, preds, average="weighted")
    acc = accuracy_score(pred.label_ids, preds)
    return {"accuracy": acc, "f1": f1, "precision": precision, "recall": recall}

# Training args
training_args = TrainingArguments(
    output_dir="model_output",
    evaluation_strategy="epoch",
    save_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    load_best_model_at_end=True,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
)

trainer.train()
trainer.save_model("trained_clause_classifier")
print("✅ Model saved to trained_clause_classifier/")
