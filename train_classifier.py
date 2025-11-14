"""
Model training script (Hugging Face Transformers + datasets):
- Loads CSV dataset produced by prepare_dataset.py
- Splits into train/test subsets (80/20)
- Tokenizes text with DistilBERT tokenizer (fixed max_length=256)
- Encodes string labels to integer IDs
- Initializes DistilBERT for sequence classification with dynamic number of labels
- Trains with basic TrainingArguments (3 epochs, evaluation each epoch)
- Computes accuracy, precision, recall, F1 (weighted)
- Saves trained model artifacts to 'trained_clause_classifier/'

Prerequisites:
pip install datasets transformers scikit-learn numpy
"""

from datasets import load_dataset  # Hugging Face datasets loader
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer  # Core transformer components
from sklearn.metrics import accuracy_score, precision_recall_fscore_support  # Evaluation metrics
import numpy as np  # Numerical operations

MODEL_NAME = "distilbert-base-uncased"  # Pretrained base model identifier

# Load dataset from CSV; returns a DatasetDict with a 'train' key by default
dataset = load_dataset("csv", data_files="data/training_dataset.csv")

# Split into train/test partitions (creates new DatasetDict with 'train' and 'test')
dataset = dataset["train"].train_test_split(test_size=0.2, seed=42)

# Initialize tokenizer for chosen model; will produce input_ids, attention_mask
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

def tokenize(batch):
    """
    Tokenize a batch of examples.
    - truncation: ensures sequences don't exceed max_length
    - padding='max_length': uniform tensor shapes for batching
    """
    return tokenizer(batch["text"], truncation=True, padding="max_length", max_length=256)

# Apply tokenization across entire dataset (batched mapping for efficiency)
dataset = dataset.map(tokenize, batched=True)

# Derive consistent label ordering (sorted for reproducibility)
labels = sorted(set(dataset["train"]["label"]))
label2id = {l: i for i, l in enumerate(labels)}  # String label -> integer index
id2label = {i: l for l, i in label2id.items()}   # Integer index -> string label

def encode_labels(example):
    """Add integer label encoding under key 'labels' expected by Trainer."""
    example["labels"] = label2id[example["label"]]
    return example

# Map encoding function over datasets
dataset = dataset.map(encode_labels)

# Instantiate sequence classification model with correct label metadata
model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=len(labels),
    id2label=id2label,
    label2id=label2id,
)

def compute_metrics(pred):
    """
    Compute evaluation metrics after each prediction step.
    - preds: argmax over model logits
    - precision/recall/F1: weighted to account for class imbalance
    - accuracy: overall correctness
    """
    preds = np.argmax(pred.predictions, axis=1)
    precision, recall, f1, _ = precision_recall_fscore_support(pred.label_ids, preds, average="weighted")
    acc = accuracy_score(pred.label_ids, preds)
    return {"accuracy": acc, "f1": f1, "precision": precision, "recall": recall}

# Training configuration (output paths, strategies, hyperparameters)
training_args = TrainingArguments(
    output_dir="model_output",          # Directory for intermediate checkpoints
    evaluation_strategy="epoch",        # Evaluate after each epoch
    save_strategy="epoch",              # Save checkpoint each epoch
    learning_rate=2e-5,                 # Typical fine-tuning LR for transformers
    per_device_train_batch_size=8,      # Training batch size
    per_device_eval_batch_size=8,       # Evaluation batch size
    num_train_epochs=3,                 # Total epochs
    weight_decay=0.01,                  # Regularization
    load_best_model_at_end=True,        # Restores best checkpoint (based on metric)
)

# Trainer orchestrates the training loop
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
)

# Execute training process
trainer.train()
trainer.save_model("trained_clause_classifier")  # Persist final model & tokenizer config
print("✅ Model saved to trained_clause_classifier/")  # Confirmation output