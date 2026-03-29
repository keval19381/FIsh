import importlib.util
import os


def _load_fish_delivery_app():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.join(root_dir, "artifacts", "fish-delivery", "app.py")
    spec = importlib.util.spec_from_file_location("fish_delivery_app", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_fish_delivery = _load_fish_delivery_app()

try:
    if hasattr(_fish_delivery, "init_db"):
        _fish_delivery.init_db()
except Exception:
    pass

app = _fish_delivery.app
