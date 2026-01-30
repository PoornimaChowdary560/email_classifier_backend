# backend/ml/ml_loader.py
import os
import joblib
import pickle
import traceback

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
MODELS_DIR = os.path.join(BASE, "ml_models")
MODEL_PATH = os.path.join(MODELS_DIR, "spam_model.pkl")

_model = None
_model_meta = {"name": None}


def _safe_load():
    global _model, _model_meta
    if _model is not None:
        return

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Place spam_model.pkl there.")

    try:
        _model = joblib.load(MODEL_PATH)
    except Exception:
        with open(MODEL_PATH, "rb") as f:
            _model = pickle.load(f)

    _model_meta["name"] = getattr(_model, "__class__", type(_model)).__name__


def predict_text(text: str):
    """
    Run spam/ham classification.
    Returns: (label: str, confidence: float|None, metadata: dict)
    """
    _safe_load()

    try:
        pred = _model.predict([text])
        raw = pred[0]

        # Try probability
        confidence = None
        try:
            proba = _model.predict_proba([text])[0]
            confidence = float(max(proba))
        except Exception:
            pass

        # Normalize label
        if isinstance(raw, (int, float)):
            label = "Spam" if int(raw) == 1 else "Ham"
        else:
            s = str(raw).lower()
            if s in ("1", "spam", "true", "yes"):
                label = "Spam"
            elif s in ("0", "ham", "notspam", "no", "false"):
                label = "Ham"
            else:
                label = str(raw)

        return label, confidence, {"model_name": _model_meta.get("name")}

    except Exception as e:
        traceback.print_exc()
        return "error", None, {"error": str(e)}
