"""Model registry persistence to Postgres."""

import os
from typing import Optional

from sqlalchemy.orm import Session

from database.models import Stock, ModelRegistry


def _get_stock_id(db: Session, symbol: str) -> Optional[int]:
    s = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    return s.id if s else None


def save_model_binary(
    db: Session,
    symbol: str,
    model_type: str,
    horizon: int,
    model_version: str,
    pkl_path: Optional[str] = None,
    keras_path: Optional[str] = None,
) -> None:
    stock_id = _get_stock_id(db, symbol)
    if stock_id is None:
        return
    pkl_bytes = None
    keras_bytes = None
    if pkl_path and os.path.exists(pkl_path):
        with open(pkl_path, 'rb') as f:
            pkl_bytes = f.read()
    if keras_path and os.path.exists(keras_path):
        with open(keras_path, 'rb') as f:
            keras_bytes = f.read()
    existing = (
        db.query(ModelRegistry)
        .filter(
            ModelRegistry.stock_id == stock_id,
            ModelRegistry.model_type == model_type,
            ModelRegistry.prediction_horizon == horizon,
        )
        .first()
    )
    if existing:
        existing.pkl_data = pkl_bytes or existing.pkl_data
        existing.keras_data = keras_bytes or existing.keras_data
        existing.model_version = model_version
    else:
        db.add(
            ModelRegistry(
                stock_id=stock_id,
                model_type=model_type,
                prediction_horizon=horizon,
                model_version=model_version,
                pkl_data=pkl_bytes,
                keras_data=keras_bytes,
            )
        )
    db.commit()


def restore_model_binary(
    db: Session,
    symbol: str,
    model_type: str,
    horizon: int,
    out_base_path: str,
) -> bool:
    stock_id = _get_stock_id(db, symbol)
    if stock_id is None:
        return False
    rec = (
        db.query(ModelRegistry)
        .filter(
            ModelRegistry.stock_id == stock_id,
            ModelRegistry.model_type == model_type,
            ModelRegistry.prediction_horizon == horizon,
        )
        .first()
    )
    if not rec:
        return False
    restored = False
    if model_type == 'neural_network' and rec.keras_data:
        out_path = out_base_path + '.keras'
        with open(out_path, 'wb') as f:
            f.write(rec.keras_data)
        restored = True
    elif rec.pkl_data:
        out_path = out_base_path + '.pkl'
        with open(out_path, 'wb') as f:
            f.write(rec.pkl_data)
        restored = True
    return restored


